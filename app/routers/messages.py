from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.deps import require_identity
from app.models import DirectMessage, User
from app.services.messaging import eligible_user, message_token, verify_message_token
from app.services.notifications import notify_direct_message

router = APIRouter()


def pair(sender_id, recipient_id):
    return or_(and_(DirectMessage.sender_id == sender_id, DirectMessage.receiver_id == recipient_id),
               and_(DirectMessage.sender_id == recipient_id, DirectMessage.receiver_id == sender_id))


def current_user(db, ident):
    user = db.get(User, ident.user_id) if ident.user_id else None
    if not eligible_user(user):
        raise HTTPException(403, "Для листування потрібен підтверджений особистий профіль.")
    return user


def recipient_user(db, current, user_id):
    recipient = db.get(User, user_id)
    if not eligible_user(recipient) or current.id == user_id:
        raise HTTPException(404, "Користувача не знайдено")
    if not recipient.is_profile_public and not db.query(DirectMessage.id).filter(pair(current.id, user_id)).first():
        raise HTTPException(404, "Користувача не знайдено")
    return recipient


def render(request, template, ident, **context):
    return request.app.state.templates.TemplateResponse(request, template, {
        "request": request, "app_name": "AlumnixHub", "ident": ident, **context})


@router.get('/messages')
def inbox(request: Request, q: str = '', page: int = 1, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if not ident.user_id:
        return render(request, 'messages/list.html', ident, personal_profile_required=True)
    current = current_user(db, ident)
    page = max(1, page)
    participant = case((DirectMessage.sender_id == current.id, DirectMessage.receiver_id), else_=DirectMessage.sender_id)
    latest = db.query(func.max(DirectMessage.id)).filter(
        or_(DirectMessage.sender_id == current.id, DirectMessage.receiver_id == current.id)
    ).group_by(participant).scalar_subquery()
    messages = db.query(DirectMessage).options(joinedload(DirectMessage.sender), joinedload(DirectMessage.receiver)).filter(
        DirectMessage.id.in_(latest)).order_by(DirectMessage.id.desc()).offset((page - 1) * 30).limit(31).all()
    unread = dict(db.query(DirectMessage.sender_id, func.count(DirectMessage.id)).filter(
        DirectMessage.receiver_id == current.id, DirectMessage.is_read == False).group_by(DirectMessage.sender_id).all())
    people = db.query(User).filter(User.id != current.id, User.is_active == True,
        User.is_blocked == False, User.is_email_verified == True, User.is_profile_public == True)
    q = q.strip()[:120]
    if q:
        people = people.filter(or_(User.full_name.icontains(q, autoescape=True), User.full_name_en.icontains(q, autoescape=True)))
    people = people.order_by(User.full_name, User.id).limit(21).all()
    return render(request, 'messages/list.html', ident, messages=messages[:30], has_next=len(messages) > 30,
                  page=page, people=people[:20], more_people=len(people) > 20, q=q, unread=unread)


@router.get('/messages/{user_id}')
def thread(user_id: int, request: Request, before: int | None = None,
           db: Session = Depends(get_db), ident=Depends(require_identity)):
    current = current_user(db, ident)
    recipient = recipient_user(db, current, user_id)
    query = db.query(DirectMessage).options(joinedload(DirectMessage.sender)).filter(pair(current.id, user_id))
    if before is not None:
        query = query.filter(DirectMessage.id < before)
    rows = query.order_by(DirectMessage.id.desc()).limit(51).all()
    displayed = rows[:50]
    if displayed:
        db.query(DirectMessage).filter(DirectMessage.id.in_([m.id for m in displayed]),
            DirectMessage.receiver_id == current.id, DirectMessage.sender_id == user_id).update(
                {"is_read": True}, synchronize_session=False)
        db.commit()
    return render(request, 'messages/thread.html', ident, recipient=recipient, thread=list(reversed(displayed)),
                  older=displayed[-1].id if len(rows) > 50 else None, csrf=message_token(current.id, user_id))


@router.post('/messages/{user_id}')
def send(user_id: int, body: str = Form(..., max_length=1000), csrf: str = Form(''),
         db: Session = Depends(get_db), ident=Depends(require_identity)):
    current = current_user(db, ident)
    recipient = recipient_user(db, current, user_id)
    verify_message_token(csrf, current.id, user_id)
    body = body.strip()
    if not body:
        raise HTTPException(400, "Введіть повідомлення.")
    recent = db.query(DirectMessage.id).filter(DirectMessage.sender_id == current.id,
        DirectMessage.created_at >= datetime.utcnow() - timedelta(minutes=1)).count()
    if recent >= 30:
        raise HTTPException(429, "Забагато повідомлень. Спробуйте за хвилину.")
    db.add(DirectMessage(sender_id=current.id, receiver_id=user_id, body=body))
    notify_direct_message(db, sender=current, receiver=recipient, message_preview=body[:500])
    db.commit()
    return RedirectResponse(f'/messages/{user_id}', status_code=303)
