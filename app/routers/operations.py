import re
import secrets
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import require_admin
from app.models import AdministratorGrant, AdminAudit, InterestTopic, User, News, TelegramNewsSubmission, BackupRecord
from app.services.admin_permissions import may_manage, require_manager
from app.services.operational_security import token, verify, confirm_password
from app.services.backups import create_backup, verify_backup

router = APIRouter(prefix="/admin/operations", tags=["operations"])


def page(request, db, admin, section, **values):
    return request.app.state.templates.TemplateResponse(request, "admin/operations.html", {
        "request":request, "ident":admin, "app_name":"AlumnixHub", "section":section,
        "csrf":token(admin), "manager":may_manage(db, admin), **values})


@router.get("")
def administrators(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return page(request, db, admin, "admins", users=db.query(User).order_by(User.full_name).all(),
                grants={g.user_id:g for g in db.query(AdministratorGrant)})


@router.post("/administrators/{user_id}")
def administrator_change(user_id: int, csrf: str = Form(""), action: str = Form(""),
                         password: str = Form(""), confirm: str = Form(""),
                         db: Session = Depends(get_db), admin=Depends(require_manager)):
    verify(csrf, admin)
    confirm_password(db, admin, password, confirm)
    user = db.get(User, user_id)
    if not user or not user.is_email_verified or not user.is_active or user.is_blocked:
        raise HTTPException(400, "Потрібен активний користувач із підтвердженим email.")
    if user_id == admin.user_id:
        raise HTTPException(409, "Не можна змінювати власні адміністративні права.")
    if action not in {"admin", "manager", "revoke"}:
        raise HTTPException(400)
    grant = db.get(AdministratorGrant, user_id)
    if action == "revoke":
        if grant:
            db.delete(grant)
    else:
        if not grant:
            grant = AdministratorGrant(user_id=user_id, granted_by=admin.email)
            db.add(grant)
        grant.can_manage_admins = action=="manager"
    db.add(AdminAudit(actor=admin.email, action="administrator:"+action, target=str(user_id)))
    db.commit()
    return RedirectResponse("/admin/operations", 303)


@router.get("/users/{user_id}/delete")
def deletion_review(user_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(require_manager)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404)
    return page(request, db, admin, "delete", user=user)


@router.post("/users/{user_id}/delete")
def delete_user(user_id: int, csrf: str = Form(""), password: str = Form(""),
                confirm: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_manager)):
    verify(csrf, admin)
    confirm_password(db, admin, password, confirm)
    if user_id==admin.user_id or db.get(AdministratorGrant, user_id):
        raise HTTPException(409, "Спочатку відкличте адміністративні права іншого користувача.")
    if not db.get(User, user_id):
        raise HTTPException(404)
    from scripts.prepare_release_data import delete_users
    delete_users(db, [user_id])
    db.add(AdminAudit(actor=admin.email, action="user:delete", target=str(user_id)))
    db.commit()
    return RedirectResponse("/admin/users", 303)


@router.get("/audit")
def audit(request: Request, page_number: int = 1, db: Session = Depends(get_db), admin=Depends(require_admin)):
    page_number = max(1, page_number)
    rows = db.query(AdminAudit).order_by(AdminAudit.id.desc()).offset((page_number-1)*50).limit(51).all()
    return page(request, db, admin, "audit", rows=rows[:50], has_next=len(rows)>50, page_number=page_number)


@router.get("/topics")
def topics(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return page(request, db, admin, "topics", rows=db.query(InterestTopic).order_by(InterestTopic.label_uk).all())


@router.post("/topics")
def save_topic(key: str = Form(""), label_uk: str = Form(..., max_length=120),
               label_en: str = Form(..., max_length=120), aliases: str = Form("", max_length=4000),
               active: str = Form(""), csrf: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify(csrf, admin)
    if not label_uk.strip() or not label_en.strip():
        raise HTTPException(400)
    stopwords = {"та", "що", "і", "й", "або", "для", "the", "and", "or", "of", "to", "for", "a", "in"}
    terms = [label_uk, label_en, *aliases.splitlines()]
    if any(term.strip().casefold() in stopwords for term in terms):
        raise HTTPException(400, "Службові слова не є тематикою інтересів.")
    key = key or "custom_" + secrets.token_hex(6)
    if not re.fullmatch(r"[a-z0-9_]{1,80}", key) or len(aliases.splitlines())>40 or any(len(a)>120 for a in aliases.splitlines()):
        raise HTTPException(400)
    item = db.get(InterestTopic, key)
    if not item:
        item = InterestTopic(key=key)
        db.add(item)
    item.label_uk, item.label_en = label_uk.strip(), label_en.strip()
    item.aliases, item.is_active = aliases.strip(), active=="yes"
    db.commit()
    return RedirectResponse("/admin/operations/topics", 303)


@router.get("/submissions")
def submissions(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    rows = db.query(TelegramNewsSubmission, News, User).join(
        News, News.id==TelegramNewsSubmission.news_id).join(User, User.id==TelegramNewsSubmission.user_id).filter(
        TelegramNewsSubmission.status=="pending").order_by(TelegramNewsSubmission.created_at).limit(100).all()
    return page(request, db, admin, "submissions", rows=rows)


@router.post("/submissions/{update_id}")
def review_submission(update_id: int, action: str = Form(""), confirm: str = Form(""),
                      csrf: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify(csrf, admin)
    if confirm!="yes" or action not in {"publish", "reject"}:
        raise HTTPException(400)
    submission = db.get(TelegramNewsSubmission, update_id)
    news = db.get(News, submission.news_id) if submission else None
    if not news:
        raise HTTPException(404)
    if submission.status!="pending":
        raise HTTPException(409)
    news.is_published = action=="publish"
    submission.status = "published" if action=="publish" else "rejected"
    db.commit()
    return RedirectResponse("/admin/operations/submissions", 303)


@router.get("/backups")
def backups(request: Request, db: Session = Depends(get_db), admin=Depends(require_manager)):
    from app.config import env_bool
    return page(request, db, admin, "backups", rows=db.query(BackupRecord).order_by(
        BackupRecord.created_at.desc()).limit(30).all(), enabled=env_bool("BACKUP_ENABLED"))


@router.post("/backups")
def new_backup(csrf: str = Form(""), password: str = Form(""), confirm: str = Form(""),
               db: Session = Depends(get_db), admin=Depends(require_manager)):
    verify(csrf, admin)
    confirm_password(db, admin, password, confirm)
    create_backup(db)
    return RedirectResponse("/admin/operations/backups", 303)


@router.post("/backups/{backup_id}/verify")
def check_backup(backup_id: int, csrf: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_manager)):
    verify(csrf, admin)
    record = db.get(BackupRecord, backup_id)
    if not record:
        raise HTTPException(404)
    try:
        verify_backup(record)
    except Exception:
        raise HTTPException(409, "Копія не пройшла перевірку.") from None
    db.commit()
    return RedirectResponse("/admin/operations/backups", 303)
