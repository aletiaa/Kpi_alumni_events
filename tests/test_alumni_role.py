from datetime import date
from types import SimpleNamespace
import pytest
from app.services.alumni_role import promote_graduated_student, promote_existing_students
from app.models import User


@pytest.mark.parametrize('role,year,expected', [
    ('student',2025,'alumni'), ('student',2026,'student'),
    ('student',2027,'student'), ('student',None,'student'),
    ('student',1905,'student'), ('guest',2025,'guest'),
    ('admin',2025,'admin'), ('alumni',2025,'alumni'),
])
def test_role_boundaries(role, year, expected):
    user=SimpleNamespace(role=role,graduation_year=year,birth_date=None)
    promote_graduated_student(user,today=date(2026,10,6))
    assert user.role==expected


def test_invalid_dates_do_not_promote_and_status_is_preserved():
    user=SimpleNamespace(role='student',graduation_year=2025,
                         birth_date=date(2015,1,1),status='Employed')
    assert not promote_graduated_student(user,today=date(2026,10,6))
    user.birth_date=date(1990,1,1)
    assert not promote_graduated_student(user,2026,today=date(2026,10,6))
    assert promote_graduated_student(user,2020,today=date(2026,10,6))
    assert user.status=='Employed'
    assert not promote_graduated_student(user,today=date(2026,10,6))


def test_existing_student_promotion_is_idempotent(db):
    user=User(email='graduated-student@example.test',full_name='Graduate',role='student',
              graduation_year=date.today().year-1,password_hash='unused')
    db.add(user); db.commit()
    assert promote_existing_students(db)==1
    db.commit()
    assert user.role=='alumni'
    assert promote_existing_students(db)==0
