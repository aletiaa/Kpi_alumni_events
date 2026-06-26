import calendar
from datetime import date, datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.config import APP_NAME
from app.db import get_db
from app.deps import get_current_identity, require_identity
from app.models import ChatLink, Event, News, Notification, Registration, Survey, SurveyAnswer, User
from app.routers.web import build_events_context
from app.services.specialties import specialty_options

router = APIRouter()


def render(request: Request, template: str, context: dict, status_code: int = 200):
    payload = {"request": request, "app_name": APP_NAME}
    payload.update(context)
    return request.app.state.templates.TemplateResponse(request, template, payload, status_code=status_code)


def clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def parse_int(value: str | None) -> int | None:
    value = clean(value)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_date(value: str | None) -> date | None:
    value = clean(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def build_event_calendar(events: list[Event], year: int | None = None, month: int | None = None) -> dict:
    today = date.today()
    year = year or today.year
    month = month or today.month
    month = min(12, max(1, month))
    cal = calendar.Calendar(firstweekday=0)
    events_by_day: dict[int, list[Event]] = {}
    for event in events:
        if event.start_time and event.start_time.year == year and event.start_time.month == month:
            events_by_day.setdefault(event.start_time.day, []).append(event)
    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year
    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "weeks": cal.monthdayscalendar(year, month),
        "events_by_day": events_by_day,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    }



def same_stream(current: User | None, other: User) -> bool:
    if not current or current.id == other.id:
        return False
    if current.group_name and other.group_name and current.group_name.strip().lower() == other.group_name.strip().lower():
        return True
    if current.graduation_year and other.graduation_year and current.graduation_year == other.graduation_year:
        same_faculty = current.faculty and other.faculty and current.faculty.strip().lower() == other.faculty.strip().lower()
        same_specialty = current.specialty and other.specialty and current.specialty.strip().lower() == other.specialty.strip().lower()
        return bool(same_faculty or same_specialty)
    return False
def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def template_context(request: Request, ident, **context):
    context.setdefault("ident", ident)
    context.setdefault("specialties", specialty_options())
    return context


@router.get("/")
def home(request: Request, db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    now = datetime.utcnow()
    upcoming_events = db.query(Event).filter(Event.start_time >= now).order_by(Event.start_time.asc()).limit(4).all()
    latest_news = db.query(News).filter(News.is_published == True).order_by(News.created_at.desc()).limit(3).all()
    mentors = (
        db.query(User)
        .filter(User.is_profile_public == True, User.is_blocked == False, User.is_mentor == True)
        .order_by(User.full_name.asc())
        .limit(4)
        .all()
    )
    personal_events = []
    unread_messages = 0
    current_user = None
    if ident and ident.role != "admin" and ident.user_id:
        current_user = db.get(User, ident.user_id)
        personal_events = (
            db.query(Event)
            .join(Registration, Registration.event_id == Event.id)
            .filter(Registration.user_id == ident.user_id)
            .order_by(Event.start_time.asc())
            .limit(3)
            .all()
        )
        from app.models import DirectMessage

        unread_messages = db.query(func.count(DirectMessage.id)).filter(
            DirectMessage.receiver_id == ident.user_id,
            DirectMessage.is_read == False,
        ).scalar() or 0
    stats = {
        "events": db.query(func.count(Event.id)).scalar() or 0,
        "users": db.query(func.count(User.id)).filter(User.is_profile_public == True, User.is_blocked == False).scalar() or 0,
        "mentors": db.query(func.count(User.id)).filter(User.is_profile_public == True, User.is_mentor == True).scalar() or 0,
        "news": db.query(func.count(News.id)).filter(News.is_published == True).scalar() or 0,
    }
    return render(
        request,
        "home.html",
        {
            "ident": ident,
            "current_user": current_user,
            "upcoming_events": upcoming_events,
            "latest_news": latest_news,
            "mentors": mentors,
            "personal_events": personal_events,
            "unread_messages": unread_messages,
            "stats": stats,
        },
    )


@router.get("/events")
def events(
    request: Request,
    year: str = "",
    month: str = "",
    db: Session = Depends(get_db),
    ident=Depends(get_current_identity),
):
    context = build_events_context(request, db, ident)
    context["calendar"] = build_event_calendar(
        context["events"],
        year=parse_int(year),
        month=parse_int(month),
    )
    return render(request, "events.html", context)


@router.get("/search")
def global_search(request: Request, q: str = "", db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    term = clean(q) or ""
    events_found = []
    news_found = []
    users_found = []
    if term:
        like = f"%{term}%"
        events_found = (
            db.query(Event)
            .filter(or_(Event.title.ilike(like), Event.description.ilike(like), Event.short_description.ilike(like), Event.location.ilike(like)))
            .order_by(Event.start_time.asc())
            .limit(8)
            .all()
        )
        news_found = (
            db.query(News)
            .filter(News.is_published == True)
            .filter(or_(News.title.ilike(like), News.short_description.ilike(like), News.content.ilike(like)))
            .order_by(News.created_at.desc())
            .limit(8)
            .all()
        )
        users_found = (
            db.query(User)
            .filter(User.is_profile_public == True, User.is_blocked == False)
            .filter(or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                User.bio.ilike(like),
                User.faculty.ilike(like),
                User.specialty.ilike(like),
                User.group_name.ilike(like),
                User.status.ilike(like),
                User.current_position.ilike(like),
                User.company.ilike(like),
                User.skills.ilike(like),
                User.help_topics.ilike(like),
                User.mentorship_topics.ilike(like),
            ))
            .order_by(User.full_name.asc())
            .limit(8)
            .all()
        )
    return render(
        request,
        "search.html",
        template_context(request, ident, q=term, events_found=events_found, news_found=news_found, users_found=users_found),
    )


@router.get("/news")
def news_list(request: Request, db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    news = (
        db.query(News)
        .filter(News.is_published == True)
        .order_by(News.created_at.desc())
        .all()
    )
    return render(request, "news/list.html", {"ident": ident, "news_items": news})


@router.get("/news/{news_id}")
def news_detail(news_id: int, request: Request, db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    item = db.query(News).filter(News.id == news_id, News.is_published == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="Новину не знайдено")
    return render(request, "news/detail.html", {"ident": ident, "item": item})


@router.get("/profile")
def profile_form(request: Request, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/admin", status_code=303)
    user = db.get(User, ident.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    return render(request, "profile.html", template_context(request, ident, user=user))


@router.post("/profile")
def profile_save(
    request: Request,
    full_name: str = Form(...),
    group_name: str = Form(""),
    birth_date: str = Form(""),
    faculty: str = Form(""),
    specialty: str = Form(""),
    graduation_year: str = Form(""),
    bio: str = Form(""),
    telegram_username: str = Form(""),
    linkedin_url: str = Form(""),
    avatar_url: str = Form(""),
    status: str = Form(""),
    city_country: str = Form(""),
    current_position: str = Form(""),
    company: str = Form(""),
    skills: str = Form(""),
    help_topics: str = Form(""),
    is_mentor: str | None = Form(None),
    mentorship_topics: str = Form(""),
    preferred_language: str = Form("uk"),
    notifications_enabled: str | None = Form(None),
    is_profile_public: str | None = Form(None),
    db: Session = Depends(get_db),
    ident=Depends(require_identity),
):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/admin", status_code=303)
    user = db.get(User, ident.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")

    linkedin = clean(linkedin_url)
    avatar = clean(avatar_url)
    if avatar and not is_http_url(avatar):
        return render(request, "profile.html", template_context(request, ident, user=user, error="URL фото має починатися з http:// або https://"), status_code=400)
    if linkedin and not is_http_url(linkedin):
        return render(request, "profile.html", template_context(request, ident, user=user, error="LinkedIn URL має починатися з http:// або https://"), status_code=400)

    user.full_name = full_name.strip() or user.full_name
    user.group_name = clean(group_name)
    user.birth_date = parse_date(birth_date)
    user.faculty = clean(faculty)
    user.specialty = clean(specialty)
    user.graduation_year = parse_int(graduation_year)
    user.bio = clean(bio)
    user.telegram_username = clean(telegram_username)
    user.linkedin_url = linkedin
    user.avatar_url = avatar
    user.status = clean(status)
    user.city_country = clean(city_country)
    user.current_position = clean(current_position)
    user.company = clean(company)
    user.skills = clean(skills)
    user.help_topics = clean(help_topics)
    user.is_mentor = bool(is_mentor)
    user.mentorship_topics = clean(mentorship_topics)
    user.preferred_language = preferred_language if preferred_language in {"uk", "en"} else "uk"
    user.notifications_enabled = bool(notifications_enabled)
    user.is_profile_public = bool(is_profile_public)
    db.commit()
    return RedirectResponse("/profile?saved=1", status_code=303)


@router.get("/alumni")
def alumni_list(
    request: Request,
    q: str = "",
    faculty: str = "",
    specialty: str = "",
    group_name: str = "",
    graduation_year: str = "",
    db: Session = Depends(get_db),
    ident=Depends(get_current_identity),
):
    query = db.query(User).filter(User.is_profile_public == True, User.is_blocked == False)
    if clean(q):
        like = f"%{q.strip()}%"
        query = query.filter(or_(
            User.full_name.ilike(like),
            User.email.ilike(like),
            User.bio.ilike(like),
            User.status.ilike(like),
            User.current_position.ilike(like),
            User.company.ilike(like),
            User.skills.ilike(like),
            User.help_topics.ilike(like),
            User.mentorship_topics.ilike(like),
        ))
    if clean(faculty):
        query = query.filter(User.faculty.ilike(f"%{faculty.strip()}%"))
    if clean(specialty):
        query = query.filter(User.specialty.ilike(f"%{specialty.strip()}%"))
    if clean(group_name):
        query = query.filter(User.group_name.ilike(f"%{group_name.strip()}%"))
    grad = parse_int(graduation_year)
    if grad:
        query = query.filter(User.graduation_year == grad)
    users = query.order_by(User.full_name.asc()).limit(100).all()
    current_user = db.get(User, ident.user_id) if ident and ident.user_id else None
    can_message_ids = {u.id for u in users if same_stream(current_user, u)}
    return render(request, "alumni/list.html", template_context(request, ident, users=users, can_message_ids=can_message_ids))


@router.get("/mentors")
def mentors_list(
    request: Request,
    q: str = "",
    faculty: str = "",
    specialty: str = "",
    db: Session = Depends(get_db),
    ident=Depends(get_current_identity),
):
    query = db.query(User).filter(
        User.is_profile_public == True,
        User.is_blocked == False,
        User.is_mentor == True,
    )
    if clean(q):
        like = f"%{q.strip()}%"
        query = query.filter(or_(
            User.full_name.ilike(like),
            User.bio.ilike(like),
            User.status.ilike(like),
            User.current_position.ilike(like),
            User.company.ilike(like),
            User.skills.ilike(like),
            User.help_topics.ilike(like),
            User.mentorship_topics.ilike(like),
        ))
    if clean(faculty):
        query = query.filter(User.faculty.ilike(f"%{faculty.strip()}%"))
    if clean(specialty):
        query = query.filter(User.specialty.ilike(f"%{specialty.strip()}%"))
    mentors = query.order_by(User.full_name.asc()).limit(100).all()
    current_user = db.get(User, ident.user_id) if ident and ident.user_id else None
    can_message_ids = {u.id for u in mentors if same_stream(current_user, u)}
    return render(
        request,
        "mentors/list.html",
        template_context(request, ident, mentors=mentors, can_message_ids=can_message_ids, q=q, faculty=faculty, specialty=specialty),
    )


@router.get("/chats")
def chats_list(
    request: Request,
    faculty: str = "",
    specialty: str = "",
    group_name: str = "",
    graduation_year: str = "",
    db: Session = Depends(get_db),
    ident=Depends(get_current_identity),
):
    query = db.query(ChatLink).filter(ChatLink.is_active == True)
    if clean(faculty):
        query = query.filter(ChatLink.faculty.ilike(f"%{faculty.strip()}%"))
    if clean(specialty):
        query = query.filter(ChatLink.specialty.ilike(f"%{specialty.strip()}%"))
    if clean(group_name):
        query = query.filter(ChatLink.group_name.ilike(f"%{group_name.strip()}%"))
    grad = parse_int(graduation_year)
    if grad:
        query = query.filter(ChatLink.graduation_year == grad)
    links = query.order_by(ChatLink.created_at.desc()).all()
    return render(request, "chats/list.html", {"ident": ident, "links": links})


@router.get("/surveys")
def surveys_list(request: Request, db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    surveys = db.query(Survey).filter(Survey.is_active == True).order_by(Survey.created_at.desc()).all()
    return render(request, "surveys/list.html", {"ident": ident, "surveys": surveys})


@router.get("/surveys/{survey_id}")
def survey_detail(survey_id: int, request: Request, db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    survey = (
        db.query(Survey)
        .options(joinedload(Survey.questions))
        .filter(Survey.id == survey_id, Survey.is_active == True)
        .first()
    )
    if not survey:
        raise HTTPException(status_code=404, detail="Опитування не знайдено")
    return render(request, "surveys/detail.html", {"ident": ident, "survey": survey})


@router.post("/surveys/{survey_id}")
async def survey_submit(survey_id: int, request: Request, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/surveys", status_code=303)
    survey = db.query(Survey).options(joinedload(Survey.questions)).filter(Survey.id == survey_id, Survey.is_active == True).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Опитування не знайдено")
    form = await request.form()
    for question in survey.questions:
        answer = clean(str(form.get(f"question_{question.id}", "")))
        if answer:
            db.add(SurveyAnswer(survey_id=survey.id, question_id=question.id, user_id=ident.user_id, answer_text=answer))
    db.commit()
    return RedirectResponse(f"/surveys/{survey_id}?submitted=1", status_code=303)


@router.get("/notifications")
def notifications_list(request: Request, db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role == "admin" or not ident.user_id:
        return RedirectResponse("/admin", status_code=303)
    items = (
        db.query(Notification)
        .filter(Notification.user_id == ident.user_id)
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )
    unread_count = db.query(func.count(Notification.id)).filter(
        Notification.user_id == ident.user_id,
        Notification.is_read == False,
    ).scalar() or 0
    return render(request, "notifications/list.html", {"ident": ident, "items": items, "unread_count": unread_count})


@router.post("/notifications/read-all")
def notifications_read_all(db: Session = Depends(get_db), ident=Depends(require_identity)):
    if ident.role != "admin" and ident.user_id:
        db.query(Notification).filter(Notification.user_id == ident.user_id, Notification.is_read == False).update({"is_read": True})
        db.commit()
    return RedirectResponse("/notifications", status_code=303)




