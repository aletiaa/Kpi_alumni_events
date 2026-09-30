import json
import asyncio
import logging
from datetime import datetime, timedelta

from app.models import (TelegramBotReply, TelegramSubscription, TelegramAutomationPreference,
                        User, Registration, Event, TelegramLink)
from app.services.messaging import eligible_user
from app.services.telegram_live import api, TelegramError


def enqueue_automations(db, now=None):
    now = now or datetime.utcnow()
    rows = db.query(TelegramSubscription, TelegramAutomationPreference, User).join(
        TelegramAutomationPreference, TelegramAutomationPreference.user_id == TelegramSubscription.user_id).join(
        User, User.id == TelegramSubscription.user_id).filter(
        TelegramSubscription.chat_id.is_not(None), TelegramSubscription.revoked_at.is_(None),
        User.is_active == True, User.is_email_verified == True, User.is_blocked == False).all()
    for sub, pref, user in rows:
        en = user.preferred_language == 'en'
        jobs = []
        if pref.birthdays and user.birth_date and (user.birth_date.month,user.birth_date.day) == (now.month,now.day):
            jobs.append((f'birthday:{now.year}:{user.id}', {
                'text':f'Happy birthday, {user.full_name}! Best wishes from AlumnixHub.' if en else f'З днем народження, {user.full_name}! Найкращі побажання від AlumnixHub.',
                '_automation':'birthdays'}))
        if pref.reminders:
            events = db.query(Event).join(Registration).filter(Registration.user_id == user.id,
                Event.start_time > now, Event.start_time <= now+timedelta(hours=1)).all()
            for event in events:
                jobs.append((f'reminder:{event.id}:{event.start_time.isoformat()}:{user.id}', {
                    'text':('Event reminder: ' if en else 'Нагадування про подію: ')+event.title+f'\n{event.start_time:%d.%m.%Y %H:%M} UTC',
                    '_automation':'reminders','_event_id':event.id,'_start':event.start_time.isoformat()}))
        for key, payload in jobs:
            if not db.get(TelegramBotReply, key):
                payload['chat_id'] = sub.chat_id
                payload['_consent'] = sub.consent_at.isoformat()
                db.add(TelegramBotReply(key=key,chat_id=sub.chat_id,user_id=user.id,
                    payload=json.dumps(payload,ensure_ascii=False)))
    db.commit()


def send_reply(factory):
    with factory() as db:
        db.query(TelegramBotReply).filter(TelegramBotReply.status=='sending',
            TelegramBotReply.attempted_at < datetime.utcnow()-timedelta(minutes=2)).update({'status':'unknown'})
        db.commit()
        row = db.query(TelegramBotReply).filter_by(status='queued').order_by(TelegramBotReply.created_at).first()
        if not row:
            return False
        if not db.query(TelegramBotReply).filter_by(key=row.key,status='queued').update(
                {'status':'sending','attempted_at':datetime.utcnow()}):
            db.rollback()
            return True
        db.commit()
        payload = json.loads(row.payload)
        valid = True
        if payload.get('_admin'):
            from app.services.admin_csv import find_admin_by_email
            link = db.get(TelegramLink,payload['_admin'])
            valid = bool(link and link.chat_id==row.chat_id and find_admin_by_email(payload['_admin']))
        if row.user_id:
            sub = db.get(TelegramSubscription,row.user_id)
            valid = bool(eligible_user(db.get(User,row.user_id)) and sub and not sub.revoked_at and sub.chat_id==row.chat_id)
            kind = payload.get('_automation')
            if valid and kind:
                pref = db.get(TelegramAutomationPreference,row.user_id)
                valid = bool(pref and getattr(pref,kind,False) and sub.consent_at.isoformat()==payload.get('_consent'))
                if valid and kind=='reminders':
                    event = db.get(Event,payload['_event_id'])
                    valid = bool(event and event.start_time>datetime.utcnow() and event.start_time.isoformat()==payload['_start'] and
                        db.query(Registration.id).filter_by(user_id=row.user_id,event_id=event.id).first())
                if valid and kind=='birthdays':
                    today = datetime.utcnow()
                    person = db.get(User,row.user_id)
                    valid = bool(person.birth_date and (person.birth_date.month,person.birth_date.day)==(today.month,today.day))
        if not valid:
            row.status='skipped'
        else:
            try:
                api(row.method, **{k:v for k,v in payload.items() if not k.startswith('_')})
                row.status='accepted'
            except TelegramError as exc:
                row.status=exc.status
        db.commit()
        return True


def run_jobs(factory):
    with factory() as db:
        enqueue_automations(db)
    for _ in range(5):
        if not send_reply(factory):
            break


async def reply_loop(factory):
    while True:
        try:
            await asyncio.to_thread(run_jobs, factory)
        except Exception:
            logging.getLogger(__name__).warning('Telegram reply worker failed; retrying')
        await asyncio.sleep(1)
