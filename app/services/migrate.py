from sqlalchemy import text

def ensure_email_verified_column(engine):
    # PostgreSQL-safe: add column if missing
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN NOT NULL DEFAULT FALSE
        """))

def ensure_event_time_columns(engine):
    # PostgreSQL-safe: add columns if missing
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE events
            ADD COLUMN IF NOT EXISTS end_time TIMESTAMP
        """))
        conn.execute(text("""
            ALTER TABLE events
            ADD COLUMN IF NOT EXISTS registration_deadline TIMESTAMP
        """))

def ensure_password_reset_columns(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS reset_token VARCHAR(256)
        """))
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP
        """))
