from fastapi import Depends, Form, HTTPException
from itsdangerous import BadSignature, URLSafeTimedSerializer
from app.config import SECRET_KEY
from app.security import verify_password
from app.models import User
from app.services import admin_csv
from app.deps import require_admin

signer = URLSafeTimedSerializer(SECRET_KEY, salt="operations-csrf")


def token(identity):
    email = getattr(identity, "email", None)
    return signer.dumps(email) if email else ""


def verify(token, identity):
    try:
        if signer.loads(token, max_age=7200) != identity.email:
            raise BadSignature("Different account")
    except BadSignature:
        raise HTTPException(403, "Оновіть сторінку та повторіть дію.") from None


def confirm_password(db, identity, password, confirmation):
    if confirmation != "yes":
        raise HTTPException(400, "Підтвердьте дію.")
    record = db.get(User, identity.user_id) if identity.user_id else admin_csv.find_admin_by_email(identity.email)
    if not record or not verify_password(password, record.password_hash):
        raise HTTPException(403, "Неправильний пароль.")


def destructive_confirmation(csrf: str = Form(""), confirm: str = Form(""),
                             identity=Depends(require_admin)):
    verify(csrf, identity)
    if confirm != "yes":
        raise HTTPException(400, "Підтвердьте видалення.")
