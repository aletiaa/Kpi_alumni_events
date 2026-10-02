import asyncio
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.exc import IntegrityError

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERNAME
from app.models import TelegramLink, TelegramState, TelegramDelivery
from app.models import TelegramSubscription
from app.services.telegram_subscriptions import accept_link, revoke


class TelegramError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(status)


def api(method, **payload):
    if not TELEGRAM_BOT_TOKEN:
        raise TelegramError("not_configured")
    request = Request(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}",
                      data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise TelegramError({401: "unauthorized", 403: "blocked", 409: "poll_conflict",
                             429: "rate_limited"}.get(exc.code, "rejected")) from None
    except (URLError, TimeoutError, ValueError, OSError):
        # Never expose exception URLs: they contain the bot token.
        raise TelegramError("unknown") from None
    if not data.get("ok"):
        raise TelegramError("rejected")
    return data["result"]


def begin_link(db, email):
    code = secrets.token_urlsafe(24)
    link = db.get(TelegramLink, email)
    if not link:
        link = TelegramLink(admin_email=email)
        db.add(link)
    link.code_hash = hashlib.sha256(code.encode()).hexdigest()
    link.expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    return code


def consume_update(db, update):
    message = update.get("message", {})
    chat = message.get("chat", {})
    sender = message.get("from", {})
    text = message.get("text", "")
    if chat.get("type") != "private" or sender.get("id") != chat.get("id") or sender.get("is_bot"):
        return
    username = sender.get("username", "").lower()
    if text == "/stop":
        for sub in db.query(TelegramSubscription).filter_by(chat_id=str(chat["id"])):
            revoke(sub)
        for link in db.query(TelegramLink).filter_by(chat_id=str(chat["id"])):
            link.chat_id = None
            link.code_hash = None
        return
    parts = text.split()
    if len(parts) != 2 or parts[0].split("@")[0] != "/start":
        return
    accept_link(db, parts[1], str(chat['id']), username)
    digest = hashlib.sha256(parts[1].encode()).hexdigest()
    link = db.query(TelegramLink).filter_by(code_hash=digest).first()
    if link and link.expires_at and link.expires_at > datetime.utcnow():
        from app.models import User
        from app.services.admin_permissions import valid_grant, is_administrator_email
        if not is_administrator_email(db, link.admin_email):
            return
        user = db.query(User).filter_by(email=link.admin_email).first()
        delegated = bool(valid_grant(db, user)) if user else False
        if not delegated and (not TELEGRAM_ALLOWED_USERNAME or username != TELEGRAM_ALLOWED_USERNAME):
            return
        occupied = db.query(TelegramLink).filter(
            TelegramLink.chat_id == str(chat["id"]),
            TelegramLink.admin_email != link.admin_email,
        ).first()
        if occupied:
            return
        link.chat_id = str(chat["id"])
        link.username = username
        link.code_hash = None
        link.expires_at = None


def poll_once(factory):
    with factory() as db:
        state = db.get(TelegramState, 1)
        if state is None:
            state = TelegramState(id=1, offset=0, status="not_checked")
            db.add(state)
            db.commit()
        try:
            if not state.bot_username:
                state.bot_username = api("getMe")["username"]
            updates = api("getUpdates", offset=state.offset, timeout=0, allowed_updates=["message", "callback_query"], limit=20)
            for update in updates:
                if update['update_id'] < state.offset:
                    continue
                consume_update(db, update)
                db.flush()
                from app.services.telegram_commands import dispatch
                dispatch(db, update)
                state.offset = max(state.offset, update["update_id"] + 1)
                db.commit()
                callback = update.get('callback_query')
                if callback:
                    try:
                        api('answerCallbackQuery', callback_query_id=callback['id'])
                    except TelegramError:
                        pass
            state.status = "connected"
        except TelegramError as exc:
            state.status = exc.status
        state.checked_at = datetime.utcnow()
        db.commit()


async def poll_loop(factory):
    while True:
        try:
            await asyncio.to_thread(poll_once, factory)
        except Exception:
            logging.getLogger(__name__).warning("Telegram polling failed; retrying without exposing credentials")
        await asyncio.sleep(5)


def send_campaign(db, campaign, email):
    link = db.get(TelegramLink, email)
    if not link or not link.chat_id:
        raise TelegramError("not_linked")
    delivery = TelegramDelivery(campaign_id=campaign.id, admin_email=email, chat_id=link.chat_id)
    db.add(delivery)
    try:
        # Persist the attempt before sending. Never automatically retry ambiguous sends.
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.get(TelegramDelivery, campaign.id)
    try:
        result = api("sendMessage", chat_id=link.chat_id, text=campaign.body)
        delivery.status = "accepted"
        delivery.message_id = str(result["message_id"])
    except TelegramError as exc:
        delivery.status = exc.status
    db.commit()
    return delivery
