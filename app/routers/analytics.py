from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import APP_NAME
from app.db import get_db
from app.deps import require_admin
from app.middleware.analytics import ANALYTICS_COOKIE
from app.security import read_session_token
from app.services.analytics import analytics_dashboard_data, record_page_duration

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def analytics_dashboard(request: Request, db: Session = Depends(get_db), ident=Depends(require_admin)):
    return request.app.state.templates.TemplateResponse(
        request,
        "analytics/dashboard.html",
        {
            "request": request,
            "app_name": APP_NAME,
            "ident": ident,
            "analytics": analytics_dashboard_data(db),
        },
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
