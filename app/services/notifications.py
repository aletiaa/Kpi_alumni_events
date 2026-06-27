from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Event, Notification, Registration, User
from app.services.email_service import send_email


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    body: str,
    url: str | None = None,
    kind: str = "info",
    email_to: str | None = None,
) -> Notification:
    row = Notification(
        user_id=user_id,
        title=title[:200],
        body=body[:2000],
        url=(url or "")[:500] or None,
        kind=kind[:40] or "info",
    )
    db.add(row)
    if email_to:
        link_html = f'<p><a href="{url}">Відкрити</a></p>' if url else ""
        try:
            send_email(
                to_email=email_to,
                subject=title,
                html_body=f"<h2>{title}</h2><p>{body}</p>{link_html}",
            )
        except Exception:
            # Email delivery must not block the in-app notification flow.
            pass
    return row


def notify_new_event(db: Session, event: Event) -> int:
    users = (
        db.query(User)
        .filter(
            User.is_active == True,
            User.is_blocked == False,
            User.role.in_(["student", "alumni", "guest"]),
            User.notifications_enabled == True,
        )
        .all()
    )
    body = f"Нова подія: {event.title}. Локація: {event.location}. Початок: {event.start_time}."
    for user in users:
        create_notification(
            db,
            user_id=user.id,
            title="Нова подія в AlumnixHub",
            body=body,
            url=f"/events#event-{event.id}",
            kind="event",
            email_to=user.email if user.notifications_enabled else None,
        )
    return len(users)


def notify_event_reminder(db: Session, event: Event) -> int:
    users = (
        db.query(User)
        .join(Registration, Registration.user_id == User.id)
        .filter(
            Registration.event_id == event.id,
            User.is_active == True,
            User.is_blocked == False,
            User.notifications_enabled == True,
        )
        .all()
    )
    body = f"Нагадування: ви зареєстровані на подію «{event.title}». Початок: {event.start_time}. Локація: {event.location}."
    for user in users:
        create_notification(
            db,
            user_id=user.id,
            title="Нагадування про подію",
            body=body,
            url=f"/events#event-{event.id}",
            kind="event_reminder",
            email_to=user.email if user.notifications_enabled else None,
        )
    return len(users)


def notify_direct_message(db: Session, *, sender: User, receiver: User, message_preview: str) -> Notification:
    return create_notification(
        db,
        user_id=receiver.id,
        title=f"Нове повідомлення від {sender.full_name}",
        body=message_preview[:500],
        url=f"/messages/{sender.id}",
        kind="message",
        email_to=receiver.email if receiver.notifications_enabled else None,
    )
