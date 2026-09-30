"""Offline adapter for aletiaa/Diploma; no Telegram credentials or network calls."""
from sqlalchemy import func

from app.models import Event, Registration

# Synthetic recipients cannot be mistaken for Telegram chat IDs.
DEMO_RECIPIENTS = (
    ("demo-alumni-01", "alumni"),
    ("demo-alumni-02", "alumni"),
    ("demo-student-01", "student"),
)


def demo_recipients(audience):
    return [name for name, role in DEMO_RECIPIENTS if audience == "all" or role == audience]


def export_events(db):
    """Match BOT/handlers/events/utils/event_utils.py's events.json schema."""
    counts = dict(db.query(Registration.event_id, func.count(Registration.id))
                  .group_by(Registration.event_id).all())
    return [{"id": event.id, "title": event.title, "description": event.description or "",
             "datetime": event.start_time.isoformat(), "max_seats": event.capacity,
             "available_seats": max(0, event.capacity - counts.get(event.id, 0))}
            for event in db.query(Event).order_by(Event.start_time, Event.id).all()]
