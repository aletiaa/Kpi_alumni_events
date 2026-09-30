import hashlib
import secrets
from datetime import datetime, timedelta

from app.models import TelegramSubscription, User
from app.services.messaging import eligible_user


def revoke(subscription):
    subscription.chat_id = None
    subscription.code_hash = None
    subscription.expires_at = None
    subscription.revoked_at = datetime.utcnow()
    subscription.news = False
    subscription.events = False


def subscribe(db, user, news, events):
    subscription = db.get(TelegramSubscription, user.id)
    if subscription is None:
        subscription = TelegramSubscription(user_id=user.id)
        db.add(subscription)
    subscription.news = news
    subscription.events = events
    subscription.consent_at = datetime.utcnow()
    subscription.revoked_at = None
    code = None
    if not subscription.chat_id:
        code = secrets.token_urlsafe(24)
        subscription.code_hash = hashlib.sha256(code.encode()).hexdigest()
        subscription.expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    return code


def accept_link(db, code, chat_id, username):
    digest = hashlib.sha256(code.encode()).hexdigest()
    subscription = db.query(TelegramSubscription).filter_by(code_hash=digest).first()
    if not subscription or not subscription.expires_at or subscription.expires_at <= datetime.utcnow():
        return
    if subscription.revoked_at or not subscription.consent_at:
        return
    if not eligible_user(db.get(User, subscription.user_id)):
        return
    # One Telegram chat can belong to only one website subscriber.
    existing = db.query(TelegramSubscription).filter_by(chat_id=chat_id).first()
    if existing and existing.user_id != subscription.user_id:
        return
    subscription.chat_id = chat_id
    subscription.username = username or None
    subscription.code_hash = None
    subscription.expires_at = None
