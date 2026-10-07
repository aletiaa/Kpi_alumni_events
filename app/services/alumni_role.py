"""Promote students only after a valid recorded graduation year has elapsed."""
from datetime import date


def promote_graduated_student(user, admission_year=None, today=None):
    today = today or date.today()
    year = user.graduation_year
    if user.role != 'student' or not year or not 1965 <= year < today.year:
        return False
    if user.birth_date and (user.birth_date > today or year < user.birth_date.year + 15):
        return False
    if admission_year is not None and year < admission_year:
        return False
    user.role = 'alumni'
    return True


def promote_existing_students(db):
    from app.models import User, ProfileReference
    changed = 0
    for user in db.query(User).filter_by(role='student').all():
        reference = db.get(ProfileReference, user.id)
        changed += promote_graduated_student(user, reference.admission_year if reference else None)
    return changed
