"""Maintain Ukrainian source text and reviewed English translations for test accounts."""
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

from app.db import SessionLocal, engine
from app.models import ContentTranslation, User


TEXTS = [
    ("Олена Коваль", "Бекенд-розробниця", "Python, FastAPI, PostgreSQL", "Архітектура серверних застосунків і перевірка коду"),
    ("Андрій Мельник", "Інженер із кібербезпеки", "Кібербезпека, SOC, Linux", "Безпека застосунків і планування кар'єри"),
    ("Софія Литвин", "Фронтенд-розробниця", "React, TypeScript, доступність інтерфейсів", "Портфоліо розробника та доступні інтерфейси"),
    ("Дмитро Гончар", "Інженер даних", "SQL, Python, ETL", "Обробка даних і підготовка до технічних співбесід"),
    ("Марія Шевченко", "Координаторка проєктів", "Планування, комунікація, Scrum", "Спільнотні проєкти та організація подій"),
    ("Ігор Петренко", "Інженер із тестування", "Тестування, Playwright, перевірка API", "Плани тестування та забезпечення якості"),
    ("Катерина Романюк", "Продуктова аналітикиня", "Аналітика, SQL, дослідження", "Дослідження продуктів і створення опитувань"),
    ("Назар Бойко", "Студент напряму кібербезпеки", "Linux, мережі, Python", "Студентські воркшопи з кібербезпеки"),
    ("Юлія Бондар", "Студентка програмної інженерії", "Python, HTML, CSS", "Навчальні групи та студентські проєкти"),
    ("Максим Савчук", "Студент напряму науки про дані", "Python, статистика, SQL", "Навчальні групи з аналізу даних"),
]
SPECIALTIES = {"Software Engineering": "Інженерія програмного забезпечення",
               "Cybersecurity": "Кібербезпека", "Computer Science": "Комп'ютерні науки",
               "Management": "Менеджмент"}
CITIES = {"Kyiv, Ukraine": "Україна, Київ", "Warsaw, Poland": "Польща, Варшава",
          "Lviv, Ukraine": "Україна, Львів", "Prague, Czechia": "Чехія, Прага",
          "Berlin, Germany": "Німеччина, Берлін"}


def apply_text(db, user, index, profile):
    name, alias, position, skills, help_topics, faculty, specialty, group, year, location = profile
    uk_name, uk_position, uk_skills, uk_help = TEXTS[index]
    user.full_name, user.full_name_en = uk_name, name
    user.group_name = group.replace("IP", "ІП").replace("KN", "КН").replace("KB", "КБ").replace("UV", "УВ")
    uk_bio = f"Цікавлюся співпрацею у спільноті випускників, обміном досвідом і професійним розвитком. Мій напрям: {SPECIALTIES[specialty].lower()}."
    en_bio = f"Interested in alumni collaboration, sharing experience and professional development. My field is {specialty.lower()}."
    pairs = {
        "bio": (uk_bio, en_bio),
        "current_position": (uk_position, position),
        "skills": (uk_skills, skills),
        "help_topics": (uk_help, help_topics),
        "specialty": (SPECIALTIES[specialty], specialty),
        "faculty": ({"FIOT": "ФІОТ", "FEL": "ФЕЛ", "FMM": "ФММ"}[faculty], faculty),
        "city_country": (CITIES[location], location),
        "company": ("Спільнота AlumnixHub", "AlumnixHub Community"),
        "status": ("Відкритий до менторства" if index < 4 else "Відкритий до співпраці",
                   "Available for mentoring" if index < 4 else "Open to collaboration"),
        "interests": (f"{SPECIALTIES[specialty]}, події випускників, менторство, кар'єрний розвиток",
                      f"{specialty}, alumni events, mentoring, career development"),
    }
    if user.is_mentor:
        pairs["mentorship_topics"] = (uk_help, help_topics)
    for field, (ukrainian, english) in pairs.items():
        setattr(user, field, ukrainian)
        digest = hashlib.sha256(("deepl:en-gb:v1:" + ukrainian).encode("utf-8")).hexdigest()
        cached = db.get(ContentTranslation, digest)
        if cached:
            cached.english = english
        else:
            db.add(ContentTranslation(source_hash=digest, english=english))
        db.flush()


def main():
    from scripts.create_test_profiles import PROFILES
    if engine.dialect.name != "sqlite":
        raise SystemExit("Local SQLite only")
    folder = Path(__file__).resolve().parents[1] / "backups"
    folder.mkdir(exist_ok=True)
    with sqlite3.connect(engine.url.database) as source, sqlite3.connect(folder / datetime.now().strftime("profile-text-%Y%m%d-%H%M%S.db")) as target:
        source.backup(target)
    with SessionLocal() as db:
        count = 0
        for index, profile in enumerate(PROFILES):
            user = db.query(User).filter_by(email=profile[1] + "@example.test").first()
            if user:
                apply_text(db, user, index, profile)
                count += 1
        db.commit()
    print("Bilingual profiles updated:", count)


if __name__ == "__main__":
    main()
