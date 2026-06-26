from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import APP_BASE_URL, APP_NAME, EMAIL_ENABLED
from ..db import get_db
from ..models import User
from ..security import generate_reset_token, hash_password, hash_token, reset_expiry
from ..services.emailer import send_reset_password_email

router = APIRouter()


def render(request: Request, template: str, ctx: dict, status_code: int = 200):
    base = {"request": request, "app_name": APP_NAME}
    base.update(ctx)
    return request.app.state.templates.TemplateResponse(request, template, base, status_code=status_code)


def redirect(url: str):
    return RedirectResponse(url=url, status_code=303)


@router.get("/forgot-password")
def forgot_password_form(request: Request):
    return render(request, "forgot_password.html", {})


@router.post("/forgot-password")
def forgot_password_submit(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    email_n = (email or "").strip().lower()
    user = db.query(User).filter(User.email == email_n).first()
    demo_link = None
    email_error = None

    if user and user.is_active:
        raw_token = generate_reset_token()
        user.reset_token = hash_token(raw_token)
        user.reset_token_expires_at = reset_expiry(30)
        db.commit()
        reset_link = f"{APP_BASE_URL}/reset-password?token={raw_token}&email={user.email}"

        if EMAIL_ENABLED:
            try:
                send_reset_password_email(user.email, reset_link)
            except Exception as exc:
                email_error = str(exc)
                demo_link = reset_link
        else:
            demo_link = reset_link

    return render(
        request,
        "forgot_password_sent.html",
        {"email": email_n, "demo_link": demo_link, "email_error": email_error, "email_enabled": EMAIL_ENABLED},
    )


@router.get("/reset-password")
def reset_password_form(request: Request, token: str, email: str):
    return render(request, "reset_password.html", {"token": token, "email": email})


@router.post("/reset-password")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    email: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    email_n = (email or "").strip().lower()
    token_h = hash_token(token)

    user = db.query(User).filter(User.email == email_n).first()
    if not user or not user.reset_token or not user.reset_token_expires_at:
        return render(request, "reset_password.html", {"token": token, "email": email_n, "error": "Недійсне або прострочене посилання для скидання пароля."}, 400)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.reset_token != token_h or now > user.reset_token_expires_at:
        return render(request, "reset_password.html", {"token": token, "email": email_n, "error": "Недійсне або прострочене посилання для скидання пароля."}, 400)

    user.password_hash = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()
    return redirect("/login?msg=password_reset_ok")