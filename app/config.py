import os
from pathlib import Path
from dotenv import load_dotenv


def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_APP_NAME = "AlumnixHub"
APP_NAME = os.getenv("APP_NAME", DEFAULT_APP_NAME)
if "??" in APP_NAME:
    APP_NAME = DEFAULT_APP_NAME

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

EMAIL_ENABLED = env_bool("EMAIL_ENABLED", False)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_TLS = env_bool("SMTP_TLS", True)
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", APP_NAME)
EMAIL_FROM_EMAIL = os.getenv("EMAIL_FROM_EMAIL", SMTP_USERNAME)
ADMINS_CSV_PATH = os.getenv("ADMINS_CSV_PATH", str(BASE_DIR / "admins.csv"))
