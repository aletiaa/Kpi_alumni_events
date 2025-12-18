from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event
from app.deps import require_admin
from app.config import APP_NAME, APP_BASE_URL
from pathlib import Path
from app.ml.summarizer import generate_short_description
from app.ml.qr import generate_event_qr_png

router = APIRouter(prefix="/admin", tags=["admin-events"])


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    """
    Accepts:
      - YYYY-MM-DDTHH:MM
      - YYYY-MM-DD HH:MM
      - YYYY-MM-DD HH:MM:SS(.micro)
    """
    if not value:
        return None

    v = value.strip()
    if not v:
        return None

    v = v.replace("T", " ")
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {value}")


@router.get("/events")
def admin_events_list(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    events = db.query(Event).order_by(Event.start_time.asc()).all()

    return request.app.state.templates.TemplateResponse(
        "admin_events.html",
        {
            "request": request,
            "app_name": APP_NAME,
            "ident": admin,
            "events": events,
        },
    )


@router.post("/events/create")
def admin_create_event(
    title: str = Form(...),
    description: str = Form(""),
    location: str = Form("KPI"),
    start_time: str = Form(...),
    end_time: str = Form(""),
    registration_deadline: str = Form(""),
    capacity: int = Form(100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    if not title.strip():
        return RedirectResponse("/admin/events?error=title_required", status_code=303)

    ev = Event(
        title=title.strip(),
        description=description.strip(),
        location=location.strip() or "KPI",
        start_time=parse_dt(start_time),
        end_time=parse_dt(end_time),
        registration_deadline=parse_dt(registration_deadline),
        capacity=max(int(capacity), 1),
    )

    db.add(ev)
    db.commit()

    return RedirectResponse("/admin/events?created=1", status_code=303)


@router.get("/events/{event_id}/edit")
def admin_edit_event_form(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return request.app.state.templates.TemplateResponse(
        "admin_event_edit.html",
        {
            "request": request,
            "app_name": APP_NAME,
            "ident": admin,
            "event": event,
        },
    )

@router.post("/events/{event_id}/edit")
def admin_edit_event_save(
    event_id: int,
    title: str = Form(...),
    description: str = Form(""),
    location: str = Form("KPI"),
    start_time: str = Form(...),
    end_time: str = Form(""),
    registration_deadline: str = Form(""),
    capacity: int = Form(100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not title.strip():
        return RedirectResponse(
            f"/admin/events/{event_id}/edit?error=title_required",
            status_code=303,
        )

    # Update ALL editable fields
    event.title = title.strip()
    event.description = description.strip()
    event.location = location.strip() or "KPI"
    event.capacity = max(int(capacity), 1)

    event.start_time = parse_dt(start_time) or event.start_time
    event.end_time = parse_dt(end_time)
    event.registration_deadline = parse_dt(registration_deadline)

    db.commit()
    db.refresh(event)

    return RedirectResponse("/admin/events?updated=1", status_code=303)


@router.post("/events/{event_id}/delete")
def admin_delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    event = db.get(Event, event_id)
    if not event:
        return RedirectResponse("/admin/events?deleted=0", status_code=303)

    db.delete(event)
    db.commit()

    return RedirectResponse("/admin/events?deleted=1", status_code=303)

@router.post("/events/{event_id}/generate_summary")
def admin_generate_summary(
    event_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    short = generate_short_description(event.title, event.description or "")

    # Option A (recommended): store in DB field event.short_description
    # Make sure your Event model has short_description = Column(String, nullable=True)
    if hasattr(event, "short_description"):
        event.short_description = short
        db.commit()
        db.refresh(event)

    # Option B (no DB change): you can store it elsewhere (not recommended)

    return RedirectResponse(f"/admin/events/{event_id}/edit?summary=1", status_code=303)


@router.post("/events/{event_id}/generate_qr")
def admin_generate_qr(
    event_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # This is the URL encoded into the QR.
    # Choose what you want users to land on:
    # - home page anchored to the event
    # - a dedicated event page
    # - a special /qr/{event_id} endpoint (optional)
    register_url = f"{APP_BASE_URL}/?focus={event_id}"

    out_path = Path("app/static/qr") / f"event_{event_id}.png"
    generate_event_qr_png(data=register_url, out_path=out_path)

    return RedirectResponse(f"/admin/events/{event_id}/edit?qr=1", status_code=303)
