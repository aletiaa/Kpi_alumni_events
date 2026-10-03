from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.deps import require_identity
from app.models import User


def profile_user(client, db):
    user = User(email="dates@example.test", full_name="Original Name", password_hash="unused",
                role="alumni", is_active=True, birth_date=date(1990, 1, 1), graduation_year=2012)
    db.add(user)
    db.commit()
    client.app.dependency_overrides[require_identity] = lambda: SimpleNamespace(
        role="alumni", user_id=user.id, full_name=user.full_name, email=user.email)
    return user


@pytest.mark.parametrize("birthday,year", [
    ((date.today() + timedelta(days=1)).isoformat(), "1905"),
    ("2028-09-21", "1905"),
    ("2020-02-30", "2012"),
    ("1990-01-01", "not-a-year"),
    ("1990-01-01", "2012.5"),
    ("1990-01-01", "1899"),
    ("1990-01-01", str(date.today().year + 1)),
    ("2000-01-01", "1905"),
    ("2000-01-01", "2000"),
])
def test_invalid_dates_do_not_change_profile(client, db, birthday, year):
    user = profile_user(client, db)
    response = client.post("/profile", data={"full_name": "Changed Name", "birth_date": birthday,
                                           "graduation_year": year}, follow_redirects=False)
    assert response.status_code == 400
    db.refresh(user)
    assert user.full_name == "Original Name"
    assert user.birth_date == date(1990, 1, 1)
    assert user.graduation_year == 2012


@pytest.mark.parametrize("birthday,year", [("1990-01-01", "2012"), ("", ""),
                                         ("1990-01-01", str(date.today().year))])
def test_valid_or_optional_dates_save(client, db, birthday, year):
    user = profile_user(client, db)
    response = client.post("/profile", data={"full_name": user.full_name, "birth_date": birthday,
                                           "graduation_year": year}, follow_redirects=False)
    assert response.status_code == 303
    db.refresh(user)
    assert user.birth_date == (date.fromisoformat(birthday) if birthday else None)
    assert user.graduation_year == (int(year) if year else None)


def test_profile_form_has_date_limits(client, db):
    profile_user(client, db)
    page = client.get("/profile").text
    assert f'max="{date.today().isoformat()}"' in page
    assert f'max="{date.today().year}"' in page
    assert 'min="1900"' in page
