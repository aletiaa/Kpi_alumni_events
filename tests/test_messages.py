from types import SimpleNamespace

import pytest

from app.deps import require_identity
from app.models import DirectMessage, User
from app.services.messaging import message_token


def person(db, name, **kwargs):
    values = dict(full_name=name, email=name+'@example.com', password_hash='unused',
                  is_active=True, is_email_verified=True, is_profile_public=True, notifications_enabled=False)
    values.update(kwargs)
    user = User(**values)
    db.add(user)
    db.commit()
    return user


def login(client, user):
    client.app.dependency_overrides[require_identity] = lambda: SimpleNamespace(
        user_id=user.id, full_name=user.full_name, email=user.email, role=user.role)


def send(client, sender, receiver, body='Hello'):
    return client.post(f'/messages/{receiver.id}', data={
        'body':body, 'csrf':message_token(sender.id, receiver.id)}, follow_redirects=False)


def test_guest_cannot_read_search_or_send(client):
    assert client.get('/messages?q=someone').status_code == 401
    assert client.get('/messages/1').status_code == 401
    assert client.post('/messages/1', data={'body':'Hello'}).status_code == 401


def test_different_cohorts_send_reply_inbox_and_read_state(client, db):
    a, b = person(db, 'Alice', group_name='A'), person(db, 'Bob', group_name='B')
    login(client, a)
    assert f'/messages/{b.id}' in client.get('/messages?q=Bob').text
    assert send(client, a, b).status_code == 303
    assert send(client, a, b, 'Second').status_code == 303
    login(client, b)
    inbox = client.get('/messages').text
    assert '>Second</span>' in inbox and '>Hello</span>' not in inbox
    assert '2 <span>непрочитаних</span>' in inbox
    thread = client.get(f'/messages/{a.id}')
    assert thread.status_code == 200 and 'Hello' in thread.text
    db.expire_all()
    assert all(m.is_read for m in db.query(DirectMessage).all())
    assert send(client, b, a, 'Reply').status_code == 303
    login(client, a)
    assert 'Reply' in client.get(f'/messages/{b.id}').text


def test_third_party_cannot_read_or_mark_others_messages(client, db):
    a,b,c = [person(db,name) for name in ['Alice','Bob','Charlie']]
    login(client,a)
    send(client,a,b,'Private secret')
    login(client,c)
    assert 'Private secret' not in client.get(f'/messages/{b.id}').text
    assert 'Private secret' not in client.get('/messages').text
    db.expire_all()
    assert not db.query(DirectMessage).one().is_read


@pytest.mark.parametrize('changes', [{'is_blocked':True},{'is_active':False},{'is_email_verified':False}])
def test_ineligible_accounts_cannot_send_or_receive(client, db, changes):
    a,b = person(db,'Alice'),person(db,'Bob',**changes)
    login(client,a)
    assert send(client,a,b).status_code == 404
    assert 'Bob' not in client.get('/messages').text
    login(client,b)
    assert send(client,b,a).status_code == 403
    assert client.get('/messages').status_code == 403


def test_private_profile_not_discoverable_and_csrf_validation(client, db):
    a,b = person(db,'Alice'),person(db,'Bob',is_profile_public=False)
    login(client,a)
    assert f'href="/messages/{b.id}"' not in client.get('/messages?q=Bob').text
    assert send(client,a,b).status_code == 404
    b.is_profile_public=True
    db.commit()
    assert client.post(f'/messages/{b.id}',data={'body':'Hello'}).status_code == 403
    assert client.post(f'/messages/{b.id}',data={'body':'Hello','csrf':message_token(b.id,a.id)}).status_code == 403
    assert send(client,a,b,'  ').status_code == 400
    assert send(client,a,b,'x'*1001).status_code == 422
    assert send(client,a,a).status_code == 404
    assert db.query(DirectMessage).count() == 0


def test_older_messages_and_html_escape(client, db):
    a,b=person(db,'Alice'),person(db,'Bob')
    db.add_all([DirectMessage(sender_id=a.id,receiver_id=b.id,body=f'Message {i:03d}') for i in range(55)])
    db.commit()
    login(client,b)
    first=client.get(f'/messages/{a.id}').text
    assert 'Message 054' in first and 'Message 000' not in first
    before=db.query(DirectMessage).order_by(DirectMessage.id).offset(5).first().id
    assert 'Message 000' in client.get(f'/messages/{a.id}?before={before}').text
    assert send(client,b,a,'<script>alert(1)</script>').status_code == 303
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in client.get(f'/messages/{a.id}').text
