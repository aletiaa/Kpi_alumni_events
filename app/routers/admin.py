# app/routers/admin.py
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.db import get_db
from app.models import ChatLink, Event, EventComment, EventReaction, News, Registration, Survey, User
from app.deps import require_admin
from app.config import APP_NAME
from app.services.analytics import analytics_overview, average_page_duration_by_page, top_pages

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
    upcoming_events = db.query(func.count(Event.id)).filter(Event.start_time >= now).scalar() or 0
    total_registrations = db.query(func.count(Registration.id)).scalar() or 0
    total_news = db.query(func.count(News.id)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_chats = db.query(func.count(ChatLink.id)).scalar() or 0
    total_surveys = db.query(func.count(Survey.id)).scalar() or 0
    total_mentors = db.query(func.count(User.id)).filter(User.is_mentor == True, User.is_profile_public == True).scalar() or 0
    total_reactions = db.query(func.count(EventReaction.id)).scalar() or 0
    total_comments = db.query(func.count(EventComment.id)).scalar() or 0

    recent_events = db.query(Event).order_by(Event.start_time.desc()).limit(5).all()
    popular_events = (
        db.query(Event, func.count(Registration.id).label("registrations"))
        .outerjoin(Registration, Registration.event_id == Event.id)
        .group_by(Event.id)
        .order_by(func.count(Registration.id).desc(), Event.start_time.asc())
        .limit(5)
        .all()
    )
    analytics_summary = analytics_overview(db)
    analytics_top_pages = top_pages(db, limit=5)
    analytics_page_durations = average_page_duration_by_page(db, limit=5)

    try:
        iot_rows = db.execute(text("""
            SELECT event_id, COALESCE(SUM(delta), 0) AS net, MAX(ts) AS last_ts
            FROM iot_visits
            GROUP BY event_id
            ORDER BY event_id
            LIMIT 5
        """)).mappings().all()
    except Exception:
        iot_rows = []

    return request.app.state.templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "request": request,
            "app_name": APP_NAME,
            "ident": ident,
            "total_events": total_events,
            "upcoming_events": upcoming_events,
            "total_registrations": total_registrations,
            "total_news": total_news,
            "total_users": total_users,
            "total_chats": total_chats,
            "total_surveys": total_surveys,
            "total_mentors": total_mentors,
            "total_reactions": total_reactions,
            "total_comments": total_comments,
            "recent_events": recent_events,
            "popular_events": popular_events,
            "iot_rows": iot_rows,
            "analytics_summary": analytics_summary,
            "analytics_top_pages": analytics_top_pages,
            "analytics_page_durations": analytics_page_durations,
            "now": now,
        },
    )

