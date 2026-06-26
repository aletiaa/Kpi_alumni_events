import os
import sys
import pytest
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.db import get_db

# Tests use the SQLite schema below instead of touching the configured live database.
app.router.on_startup.clear()

try:
    from app.deps import require_admin
except Exception:
    require_admin = None

TEST_DATABASE_URL = "sqlite+pysqlite://"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)

TestingSessionLocal = sessionmaker(
    bind=engine_test,
    autocommit=False,
    autoflush=False,
    future=True,
)


def _ensure_schema():
    """Create minimal schema required by tests."""
    with engine_test.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS iot_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                direction TEXT NOT NULL,
                delta INTEGER NOT NULL,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                email TEXT,
                password_hash TEXT,
                role TEXT,
                is_active BOOLEAN,
                is_email_verified BOOLEAN,
                is_blocked BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP,
                reset_token TEXT,
                reset_token_expires_at TIMESTAMP,
                group_name TEXT,
                birth_date DATE,
                faculty TEXT,
                specialty TEXT,
                graduation_year INTEGER,
                bio TEXT,
                telegram_username TEXT,
                linkedin_url TEXT,
                is_profile_public BOOLEAN DEFAULT FALSE
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                location TEXT,
                start_time TIMESTAMP,
                capacity INTEGER,
                end_time TIMESTAMP,
                registration_deadline TIMESTAMP,
                created_at TIMESTAMP,
                short_description TEXT,
                image_url TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id INTEGER,
                registered_at TIMESTAMP,
                UNIQUE(user_id, event_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id INTEGER,
                reaction TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(user_id, event_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id INTEGER,
                body TEXT,
                created_at TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS direct_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                receiver_id INTEGER,
                body TEXT,
                created_at TIMESTAMP,
                is_read BOOLEAN DEFAULT FALSE
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                body TEXT,
                url TEXT,
                kind TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                short_description TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                is_published BOOLEAN,
                author_id INTEGER
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                url TEXT,
                faculty TEXT,
                specialty TEXT,
                group_name TEXT,
                graduation_year INTEGER,
                is_active BOOLEAN,
                created_at TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                is_active BOOLEAN,
                created_at TIMESTAMP
            )
        """))
        for ddl in [
            "ALTER TABLE events ADD COLUMN image_url TEXT",
            "ALTER TABLE events ADD COLUMN image_source_url TEXT",
            "ALTER TABLE news ADD COLUMN image_url TEXT",
            "ALTER TABLE news ADD COLUMN image_source_url TEXT",
            "ALTER TABLE users ADD COLUMN avatar_url TEXT",
            "ALTER TABLE users ADD COLUMN status TEXT",
            "ALTER TABLE users ADD COLUMN preferred_language TEXT DEFAULT 'uk'",
            "ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN city_country TEXT",
            "ALTER TABLE users ADD COLUMN current_position TEXT",
            "ALTER TABLE users ADD COLUMN company TEXT",
            "ALTER TABLE users ADD COLUMN skills TEXT",
            "ALTER TABLE users ADD COLUMN help_topics TEXT",
            "ALTER TABLE users ADD COLUMN is_mentor BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN mentorship_topics TEXT",
        ]:
            try:
                conn.execute(text(ddl))
            except Exception:
                pass
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS survey_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER,
                question_text TEXT,
                question_type TEXT,
                options_text TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS page_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT NOT NULL,
                page TEXT NOT NULL,
                route TEXT,
                http_method TEXT NOT NULL,
                viewed_at TIMESTAMP,
                request_duration_ms FLOAT,
                ip_address TEXT,
                user_agent TEXT,
                referrer TEXT,
                response_status_code INTEGER
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT NOT NULL UNIQUE,
                first_activity TIMESTAMP,
                last_activity TIMESTAMP,
                duration_seconds INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 1
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS page_duration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT NOT NULL,
                page TEXT NOT NULL,
                opened_at TIMESTAMP,
                closed_at TIMESTAMP,
                duration_seconds INTEGER DEFAULT 0
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS survey_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER,
                question_id INTEGER,
                user_id INTEGER,
                answer_text TEXT,
                created_at TIMESTAMP
            )
        """))


@pytest.fixture(scope="session", autouse=True)
def _create_schema_once():
    _ensure_schema()


@pytest.fixture(scope="function")
def db():
    session = TestingSessionLocal()
    try:
        for table in ["page_duration", "user_activity", "page_views", "notifications", "direct_messages", "event_comments", "event_reactions", "survey_answers", "survey_questions", "surveys", "chat_links", "news", "iot_visits", "registrations", "events", "users"]:
            session.execute(text(f"DELETE FROM {table}"))
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.state.analytics_session_factory = TestingSessionLocal
    os.environ["IOT_API_KEY"] = "test-key"

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_client(client):
    if require_admin is None:
        pytest.skip("require_admin dependency not found; adjust import in conftest.py.")

    def override_require_admin():
        return SimpleNamespace(role="admin", user_id=None, email="admin@test.local", full_name="Admin")

    app.dependency_overrides[require_admin] = override_require_admin
    yield client





