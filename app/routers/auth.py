import re

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import User
from app.config import APP_NAME, APP_BASE_URL, EMAIL_ENABLED
from app.services.admin_csv import find_admin_by_email
from app.services.emailer import send_verification_email
from app.security import (
    hash_password,
    verify_password,
    create_session_token,
    create_email_verify_token,
    read_email_verify_token,
)

router = APIRouter()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def render(request: Request, template: str, context: dict, status_code: int = 200):
    payload = {"request": request, "app_name": APP_NAME}
    payload.update(context)
    return request.app.state.templates.TemplateResponse(request, template, payload, status_code=status_code)


def redirect(url: str, session_token: str | None = None, clear_session: bool = False):
    resp = RedirectResponse(url=url, status_code=303)
    if clear_session:
        resp.delete_cookie("session")
    if session_token:
        resp.set_cookie("session", session_token, httponly=True, samesite="lax")
    return resp


def normalize_role(role: str) -> str:
    return role if role in {"student", "alumni", "guest"} else "guest"


@router.get("/register")
def register_form(request: Request):
    return render(request, "register.html", {})


@router.post("/register")
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("guest"),
    db: Session = Depends(get_db),
):
    email_n = (email or "").strip().lower()
    name_n = (full_name or "").strip()
    role_n = normalize_role(role)
    form_data = {"full_name": name_n, "email": email_n, "role": role_n}

    if not name_n or not email_n:
        return render(request, "register.html", {"error": "Ім'я та email обов'язкові.", **form_data}, status_code=400)
    if len(name_n) < 2:
        return render(request, "register.html", {"error": "Ім'я має містити щонайменше 2 символи.", **form_data}, status_code=400)
    if not EMAIL_RE.match(email_n):
        return render(request, "register.html", {"error": "Вкажіть коректний email.", **form_data}, status_code=400)
    if len(password or "") < 8:
        return render(request, "register.html", {"error": "Пароль має містити щонайменше 8 символів.", **form_data}, status_code=400)

    if find_admin_by_email(email_n):
        return render(request, "register.html", {"error": "Цей email зарезервовано для адміністратора.", **form_data}, status_code=400)

    existing = db.query(User).filter(func.lower(User.email) == email_n).first()
    if existing:
        return render(request, "register.html", {"error": "Цей email вже зареєстровано.", **form_data}, status_code=400)

    user = User(
        full_name=name_n,
        email=email_n,
        password_hash=hash_password(password),
        role=role_n,
        is_email_verified=False,
        is_active=True,
        is_profile_public=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_email_verify_token(user.email)
    verify_link = f"{APP_BASE_URL}/verify?token={token}"

    if EMAIL_ENABLED:
        try:
            send_verification_email(user.email, verify_link)
            return render(request, "register_success.html", {"email_sent": True, "email": user.email})
        except Exception as exc:
            print("EMAIL SEND FAILED:", repr(exc))
            return render(
                request,
                "register_success.html",
                {"email_sent": False, "email": user.email, "verify_link": verify_link, "email_error": str(exc)},
            )

    return render(
        request,
        "register_success.html",
        {"email_sent": False, "verify_link": verify_link, "email": user.email},
    )


@router.get("/verify")
def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    email = read_email_verify_token(token)
    if not email:
        return render(
            request,
            "verify_result.html",
            {"ok": False, "error": "Посилання підтвердження недійсне або прострочене"},
            status_code=400,
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return render(request, "verify_result.html", {"ok": False, "error": "Користувача не знайдено"}, status_code=404)

    if user.is_email_verified:
        return render(request, "verify_result.html", {"ok": True, "already": True})

    user.is_email_verified = True
    db.commit()
    return render(request, "verify_result.html", {"ok": True})


@router.get("/login")
def login_form(request: Request):
    return render(request, "login.html", {})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email_n = (email or "").strip().lower()

    admin = find_admin_by_email(email_n)
    if admin:
        if password != admin.password:
            return render(request, "login.html", {"error": "Неправильний email або пароль."}, status_code=400)
        token = create_session_token(None, "admin", admin.email, admin.full_name)
        return redirect("/admin", session_token=token)

    user = db.query(User).filter(func.lower(User.email) == email_n).first()
    if not user or not verify_password(password, user.password_hash):
        return render(request, "login.html", {"error": "Неправильний email або пароль."}, status_code=400)

    if getattr(user, "is_blocked", False):
        return render(request, "login.html", {"error": "Обліковий запис заблоковано."}, status_code=403)
    if not user.is_active:
        return render(request, "login.html", {"error": "Обліковий запис вимкнено."}, status_code=403)
    if not user.is_email_verified:
        return render(request, "login.html", {"error": "Підтвердьте email перед входом."}, status_code=403)

    token = create_session_token(user.id, user.role, user.email, user.full_name, getattr(user, "avatar_url", None), getattr(user, "status", None))
    return redirect("/", session_token=token)


@router.get("/logout")
def logout():
    return redirect("/", clear_session=True)
