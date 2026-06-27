from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import APP_NAME
from app.db import get_db
from app.deps import require_admin
from app.middleware.analytics import ANALYTICS_COOKIE
from app.security import read_session_token
from app.services.analytics import analytics_dashboard_data, analytics_page_options, record_page_duration

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _parse_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _analytics_filters(request: Request) -> dict[str, object]:
    start_date = _parse_date(request.query_params.get("start"))
    end_date = _parse_date(request.query_params.get("end"))
    role = (request.query_params.get("role") or "").strip()
    page = (request.query_params.get("page") or "").strip()
    filters: dict[str, object] = {
        "start": datetime.combine(start_date, datetime.min.time()) if start_date else None,
        "end": datetime.combine(end_date + timedelta(days=1), datetime.min.time()) if end_date else None,
        "role": role if role in {"student", "alumni", "guest", "anonymous"} else "",
        "page": page if page.startswith("/") else "",
        "start_value": start_date.isoformat() if start_date else "",
        "end_value": end_date.isoformat() if end_date else "",
    }
    return filters


@router.get("")
def analytics_dashboard(request: Request, db: Session = Depends(get_db), ident=Depends(require_admin)):
    filters = _analytics_filters(request)
    return request.app.state.templates.TemplateResponse(
        request,
        "analytics/dashboard.html",
        {
            "request": request,
            "app_name": APP_NAME,
            "ident": ident,
            "analytics": analytics_dashboard_data(db, filters=filters),
            "filters": filters,
            "page_options": analytics_page_options(),
        },
    )


@router.get("/export.csv")
def analytics_export_csv(request: Request, db: Session = Depends(get_db), ident=Depends(require_admin)):
    filters = _analytics_filters(request)
    analytics = analytics_dashboard_data(db, filters=filters)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["section", "metric", "value", "description"])
    for key, value in analytics["overview"].items():
        writer.writerow(["overview", key, value, ""])
    for row in analytics["top_pages"]:
        writer.writerow(["top_pages", row["title"], row["views"], row["description"]])
    for row in analytics["page_durations"]:
        writer.writerow(["page_duration", row["title"], row["avg_label"], f"{row['samples']} вимірів"])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=alumnixhub-analytics.csv"},
    )


class PageDurationIn(BaseModel):
    page: str = Field(..., max_length=1000)
    opened_at: datetime
    duration_seconds: int = Field(..., ge=0, le=60 * 60 * 24)


@router.post("/page-duration")
def page_duration(payload: PageDurationIn, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get(ANALYTICS_COOKIE)
    auth_token = request.cookies.get("session")
    user_id = None
    if auth_token:
        data = read_session_token(auth_token)
        if data and data.get("user_id"):
            user_id = int(data["user_id"])
    if not session_id and auth_token:
        import hashlib

        session_id = f"auth:{hashlib.sha256(auth_token.encode('utf-8')).hexdigest()[:32]}"
    if not session_id:
        session_id = "anon:unknown"

    record_page_duration(
        db,
        user_id=user_id,
        session_id=session_id[:80],
        page=payload.page,
        opened_at=payload.opened_at,
        closed_at=datetime.utcnow(),
        duration_seconds=payload.duration_seconds,
    )
    return {"ok": True}
