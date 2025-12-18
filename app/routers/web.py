from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.ml.nlp_recommender import recommend_events_nlp
from app.db import get_db
from app.models import Event, Registration, User
from app.deps import get_current_identity, require_identity
from app.config import APP_NAME
from app.ml.hybrid import hybrid_recommend


router = APIRouter()


def _now_naive_utc() -> datetime:
    # Your DB columns are DateTime (naive), so keep naive UTC for comparisons.
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/")
def home(request: Request, db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    # 1) Upcoming events
    events = db.query(Event).order_by(Event.start_time.asc()).limit(50).all()
    flash = request.query_params.get("msg")

    # 2) Registration counts per event
    reg_counts = dict(
        db.query(Registration.event_id, func.count(Registration.id))
        .group_by(Registration.event_id)
        .all()
    )

    # 3) Which events current user is registered to
    user_regs: set[int] = set()
    registered_events: list[Event] = []

    if ident and ident.role != "admin" and ident.user_id:
        user_regs = {
            row[0]
            for row in db.query(Registration.event_id)
            .filter(Registration.user_id == ident.user_id)
            .all()
        }

        registered_events = (
            db.query(Event)
            .join(Registration, Registration.event_id == Event.id)
            .filter(Registration.user_id == ident.user_id)
            .order_by(Event.start_time.asc())
            .all()
        )

    # 4) Recommendations (HYBRID: NLP + popularity + freshness)
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
            if not ev:
                continue
            recommended_items.append({
                "event": ev,
                "score": r.score,       # now hybrid score
                "keywords": r.keywords, # still from NLP explainability
            })

    return request.app.state.templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "app_name": APP_NAME,
            "ident": ident,
            "events": events,
            "reg_counts": reg_counts,
            "user_regs": user_regs,
            "flash": flash,
            "now": datetime.now(timezone.utc).replace(tzinfo=None),
            "recommended_items": recommended_items,
        },
    )


@router.post("/events/{event_id}/register")
def rsvp(event_id: int, db: Session = Depends(get_db), ident=Depends(require_identity)):
    # Only DB users can register (admins cannot)
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/", status_code=303)

    # Ensure user exists (and optionally verified)
    user = db.get(User, ident.user_id)
    if not user:
        return RedirectResponse("/?msg=user_missing", status_code=303)

    if hasattr(user, "is_email_verified") and not user.is_email_verified:
        return RedirectResponse("/?msg=verify_email_first", status_code=303)

    # Ensure event exists
    event = db.get(Event, event_id)
    if not event:
        return RedirectResponse("/?msg=event_not_found", status_code=303)

    # Registration deadline enforcement
    now = _now_naive_utc()
    if event.registration_deadline and now > event.registration_deadline:
        return RedirectResponse("/?msg=deadline_passed", status_code=303)

    # Prevent duplicate registrations
    exists = (
        db.query(Registration)
        .filter(Registration.user_id == ident.user_id, Registration.event_id == event_id)
        .first()
    )
    if exists:
        return RedirectResponse("/?msg=already_registered", status_code=303)

    # Capacity check
    current_count = (
        db.query(func.count(Registration.id))
        .filter(Registration.event_id == event_id)
        .scalar()
    ) or 0

    if current_count >= event.capacity:
        return RedirectResponse("/?msg=full", status_code=303)

    db.add(Registration(user_id=ident.user_id, event_id=event_id))
    db.commit()

    return RedirectResponse("/?msg=registered", status_code=303)


@router.post("/events/{event_id}/unregister")
def un_rsvp(event_id: int, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/", status_code=303)

    reg = (
        db.query(Registration)
        .filter(Registration.user_id == ident.user_id, Registration.event_id == event_id)
        .first()
    )

    if reg:
        db.delete(reg)
        db.commit()
        return RedirectResponse("/?msg=unregistered", status_code=303)

    return RedirectResponse("/?msg=not_registered", status_code=303)


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
        "my_events.html",
        {"request": request, "app_name": APP_NAME, "ident": ident, "events": rows},
    )
