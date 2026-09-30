from types import SimpleNamespace

import pytest

from app.deps import get_current_identity, require_identity
from app.models import Survey, SurveyAnswer, SurveyQuestion, User
from app.services.survey_catalog import seed_additional_surveys
from app.services.survey_results import survey_results


@pytest.fixture
def survey_setup(client, db):
    user = User(full_name="Survey Member", email="survey@example.test", password_hash="x",
                role="alumni", is_active=True, is_email_verified=True)
    survey = Survey(title="Test survey", is_active=True)
    survey.questions = [SurveyQuestion(question_text="Format", question_type="single_choice", options_text="Online\nCampus"),
                        SurveyQuestion(question_text="Feedback", question_type="text")]
    db.add_all([user, survey])
    db.commit()
    ident = SimpleNamespace(user_id=user.id, role="alumni", email=user.email, full_name=user.full_name)
    client.app.dependency_overrides[require_identity] = lambda: ident
    client.app.dependency_overrides[get_current_identity] = lambda: ident
    return survey, user


def test_submit_update_and_prefill(client, db, survey_setup):
    survey, user = survey_setup
    choice, text = survey.questions
    for answer in ["Online", "Campus"]:
        response = client.post(f"/surveys/{survey.id}", data={f"question_{choice.id}": answer,
            f"question_{text.id}": "Private feedback"}, follow_redirects=False)
        assert response.status_code == 303
    assert db.query(SurveyAnswer).count() == 2
    assert db.query(SurveyAnswer).filter_by(question_id=choice.id).one().answer_text == "Campus"
    response = client.get(f"/surveys/{survey.id}")
    assert 'value="Campus"' in response.text and 'checked' in response.text
    assert 'Private feedback</textarea>' in response.text


@pytest.mark.parametrize("choice,feedback", [("", "Note"), ("Invented", "Note"), ("Online", " "), ("Online", "x" * 4001)])
def test_invalid_submission_does_not_replace_answers(client, db, survey_setup, choice, feedback):
    survey, user = survey_setup
    first, second = survey.questions
    db.add(SurveyAnswer(survey_id=survey.id, question_id=first.id, user_id=user.id, answer_text="Campus"))
    db.commit()
    response = client.post(f"/surveys/{survey.id}", data={f"question_{first.id}": choice, f"question_{second.id}": feedback})
    assert response.status_code == 400
    assert db.query(SurveyAnswer).one().answer_text == "Campus"


def test_results_deduplicate_and_keep_text_private(client, admin_client, db, survey_setup):
    survey, user = survey_setup
    first, second = survey.questions
    for question, answer in [(first, "Online"), (first, "Campus"), (second, "PRIVATE_RESPONSE")]:
        db.add(SurveyAnswer(survey_id=survey.id, question_id=question.id, user_id=user.id, answer_text=answer))
    db.commit()
    result = survey_results(db, survey)
    assert result["respondents"] == 1
    assert result["total_answers"] == 2
    assert result["grouped"][0]["counts"] == {"Online": 0, "Campus": 1}
    response = client.get(f"/surveys/{survey.id}/results")
    assert response.status_code == 200
    assert '100.0%' in response.text and 'progress-bar' in response.text
    assert 'PRIVATE_RESPONSE' not in response.text
    response = admin_client.get(f"/admin/surveys/{survey.id}/results")
    assert response.status_code == 200 and 'PRIVATE_RESPONSE' in response.text


def test_admin_has_management_instead_of_disabled_submit(client, db, survey_setup):
    survey, _ = survey_setup
    admin = SimpleNamespace(user_id=None, role="admin", email="admin@example.test", full_name="Admin")
    client.app.dependency_overrides[get_current_identity] = lambda: admin
    client.app.dependency_overrides[require_identity] = lambda: admin
    response = client.get(f"/surveys/{survey.id}")
    assert f'/admin/surveys/{survey.id}/questions' in response.text
    assert f'action="/surveys/{survey.id}"' not in response.text
    assert client.post(f"/surveys/{survey.id}").status_code == 403
    assert db.query(SurveyAnswer).count() == 0


def test_surveys_require_login_and_hide_inactive_results(client, db, survey_setup):
    survey, _ = survey_setup
    survey.is_active = False
    db.commit()
    assert client.get(f"/surveys/{survey.id}/results").status_code == 404
    assert client.post(f"/surveys/{survey.id}").status_code == 404
    client.app.dependency_overrides.clear()
    assert client.get(f"/surveys/{survey.id}/results").status_code == 401
    assert client.post(f"/surveys/{survey.id}").status_code == 401


def test_catalog_is_idempotent_and_empty_charts_render(client, db):
    seed_additional_surveys(db)
    seed_additional_surveys(db)
    assert db.query(Survey).count() == 3
    assert db.query(SurveyQuestion).count() == 9
    survey = db.query(Survey).first()
    client.app.dependency_overrides[require_identity] = lambda: SimpleNamespace(role="alumni", user_id=1, full_name="Member", email="member@example.test")
    response = client.get(f"/surveys/{survey.id}/results")
    assert response.status_code == 200
    assert '0%' in response.text
