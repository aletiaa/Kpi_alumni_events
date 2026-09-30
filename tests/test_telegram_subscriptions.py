from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.main import app
from app.deps import require_identity
from app.models import (User, TelegramSubscription, TelegramBroadcast,
                        TelegramRecipientDelivery, BotCampaign)
from app.routers.telegram_subscriptions import signer
from app.routers.bots import signer as admin_signer
from app.services import telegram_broadcasts as broadcasts
from app.services.telegram_live import consume_update, TelegramError
from app.services.telegram_subscriptions import subscribe, revoke
from conftest import TestingSessionLocal


def user(db, suffix='1', role='alumni', verified=True):
    row = User(full_name='Test subscriber '+suffix, email=f'tg{suffix}@test.local',
               password_hash='unused', role=role, is_email_verified=verified,
               is_active=True, is_blocked=False)
    db.add(row)
    db.commit()
    return row


def logged_in(row):
    app.dependency_overrides[require_identity] = lambda: SimpleNamespace(
        user_id=row.id, email=row.email, role=row.role, full_name=row.full_name)


def linked(db, row, chat='123', news=True, events=False):
    code = subscribe(db, row, news, events)
    consume_update(db, {'message':{'text':'/start '+code,
        'chat':{'id':int(chat),'type':'private'}, 'from':{'id':int(chat),'username':'ordinary_alumni'}}})
    db.commit()
    return db.get(TelegramSubscription, row.id)


def campaign(db, audience='telegram_alumni', topic='news'):
    item = BotCampaign(body='An alumni announcement', audience=audience, created_by='admin@test.local')
    db.add(item)
    db.flush()
    broadcast = TelegramBroadcast(campaign_id=item.id, topic=topic)
    db.add(broadcast)
    db.commit()
    return item, broadcast


def test_requires_verified_user_consent_topics_csrf(client, db, monkeypatch):
    monkeypatch.setattr('app.routers.telegram_subscriptions.TELEGRAM_ENABLED', True)
    assert client.get('/profile/telegram').status_code == 401
    row = user(db, verified=False)
    logged_in(row)
    assert client.get('/profile/telegram').status_code == 403
    row.is_email_verified = True
    db.commit()
    assert client.get('/profile/telegram').status_code == 200
    assert client.post('/profile/telegram', data={'consent':'yes','news':'on'}).status_code == 403
    data = {'csrf':signer.dumps(row.id), 'news':'on'}
    assert client.post('/profile/telegram', data=data).status_code == 400
    assert client.post('/profile/telegram', data={'csrf':signer.dumps(row.id),'consent':'yes'}).status_code == 400
    data['consent'] = 'yes'
    response = client.post('/profile/telegram', data=data)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    sub = db.get(TelegramSubscription, row.id)
    assert sub.consent_at and sub.news and not sub.events and sub.chat_id is None


def test_non_allowlisted_account_link_unique_stop_and_replay(db):
    first = user(db)
    sub = linked(db, first)
    assert sub.chat_id == '123'
    second = user(db, '2')
    other = linked(db, second)
    assert other.chat_id is None
    consume_update(db, {'message':{'text':'/stop','chat':{'id':123,'type':'private'},
                                 'from':{'id':123,'username':'ordinary_alumni'}}})
    assert sub.revoked_at and sub.chat_id is None and not sub.news


def test_audience_filters_and_duplicate_queue(db):
    alumni = user(db)
    linked(db, alumni)
    linked(db, user(db, '2', role='student'), '124')
    linked(db, user(db, '3'), '125', news=False, events=True)
    disabled = user(db, '4')
    linked(db, disabled, '126')
    disabled.is_blocked = True
    db.commit()
    item, batch = campaign(db)
    broadcasts.queue(db, item, batch)
    broadcasts.queue(db, item, batch)
    rows = db.query(TelegramRecipientDelivery).all()
    assert len(rows) == 1 and rows[0].user_id == alumni.id


@pytest.mark.parametrize('change', ['revoke','block','topic','cancel'])
def test_recheck_before_send(db, monkeypatch, change):
    row = user(db)
    sub = linked(db, row)
    item, batch = campaign(db)
    broadcasts.queue(db, item, batch)
    if change == 'revoke': revoke(sub)
    if change == 'block': row.is_blocked = True
    if change == 'topic': sub.news = False
    if change == 'cancel': broadcasts.cancel(db, item.id)
    db.commit()
    calls = []
    monkeypatch.setattr(broadcasts, 'api', lambda *a, **kw: calls.append(kw))
    broadcasts.deliver_one(TestingSessionLocal)
    db.expire_all()
    assert calls == []
    assert db.get(TelegramRecipientDelivery, (item.id,row.id)).status in {'skipped','cancelled'}


@pytest.mark.parametrize('outcome', ['accepted','unknown','blocked','rate_limited'])
def test_per_recipient_results_no_retries(db, monkeypatch, outcome):
    row = user(db)
    linked(db, row)
    item, batch = campaign(db)
    broadcasts.queue(db, item, batch)
    calls = []
    def send(method, **payload):
        calls.append(payload)
        if outcome != 'accepted': raise TelegramError(outcome)
        return {'message_id':987}
    monkeypatch.setattr(broadcasts, 'api', send)
    broadcasts.deliver_one(TestingSessionLocal)
    broadcasts.deliver_one(TestingSessionLocal)
    db.expire_all()
    delivery = db.get(TelegramRecipientDelivery, (item.id,row.id))
    assert len(calls) == 1 and delivery.status == outcome and delivery.completed_at
    assert delivery.message_id == ('987' if outcome == 'accepted' else None)
    if outcome == 'blocked': assert db.get(TelegramSubscription, row.id).revoked_at


def test_admin_confirmation_and_review(admin_client, db, monkeypatch):
    monkeypatch.setattr('app.routers.bots.TELEGRAM_ENABLED', True)
    linked(db, user(db))
    csrf = admin_signer.dumps('admin@test.local')
    response = admin_client.post('/admin/bots/campaigns', data={'csrf':csrf,
        'body':'News for alumni', 'audience':'telegram_alumni','topic':'news'}, follow_redirects=False)
    assert response.status_code == 303
    url = response.headers['location']
    assert admin_client.get(url).status_code == 200
    assert admin_client.post(url+'/queue', data={'csrf':csrf}).status_code == 400
    assert admin_client.post(url+'/queue', data={'csrf':csrf,'confirm':'yes'}, follow_redirects=False).status_code == 303
    assert admin_client.get(url).status_code == 200
    assert db.query(TelegramRecipientDelivery).count() == 1


def test_unsubscribe_is_owner_scoped(client, db):
    first, second = user(db), user(db,'2')
    linked(db, first)
    linked(db, second,'124')
    logged_in(first)
    assert client.post('/profile/telegram/unsubscribe', data={'csrf':signer.dumps(second.id)}).status_code == 403
    assert client.post('/profile/telegram/unsubscribe', data={'csrf':signer.dumps(first.id)}, follow_redirects=False).status_code == 303
    assert db.get(TelegramSubscription, first.id).revoked_at
    assert db.get(TelegramSubscription, second.id).chat_id == '124'
