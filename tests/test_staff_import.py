from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest

from app.db import Base
from app.models import User
from app.security import verify_password
from app.services.staff_directory import staff_records
from scripts.import_kpi_staff import create_accounts


def test_import_is_safe_and_idempotent():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        credentials = create_accounts(db, staff_records())
        db.commit()
        assert len(credentials) == 15
        assert len({row['initial_password'] for row in credentials}) == 15
        for row in credentials:
            user = db.query(User).filter_by(email=row['login_email']).one()
            assert user.role == 'guest'
            assert user.status == 'Викладач університету'
            assert not user.notifications_enabled
            assert user.password_hash != row['initial_password']
            assert verify_password(row['initial_password'], user.password_hash)
        assert create_accounts(db, staff_records()) == []
        record = next(row for row in staff_records() if row['login_email'] == user.email)
        old_hash = user.password_hash
        user.full_name = record['source_full_name']
        create_accounts(db, [record])
        assert user.full_name == record['full_name']
        assert user.full_name_en == record['full_name_en']
        assert user.password_hash == old_hash
        user.status = 'Інший професійний статус'
        create_accounts(db, staff_records())
        assert user.status == 'Інший професійний статус'
        user.status = None
        create_accounts(db, staff_records())
        assert user.status == 'Викладач університету'
        assert db.query(User).count() == 15
        invalid = dict(staff_records()[0], login_email='real@example.org')
        with pytest.raises(ValueError):
            create_accounts(db, [invalid])


def test_public_catalog_contains_no_credentials_or_claimed_consent():
    records = staff_records()
    assert len(records) == 15
    for record in records:
        assert record['mentoring_confirmed'] is False
        assert len(record['full_name'].split()) == 2
        assert len(record['full_name_en'].split()) == 2
        assert 'password' not in record
        assert 'password_hash' not in record
        assert record['login_email'] not in record['contact_emails']
        assert record['source_url'].startswith('https://iate.kpi.ua/')
