from datetime import datetime, timedelta
from types import SimpleNamespace

from app.deps import require_admin, require_identity
from app.models import ChatLink, DirectMessage, Event, EventComment, EventReaction, News, Notification, Registration, Survey, SurveyAnswer, SurveyQuestion, User


def _user(db, public=False):
    user = User(
        full_name="Ada Alumni",
        email="ada@example.com",
        password_hash="x",
        role="alumni",
        is_active=True,
        is_email_verified=True,
        is_blocked=False,
        is_profile_public=public,
        faculty="FIOT",
        specialty="Computer Science",
        group_name="IP-01",
        graduation_year=2024,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_admin_pages_are_protected(client):
    response = client.get("/admin/news")
    assert response.status_code in {401, 403}


def test_profile_update_and_public_alumni_search(client, db):
    user = _user(db)

    def ident():
        return SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)

    client.app.dependency_overrides[require_identity] = ident
    response = client.post(
        "/profile",
        data={
            "full_name": "Ada KPI",
            "group_name": "IP-01",
            "birth_date": "2000-01-02",
            "faculty": "FIOT",
            "specialty": "Software Engineering",
            "graduation_year": "2024",
            "bio": "Builds alumni communities.",
            "telegram_username": "@ada",
            "linkedin_url": "https://linkedin.com/in/ada",
            "is_profile_public": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    db.refresh(user)
    assert user.full_name == "Ada KPI"
    assert user.is_profile_public is True

    response = client.get("/alumni?q=Ada")
    assert response.status_code == 200
    assert "Ada KPI" in response.text


def test_profile_page_shows_completeness_hint(client, db):
    user = _user(db)

    def ident():
        return SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)

    client.app.dependency_overrides[require_identity] = ident
    response = client.get("/profile")
    assert response.status_code == 200
    assert "Заповненість профілю" in response.text
    assert "Фото профілю" in response.text


def test_admin_can_create_news_chat_survey_and_question(admin_client, db):
    response = admin_client.post("/admin/news/create", data={"title": "Update", "short_description": "Short", "content": "Full", "is_published": "1"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(News).count() == 1

    response = admin_client.post("/admin/chats/create", data={"title": "Faculty chat", "description": "Main chat", "url": "https://t.me/example", "faculty": "FIOT", "is_active": "1"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(ChatLink).count() == 1

    response = admin_client.post("/admin/surveys/create", data={"title": "Feedback", "description": "Annual", "is_active": "1"}, follow_redirects=False)
    assert response.status_code == 303
    survey = db.query(Survey).first()
    assert survey is not None

    response = admin_client.post(f"/admin/surveys/{survey.id}/questions/create", data={"question_text": "Choose one", "question_type": "single_choice", "options_text": "Yes\nNo"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(SurveyQuestion).count() == 1


def test_admin_news_moderation_filter(admin_client, db):
    db.add_all(
        [
            News(title="Published item", short_description="Visible", content="Full", is_published=True),
            News(title="Draft item", short_description="Needs review", content="Draft", is_published=False),
        ]
    )
    db.commit()

    response = admin_client.get("/admin/news?status=draft")
    assert response.status_code == 200
    assert "На модерації: <b>1</b>" in response.text
    assert "Draft item" in response.text
    assert "Published item" not in response.text


def test_admin_can_upload_news_image_file(admin_client, db):
    response = admin_client.post(
        "/admin/news/create",
        data={"title": "Photo news", "short_description": "With image", "content": "Full text", "is_published": "1"},
        files={"image_file": ("poster.png", b"fake-png-bytes", "image/png")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    item = db.query(News).filter_by(title="Photo news").first()
    assert item is not None
    assert item.image_url.startswith("/static/uploads/news/")
    assert item.image_url.endswith(".png")


def test_global_search_finds_events_news_and_users(client, db):
    user = _user(db, public=True)
    user.bio = "AI mentor"
    event = Event(
        title="AI career evening",
        description="AI event for students",
        location="KPI",
        start_time=datetime.utcnow() + timedelta(days=2),
        capacity=100,
    )
    news = News(title="AI platform update", short_description="AI news", content="Full AI text", is_published=True)
    db.add_all([event, news])
    db.commit()

    response = client.get("/search?q=AI")
    assert response.status_code == 200
    assert "AI career evening" in response.text
    assert "AI platform update" in response.text
    assert user.full_name in response.text


def test_mentors_page_filters_public_mentors(client, db):
    mentor = _user(db, public=True)
    mentor.is_mentor = True
    mentor.current_position = "Data mentor"
    mentor.skills = "Python, SQL"
    mentor.mentorship_topics = "Career growth and portfolio"
    hidden = User(
        full_name="Hidden Mentor",
        email="hidden@example.com",
        password_hash="x",
        role="alumni",
        is_active=True,
        is_email_verified=True,
        is_blocked=False,
        is_profile_public=True,
        is_mentor=False,
        created_at=datetime.utcnow(),
    )
    db.add(hidden)
    db.commit()

    response = client.get("/mentors?q=Python")
    assert response.status_code == 200
    assert mentor.full_name in response.text
    assert "Hidden Mentor" not in response.text


def test_authenticated_user_can_submit_survey(client, db):
    user = _user(db, public=True)
    survey = Survey(title="Feedback", description="Annual", is_active=True)
    db.add(survey)
    db.commit()
    db.refresh(survey)
    question = SurveyQuestion(survey_id=survey.id, question_text="Comment", question_type="text")
    db.add(question)
    db.commit()
    db.refresh(question)

    def ident():
        return SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)

    client.app.dependency_overrides[require_identity] = ident
    response = client.post(f"/surveys/{survey.id}", data={f"question_{question.id}": "Great"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(SurveyAnswer).count() == 1


def test_registered_user_can_react_and_comment_on_event(client, db):
    user = _user(db, public=True)
    event = Event(
        title="Community meetup",
        description="A public event",
        location="KPI",
        start_time=datetime.utcnow(),
        capacity=20,
        image_url="/static/img/kpi-main.png",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    db.add(Registration(user_id=user.id, event_id=event.id))
    db.commit()

    def ident():
        return SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)

    client.app.dependency_overrides[require_identity] = ident
    response = client.post(f"/events/{event.id}/react", data={"reaction": "like"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(EventReaction).filter_by(user_id=user.id, event_id=event.id, reaction="like").count() == 1

    response = client.post(f"/events/{event.id}/comments", data={"body": "Great event"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(EventComment).filter_by(user_id=user.id, event_id=event.id).count() == 1



def test_authorized_user_can_react_without_event_registration(client, db):
    user = _user(db, public=True)
    event = Event(
        title="Open lecture",
        description="Anyone can react before registration",
        location="KPI",
        start_time=datetime.utcnow(),
        capacity=20,
        image_url="/static/img/kpi-main.png",
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    def ident():
        return SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)

    client.app.dependency_overrides[require_identity] = ident
    response = client.post(f"/events/{event.id}/react", data={"reaction": "like"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(EventReaction).filter_by(user_id=user.id, event_id=event.id, reaction="like").count() == 1
    assert db.query(Registration).filter_by(user_id=user.id, event_id=event.id).count() == 0




def test_authorized_user_can_comment_without_event_registration(client, db):
    user = _user(db, public=True)
    event = Event(
        title="Open comments",
        description="Comments do not require event registration",
        location="KPI",
        start_time=datetime.utcnow(),
        capacity=20,
        image_url="/static/img/kpi-main.png",
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    def ident():
        return SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)

    client.app.dependency_overrides[require_identity] = ident
    response = client.post(f"/events/{event.id}/comments", data={"body": "Comment before registration"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(EventComment).filter_by(user_id=user.id, event_id=event.id).count() == 1
    assert db.query(Registration).filter_by(user_id=user.id, event_id=event.id).count() == 0
def test_event_reaction_is_unique_and_mutually_exclusive(client, db):
    user = _user(db, public=True)
    event = Event(
        title="Reaction rules",
        description="One reaction per user",
        location="KPI",
        start_time=datetime.utcnow(),
        capacity=20,
        image_url="/static/img/kpi-main.png",
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    def ident():
        return SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)

    client.app.dependency_overrides[require_identity] = ident
    client.post(f"/events/{event.id}/react", data={"reaction": "like"}, follow_redirects=False)
    client.post(f"/events/{event.id}/react", data={"reaction": "dislike"}, follow_redirects=False)

    reactions = db.query(EventReaction).filter_by(user_id=user.id, event_id=event.id).all()
    assert len(reactions) == 1
    assert reactions[0].reaction == "dislike"

    client.post(f"/events/{event.id}/react", data={"reaction": "dislike"}, follow_redirects=False)
    assert db.query(EventReaction).filter_by(user_id=user.id, event_id=event.id).count() == 0


def test_register_validates_email_and_password(client):
    response = client.post(
        "/register",
        data={"full_name": "A", "email": "wrong", "password": "123", "role": "student"},
    )
    assert response.status_code == 400
    assert "має містити щонайменше 2 символи" in response.text


def test_registered_user_is_public_in_alumni_search(client, db):
    response = client.post(
        "/register",
        data={"full_name": "New Public Student", "email": "new-public@example.com", "password": "demo12345", "role": "student"},
    )
    assert response.status_code == 200
    user = db.query(User).filter_by(email="new-public@example.com").first()
    assert user is not None
    assert user.is_profile_public is True


def test_assistant_page_and_query_are_available(client, db):
    event = Event(
        title="AI meetup",
        description="Machine learning lecture",
        location="KPI",
        start_time=datetime.utcnow() + timedelta(days=1),
        capacity=50,
        image_url="/static/img/kpi-main.png",
    )
    db.add(event)
    db.commit()

    response = client.get("/assistant")
    assert response.status_code == 200
    assert "ШІ-асистент" in response.text

    response = client.post("/assistant/query", json={"query": "події"})
    assert response.status_code == 200
    assert response.json()["message"] == "Ось події, які я знайшов."
    assert response.json()["events"][0]["title"] == "AI meetup"

    response = client.post("/assistant/query", json={"query": "потрібен ментор для кар'єри"})
    assert response.status_code == 200
    assert response.json()["links"][0]["url"] == "/mentors"

def test_user_can_message_same_stream_user(client, db):
    sender = _user(db, public=True)
    receiver = User(
        full_name="Grace Alumni",
        email="grace@example.com",
        password_hash="x",
        role="alumni",
        is_active=True,
        is_email_verified=True,
        is_blocked=False,
        is_profile_public=True,
        faculty="FIOT",
        specialty="Computer Science",
        group_name="IP-01",
        graduation_year=2024,
        created_at=datetime.utcnow(),
    )
    db.add(receiver)
    db.commit()
    db.refresh(receiver)

    def ident():
        return SimpleNamespace(user_id=sender.id, role="alumni", email=sender.email, full_name=sender.full_name)

    client.app.dependency_overrides[require_identity] = ident
    response = client.post(f"/messages/{receiver.id}", data={"body": "Hello from the same stream"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(DirectMessage).filter_by(sender_id=sender.id, receiver_id=receiver.id).count() == 1
    assert db.query(Notification).filter_by(user_id=receiver.id, kind="message").count() == 1


def test_admin_event_creation_notifies_users(admin_client, db):
    user = _user(db, public=True)
    user.notifications_enabled = True
    db.commit()

    response = admin_client.post(
        "/admin/events/create",
        data={
            "title": "Notification event",
            "description": "New event announcement",
            "location": "KPI",
            "start_time": (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
            "capacity": "30",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert db.query(Notification).filter_by(user_id=user.id, kind="event").count() == 1


def test_admin_can_send_event_reminders(admin_client, db):
    user = _user(db, public=True)
    user.notifications_enabled = True
    event = Event(
        title="Reminder event",
        description="Registered users should be notified",
        location="KPI",
        start_time=datetime.utcnow() + timedelta(days=1),
        capacity=50,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    db.add(Registration(user_id=user.id, event_id=event.id))
    db.commit()

    response = admin_client.post(f"/admin/events/{event.id}/send_reminders", follow_redirects=False)
    assert response.status_code == 303
    assert db.query(Notification).filter_by(user_id=user.id, kind="event_reminder").count() == 1


def test_user_can_view_and_mark_notifications_read(client, db):
    user = _user(db, public=True)
    db.add(Notification(user_id=user.id, title="Test", body="Body", url="/events", kind="info"))
    db.commit()

    def ident():
        return SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)

    client.app.dependency_overrides[require_identity] = ident
    response = client.get("/notifications")
    assert response.status_code == 200
    assert "Test" in response.text

    response = client.post("/notifications/read-all", follow_redirects=False)
    assert response.status_code == 303
    assert db.query(Notification).filter_by(user_id=user.id, is_read=False).count() == 0


def test_forgot_password_shows_demo_link_when_email_disabled(client, db):
    user = _user(db, public=True)
    response = client.post("/forgot-password", data={"email": user.email})
    assert response.status_code == 200
    assert "/reset-password?token=" in response.text
