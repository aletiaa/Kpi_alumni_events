# app/routers/admin.py
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import Event, Registration
from app.deps import require_admin
from app.config import APP_NAME

router = APIRouter()

def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

@router.get("/admin")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    ident=Depends(require_admin),
):
    now = _now_naive_utc()

    total_events = db.query(func.count(Event.id)).scalar() or 0
    upcoming_events = (
        db.query(func.count(Event.id))
        .filter(Event.start_time >= now)
        .scalar()
        or 0
    )
    total_registrations = db.query(func.count(Registration.id)).scalar() or 0

    # Optional: show a small “recent events” list in the dashboard
    recent_events = (
        db.query(Event)
        .order_by(Event.start_time.desc())
        .limit(5)
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "app_name": APP_NAME,
            "ident": ident,
            "total_events": total_events,
            "upcoming_events": upcoming_events,
            "total_registrations": total_registrations,
            "recent_events": recent_events,
            "now": now,
        },
    )
