# scripts/migrate_add_event_times.py
from sqlalchemy import text

from app.db import SessionLocal


def main():
    db = SessionLocal()
    try:
        # Add end_time if missing
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS iot_visits (
                id BIGSERIAL PRIMARY KEY,
                event_id INT NOT NULL,
                device_id TEXT NOT NULL,
                direction TEXT NOT NULL CHECK (direction IN ('in','out')),
                delta INT NOT NULL CHECK (delta IN (1, -1)),
                ts TIMESTAMPTZ NOT NULL DEFAULT now()
                );

            CREATE INDEX IF NOT EXISTS idx_iot_visits_event_ts ON iot_visits(event_id, ts DESC);
            CREATE INDEX IF NOT EXISTS idx_iot_visits_device_ts ON iot_visits(device_id, ts DESC);
        """))
    
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS iot_counters (
                event_id INT NOT NULL,
                device_id TEXT NOT NULL,
                people_count INT NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (event_id, device_id));
        """))


        db.commit()
        print("OK: columns added (or already existed).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
