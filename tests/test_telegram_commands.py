import json
from datetime import datetime, timedelta

from app.models import (User, TelegramSubscription, TelegramBotReply, TelegramUpload,
    TelegramAutomationPreference, TelegramState, Event, Registration, News)
from app.services import telegram_live, telegram_bot_jobs as jobs
from app.services.telegram_commands import dispatch
from app.services.telegram_subscriptions import subscribe, revoke
from app.services.event_registration import register
from conftest import TestingSessionLocal


def update(text='/start', update_id=1, chat_id=123, callback=False):
    sender={'id':chat_id,'language_code':'en','username':'test_alumni'}
    message={'from':sender,'chat':{'id':chat_id,'type':'private'},'text':text}
    if callback:
        return {'update_id':update_id,'callback_query':{'id':str(update_id),'data':text,'from':sender,'message':message}}
    return {'update_id':update_id,'message':message}


def person(db, suffix='1', chat='123'):
    user=User(full_name='Example Alumni', email=f'cmd{suffix}@test.local',password_hash='unused',
              role='alumni',is_active=True,is_blocked=False,is_email_verified=True,preferred_language='en')
    db.add(user)
    db.flush()
    db.add(TelegramSubscription(user_id=user.id,chat_id=chat,consent_at=datetime.utcnow(),news=True,events=True))
    db.commit()
    return user


def event(db, capacity=1):
    item=Event(title='Shared event',description='Details',location='KPI',capacity=capacity,
               start_time=datetime.utcnow()+timedelta(minutes=45))
    db.add(item)
    db.commit()
    return item


def test_plain_start_produces_and_sends_menu_once(db, monkeypatch):
    dispatch(db,update())
    db.commit()
    dispatch(db,update())
    db.commit()
    row=db.get(TelegramBotReply,'update:1')
    assert 'alumni menu' in json.loads(row.payload)['text']
    calls=[]
    monkeypatch.setattr(jobs,'api',lambda method,**payload:calls.append((method,payload)) or {'message_id':1})
    jobs.send_reply(TestingSessionLocal)
    jobs.send_reply(TestingSessionLocal)
    assert len(calls)==1 and calls[0][0]=='sendMessage'
    assert calls[0][1]['reply_markup']['inline_keyboard']


def test_start_link_and_poll_ack_are_atomic(db, monkeypatch):
    user=person(db)
    sub=db.get(TelegramSubscription,user.id)
    revoke(sub)
    db.commit()
    code=subscribe(db,user,True,True)
    calls=[]
    def api(method,**kwargs):
        calls.append(method)
        if method=='getMe':return {'username':'test_bot'}
        if method=='getUpdates':return [update('/start '+code)]
    monkeypatch.setattr(telegram_live,'api',api)
    telegram_live.poll_once(TestingSessionLocal)
    telegram_live.poll_once(TestingSessionLocal)
    db.expire_all()
    assert db.get(TelegramSubscription,user.id).chat_id=='123'
    assert db.get(TelegramState,1).offset==2
    assert db.query(TelegramBotReply).count()==1
    assert 'Profile linked.' in json.loads(db.get(TelegramBotReply,'update:1').payload)['text']


def test_event_buttons_share_capacity_and_registration(db):
    user=person(db)
    second=person(db,'2','124')
    item=event(db)
    dispatch(db,update(f'event:{item.id}',callback=True))
    db.commit()
    assert 'Confirm registration' in db.get(TelegramBotReply,'update:1').payload
    dispatch(db,update(f'join:{item.id}',2,callback=True))
    db.commit()
    assert db.query(Registration).count()==1
    assert register(db,second,item.id)=='full'
    db.commit()
    dispatch(db,update(f'join:{item.id}',2,callback=True))
    db.commit()
    assert db.query(Registration).count()==1
    dispatch(db,update(f'leave:{item.id}',3,callback=True))
    db.commit()
    assert db.query(Registration).count()==0


def test_unlinked_blocked_and_group_cannot_register(db):
    item=event(db)
    dispatch(db,update(f'join:{item.id}',callback=True))
    db.commit()
    assert db.query(Registration).count()==0
    user=person(db)
    user.is_blocked=True
    db.commit()
    dispatch(db,update(f'join:{item.id}',2,callback=True))
    group=update(f'join:{item.id}',3)
    group['message']['chat']['type']='group'
    dispatch(db,group)
    db.commit()
    assert db.query(Registration).count()==0
    assert db.get(TelegramBotReply,'update:3') is None


def test_news_drafts_and_other_users_files_not_exposed(db):
    user=person(db)
    second=person(db,'2','124')
    draft=News(title='Private draft',content='Secret draft content',is_published=False)
    upload=TelegramUpload(user_id=second.id,update_id=99,file_id='private-file-id',kind='document',filename='private.pdf')
    db.add_all([draft,upload])
    db.commit()
    dispatch(db,update(f'article:{draft.id}',callback=True))
    dispatch(db,update(f'file:{upload.id}',2,callback=True))
    db.commit()
    payloads=' '.join(r.payload for r in db.query(TelegramBotReply))
    assert 'Secret draft content' not in payloads and 'private-file-id' not in payloads


def test_upload_saved_once_with_limits(db):
    user=person(db)
    incoming=update('')
    incoming['message']['document']={'file_id':'opaque-id','file_name':'report.pdf','file_size':100}
    dispatch(db,incoming)
    db.commit()
    dispatch(db,incoming)
    db.commit()
    assert db.query(TelegramUpload).count()==1
    incoming['update_id']=2
    incoming['message']['document']['file_size']=21*1024*1024
    dispatch(db,incoming)
    db.commit()
    assert db.query(TelegramUpload).count()==1


def test_automation_opt_in_dedup_and_revocation(db, monkeypatch):
    user=person(db)
    now=datetime.utcnow()
    user.birth_date=now.date().replace(year=2000)
    item=event(db)
    db.add(Registration(user_id=user.id,event_id=item.id))
    db.commit()
    jobs.enqueue_automations(db,now)
    assert db.query(TelegramBotReply).count()==0
    db.add(TelegramAutomationPreference(user_id=user.id,birthdays=True,reminders=True))
    db.commit()
    jobs.enqueue_automations(db,now)
    jobs.enqueue_automations(db,now)
    assert db.query(TelegramBotReply).count()==2
    revoke(db.get(TelegramSubscription,user.id))
    db.commit()
    calls=[]
    monkeypatch.setattr(jobs,'api',lambda *a,**kw:calls.append(kw))
    jobs.send_reply(TestingSessionLocal)
    jobs.send_reply(TestingSessionLocal)
    db.expire_all()
    assert calls==[] and {r.status for r in db.query(TelegramBotReply)}=={'skipped'}


def test_command_reply_failure_does_not_resend(db, monkeypatch):
    dispatch(db,update())
    db.commit()
    calls=[]
    def fail(*args,**kwargs):
        calls.append(1)
        raise telegram_live.TelegramError('unknown')
    monkeypatch.setattr(jobs,'api',fail)
    jobs.send_reply(TestingSessionLocal)
    jobs.send_reply(TestingSessionLocal)
    db.expire_all()
    assert calls==[1] and db.get(TelegramBotReply,'update:1').status=='unknown'
