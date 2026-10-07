from datetime import datetime
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User
from app.db import Base
from app.routers.admin_events import validate_event_dates, parse_dt


@pytest.mark.parametrize('start,end,deadline,capacity', [
    (None, None, None, 10),
    ('2026-11-10T10:00', '2026-11-10T09:00', None, 10),
    ('2026-11-10T10:00', '2026-11-10T10:00', None, 10),
    ('2026-11-10T10:00', None, '2026-11-10T11:00', 10),
    ('2026-11-10T10:00', None, None, 0),
    ('2026-11-10T10:00', None, None, -1),
])
def test_invalid_event_logic(start, end, deadline, capacity):
    with pytest.raises(HTTPException) as error:
        validate_event_dates(parse_dt(start), parse_dt(end), parse_dt(deadline), capacity)
    assert error.value.status_code == 400


def test_valid_event_dates_and_timezone():
    start = parse_dt('2026-11-10T12:00+02:00')
    assert start == datetime(2026, 11, 10, 10)
    validate_event_dates(start, datetime(2026, 11, 10, 11), start, 1)
    validate_event_dates(start, None, None, 10)


def test_startup_does_not_override_profile_privacy(tmp_path, monkeypatch):
    from app import main
    engine = create_engine('sqlite:///' + str(tmp_path / 'startup.db'))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        user = User(email='hidden@example.test', full_name='Hidden User', role='alumni',
                    password_hash='unused', is_profile_public=False, is_active=True)
        db.add(user)
        db.commit()
        user_id = user.id
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(main, 'SessionLocal', factory)
    monkeypatch.setattr(main, 'SEED_DEMO_DATA', False)
    main.bootstrap_database()
    main.bootstrap_database()
    with factory() as db:
        assert db.get(User, user_id).is_profile_public is False
