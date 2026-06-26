from sqlalchemy import inspect, text


def _has_column(conn, table_name: str, column_name: str) -> bool:
    return column_name in {col["name"] for col in inspect(conn).get_columns(table_name)}


def _add_column_if_missing(conn, table_name: str, column_name: str, ddl: str):
    if not _has_column(conn, table_name, column_name):
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))


def ensure_email_verified_column(engine):
    with engine.begin() as conn:
        _add_column_if_missing(conn, "users", "is_email_verified", "is_email_verified BOOLEAN NOT NULL DEFAULT FALSE")


def ensure_event_time_columns(engine):
    with engine.begin() as conn:
        _add_column_if_missing(conn, "events", "end_time", "end_time TIMESTAMP")
        _add_column_if_missing(conn, "events", "registration_deadline", "registration_deadline TIMESTAMP")
        _add_column_if_missing(conn, "events", "short_description", "short_description VARCHAR(500)")
        _add_column_if_missing(conn, "events", "image_url", "image_url VARCHAR(500)")
        _add_column_if_missing(conn, "events", "image_source_url", "image_source_url VARCHAR(500)")


def ensure_password_reset_columns(engine):
    with engine.begin() as conn:
        _add_column_if_missing(conn, "users", "reset_token", "reset_token VARCHAR(256)")
        _add_column_if_missing(conn, "users", "reset_token_expires_at", "reset_token_expires_at TIMESTAMP")


def ensure_alumni_profile_columns(engine):
    with engine.begin() as conn:
        _add_column_if_missing(conn, "users", "is_blocked", "is_blocked BOOLEAN NOT NULL DEFAULT FALSE")
        _add_column_if_missing(conn, "users", "group_name", "group_name VARCHAR(80)")
        _add_column_if_missing(conn, "users", "birth_date", "birth_date DATE")
        _add_column_if_missing(conn, "users", "faculty", "faculty VARCHAR(120)")
        _add_column_if_missing(conn, "users", "specialty", "specialty VARCHAR(120)")
        _add_column_if_missing(conn, "users", "graduation_year", "graduation_year INTEGER")
        _add_column_if_missing(conn, "users", "bio", "bio TEXT")
        _add_column_if_missing(conn, "users", "telegram_username", "telegram_username VARCHAR(120)")
        _add_column_if_missing(conn, "users", "linkedin_url", "linkedin_url VARCHAR(300)")
        _add_column_if_missing(conn, "users", "is_profile_public", "is_profile_public BOOLEAN NOT NULL DEFAULT TRUE")
        _add_column_if_missing(conn, "users", "avatar_url", "avatar_url VARCHAR(500)")
        _add_column_if_missing(conn, "users", "status", "status VARCHAR(120)")
        _add_column_if_missing(conn, "users", "preferred_language", "preferred_language VARCHAR(5) NOT NULL DEFAULT 'uk'")
        _add_column_if_missing(conn, "users", "notifications_enabled", "notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE")
        _add_column_if_missing(conn, "users", "city_country", "city_country VARCHAR(160)")
        _add_column_if_missing(conn, "users", "current_position", "current_position VARCHAR(160)")
        _add_column_if_missing(conn, "users", "company", "company VARCHAR(160)")
        _add_column_if_missing(conn, "users", "skills", "skills TEXT")
        _add_column_if_missing(conn, "users", "help_topics", "help_topics TEXT")
        _add_column_if_missing(conn, "users", "is_mentor", "is_mentor BOOLEAN NOT NULL DEFAULT FALSE")
        _add_column_if_missing(conn, "users", "mentorship_topics", "mentorship_topics TEXT")


def ensure_regular_profiles_are_public(engine):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE users
                SET is_profile_public = TRUE
                WHERE role IN ('guest', 'student', 'alumni')
                  AND is_blocked = FALSE
                  AND email != 'private@example.com'
                  AND is_profile_public = FALSE
            """)
        )


def ensure_event_social_tables(engine):
    id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if engine.dialect.name == "sqlite" else "SERIAL PRIMARY KEY"
    bool_false = "0" if engine.dialect.name == "sqlite" else "FALSE"
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS event_reactions (
                id {id_type},
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                reaction VARCHAR(10) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_user_event_reaction UNIQUE (user_id, event_id)
            )
        """))


def ensure_notifications_table(engine):
    id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if engine.dialect.name == "sqlite" else "SERIAL PRIMARY KEY"
    bool_false = "0" if engine.dialect.name == "sqlite" else "FALSE"
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS notifications (
                id {id_type},
                user_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                body TEXT NOT NULL,
                url VARCHAR(500),
                kind VARCHAR(40) NOT NULL DEFAULT 'info',
                is_read BOOLEAN NOT NULL DEFAULT {bool_false},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        for ddl in [
            "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications (is_read)",
            "CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications (created_at)",
        ]:
            try:
                conn.execute(text(ddl))
            except Exception:
                pass
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS event_comments (
                id {id_type},
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS direct_messages (
                id {id_type},
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN NOT NULL DEFAULT {bool_false}
            )
        """))


def ensure_iot_visits_table(engine):
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
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
        else:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS iot_visits (
                    id SERIAL PRIMARY KEY,
                    event_id INTEGER NOT NULL,
                    device_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
def ensure_news_image_columns(engine):
    with engine.begin() as conn:
        _add_column_if_missing(conn, "news", "image_url", "image_url VARCHAR(500)")
        _add_column_if_missing(conn, "news", "image_source_url", "image_source_url VARCHAR(500)")

def ensure_analytics_tables(engine):
    id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if engine.dialect.name == "sqlite" else "SERIAL PRIMARY KEY"
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS page_views (
                id {id_type},
                user_id INTEGER NULL,
                session_id VARCHAR(80) NOT NULL,
                page VARCHAR(1000) NOT NULL,
                route VARCHAR(200),
                http_method VARCHAR(12) NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                request_duration_ms FLOAT,
                ip_address VARCHAR(80),
                user_agent VARCHAR(500),
                referrer VARCHAR(1000),
                response_status_code INTEGER
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS user_activity (
                id {id_type},
                user_id INTEGER NULL,
                session_id VARCHAR(80) NOT NULL UNIQUE,
                first_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_seconds INTEGER NOT NULL DEFAULT 0,
                total_requests INTEGER NOT NULL DEFAULT 1
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS page_duration (
                id {id_type},
                user_id INTEGER NULL,
                session_id VARCHAR(80) NOT NULL,
                page VARCHAR(1000) NOT NULL,
                opened_at TIMESTAMP NOT NULL,
                closed_at TIMESTAMP NOT NULL,
                duration_seconds INTEGER NOT NULL DEFAULT 0
            )
        """))
        for ddl in [
            "CREATE INDEX IF NOT EXISTS ix_page_views_session_id ON page_views (session_id)",
            "CREATE INDEX IF NOT EXISTS ix_page_views_page ON page_views (page)",
            "CREATE INDEX IF NOT EXISTS ix_page_views_viewed_at ON page_views (viewed_at)",
            "CREATE INDEX IF NOT EXISTS ix_page_duration_page ON page_duration (page)",
            "CREATE INDEX IF NOT EXISTS ix_page_duration_session_id ON page_duration (session_id)",
        ]:
            try:
                conn.execute(text(ddl))
            except Exception:
                pass
