from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event
from app.services.assistant_nlp import parse_event_query

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantQueryIn(BaseModel):
    query: str


@router.post("/query")
def assistant_query(payload: AssistantQueryIn, db: Session = Depends(get_db)):
    spec = parse_event_query(payload.query, now=datetime.utcnow())

    q = db.query(Event)

    if spec.start_from:
        q = q.filter(Event.start_time >= spec.start_from)
    if spec.start_to:
        q = q.filter(Event.start_time < spec.start_to)

    q = q.order_by(Event.start_time.asc()).limit(spec.limit)

    events = q.all()

    def fmt_dt(dt):
        return dt.strftime("%Y-%m-%d %H:%M") if dt else ""

    message = "Here are the matching events."
    if not events:
        message = "I couldn’t find events for that request."

    return {
        "message": message,
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "start_time": fmt_dt(e.start_time),
                "location": e.location or "",
            }
            for e in events
        ],
    }
