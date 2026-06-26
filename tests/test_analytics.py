from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.models import PageDuration, PageView, User
from app.security import create_session_token
from app.services.analytics import average_page_duration_by_page, page_metadata, record_page_duration, top_pages


def test_analytics_middleware_records_page_view_and_session(client, db):
    response = client.get("/events", headers={"user-agent": "pytest-browser", "referer": "https://example.test/start"})
    assert response.status_code == 200

    page_view = db.execute(text("SELECT page, route, http_method, user_agent, referrer, response_status_code, request_duration_ms FROM page_views")).mappings().first()
    assert page_view is not None
    assert page_view["page"] == "/events"
    assert page_view["http_method"] == "GET"
    assert page_view["user_agent"] == "pytest-browser"
    assert page_view["referrer"] == "https://example.test/start"
    assert page_view["response_status_code"] == 200
    assert page_view["request_duration_ms"] >= 0

    activity = db.execute(text("SELECT session_id, total_requests, duration_seconds FROM user_activity")).mappings().first()
    assert activity is not None
    assert activity["total_requests"] == 1
    assert activity["duration_seconds"] >= 0
    assert response.cookies.get("analytics_session_id")


def test_analytics_middleware_reuses_session_activity(client, db):
    first = client.get("/")
    session_id = first.cookies.get("analytics_session_id")
    assert session_id

    second = client.get("/news", cookies={"analytics_session_id": session_id})
    assert second.status_code == 200

    activity_count = db.execute(text("SELECT COUNT(*) FROM user_activity")).scalar()
    total_requests = db.execute(text("SELECT total_requests FROM user_activity WHERE session_id = :sid"), {"sid": session_id}).scalar()
    assert activity_count == 1
    assert total_requests == 2


def test_analytics_ignores_static_assets(client, db):
    response = client.get("/static/styles.css")
    assert response.status_code in {200, 304}
    assert db.execute(text("SELECT COUNT(*) FROM page_views")).scalar() == 0


def test_analytics_ignores_post_and_api_requests(client, db):
    client.post("/assistant/query", json={"query": "mentor"})
    client.get("/api/iot/events/1/stats")
    assert db.execute(text("SELECT COUNT(*) FROM page_views")).scalar() == 0


def test_analytics_page_requires_admin(client):
    response = client.get("/analytics", follow_redirects=False)
    assert response.status_code in {401, 403}


def test_analytics_page_available_for_admin(admin_client):
    response = admin_client.get("/analytics")
    assert response.status_code == 200
    assert "Зрозуміла активність AlumnixHub" in response.text


def test_analytics_page_uses_clear_ukrainian_labels(admin_client):
    response = admin_client.get("/analytics")
    assert response.status_code == 200
    assert "усі змістовні перегляди сторінок" in response.text
    assert "перегляди від зареєстрованих користувачів" in response.text
    assert "середній час перегляду" in response.text
    assert "Auth views" not in response.text
    assert "Avg page time" not in response.text
    assert "meaningful page views" not in response.text


def test_page_duration_beacon_endpoint_records_duration(client, db):
    opened_at = datetime.utcnow() - timedelta(seconds=45)
    response = client.post(
        "/analytics/page-duration",
        json={"page": "/events", "opened_at": opened_at.isoformat(), "duration_seconds": 45},
    )
    assert response.status_code == 200
    row = db.execute(text("SELECT page, duration_seconds FROM page_duration")).mappings().first()
    assert row is not None
    assert row["page"] == "/events"
    assert row["duration_seconds"] == 45


def test_page_duration_beacon_accepts_timezone_aware_opened_at(client, db):
    opened_at = datetime.now(timezone.utc) - timedelta(seconds=12)
    response = client.post(
        "/analytics/page-duration",
        json={"page": "/events", "opened_at": opened_at.isoformat(), "duration_seconds": 12},
    )
    assert response.status_code == 200
    row = db.execute(text("SELECT page, duration_seconds FROM page_duration")).mappings().first()
    assert row is not None
    assert row["page"] == "/events"
    assert row["duration_seconds"] == 12


def test_page_metadata_does_not_expose_unknown_raw_routes():
    known = page_metadata("/events?msg=like_saved")
    unknown = page_metadata("/technical-root-with-query?debug=1")
    admin_unknown = page_metadata("/admin/experimental-panel")

    assert known["path"] == "/events"
    assert known["title"] == "Події"
    assert unknown["path"] == "/technical-root-with-query"
    assert unknown["title"] == "Інший розділ платформи"
    assert "/technical-root-with-query" not in unknown["title"]
    assert admin_unknown["title"] == "Адмін-панель"


def test_record_page_duration_calculates_closed_at_from_payload(db):
    opened_at = datetime.utcnow() - timedelta(minutes=10)
    wrong_closed_at = datetime.utcnow()
    row = record_page_duration(
        db,
        user_id=None,
        session_id="s-duration",
        page="/events",
        opened_at=opened_at,
        closed_at=wrong_closed_at,
        duration_seconds=30,
    )
    assert row.closed_at == opened_at + timedelta(seconds=30)

def test_analytics_records_authenticated_user_id(client, db):
    user = User(
        full_name="Analytics User",
        email="analytics-user@example.com",
        password_hash="x",
        role="alumni",
        is_active=True,
        is_email_verified=True,
        is_blocked=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_session_token(user.id, user.role, user.email, user.full_name)

    response = client.get("/events", cookies={"session": token})
    assert response.status_code == 200

    row = db.execute(text("SELECT user_id, session_id FROM page_views WHERE page = '/events'")).mappings().first()
    assert row is not None
    assert row["user_id"] == user.id
    assert row["session_id"].startswith("auth:")
    activity_user_id = db.execute(text("SELECT user_id FROM user_activity WHERE session_id = :sid"), {"sid": row["session_id"]}).scalar()
    assert activity_user_id == user.id


def test_analytics_helpers_show_friendly_pages_without_query_duplicates(db):
    now = datetime.utcnow()
    db.add_all(
        [
            PageView(session_id="s1", page="/events?msg=like_saved", route="events", http_method="GET", viewed_at=now, request_duration_ms=20),
            PageView(session_id="s2", page="/events?msg=dislike_saved", route="events", http_method="GET", viewed_at=now, request_duration_ms=40),
            PageView(session_id="s3", page="/alumni?q=&faculty=%D0%A4", route="alumni", http_method="GET", viewed_at=now, request_duration_ms=30),
            PageDuration(session_id="s1", page="/events?msg=like_saved", opened_at=now, closed_at=now + timedelta(seconds=30), duration_seconds=30),
            PageDuration(session_id="s2", page="/events?msg=dislike_saved", opened_at=now, closed_at=now + timedelta(seconds=90), duration_seconds=90),
        ]
    )
    db.commit()

    pages = top_pages(db)
    events = next(row for row in pages if row["page"] == "/events")
    alumni = next(row for row in pages if row["page"] == "/alumni")

    assert events["title"] == "Події"
    assert events["views"] == 2
    assert events["avg_request_ms"] == 30
    assert alumni["title"] == "Пошук випускників"

    durations = average_page_duration_by_page(db)
    event_duration = next(row for row in durations if row["page"] == "/events")
    assert event_duration["title"] == "Події"
    assert event_duration["samples"] == 2
    assert event_duration["avg_seconds"] == 60
    assert event_duration["avg_label"] == "1.0 хв"


def test_admin_dashboard_hides_technical_analytics_paths(admin_client, db):
    now = datetime.utcnow()
    db.add_all(
        [
            PageView(
                session_id="s1",
                page="/events?msg=like_saved",
                route="events",
                http_method="GET",
                viewed_at=now,
                request_duration_ms=20,
            ),
            PageDuration(
                session_id="s1",
                page="/events?msg=like_saved",
                opened_at=now,
                closed_at=now + timedelta(seconds=30),
                duration_seconds=30,
            ),
        ]
    )
    db.commit()

    response = admin_client.get("/admin")
    assert response.status_code == 200
    assert "Події" in response.text
    assert "Технічний шлях" not in response.text
    assert "/events?msg=like_saved" not in response.text
