"""Back up local SQLite, remove known seeded accounts, add isolated demo surveys.

Run with `python -m scripts.prepare_release_data --apply` while the app is stopped.
Without --apply this only reports the number of matching seeded accounts.
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, or_, update

from app.db import Base, SessionLocal, engine
from app.models import Survey, SurveyAnswer, SurveyQuestion, User


SEED_EMAILS = {
    "olena.alumni@example.com", "andrii.alumni@example.com",
    "maria.student@example.com", "private@example.com", "ihor.ip91@example.com",
    "sofia.ip91@example.com", "dmytro.fiot@example.com",
    "kateryna.fmm@example.com", "nazar.cyber@example.com",
}
DEMO_NOTICE = "DEMO: Synthetic anonymous answers for chart demonstration only. Not research data."


def clean_seed_users(db):
    ids = [u.id for u in db.query(User).filter(User.email.in_(SEED_EMAILS))]
    return delete_users(db, ids)


def delete_users(db, ids):
    if not ids:
        return 0
    # Preserve authored news, remove dependent test activity before its users.
    for table in reversed(Base.metadata.sorted_tables):
        if table.name == "users":
            continue
        columns = [c for c in table.c if any(fk.target_fullname == "users.id" for fk in c.foreign_keys)]
        if table.name == "telegram_bot_replies":
            columns.append(table.c.user_id)
        if not columns:
            continue
        condition = or_(*(c.in_(ids) for c in columns))
        if table.name == "news":
            db.execute(update(table).where(condition).values(author_id=None))
        else:
            db.execute(delete(table).where(condition))
    db.execute(delete(User).where(User.id.in_(ids)))
    return len(ids)


def add_demo_surveys(db):
    created = 0
    originals = db.query(Survey).filter(~Survey.title.startswith("[DEMO]")).all()
    for original in originals:
        title = "[DEMO] " + original.title[:190]
        if db.query(Survey).filter_by(title=title).first():
            continue
        demo = Survey(title=title, description=DEMO_NOTICE, is_active=False)
        db.add(demo)
        db.flush()
        for source in original.questions:
            question = SurveyQuestion(survey_id=demo.id, question_text=source.question_text,
                                      question_type=source.question_type, options_text=source.options_text)
            db.add(question)
            db.flush()
            options = [line.strip() for line in (source.options_text or "").splitlines() if line.strip()]
            for number in range(8):
                answer = (options[(number * number + source.id) % len(options)]
                          if source.question_type == "single_choice" and options
                          else "[DEMO] More alumni events and mentoring opportunities.")
                db.add(SurveyAnswer(survey_id=demo.id, question_id=question.id,
                                    user_id=None, answer_text=answer))
        created += 1
    return created


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        print("Known seeded accounts:", db.query(User).filter(User.email.in_(SEED_EMAILS)).count())
        if not args.apply:
            return
        if engine.dialect.name != "sqlite" or not engine.url.database:
            raise SystemExit("This maintenance command requires a local SQLite database.")
        backup_dir = Path(__file__).resolve().parents[1] / "backups"
        backup_dir.mkdir(exist_ok=True)
        destination = backup_dir / (datetime.now().strftime("release-%Y%m%d-%H%M%S-%f") + ".db")
        with sqlite3.connect(engine.url.database) as source, sqlite3.connect(destination) as target:
            source.backup(target)
        print("Backup created:", destination.name)
        removed = clean_seed_users(db)
        created = add_demo_surveys(db)
        db.commit()
        print("Removed seeded accounts:", removed, "Demo surveys created:", created)


if __name__ == "__main__":
    main()
