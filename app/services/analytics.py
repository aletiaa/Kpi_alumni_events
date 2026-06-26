from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import PageDuration, PageView, UserActivity

PAGE_LABELS: dict[str, tuple[str, str]] = {
    "/": ("Головна сторінка", "Стартова сторінка AlumnixHub"),
    "/events": ("Події", "Перегляд подій, реакцій і коментарів"),
    "/news": ("Новини", "Оголошення, публікації та можливості"),
    "/alumni": ("Пошук випускників", "Публічні профілі alumni-спільноти"),
    "/mentors": ("Ментори", "Випускники, які готові допомагати студентам"),
    "/chats": ("Чати", "Тематичні обговорення спільноти"),
    "/assistant": ("ШІ-асистент", "Пошук подій природною мовою"),
    "/profile": ("Профіль", "Особистий кабінет користувача"),
    "/search": ("Пошук", "Пошук по випускниках, подіях і новинах"),
    "/notifications": ("Сповіщення", "Повідомлення для користувача"),
    "/messages": ("Повідомлення", "Особисте листування між користувачами"),
    "/me/events": ("Мої події", "Події, на які користувач зареєструвався"),
    "/surveys": ("Опитування", "Анкети та зворотний зв’язок"),
    "/login": ("Вхід", "Авторизація користувача"),
    "/register": ("Реєстрація", "Створення нового облікового запису"),
    "/verify": ("Підтвердження email", "Перевірка електронної пошти"),
    "/forgot-password": ("Відновлення пароля", "Запит на скидання пароля"),
    "/reset-password": ("Скидання пароля", "Створення нового пароля"),
    "/admin": ("Адмін-панель", "Керування платформою та перегляд статистики"),
    "/admin/events": ("Адмін: події", "Керування подіями"),
    "/admin/news": ("Адмін: новини", "Керування новинами"),
    "/admin/users": ("Адмін: користувачі", "Керування профілями"),
    "/admin/chats": ("Адмін: чати", "Модерація чатів"),
    "/admin/surveys": ("Адмін: опитування", "Керування анкетами"),
}


def _unknown_page_label(path: str) -> tuple[str, str]:
    if path.startswith("/admin/"):
        return ("Адмін-панель", "Додаткова сторінка керування платформою")
    return ("Інший розділ платформи", "Сторінка застосунку без окремої назви")


def page_metadata(page: str | None) -> dict[str, str]:
    path = urlsplit(page or "/").path or "/"
    if path.startswith("/events/"):
        return {"path": path, "title": "Сторінка події", "description": "Деталі окремої події"}
    if path.startswith("/news/"):
        return {"path": path, "title": "Сторінка новини", "description": "Повний текст новини або оголошення"}
    if path.startswith("/messages/"):
        return {"path": path, "title": "Діалог повідомлень", "description": "Переписка з іншим користувачем"}
    if path.startswith("/surveys/"):
        return {"path": path, "title": "Сторінка опитування", "description": "Заповнення анкети користувачем"}

    title, description = PAGE_LABELS.get(path, _unknown_page_label(path))
    return {"path": path, "title": title, "description": description}


def _friendly_duration(seconds: float) -> str:
    if seconds >= 60:
        minutes = seconds / 60
        return f"{minutes:.1f} хв"
    return f"{seconds:.1f} с"


def _as_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def record_page_duration(
    db: Session,
    *,
    user_id: int | None,
    session_id: str,
    page: str,
    opened_at: datetime,
    closed_at: datetime,
    duration_seconds: int,
) -> PageDuration:
    duration_seconds = max(0, int(duration_seconds))
    opened_at = _as_naive_utc(opened_at)
    closed_at = _as_naive_utc(closed_at)
    calculated_closed_at = opened_at + timedelta(seconds=duration_seconds)
    if closed_at < opened_at or abs((closed_at - calculated_closed_at).total_seconds()) > 5:
        closed_at = calculated_closed_at
    row = PageDuration(
        user_id=user_id,
        session_id=session_id,
        page=page[:1000],
        opened_at=opened_at,
        closed_at=closed_at,
        duration_seconds=duration_seconds,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def analytics_overview(db: Session) -> dict[str, float | int]:
    total_page_views = db.query(func.count(PageView.id)).scalar() or 0
    unique_sessions = db.query(func.count(func.distinct(PageView.session_id))).scalar() or 0
    authenticated_views = db.query(func.count(PageView.id)).filter(PageView.user_id.isnot(None)).scalar() or 0
    avg_request_duration = db.query(func.avg(PageView.request_duration_ms)).scalar() or 0
    avg_page_duration = db.query(func.avg(PageDuration.duration_seconds)).scalar() or 0
    avg_session_duration = db.query(func.avg(UserActivity.duration_seconds)).scalar() or 0
    return {
        "total_page_views": total_page_views,
        "unique_sessions": unique_sessions,
        "authenticated_views": authenticated_views,
        "anonymous_views": max(0, total_page_views - authenticated_views),
        "avg_request_duration_ms": round(float(avg_request_duration), 2),
        "avg_page_duration_seconds": round(float(avg_page_duration), 2),
        "avg_session_duration_seconds": round(float(avg_session_duration), 2),
    }


def top_pages(db: Session, limit: int = 10) -> list[dict[str, object]]:
    rows = (
        db.query(
            PageView.page.label("page"),
            func.count(PageView.id).label("views"),
            func.avg(PageView.request_duration_ms).label("avg_request_ms"),
        )
        .group_by(PageView.page)
        .order_by(func.count(PageView.id).desc())
        .all()
    )
    merged: dict[str, dict[str, object]] = {}
    weighted_duration: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        meta = page_metadata(row.page)
        views = int(row.views or 0)
        path = meta["path"]
        item = merged.setdefault(
            path,
            {
                "page": path,
                "title": meta["title"],
                "description": meta["description"],
                "views": 0,
                "avg_request_ms": 0.0,
            },
        )
        item["views"] = int(item["views"]) + views
        weighted_duration[path] += float(row.avg_request_ms or 0) * views

    for path, item in merged.items():
        views = max(1, int(item["views"]))
        item["avg_request_ms"] = round(weighted_duration[path] / views, 2)

    return sorted(merged.values(), key=lambda item: int(item["views"]), reverse=True)[:limit]


def average_page_duration_by_page(db: Session, limit: int = 10) -> list[dict[str, object]]:
    rows = (
        db.query(
            PageDuration.page.label("page"),
            func.count(PageDuration.id).label("samples"),
            func.avg(PageDuration.duration_seconds).label("avg_seconds"),
        )
        .group_by(PageDuration.page)
        .order_by(func.avg(PageDuration.duration_seconds).desc())
        .all()
    )
    merged: dict[str, dict[str, object]] = {}
    weighted_seconds: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        meta = page_metadata(row.page)
        samples = int(row.samples or 0)
        path = meta["path"]
        item = merged.setdefault(
            path,
            {
                "page": path,
                "title": meta["title"],
                "description": meta["description"],
                "samples": 0,
                "avg_seconds": 0.0,
                "avg_label": "0.0 с",
            },
        )
        item["samples"] = int(item["samples"]) + samples
        weighted_seconds[path] += float(row.avg_seconds or 0) * samples

    for path, item in merged.items():
        samples = max(1, int(item["samples"]))
        seconds = round(weighted_seconds[path] / samples, 2)
        item["avg_seconds"] = seconds
        item["avg_label"] = _friendly_duration(seconds)

    return sorted(merged.values(), key=lambda item: float(item["avg_seconds"]), reverse=True)[:limit]


def daily_page_views(db: Session, limit: int = 14) -> list[dict[str, object]]:
    rows = (
        db.query(
            func.date(PageView.viewed_at).label("day"),
            func.count(PageView.id).label("views"),
        )
        .group_by(func.date(PageView.viewed_at))
        .order_by(func.date(PageView.viewed_at).desc())
        .limit(limit)
        .all()
    )
    return [
        {"day": str(row.day), "views": int(row.views or 0)}
        for row in reversed(rows)
    ]


def analytics_dashboard_data(db: Session) -> dict[str, object]:
    overview = analytics_overview(db)
    pages = top_pages(db, limit=8)
    durations = average_page_duration_by_page(db, limit=8)
    daily = daily_page_views(db, limit=14)
    max_views = max([int(row["views"]) for row in pages] + [1])
    max_duration = max([float(row["avg_seconds"]) for row in durations] + [1.0])
    max_daily = max([int(row["views"]) for row in daily] + [1])
    return {
        "overview": overview,
        "top_pages": pages,
        "page_durations": durations,
        "daily_views": daily,
        "max_views": max_views,
        "max_duration": max_duration,
        "max_daily": max_daily,
    }
