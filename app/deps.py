from dataclasses import dataclass
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .db import get_db
from .security import read_session_token
from .models import User

@dataclass
class CurrentIdentity:
    user_id: int | None
    role: str
    email: str
    full_name: str

def get_current_identity(session: str | None = Cookie(default=None)) -> CurrentIdentity | None:
    if not session:
        return None
    data = read_session_token(session)
    if not data:
        return None
    return CurrentIdentity(
        user_id=data.get("user_id"),
        role=data.get("role", "guest"),
        email=data.get("email", ""),
        full_name=data.get("full_name", "")
    )

def require_identity(ident: CurrentIdentity | None = Depends(get_current_identity)) -> CurrentIdentity:
    if not ident:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return ident

def require_admin(ident: CurrentIdentity = Depends(require_identity)) -> CurrentIdentity:
    if ident.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return ident

def get_db_user(db: Session = Depends(get_db), ident: CurrentIdentity | None = Depends(get_current_identity)) -> User | None:
    # returns DB user only for non-admin users
    if not ident or not ident.user_id:
        return None
    return db.get(User, ident.user_id)
