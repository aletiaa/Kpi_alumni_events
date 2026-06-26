from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.config import APP_NAME
from app.db import get_db
from app.deps import get_current_identity, require_identity
from app.ml.hybrid import hybrid_recommend
from app.models import DirectMessage, Event, EventComment, EventReaction, Registration, User
from app.services.notifications import notify_direct_message

router = APIRouter()


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_registered(db: Session, user_id: int, event_id: int) -> bool:
    return db.query(Registration.id).filter(
        Registration.user_id == user_id,
        Registration.event_id == event_id,
    ).first() is not None


def _same_stream(current: User, other: User) -> bool:
    if not current or not other or current.id == other.id:
        return False
    if current.group_name and other.group_name and current.group_name.strip().lower() == other.group_name.strip().lower():
        return True
    if current.graduation_year and other.graduation_year and current.graduation_year == other.graduation_year:
        same_faculty = current.faculty and other.faculty and current.faculty.strip().lower() == other.faculty.strip().lower()
        same_specialty = current.specialty and other.specialty and current.specialty.strip().lower() == other.specialty.strip().lower()
        return bool(same_faculty or same_specialty)
    return False


def build_events_context(request: Request, db: Session, ident):
    events = db.query(Event).order_by(Event.start_time.asc()).limit(50).all()
    flash = request.query_params.get("msg")

    reg_counts = dict(
        db.query(Registration.event_id, func.count(Registration.id))
        .group_by(Registration.event_id)
        .all()
    )
    like_counts = dict(
        db.query(EventReaction.event_id, func.count(EventReaction.id))
        .filter(EventReaction.reaction == "like")
        .group_by(EventReaction.event_id)
        .all()
    )
    dislike_counts = dict(
        db.query(EventReaction.event_id, func.count(EventReaction.id))
        .filter(EventReaction.reaction == "dislike")
        .group_by(EventReaction.event_id)
        .all()
    )

    comments_by_event: dict[int, list[EventComment]] = defaultdict(list)
    comments = (
        db.query(EventComment)
        .options(joinedload(EventComment.user))
        .order_by(EventComment.created_at.asc())
        .limit(300)
        .all()
    )
    for comment in comments:
        comments_by_event[comment.event_id].append(comment)

    user_regs: set[int] = set()
    user_reactions: dict[int, str] = {}
    registered_events: list[Event] = []

    if ident and ident.role != "admin" and ident.user_id:
        user_regs = {
            row[0]
            for row in db.query(Registration.event_id)
            .filter(Registration.user_id == ident.user_id)
            .all()
        }
        user_reactions = dict(
            db.query(EventReaction.event_id, EventReaction.reaction)
            .filter(EventReaction.user_id == ident.user_id)
            .all()
        )
        registered_events = (
            db.query(Event)
            .join(Registration, Registration.event_id == Event.id)
            .filter(Registration.user_id == ident.user_id)
            .order_by(Event.start_time.asc())
            .all()
        )

    recommended_items = []
    if ident and ident.role != "admin" and ident.user_id:
        user_texts = [f"{e.title} {e.location} {(e.description or '')}" for e in registered_events]
        candidates = [e for e in events if e.id not in user_regs]

        recs = hybrid_recommend(
            user_texts=user_texts,
            candidate_events=candidates,
            registration_counts=reg_counts,
            top_k=3,
            w_nlp=0.6,
            w_popularity=0.25,
            w_freshness=0.15,
        )

        id_to_event = {e.id: e for e in candidates}
        for r in recs:
            ev = id_to_event.get(r.event_id)
            if ev:
                recommended_items.append({"event": ev, "score": r.score, "keywords": r.keywords})

    return {
        "ident": ident,
        "events": events,
        "reg_counts": reg_counts,
        "like_counts": like_counts,
        "dislike_counts": dislike_counts,
        "comments_by_event": comments_by_event,
        "user_regs": user_regs,
        "user_reactions": user_reactions,
        "flash": flash,
        "now": _now_naive_utc(),
        "recommended_items": recommended_items,
    }


@router.post("/events/{event_id}/register")
def rsvp(event_id: int, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/events", status_code=303)

    user = db.get(User, ident.user_id)
    if not user:
        return RedirectResponse("/events?msg=user_missing", status_code=303)
    if getattr(user, "is_blocked", False):
        return RedirectResponse("/events?msg=account_blocked", status_code=303)
    if hasattr(user, "is_email_verified") and not user.is_email_verified:
        return RedirectResponse("/events?msg=verify_email_first", status_code=303)

    event = db.get(Event, event_id)
    if not event:
        return RedirectResponse("/events?msg=event_not_found", status_code=303)

    now = _now_naive_utc()
    if event.registration_deadline and now > event.registration_deadline:
        return RedirectResponse("/events?msg=deadline_passed", status_code=303)

    exists = db.query(Registration).filter(Registration.user_id == ident.user_id, Registration.event_id == event_id).first()
    if exists:
        return RedirectResponse("/events?msg=already_registered", status_code=303)

    current_count = db.query(func.count(Registration.id)).filter(Registration.event_id == event_id).scalar() or 0
    if current_count >= event.capacity:
        return RedirectResponse("/events?msg=full", status_code=303)

    db.add(Registration(user_id=ident.user_id, event_id=event_id))
    db.commit()
    return RedirectResponse("/events?msg=registered", status_code=303)


@router.post("/events/{event_id}/unregister")
def un_rsvp(event_id: int, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/events", status_code=303)

    reg = db.query(Registration).filter(Registration.user_id == ident.user_id, Registration.event_id == event_id).first()
    if reg:
        db.delete(reg)
        db.commit()
        return RedirectResponse("/events?msg=unregistered", status_code=303)
    return RedirectResponse("/events?msg=not_registered", status_code=303)


@router.post("/events/{event_id}/react")
def react_to_event(event_id: int, reaction: str = Form(...), db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id or reaction not in {"like", "dislike"}:
        return RedirectResponse("/events", status_code=303)
    if not db.get(Event, event_id):
        return RedirectResponse("/events?msg=event_not_found", status_code=303)

    existing = db.query(EventReaction).filter(EventReaction.user_id == ident.user_id, EventReaction.event_id == event_id).first()
    if existing and existing.reaction == reaction:
        db.delete(existing)
    elif existing:
        existing.reaction = reaction
        existing.updated_at = _now_naive_utc()
    else:
        db.add(EventReaction(user_id=ident.user_id, event_id=event_id, reaction=reaction))
    db.commit()
    return RedirectResponse(f"/events?msg={reaction}_saved#event-{event_id}", status_code=303)


@router.post("/events/{event_id}/comments")
def comment_on_event(event_id: int, body: str = Form(...), db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/events", status_code=303)
    if not db.get(Event, event_id):
        return RedirectResponse("/events?msg=event_not_found", status_code=303)
    text = (body or "").strip()
    if not text:
        return RedirectResponse(f"/events?msg=empty_comment#event-{event_id}", status_code=303)
    db.add(EventComment(user_id=ident.user_id, event_id=event_id, body=text[:1000]))
    db.commit()
    return RedirectResponse(f"/events?msg=comment_added#event-{event_id}", status_code=303)


@router.get("/me/events")
def my_events(request: Request, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/", status_code=303)
    rows = (
        db.query(Event)
        .join(Registration, Registration.event_id == Event.id)
        .filter(Registration.user_id == ident.user_id)
        .order_by(Event.start_time.asc())
        .all()
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "my_events.html",
        {"request": request, "app_name": "Платформа випускників КПІ", "ident": ident, "events": rows},
    )


@router.get("/messages")
def messages_index(request: Request, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/", status_code=303)
    messages = (
        db.query(DirectMessage)
        .options(joinedload(DirectMessage.sender), joinedload(DirectMessage.receiver))
        .filter(or_(DirectMessage.sender_id == ident.user_id, DirectMessage.receiver_id == ident.user_id))
        .order_by(DirectMessage.created_at.desc())
        .limit(100)
        .all()
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "messages/list.html",
        {"request": request, "app_name": "Платформа випускників КПІ", "ident": ident, "messages": messages},
    )


@router.get("/messages/{user_id}")
def message_thread(user_id: int, request: Request, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/", status_code=303)
    current = db.get(User, ident.user_id)
    recipient = db.get(User, user_id)
    if not current or not recipient or not _same_stream(current, recipient):
        return RedirectResponse("/alumni?msg=not_same_stream", status_code=303)
    thread = (
        db.query(DirectMessage)
        .options(joinedload(DirectMessage.sender), joinedload(DirectMessage.receiver))
        .filter(or_(
            and_(DirectMessage.sender_id == ident.user_id, DirectMessage.receiver_id == user_id),
            and_(DirectMessage.sender_id == user_id, DirectMessage.receiver_id == ident.user_id),
        ))
        .order_by(DirectMessage.created_at.asc())
        .all()
    )
    db.query(DirectMessage).filter(DirectMessage.sender_id == user_id, DirectMessage.receiver_id == ident.user_id).update({"is_read": True})
    db.commit()
    return request.app.state.templates.TemplateResponse(
        request,
        "messages/thread.html",
        {"request": request, "app_name": "Платформа випускників КПІ", "ident": ident, "recipient": recipient, "thread": thread},
    )


@router.post("/messages/{user_id}")
def send_message(user_id: int, body: str = Form(...), db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/", status_code=303)
    current = db.get(User, ident.user_id)
    recipient = db.get(User, user_id)
    if not current or not recipient or not _same_stream(current, recipient):
        return RedirectResponse("/alumni?msg=not_same_stream", status_code=303)
    text = (body or "").strip()
    if text:
        db.add(DirectMessage(sender_id=ident.user_id, receiver_id=user_id, body=text[:1000]))
        notify_direct_message(db, sender=current, receiver=recipient, message_preview=text[:500])
        db.commit()
    return RedirectResponse(f"/messages/{user_id}", status_code=303)
