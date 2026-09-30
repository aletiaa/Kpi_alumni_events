from datetime import datetime
from sqlalchemy import func, update
from app.models import Event, Registration
from app.services.messaging import eligible_user


def register(db, user, event_id):
    if not eligible_user(user):
        return 'verify_email_first'
    # Serialize capacity checks on the same event in SQLite and PostgreSQL.
    changed = db.execute(update(Event).where(Event.id == event_id).values(capacity=Event.capacity)).rowcount
    if not changed:
        return 'event_not_found'
    event = db.get(Event, event_id)
    db.refresh(event)
    if db.query(Registration.id).filter_by(user_id=user.id, event_id=event_id).first():
        return 'already_registered'
    now = datetime.utcnow()
    if event.start_time <= now or (event.registration_deadline and event.registration_deadline <= now):
        return 'deadline_passed'
    count = db.query(func.count(Registration.id)).filter_by(event_id=event_id).scalar() or 0
    if count >= event.capacity:
        return 'full'
    db.add(Registration(user_id=user.id, event_id=event_id))
    db.flush()
    return 'registered'
