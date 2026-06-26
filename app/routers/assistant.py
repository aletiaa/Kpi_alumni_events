from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import APP_NAME
from app.db import get_db
from app.deps import get_current_identity
from app.models import Event, News, User
from app.services.assistant_nlp import parse_event_query

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantQueryIn(BaseModel):
    query: str


@router.get("")
def assistant_page(request: Request, ident=Depends(get_current_identity)):
    return request.app.state.templates.TemplateResponse(
        request,
        "assistant.html",
        {"request": request, "app_name": APP_NAME, "ident": ident},
    )


@router.post("/query")
def assistant_query(payload: AssistantQueryIn, db: Session = Depends(get_db)):
    raw_query = payload.query or ""
    normalized = raw_query.strip().lower()
    quick_links = [
        {
            "keywords": ("mentor", "ментор", "настав", "кар'єр", "career", "cv", "портфоліо"),
            "message": "Я підготував розділ з менторами та профілями, які можуть допомогти з кар'єрою.",
            "links": [
                {"title": "Ментори", "url": "/mentors", "description": "Пошук випускників, які готові консультувати студентів."},
                {"title": "Випускники", "url": "/alumni", "description": "Публічні профілі за факультетом, спеціальністю, групою або роком."},
            ],
        },
        {
            "keywords": ("news", "новин", "оголош", "істор"),
            "message": "Ось розділи, де можна читати й додавати новини спільноти.",
            "links": [
                {"title": "Новини", "url": "/news", "description": "Оголошення, історії випускників і університетські оновлення."},
                {"title": "Адмін: новини", "url": "/admin/news", "description": "Створення публікацій з текстом і зображенням."},
            ],
        },
        {
            "keywords": ("profile", "проф", "фото", "статус", "навич"),
            "message": "Профіль можна оновити в особистому кабінеті.",
            "links": [
                {"title": "Профіль", "url": "/profile", "description": "Фото, статус, навички, менторство, мова і сповіщення."},
            ],
        },
        {
            "keywords": ("chat", "чат", "message", "повідом"),
            "message": "Для спілкування є чати та приватні повідомлення між користувачами одного потоку.",
            "links": [
                {"title": "Чати", "url": "/chats", "description": "Корисні групові чати за факультетом або потоком."},
                {"title": "Повідомлення", "url": "/messages", "description": "Особисті повідомлення користувачам зі спільного потоку."},
            ],
        },
        {
            "keywords": ("survey", "опит", "анкета", "question"),
            "message": "Опитування допомагають збирати дані про кар'єру, країну проживання і потреби alumni-спільноти.",
            "links": [
                {"title": "Опитування", "url": "/surveys", "description": "Анкети для студентів і випускників."},
            ],
        },
        {
            "keywords": ("analytics", "аналіт", "статист", "активн"),
            "message": "Аналітика показує активність сторінок, сесій і час взаємодії користувачів.",
            "links": [
                {"title": "Аналітика", "url": "/analytics", "description": "Зрозумілі метрики відвідуваності й активності."},
                {"title": "Адмін-панель", "url": "/admin", "description": "Короткий dashboard для адміністратора."},
            ],
        },
    ]
    if normalized and not any(word in normalized for word in ("event", "под", "зустр", "лекц", "workshop", "воркшоп", "week", "month")):
        for block in quick_links:
            if any(keyword in normalized for keyword in block["keywords"]):
                return {"message": block["message"], "events": [], "links": block["links"]}

    spec = parse_event_query(payload.query, now=datetime.utcnow())

    q = db.query(Event)
    if spec.start_from:
        q = q.filter(Event.start_time >= spec.start_from)
    if spec.start_to:
        q = q.filter(Event.start_time < spec.start_to)

    events = q.order_by(Event.start_time.asc()).limit(spec.limit).all()

    def fmt_dt(dt):
        return dt.strftime("%Y-%m-%d %H:%M") if dt else ""

    message = "Ось події, які я знайшов."
    if not events:
        message = "Не знайшов подій за цим запитом. Спробуйте згадати дату, формат або тему."

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
        "links": [
            {"title": "Календар подій", "url": "/events", "description": "Переглянути всі зустрічі у календарному вигляді."},
            {"title": "Мої події", "url": "/me/events", "description": "Список подій, на які ви вже зареєструвалися."},
        ] if events else [],
    }
