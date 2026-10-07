"""Public provenance for administrator-created staff test profiles."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def staff_records():
    path = Path(__file__).resolve().parents[1] / 'data/kpi_staff.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []


def staff_record(user):
    return next((row for row in staff_records() if row['login_email'] == user.email), None)
