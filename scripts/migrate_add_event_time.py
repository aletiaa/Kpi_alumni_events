# scripts/migrate_add_event_times.py
from sqlalchemy import text

from app.db import SessionLocal


def main():
    db = SessionLocal()
    try:
        # Add end_time if missing
        db.execute(text("""
            ALTER TABLE events
            ADD COLUMN IF NOT EXISTS end_time TIMESTAMP NULL;
        """))

        # Add registration_deadline if missing
        db.execute(text("""
            ALTER TABLE events
            ADD COLUMN IF NOT EXISTS registration_deadline TIMESTAMP NULL;
        """))
        
        db.execute(text("""
           ALTER TABLE events
           ADD COLUMN IF NOT EXISTS short_description TEXT;
        """))     

        db.commit()
        print("OK: columns added (or already existed).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
