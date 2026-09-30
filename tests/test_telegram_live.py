from datetime import datetime, timedelta

from app.models import BotCampaign, TelegramLink, TelegramDelivery
from app.services import telegram_live as live
from app.routers.bots import signer


def update(code, username='a_seikaaa', chat_type='private'):
    return {'update_id':1,'message':{'text':'/start '+code,
        'chat':{'id':123,'type':chat_type}, 'from':{'id':123,'username':username}}}


def test_link_requires_one_use_code_and_allowed_private_account(db, monkeypatch):
    monkeypatch.setattr(live, 'TELEGRAM_ALLOWED_USERNAME', 'a_seikaaa')
    code = live.begin_link(db, 'admin@test.local')
    link = db.get(TelegramLink, 'admin@test.local')
    assert code != link.code_hash
    live.consume_update(db, update(code, 'someone_else'))
    live.consume_update(db, update(code, chat_type='group'))
    assert link.chat_id is None
    live.consume_update(db, update(code))
    assert link.chat_id == '123' and link.code_hash is None
    link.chat_id = None
    live.consume_update(db, update(code))
    assert link.chat_id is None


def test_expired_code_and_stop(db, monkeypatch):
    monkeypatch.setattr(live, 'TELEGRAM_ALLOWED_USERNAME', 'a_seikaaa')
    code = live.begin_link(db, 'admin@test.local')
    link = db.get(TelegramLink, 'admin@test.local')
    link.expires_at = datetime.utcnow() - timedelta(seconds=1)
    live.consume_update(db, update(code))
    assert link.chat_id is None
    link.chat_id = '123'
    db.commit()
    stop = update(code)
    stop['message']['text'] = '/stop'
    live.consume_update(db, stop)
    assert link.chat_id is None


def test_real_send_is_deduplicated_and_plaintext(admin_client, db, monkeypatch):
    monkeypatch.setattr('app.routers.bots.TELEGRAM_ENABLED', True)
    db.add(TelegramLink(admin_email='admin@test.local', chat_id='123'))
    campaign = BotCampaign(body='<b>Hello</b>', audience='telegram_self', created_by='admin@test.local')
    db.add(campaign)
    db.commit()
    calls = []
    def fake_api(method, **data):
        calls.append((method, data))
        return {'message_id':42}
    monkeypatch.setattr(live, 'api', fake_api)
    for _ in range(2):
        response = admin_client.post(f'/admin/bots/campaigns/{campaign.id}/send',
            data={'csrf':signer.dumps('admin@test.local')}, follow_redirects=False)
        assert response.status_code == 303
    assert calls == [('sendMessage', {'chat_id':'123','text':'<b>Hello</b>'})]
    assert db.get(TelegramDelivery, campaign.id).status == 'accepted'
    assert db.get(TelegramDelivery, campaign.id).message_id == '42'


def test_unknown_result_not_retried(db, monkeypatch):
    db.add(TelegramLink(admin_email='admin@test.local', chat_id='123'))
    campaign = BotCampaign(body='Hello', audience='telegram_self', created_by='admin@test.local')
    db.add(campaign)
    db.commit()
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise live.TelegramError('unknown')
    monkeypatch.setattr(live, 'api', fail)
    assert live.send_campaign(db, campaign, 'admin@test.local').status == 'unknown'
    live.send_campaign(db, campaign, 'admin@test.local')
    assert len(calls) == 1


def test_send_requires_csrf_and_link(admin_client, db, monkeypatch):
    monkeypatch.setattr('app.routers.bots.TELEGRAM_ENABLED', True)
    campaign = BotCampaign(body='Hello', audience='telegram_self', created_by='admin@test.local')
    db.add(campaign)
    db.commit()
    url = f'/admin/bots/campaigns/{campaign.id}/send'
    assert admin_client.post(url).status_code == 403
    assert admin_client.post(url, data={'csrf':signer.dumps('admin@test.local')}).status_code == 409
    assert db.query(TelegramDelivery).count() == 0
