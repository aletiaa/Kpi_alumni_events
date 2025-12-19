import os
import sys
import pytest
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

# --- Ensure project root is on sys.path ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.db import get_db

# Admin dependency (adjust only if your project uses a different name)
try:
    from app.deps import require_admin
except Exception:
    require_admin = None


# IMPORTANT: shared in-memory SQLite across threads/connections
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
        # IoT table required by app/routers/iot.py (uses ts in stats queries)
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
        # Minimal users table for foreign key
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                email TEXT,
                password_hash TEXT,
                role TEXT,
                is_active BOOLEAN,
                is_email_verified BOOLEAN,
                created_at TIMESTAMP,
                reset_token TEXT,
                reset_token_expires_at TIMESTAMP
            )
        """))
        # Minimal events table for API tests
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
                short_description TEXT
            )
        """))
        # Minimal registrations table for foreign key
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id INTEGER,
                registered_at TIMESTAMP,
                UNIQUE(user_id, event_id)
            )
        """))


@pytest.fixture(scope="session", autouse=True)
def _create_schema_once():
    _ensure_schema()


@pytest.fixture(scope="function")
def db():
    session = TestingSessionLocal()
    try:
        # clean between tests
        session.execute(text("DELETE FROM iot_visits"))
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    os.environ["IOT_API_KEY"] = "test-key"

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_client(client):
    if require_admin is None:
        pytest.skip("require_admin dependency not found; adjust import in conftest.py.")

    def override_require_admin():
        # Return whatever your endpoints expect; many accept any truthy object
        return {"role": "admin", "id": 1, "email": "admin@test.local"}

    app.dependency_overrides[require_admin] = override_require_admin
    yield client
    # cleared by client fixture
