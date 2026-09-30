from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, TELEGRAM_ENABLED
from app.db import get_db
from app.deps import require_identity
from app.models import TelegramSubscription, TelegramState, TelegramAutomationPreference
from app.routers.messages import current_user
from app.services.telegram_subscriptions import subscribe, revoke
from app.services.telegram_health import health

router = APIRouter(prefix='/profile/telegram', tags=['telegram-subscriptions'])
signer = URLSafeTimedSerializer(SECRET_KEY, salt='telegram-subscriber')


def verify(token, user):
    try:
        if signer.loads(token, max_age=7200) != user.id:
            raise BadSignature('Wrong user')
    except BadSignature:
        raise HTTPException(403, 'Оновіть сторінку та повторіть дію.')


def render(request, db, ident, user, code=None):
    response = request.app.state.templates.TemplateResponse(request, 'telegram_settings.html', {
        'request':request, 'ident':ident, 'app_name':'AlumnixHub', 'code':code,
        'subscription':db.get(TelegramSubscription, user.id),
        'preferences':db.get(TelegramAutomationPreference, user.id),
        'state':db.get(TelegramState, 1), 'enabled':TELEGRAM_ENABLED,
        'bot_health':health(request, db),
        'csrf':signer.dumps(user.id)})
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@router.get('')
def settings(request: Request, db: Session = Depends(get_db), ident=Depends(require_identity)):
    return render(request, db, ident, current_user(db, ident))


@router.get('/status')
def connection_status(request: Request, db: Session = Depends(get_db), ident=Depends(require_identity)):
    user = current_user(db, ident)
    sub = db.get(TelegramSubscription,user.id)
    return {'online':health(request,db)['online'], 'linked':bool(sub and sub.chat_id and not sub.revoked_at)}


@router.post('')
def save(request: Request, consent: str = Form(''), news: bool = Form(False),
         events: bool = Form(False), reminders: bool = Form(False), birthdays: bool = Form(False), csrf: str = Form(''),
         db: Session = Depends(get_db), ident=Depends(require_identity)):
    user = current_user(db, ident)
    verify(csrf, user)
    if not TELEGRAM_ENABLED:
        raise HTTPException(409)
    if consent != 'yes' or not (news or events or reminders or birthdays):
        raise HTTPException(400, 'Оберіть теми та підтвердьте згоду.')
    pref = db.get(TelegramAutomationPreference,user.id)
    if pref is None:
        pref = TelegramAutomationPreference(user_id=user.id)
        db.add(pref)
    pref.reminders, pref.birthdays = reminders, birthdays
    code = subscribe(db, user, news, events)
    return render(request, db, ident, user, code)


@router.post('/unsubscribe')
def unsubscribe(csrf: str = Form(''), db: Session = Depends(get_db), ident=Depends(require_identity)):
    user = current_user(db, ident)
    verify(csrf, user)
    subscription = db.get(TelegramSubscription, user.id)
    if subscription:
        revoke(subscription)
        db.commit()
    return RedirectResponse('/profile/telegram', status_code=303)
