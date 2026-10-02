from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import AdministratorGrant, User
from app.services import admin_csv
from app.deps import require_admin


def valid_grant(db, user):
    if not user or not user.is_active or user.is_blocked or not user.is_email_verified:
        return None
    return db.get(AdministratorGrant, user.id)


def is_administrator_email(db, email):
    if admin_csv.find_admin_by_email(email):
        return True
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    return bool(valid_grant(db, user))


def may_manage(db, identity):
    if identity.user_id:
        grant = valid_grant(db, db.get(User, identity.user_id))
        return bool(grant and grant.can_manage_admins)
    return bool(admin_csv.find_admin_by_email(identity.email))


def require_manager(db: Session = Depends(get_db), identity=Depends(require_admin)):
    if not may_manage(db, identity):
        raise HTTPException(403, "Потрібне право керування адміністраторами.")
    return identity
