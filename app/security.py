from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext
from .config import SECRET_KEY
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256

# Use PBKDF2 to avoid bcrypt backend issues on Windows and the 72-byte limit
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="kpi-events-session")

def hash_password(password: str) -> str:
    # Accept long passwords safely (pbkdf2 has no 72-byte bcrypt limit)
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_session_token(user_id: int | None, role: str, email: str, full_name: str) -> str:
    return serializer.dumps({"user_id": user_id, "role": role, "email": email, "full_name": full_name})

def read_session_token(token: str, max_age_seconds: int = 60 * 60 * 24 * 7):
    try:
        return serializer.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None

def create_email_verify_token(email: str) -> str:
    return serializer.dumps({"email": email, "type": "email_verify"})

def read_email_verify_token(token: str, max_age_seconds: int = 60 * 60 * 24):
    data = read_session_token(token, max_age_seconds=max_age_seconds)
    if not data or data.get("type") != "email_verify":
        return None
    return data.get("email")

def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()

def reset_expiry(minutes: int = 30):
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=minutes)
