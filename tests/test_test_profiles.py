import pytest

from app.models import User
from app.security import verify_password
from scripts.create_test_profiles import REQUIRED_FIELDS, replace_profiles


def test_accounts_complete_unique_hashed_and_exactly_four_mentors(db):
    previous = User(id=50, full_name="Incomplete", email="a.s@gmail.com", password_hash="unused")
    unrelated = User(id=51, full_name="Keep", email="keep@example.test", password_hash="unused")
    db.add_all([previous, unrelated])
    db.commit()
    removed, credentials = replace_profiles(db)
    db.commit()
    assert removed == 1
    assert db.get(User, 50) is None
    assert db.get(User, 51) is not None
    assert len(credentials) == len({c['password'] for c in credentials}) == 10
    assert db.query(User).filter_by(is_mentor=True).count() == 4
    for account in credentials:
        user = db.query(User).filter_by(email=account['email']).one()
        assert user.id > 51
        assert all(getattr(user, field) for field in REQUIRED_FIELDS)
        assert verify_password(account['password'], user.password_hash)
        assert user.is_email_verified and user.is_active
        assert not user.notifications_enabled
        if user.is_mentor:
            assert user.mentorship_topics
    with pytest.raises(ValueError):
        replace_profiles(db)


def test_complete_selected_account_is_preserved(db):
    _, credentials = replace_profiles(db)
    db.flush()
    user = db.query(User).filter_by(email=credentials[0]['email']).one()
    user.email = 'a.s@gmail.com'
    # Remove other fixtures, keeping one fully populated selected profile.
    db.query(User).filter(User.id != user.id).delete(synchronize_session=False)
    db.commit()
    removed, _ = replace_profiles(db)
    assert removed == 0
    assert db.query(User).filter_by(email='a.s@gmail.com').count() == 1
