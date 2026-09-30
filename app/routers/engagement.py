from datetime import datetime
from io import BytesIO

import qrcode
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import APP_BASE_URL
from app.db import get_db
from app.deps import require_admin, require_identity, get_current_identity
from app.models import Event, Registration, User
from app.ml.summarizer import generate_short_description
from app.routers.messages import current_user
from app.services.personalization import recommendations

router = APIRouter()


@router.post('/admin/description-preview')
def summarize(title: str = Form('', max_length=200), body: str = Form(..., max_length=30000), admin=Depends(require_admin)):
    if not body.strip():
        raise HTTPException(400, 'Опис не може бути порожнім.')
    return {'summary': generate_short_description(title, body, max_chars=300)}


@router.get('/api/personal-suggestions')
def suggestions(section: str, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if section not in {'event', 'news'}:
        raise HTTPException(400)
    user = current_user(db, ident)
    return {'items': recommendations(db, user, section)}


@router.get('/events/{event_id}')
def detail(event_id: int, request: Request, db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, 'Подію не знайдено')
    count = db.query(func.count(Registration.id)).filter_by(event_id=event_id).scalar() or 0
    registered = bool(ident and ident.user_id and db.query(Registration.id).filter_by(event_id=event_id, user_id=ident.user_id).first())
    user = db.get(User, ident.user_id) if ident and ident.user_id else None
    allowed = bool(user and user.is_active and user.is_email_verified and not user.is_blocked)
    now = datetime.utcnow()
    closed = event.start_time <= now or count >= event.capacity or (event.registration_deadline and event.registration_deadline <= now)
    return request.app.state.templates.TemplateResponse(request, 'event_detail.html', {
        'request':request, 'app_name':'AlumnixHub', 'ident':ident, 'event':event,
        'registered':registered, 'closed':closed, 'allowed':allowed, 'count':count})


@router.get('/events/{event_id}/registration-qr')
def event_qr(event_id: int, db: Session = Depends(get_db), ident=Depends(require_identity)):
    current_user(db, ident)
    if not db.get(Event, event_id):
        raise HTTPException(404)
    destination = f'{APP_BASE_URL}/events/{event_id}#register-area'
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(destination)
    qr.make(fit=True)
    data = BytesIO()
    qr.make_image(fill_color='black', back_color='white').save(data, format='PNG')
    return Response(data.getvalue(), media_type='image/png', headers={'Cache-Control':'private, no-store'})
