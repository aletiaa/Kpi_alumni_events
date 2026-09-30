from app.models import User, Survey, SurveyQuestion, SurveyAnswer, Registration, Event
from app.security import hash_password, verify_password
from scripts.hash_admin_passwords import migrate
from scripts.prepare_release_data import clean_seed_users, add_demo_surveys


def test_password_hashes_are_salted_and_invalid_hashes_fail_closed():
    first = hash_password("a-long-test-password")
    assert first != hash_password("a-long-test-password")
    assert verify_password("a-long-test-password", first)
    assert not verify_password("wrong", first)
    for invalid in ("", "plaintext", None):
        assert not verify_password("plaintext", invalid)


def test_admin_migration_is_idempotent_and_removes_plaintext(tmp_path, monkeypatch):
    path = tmp_path / "admins.csv"
    path.write_text("email,password,full_name\nadmin@example.test,sample-pass,Admin\n")
    assert migrate(path) == 1
    content = path.read_text()
    assert "sample-pass" not in content
    migrate(path)
    assert path.read_text() == content
    from app.services import admin_csv
    monkeypatch.setattr(admin_csv, "ADMINS_CSV_PATH", str(path))
    record = admin_csv.find_admin_by_email("ADMIN@example.test")
    assert verify_password("sample-pass", record.password_hash)
    monkeypatch.setattr(admin_csv, "ADMINS_CSV_PATH", str(tmp_path / "missing.csv"))
    assert admin_csv.find_admin_by_email("admin@example.test") is None


def test_cleanup_preserves_other_accounts_and_demo_surveys_are_isolated(db):
    from datetime import datetime
    seeded = User(full_name="Seed", email="olena.alumni@example.com", password_hash="unused")
    real = User(full_name="Real", email="real@example.test", password_hash="unused")
    event = Event(title="Event", description="Example", start_time=datetime.utcnow())
    survey = Survey(title="Original", is_active=True)
    db.add_all([seeded, real, event, survey])
    db.flush()
    db.add(Registration(user_id=seeded.id, event_id=event.id))
    db.add(SurveyQuestion(survey_id=survey.id, question_text="Choice", question_type="single_choice", options_text="A\nB"))
    db.commit()
    assert clean_seed_users(db) == 1
    assert clean_seed_users(db) == 0
    assert add_demo_surveys(db) == 1
    assert add_demo_surveys(db) == 0
    db.commit()
    assert db.query(User).count() == 1
    assert db.query(User).first().email == real.email
    assert db.query(Registration).count() == 0
    assert db.query(SurveyAnswer).filter_by(survey_id=survey.id).count() == 0
    demo = db.query(Survey).filter(Survey.title.startswith("[DEMO]")).one()
    assert not demo.is_active
    assert db.query(SurveyAnswer).filter_by(survey_id=demo.id).count() == 8


def test_admin_login_accepts_hash_and_rejects_plaintext(client, monkeypatch):
    from app.services.admin_csv import AdminRecord
    record = AdminRecord("admin@example.test", hash_password("test-password"), "Admin")
    monkeypatch.setattr("app.routers.auth.find_admin_by_email", lambda email: record)
    result = client.post("/login", data={"email": record.email, "password": "test-password"}, follow_redirects=False)
    assert result.status_code == 303
    assert result.headers["location"] == "/admin"
    assert client.post("/login", data={"email": record.email, "password": "wrong"}).status_code == 400
    record.password_hash = "test-password"
    assert client.post("/login", data={"email": record.email, "password": "test-password"}).status_code == 400
