import time
import asyncio
import logging
from datetime import datetime, timedelta

from app.models import (BotCampaign, User, TelegramSubscription,
                        TelegramBroadcast, TelegramRecipientDelivery)
from app.services.messaging import eligible_user
from app.services.telegram_live import api, TelegramError

AUDIENCES = {'telegram_all', 'telegram_alumni', 'telegram_student'}


def status_label(status):
    return {'queued':'У черзі', 'sending':'Надсилається', 'accepted':'Прийнято Telegram',
            'skipped':'Пропущено', 'cancelled':'Скасовано', 'unknown':'Результат невідомий',
            'blocked':'Бота заблоковано', 'rate_limited':'Ліміт Telegram',
            'unauthorized':'Помилка авторизації', 'rejected':'Відхилено Telegram',
            'not_configured':'Telegram не налаштовано'}.get(status, status)


def recipients(db, campaign, broadcast):
    query = db.query(TelegramSubscription).join(User).filter(
        User.is_active == True, User.is_email_verified == True, User.is_blocked == False,
        TelegramSubscription.chat_id.is_not(None), TelegramSubscription.consent_at.is_not(None),
        TelegramSubscription.revoked_at.is_(None),
        getattr(TelegramSubscription, broadcast.topic) == True)
    if campaign.audience != 'telegram_all':
        query = query.filter(User.role == campaign.audience.removeprefix('telegram_'))
    return query.order_by(TelegramSubscription.user_id)


def queue(db, campaign, broadcast):
    if broadcast.cancelled_at or broadcast.queued_at:
        return
    now = datetime.utcnow()
    changed = db.query(TelegramBroadcast).filter_by(campaign_id=campaign.id, queued_at=None,
                                                  cancelled_at=None).update({'queued_at':now})
    if changed:
        for subscription in recipients(db, campaign, broadcast):
            db.add(TelegramRecipientDelivery(campaign_id=campaign.id, user_id=subscription.user_id,
                chat_id=subscription.chat_id, consent_at=subscription.consent_at, status='queued'))
    db.commit()


def cancel(db, campaign_id):
    db.query(TelegramBroadcast).filter_by(campaign_id=campaign_id).update({'cancelled_at':datetime.utcnow()})
    db.query(TelegramRecipientDelivery).filter_by(campaign_id=campaign_id, status='queued').update(
        {'status':'cancelled', 'completed_at':datetime.utcnow()})
    db.commit()


def deliver_one(factory):
    with factory() as db:
        # A crash after sending cannot be distinguished from a lost API response.
        db.query(TelegramRecipientDelivery).filter(
            TelegramRecipientDelivery.status == 'sending',
            TelegramRecipientDelivery.attempted_at < datetime.utcnow() - timedelta(minutes=2)).update(
                {'status':'unknown', 'completed_at':datetime.utcnow()})
        db.commit()
        row = db.query(TelegramRecipientDelivery).filter_by(status='queued').order_by(
            TelegramRecipientDelivery.campaign_id, TelegramRecipientDelivery.user_id).first()
        if row is None:
            return False
        key = {'campaign_id':row.campaign_id, 'user_id':row.user_id}
        claimed = db.query(TelegramRecipientDelivery).filter_by(**key, status='queued').update(
            {'status':'sending', 'attempted_at':datetime.utcnow()})
        db.commit()
        if not claimed:
            return True
        db.refresh(row)
        campaign = db.get(BotCampaign, row.campaign_id)
        broadcast = db.get(TelegramBroadcast, row.campaign_id)
        sub = db.get(TelegramSubscription, row.user_id)
        user = db.get(User, row.user_id)
        if broadcast.cancelled_at:
            row.status = 'cancelled'
        elif (not eligible_user(user) or not sub or sub.revoked_at or
              sub.chat_id != row.chat_id or sub.consent_at != row.consent_at or
              not getattr(sub, broadcast.topic) or
              (campaign.audience != 'telegram_all' and user.role != campaign.audience.removeprefix('telegram_'))):
            row.status = 'skipped'
        else:
            try:
                result = api('sendMessage', chat_id=row.chat_id, text=campaign.body)
                row.status = 'accepted'
                row.message_id = str(result['message_id'])
            except TelegramError as exc:
                row.status = exc.status
                if exc.status == 'blocked':
                    from app.services.telegram_subscriptions import revoke
                    revoke(sub)
        row.completed_at = datetime.utcnow()
        db.commit()
        # No automatic retries, including rate limits or uncertain responses.
        return 'rate_limited' if row.status == 'rate_limited' else True


def deliver_batch(factory):
    for _ in range(5):
        result = deliver_one(factory)
        if result == 'rate_limited':
            return 60
        if not result:
            break
        time.sleep(1)
    return 5


async def delivery_loop(factory):
    while True:
        delay = 5
        try:
            delay = await asyncio.to_thread(deliver_batch, factory)
        except Exception:
            logging.getLogger(__name__).warning('Telegram delivery worker failed; no sensitive details logged')
        await asyncio.sleep(delay)
