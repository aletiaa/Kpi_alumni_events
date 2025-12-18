from app.db import SessionLocal
from app.models import Event, Registration
from app.services.seeding import seed_events_if_empty


def main():
    db = SessionLocal()
    try:
        # 1) delete child rows first (FK dependent)
        db.query(Registration).delete()
        db.commit()

        # 2) then delete parent rows
        db.query(Event).delete()
        db.commit()

        inserted = seed_events_if_empty(db)
        print(f"OK: inserted {inserted} events")
    finally:
        db.close()


if __name__ == "__main__":
    main()
