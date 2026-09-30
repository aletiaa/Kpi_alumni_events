import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import SessionLocal
from app.models import Event


def reschedule(events):
    start = datetime(2026, 10, 2, 18)
    for index, event in enumerate(events):
        duration = event.end_time - event.start_time if event.end_time else None
        lead = event.start_time - event.registration_deadline if event.registration_deadline else None
        event.start_time = start + timedelta(days=round(index * 57 / max(len(events) - 1, 1)))
        if duration is not None:
            event.end_time = event.start_time + max(duration, timedelta(minutes=30))
        if lead is not None:
            event.registration_deadline = event.start_time - max(lead, timedelta(hours=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with SessionLocal() as db:
        events = db.query(Event).order_by(Event.start_time, Event.id).all()
        if args.apply:
            backup = Path('.pytest_cache') / ('events-before-autumn-' + datetime.now().strftime('%Y%m%d%H%M%S') + '.json')
            backup.parent.mkdir(exist_ok=True)
            backup.write_text(json.dumps([{key: (getattr(e, key).isoformat() if getattr(e, key) else None)
                for key in ('start_time', 'end_time', 'registration_deadline')} | {'id':e.id} for e in events], indent=2))
        reschedule(events)
        for event in events:
            print(event.id, event.start_time.isoformat(), event.end_time.isoformat() if event.end_time else '')
        if args.apply:
            db.commit()
            print('Updated events:', len(events))
