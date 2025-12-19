import os
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_db

router = APIRouter(prefix="/api/iot", tags=["iot"])


from app.db import get_db

router = APIRouter(prefix="/api/iot", tags=["iot"])

def get_iot_key() -> str:
    return os.getenv("IOT_API_KEY", "")

class VisitIn(BaseModel):
    event_id: int
    device_id: str = Field(min_length=3, max_length=64)
    direction: str  # "in" or "out"
    delta: int      # 1 or -1
    people_count: int | None = None

@router.post("/visits")
def post_visit(
    payload: VisitIn,
    db: Session = Depends(get_db),
    x_iot_key: str | None = Header(default=None),
):
    iot_key = get_iot_key()
    if not iot_key:
        raise HTTPException(status_code=500, detail="IOT_API_KEY is not set on server")
    if x_iot_key != iot_key:
        raise HTTPException(status_code=401, detail="Invalid IoT key")

    direction = (payload.direction or "").strip().lower()
    if direction not in ("in", "out"):
        raise HTTPException(status_code=400, detail="direction must be 'in' or 'out'")

    if payload.delta not in (1, -1):
        raise HTTPException(status_code=400, detail="delta must be 1 or -1")

    try:
        db.execute(
            text("""
                INSERT INTO iot_visits (event_id, device_id, direction, delta)
                VALUES (:event_id, :device_id, :direction, :delta)
            """),
            {
                "event_id": payload.event_id,
                "device_id": payload.device_id.strip(),
                "direction": direction,
                "delta": payload.delta,
            },
        )
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/visits")
def visits_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"ok": True, "db": "ok", "hint": "Use POST with JSON body + X-IoT-Key header."}
    except Exception as e:
        return {"ok": False, "db": "error", "detail": str(e)}


@router.get("/events/{event_id}/stats")
def event_iot_stats(event_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("""
            SELECT
              COALESCE(SUM(CASE WHEN direction='in'  THEN 1 ELSE 0 END), 0) AS in_count,
              COALESCE(SUM(CASE WHEN direction='out' THEN 1 ELSE 0 END), 0) AS out_count,
              COALESCE(SUM(delta), 0) AS net,
              MAX(ts) AS last_ts
            FROM iot_visits
            WHERE event_id = :event_id
        """),
        {"event_id": event_id},
    ).mappings().one()

    return {
        "ok": True,
        "event_id": event_id,
        "in": int(row["in_count"]),
        "out": int(row["out_count"]),
        "net": int(row["net"]),
        "last_ts": row["last_ts"].isoformat() if row["last_ts"] else None,
    }


@router.get("/stats")
def all_events_iot_stats(db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT
              event_id,
              COALESCE(SUM(CASE WHEN direction='in'  THEN 1 ELSE 0 END), 0) AS in_count,
              COALESCE(SUM(CASE WHEN direction='out' THEN 1 ELSE 0 END), 0) AS out_count,
              COALESCE(SUM(delta), 0) AS net,
              MAX(ts) AS last_ts
            FROM iot_visits
            GROUP BY event_id
            ORDER BY event_id
        """)
    ).mappings().all()

    return {
        "ok": True,
        "events": [
            {
                "event_id": int(r["event_id"]),
                "in": int(r["in_count"]),
                "out": int(r["out_count"]),
                "net": int(r["net"]),
                "last_ts": r["last_ts"].isoformat() if r["last_ts"] else None,
            }
            for r in rows
        ],
    }
