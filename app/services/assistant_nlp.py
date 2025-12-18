from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

@dataclass
class EventQuery:
    start_from: datetime | None = None
    start_to: datetime | None = None
    limit: int = 10


def parse_event_query(text: str, now: datetime | None = None) -> EventQuery:
    q = (text or "").strip().lower()
    now = now or datetime.utcnow()

    # upcoming / next events
    if re.search(r"\b(upcoming|next)\b", q):
        return EventQuery(start_from=now, limit=10)

    # this week
    if re.search(r"\b(this week|week)\b", q):
        start = now
        end = now + timedelta(days=7)
        return EventQuery(start_from=start, start_to=end, limit=20)

    # month name (e.g., "events in december")
    for name, month in MONTHS.items():
        if re.search(rf"\b{name}\b", q):
            year = now.year
            start = datetime(year, month, 1)
            # next month boundary
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)

            # if month already passed this year and user likely means next year
            if end < now:
                year += 1
                start = datetime(year, month, 1)
                end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

            return EventQuery(start_from=start, start_to=end, limit=50)

    # fallback: show upcoming by default
    return EventQuery(start_from=now, limit=10)
