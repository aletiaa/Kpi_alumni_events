from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import APP_NAME
from app.db import get_db
from app.deps import require_admin
from app.models import ChatLink, News, Survey, SurveyAnswer, SurveyQuestion, User

router = APIRouter(prefix="/admin", tags=["admin-platform"])
NEWS_UPLOAD_DIR = Path("app/static/uploads/news")
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


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


def as_bool(value: str | None) -> bool:
    return bool(value)


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def save_news_image(image_file: UploadFile | None) -> str | None:
    if not image_file or not image_file.filename:
        return None
    suffix = Path(image_file.filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Завантажте зображення у форматі JPG, PNG, WEBP або GIF.")
    NEWS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    destination = NEWS_UPLOAD_DIR / filename
    with destination.open("wb") as buffer:
        copyfileobj(image_file.file, buffer)
    return f"/static/uploads/news/{filename}"


@router.get("/news")
def admin_news(request: Request, status: str = "", db: Session = Depends(get_db), admin=Depends(require_admin)):
    query = db.query(News)
    if status == "published":
        query = query.filter(News.is_published == True)
    elif status == "draft":
        query = query.filter(News.is_published == False)
    items = query.order_by(News.created_at.desc()).all()
    moderation_count = db.query(func.count(News.id)).filter(News.is_published == False).scalar() or 0
    return render(
        request,
        "admin/news.html",
        {"ident": admin, "news_items": items, "status": status, "moderation_count": moderation_count},
    )


@router.get("/news/create")
def admin_news_create_form(request: Request, admin=Depends(require_admin)):
    return render(request, "admin/news_form.html", {"ident": admin, "item": None})


@router.post("/news/create")
def admin_news_create(
    request: Request,
    title: str = Form(...),
    short_description: str = Form(""),
    content: str = Form(...),
    image_url: str = Form(""),
    image_source_url: str = Form(""),
    image_file: UploadFile | None = File(None),
    is_published: str | None = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    try:
        uploaded_image_url = save_news_image(image_file)
    except ValueError as exc:
        return render(request, "admin/news_form.html", {"ident": admin, "item": None, "error": str(exc)}, status_code=400)
    clean_image_url = clean(image_url)
    if clean_image_url and not (clean_image_url.startswith("/static/") or is_http_url(clean_image_url)):
        return render(request, "admin/news_form.html", {"ident": admin, "item": None, "error": "URL зображення має починатися з /static/, http:// або https://"}, status_code=400)
    item = News(
        title=title.strip(),
        short_description=clean(short_description),
        content=content.strip(),
        image_url=uploaded_image_url or clean_image_url,
        image_source_url=clean(image_source_url),
        is_published=as_bool(is_published),
    )
    db.add(item)
    db.commit()
    return RedirectResponse("/admin/news?created=1", status_code=303)


@router.get("/news/{news_id}/edit")
def admin_news_edit_form(news_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    item = db.get(News, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="Новину не знайдено")
    return render(request, "admin/news_form.html", {"ident": admin, "item": item})


@router.post("/news/{news_id}/edit")
def admin_news_edit(
    news_id: int,
    request: Request,
    title: str = Form(...),
    short_description: str = Form(""),
    content: str = Form(...),
    image_url: str = Form(""),
    image_source_url: str = Form(""),
    image_file: UploadFile | None = File(None),
    is_published: str | None = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    item = db.get(News, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="Новину не знайдено")
    try:
        uploaded_image_url = save_news_image(image_file)
    except ValueError as exc:
        return render(request, "admin/news_form.html", {"ident": admin, "item": item, "error": str(exc)}, status_code=400)
    clean_image_url = clean(image_url)
    if clean_image_url and not (clean_image_url.startswith("/static/") or is_http_url(clean_image_url)):
        return render(request, "admin/news_form.html", {"ident": admin, "item": item, "error": "URL зображення має починатися з /static/, http:// або https://"}, status_code=400)
    item.title = title.strip()
    item.short_description = clean(short_description)
    item.content = content.strip()
    item.image_url = uploaded_image_url or clean_image_url or item.image_url
    item.image_source_url = clean(image_source_url)
    item.is_published = as_bool(is_published)
    item.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/admin/news?updated=1", status_code=303)


@router.post("/news/{news_id}/delete")
def admin_news_delete(news_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    item = db.get(News, news_id)
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/admin/news?deleted=1", status_code=303)


@router.post("/news/{news_id}/toggle")
def admin_news_toggle(news_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    item = db.get(News, news_id)
    if item:
        item.is_published = not item.is_published
        db.commit()
    return RedirectResponse("/admin/news", status_code=303)


@router.get("/chats")
def admin_chats(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    links = db.query(ChatLink).order_by(ChatLink.created_at.desc()).all()
    return render(request, "admin/chats.html", {"ident": admin, "links": links})


@router.get("/chats/create")
def admin_chat_create_form(request: Request, admin=Depends(require_admin)):
    return render(request, "admin/chat_form.html", {"ident": admin, "link": None})


@router.post("/chats/create")
def admin_chat_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    url: str = Form(...),
    faculty: str = Form(""),
    specialty: str = Form(""),
    group_name: str = Form(""),
    graduation_year: str = Form(""),
    is_active: str | None = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    if not is_http_url(url.strip()):
        return render(request, "admin/chat_form.html", {"ident": admin, "link": None, "error": "Посилання на чат має починатися з http:// або https://"}, status_code=400)
    db.add(ChatLink(
        title=title.strip(), description=clean(description), url=url.strip(), faculty=clean(faculty),
        specialty=clean(specialty), group_name=clean(group_name), graduation_year=parse_int(graduation_year),
        is_active=as_bool(is_active),
    ))
    db.commit()
    return RedirectResponse("/admin/chats?created=1", status_code=303)


@router.get("/chats/{chat_id}/edit")
def admin_chat_edit_form(chat_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    link = db.get(ChatLink, chat_id)
    if not link:
        raise HTTPException(status_code=404, detail="Посилання на чат не знайдено")
    return render(request, "admin/chat_form.html", {"ident": admin, "link": link})


@router.post("/chats/{chat_id}/edit")
def admin_chat_edit(
    chat_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    url: str = Form(...),
    faculty: str = Form(""),
    specialty: str = Form(""),
    group_name: str = Form(""),
    graduation_year: str = Form(""),
    is_active: str | None = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    link = db.get(ChatLink, chat_id)
    if not link:
        raise HTTPException(status_code=404, detail="Посилання на чат не знайдено")
    if not is_http_url(url.strip()):
        return render(request, "admin/chat_form.html", {"ident": admin, "link": link, "error": "Посилання на чат має починатися з http:// або https://"}, status_code=400)
    link.title = title.strip()
    link.description = clean(description)
    link.url = url.strip()
    link.faculty = clean(faculty)
    link.specialty = clean(specialty)
    link.group_name = clean(group_name)
    link.graduation_year = parse_int(graduation_year)
    link.is_active = as_bool(is_active)
    db.commit()
    return RedirectResponse("/admin/chats?updated=1", status_code=303)


@router.post("/chats/{chat_id}/delete")
def admin_chat_delete(chat_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    link = db.get(ChatLink, chat_id)
    if link:
        db.delete(link)
        db.commit()
    return RedirectResponse("/admin/chats?deleted=1", status_code=303)


@router.post("/chats/{chat_id}/toggle")
def admin_chat_toggle(chat_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    link = db.get(ChatLink, chat_id)
    if link:
        link.is_active = not link.is_active
        db.commit()
    return RedirectResponse("/admin/chats", status_code=303)


@router.get("/surveys")
def admin_surveys(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    surveys = db.query(Survey).order_by(Survey.created_at.desc()).all()
    return render(request, "admin/surveys.html", {"ident": admin, "surveys": surveys})


@router.get("/surveys/create")
def admin_survey_create_form(request: Request, admin=Depends(require_admin)):
    return render(request, "admin/survey_form.html", {"ident": admin, "survey": None})


@router.post("/surveys/create")
def admin_survey_create(title: str = Form(...), description: str = Form(""), is_active: str | None = Form(None), db: Session = Depends(get_db), admin=Depends(require_admin)):
    db.add(Survey(title=title.strip(), description=clean(description), is_active=as_bool(is_active)))
    db.commit()
    return RedirectResponse("/admin/surveys?created=1", status_code=303)


@router.get("/surveys/{survey_id}/edit")
def admin_survey_edit_form(survey_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Опитування не знайдено")
    return render(request, "admin/survey_form.html", {"ident": admin, "survey": survey})


@router.post("/surveys/{survey_id}/edit")
def admin_survey_edit(survey_id: int, title: str = Form(...), description: str = Form(""), is_active: str | None = Form(None), db: Session = Depends(get_db), admin=Depends(require_admin)):
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Опитування не знайдено")
    survey.title = title.strip()
    survey.description = clean(description)
    survey.is_active = as_bool(is_active)
    db.commit()
    return RedirectResponse("/admin/surveys?updated=1", status_code=303)


@router.post("/surveys/{survey_id}/delete")
def admin_survey_delete(survey_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    survey = db.get(Survey, survey_id)
    if survey:
        db.delete(survey)
        db.commit()
    return RedirectResponse("/admin/surveys?deleted=1", status_code=303)


@router.get("/surveys/{survey_id}/questions")
def admin_survey_questions(survey_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    survey = db.query(Survey).options(joinedload(Survey.questions)).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Опитування не знайдено")
    return render(request, "admin/survey_questions.html", {"ident": admin, "survey": survey})


@router.get("/surveys/{survey_id}/questions/create")
def admin_survey_question_create_form(survey_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Опитування не знайдено")
    return render(request, "admin/survey_question_form.html", {"ident": admin, "survey": survey})


@router.post("/surveys/{survey_id}/questions/create")
def admin_survey_question_create(survey_id: int, question_text: str = Form(...), question_type: str = Form("text"), options_text: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_admin)):
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Опитування не знайдено")
    qtype = question_type if question_type in {"text", "single_choice"} else "text"
    db.add(SurveyQuestion(survey_id=survey_id, question_text=question_text.strip(), question_type=qtype, options_text=clean(options_text)))
    db.commit()
    return RedirectResponse(f"/admin/surveys/{survey_id}/questions?created=1", status_code=303)


@router.post("/survey-questions/{question_id}/delete")
def admin_survey_question_delete(question_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    question = db.get(SurveyQuestion, question_id)
    survey_id = question.survey_id if question else None
    if question:
        db.delete(question)
        db.commit()
    return RedirectResponse(f"/admin/surveys/{survey_id}/questions?deleted=1" if survey_id else "/admin/surveys", status_code=303)


@router.get("/surveys/{survey_id}/results")
def admin_survey_results(survey_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    survey = db.query(Survey).options(joinedload(Survey.questions).joinedload(SurveyQuestion.answers)).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Опитування не знайдено")
    grouped = []
    total_answers = 0
    for question in survey.questions:
        answers = [a.answer_text for a in question.answers]
        total_answers += len(answers)
        grouped.append({
            "question": question,
            "answers": answers,
            "counts": Counter(answers) if question.question_type == "single_choice" else None,
        })
    return render(request, "admin/survey_results.html", {"ident": admin, "survey": survey, "grouped": grouped, "total_answers": total_answers})


@router.get("/users")
def admin_users(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return render(request, "admin/users.html", {"ident": admin, "users": users})


@router.get("/users/{user_id}")
def admin_user_detail(user_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    return render(request, "admin/user_detail.html", {"ident": admin, "user": user})


@router.post("/users/{user_id}/role")
def admin_user_role(user_id: int, role: str = Form(...), db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.get(User, user_id)
    if user and role in {"student", "alumni", "guest"}:
        user.role = role
        db.commit()
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)


@router.post("/users/{user_id}/block")
def admin_user_block(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.get(User, user_id)
    if user:
        user.is_blocked = not user.is_blocked
        user.is_active = not user.is_blocked
        db.commit()
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)




