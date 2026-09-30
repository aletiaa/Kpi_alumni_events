from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import APP_NAME, SECRET_KEY
from app.db import SessionLocal, get_db
from app.deps import require_admin
from app.models import Event, KpiImportItem
from app.services.kpi_import import ensure_state, run_import
from app.models import News

router = APIRouter(prefix="/admin/kpi-import", tags=["kpi-import"])
signer = URLSafeTimedSerializer(SECRET_KEY, salt="kpi-import-admin")


def verify_csrf(token, admin):
    try:
        if signer.loads(token, max_age=3600) != admin.email:
            raise BadSignature("Wrong account")
    except BadSignature:
        raise HTTPException(status_code=403, detail="Оновіть сторінку та повторіть дію.")


def back(message=""):
    return RedirectResponse("/admin/kpi-import" + ("?result=" + message if message else ""), status_code=303)


@router.get("")
def index(request: Request, page: int = 1, db: Session = Depends(get_db), admin=Depends(require_admin)):
    state = ensure_state(db)
    page = max(1, page)
    items = db.query(KpiImportItem).order_by(KpiImportItem.imported_at.desc(), KpiImportItem.id.desc()).offset((page - 1) * 20).limit(21).all()
    return request.app.state.templates.TemplateResponse(request, "admin/kpi_import.html", {
        "request": request, "app_name": APP_NAME, "ident": admin, "state": state,
        "items": items[:20], "has_next": len(items) > 20, "page": page,
        "csrf": signer.dumps(admin.email),
    })


@router.post("/settings")
def settings(csrf: str = Form(...), enabled: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    state = ensure_state(db)
    state.enabled = enabled == "1"
    db.commit()
    return back("saved")


@router.post("/run")
def run(csrf: str = Form(...), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    return back(run_import(SessionLocal, force=True))


@router.post("/{item_id}/review")
def review(item_id: int, csrf: str = Form(...), action: str = Form(...),
           start_time: str = Form(""), location: str = Form(""), capacity: int = Form(100),
           db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    item = db.get(KpiImportItem, item_id)
    if not item:
        raise HTTPException(status_code=404)
    if action not in {"news", "publish", "event", "dismiss"}:
        raise HTTPException(status_code=400)
    start = None
    if action == "event":
        try:
            start = datetime.fromisoformat(start_time)
        except ValueError:
            return back("invalid_event")
        if start.tzinfo is not None or not location.strip() or len(location.strip()) > 200 or not 1 <= capacity <= 100000:
            return back("invalid_event")
    # Claim the pending item in the same transaction as creating its destination.
    claimed = db.query(KpiImportItem).filter_by(id=item_id, status="pending").update(
        {"status": action}, synchronize_session=False)
    if not claimed:
        db.rollback()
        return back("already_reviewed")
    content = item.excerpt + "\n\nДжерело: " + item.source_url
    if action in {"news", "publish"}:
        news = News(title=item.title, content=content, short_description=item.excerpt[:500],
                    image_url=item.image_url, image_source_url=item.source_url if item.image_url else None,
                    is_published=action == "publish")
        db.add(news)
        db.flush()
        item.news_id = news.id
    elif action == "event":
        event = Event(title=item.title, description=content, short_description=item.excerpt[:500],
                      start_time=start, location=location.strip(), capacity=capacity,
                      image_url=item.image_url, image_source_url=item.source_url if item.image_url else None)
        db.add(event)
        db.flush()
        item.event_id = event.id
    db.commit()
    return back("reviewed")
