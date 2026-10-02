"""Replace only explicitly selected incomplete profiles, retaining a SQLite backup.

Credentials are written to ignored backups/test-accounts.md, never to source code.
Run locally with the application stopped: python -m scripts.create_test_profiles --apply
"""
import argparse
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func

from app.db import SessionLocal, engine
from app.models import User
from app.security import hash_password
from app.services.seeding import USER_AVATARS
from scripts.prepare_release_data import delete_users


# Explicitly requested screenshot profiles; never delete other incomplete members.
REPLACEMENTS = {
    "alina.seikauskaite2@gmail.com", "alina.seikauskaite@gmail.com", "a.s@gmail.com",
    "irene15o@icloud.com", "seikauskaite.alina_tv-52mp@edu.kpi.ua",
}
REQUIRED_FIELDS = ("full_name", "full_name_en", "faculty", "specialty", "group_name",
                   "graduation_year", "bio", "birth_date", "city_country", "current_position",
                   "company", "skills", "interests", "help_topics", "avatar_url")
PROFILES = [
    ("Olena Koval", "mentor.olena", "Backend Engineer", "Python, FastAPI, PostgreSQL", "Backend architecture and code review", "FIOT", "Software Engineering", "IP-91", 2023, "Kyiv, Ukraine"),
    ("Andrii Melnyk", "mentor.andrii", "Security Engineer", "Cybersecurity, SOC, Linux", "Application security and career planning", "FEL", "Cybersecurity", "KB-82", 2022, "Warsaw, Poland"),
    ("Sofiia Lytvyn", "mentor.sofiia", "Frontend Engineer", "React, TypeScript, accessibility", "Frontend portfolios and accessible interfaces", "FIOT", "Computer Science", "KN-91", 2023, "Lviv, Ukraine"),
    ("Dmytro Honchar", "mentor.dmytro", "Data Engineer", "SQL, Python, ETL", "Data pipelines and technical interviews", "FIOT", "Computer Science", "KN-81", 2022, "Prague, Czechia"),
    ("Mariia Shevchenko", "alumni.mariia", "Project Coordinator", "Planning, communication, Scrum", "Community projects and event coordination", "FMM", "Management", "UV-91", 2023, "Kyiv, Ukraine"),
    ("Ihor Petrenko", "alumni.ihor", "QA Engineer", "Testing, Playwright, API testing", "Test plans and quality assurance", "FIOT", "Software Engineering", "IP-01", 2024, "Berlin, Germany"),
    ("Kateryna Romaniuk", "alumni.kateryna", "Product Analyst", "Analytics, SQL, research", "Product research and survey design", "FMM", "Management", "UV-01", 2024, "Lviv, Ukraine"),
    ("Nazar Boiko", "student.nazar", "Security Student", "Linux, networks, Python", "Student security workshops", "FEL", "Cybersecurity", "KB-31", 2027, "Kyiv, Ukraine"),
    ("Yuliia Bondar", "student.yuliia", "Software Engineering Student", "Python, HTML, CSS", "Study groups and student projects", "FIOT", "Software Engineering", "IP-31", 2027, "Kyiv, Ukraine"),
    ("Maksym Savchuk", "student.maksym", "Data Science Student", "Python, statistics, SQL", "Data analysis study groups", "FIOT", "Computer Science", "KN-31", 2027, "Lviv, Ukraine"),
]


def replace_profiles(db):
    emails = [p[1] + "@example.test" for p in PROFILES]
    if db.query(User).filter(User.email.in_(emails)).count():
        raise ValueError("Test accounts already exist; refusing to reset passwords or overwrite profiles.")
    # Never reuse deleted IDs: old session cookies must not authenticate as new people.
    next_id = (db.query(func.max(User.id)).scalar() or 0) + 1
    candidates = db.query(User).filter(User.email.in_(REPLACEMENTS)).all()
    ids = [u.id for u in candidates if not all(getattr(u, key) for key in REQUIRED_FIELDS)]
    removed = delete_users(db, ids)
    credentials = []
    for index, profile in enumerate(PROFILES):
        name, alias, position, skills, help_topics, faculty, specialty, group, year, location = profile
        password = secrets.token_urlsafe(15)
        mentor = index < 4
        role = "student" if index >= 7 else "alumni"
        user = User(id=next_id + index, full_name=name, full_name_en=name,
                    email=alias + "@example.test", password_hash=hash_password(password),
                    role=role, is_active=True, is_blocked=False, is_email_verified=True,
                    faculty=faculty, specialty=specialty, group_name=group, graduation_year=year,
                    birth_date=date(2000 if index < 7 else 2005, index + 1, 12),
                    bio=f"Demo profile for testing AlumnixHub. {position} interested in alumni collaboration. "
                        f"Available for {help_topics.lower()}.",
                    city_country=location, current_position=position, company="AlumnixHub Demo Lab",
                    skills=skills, interests=f"{specialty}, alumni events, mentoring, career development",
                    help_topics=help_topics, is_mentor=mentor,
                    mentorship_topics=help_topics if mentor else None,
                    status="Available for mentoring" if mentor else "Open to collaboration",
                    avatar_url=USER_AVATARS[index % len(USER_AVATARS)], is_profile_public=True,
                    preferred_language="en", notifications_enabled=False)
        db.add(user)
        from scripts.localize_test_profiles import apply_text
        apply_text(db, user, index, profile)
        credentials.append({"name": name, "email": user.email, "password": password,
                            "role": "mentor" if mentor else role})
    db.flush()
    return removed, credentials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("No changes made. Use --apply with the local app stopped.")
        return
    if engine.dialect.name != "sqlite":
        raise SystemExit("Local SQLite only: never run this maintenance against production.")
    folder = Path(__file__).resolve().parents[1] / "backups"
    folder.mkdir(exist_ok=True)
    credentials_path = folder / "test-accounts.md"
    if credentials_path.exists():
        raise SystemExit("Credentials file already exists; refusing to overwrite.")
    backup = folder / (datetime.now().strftime("profiles-%Y%m%d-%H%M%S-%f") + ".db")
    with sqlite3.connect(engine.url.database) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    with SessionLocal() as db:
        removed, credentials = replace_profiles(db)
        lines = ["# Local test accounts", "", "Only for local testing. Emails do not receive mail.",
                 "Do not deploy these pre-verified accounts to production.", "",
                 "Login: http://127.0.0.1:8000/login", "",
                 "| Name | Role | Email | Password |", "| --- | --- | --- | --- |"]
        lines += [f"| {c['name']} | {c['role']} | {c['email']} | {c['password']} |" for c in credentials]
        credentials_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        db.commit()
    print("Removed incomplete profiles:", removed)
    print("Created accounts:", len(credentials), "Mentors:", sum(c['role'] == 'mentor' for c in credentials))
    print("Private credentials:", credentials_path)


if __name__ == "__main__":
    main()
