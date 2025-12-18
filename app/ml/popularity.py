from datetime import datetime
from typing import Dict
import math


def normalize(value: float, max_value: float) -> float:
    return value / max_value if max_value else 0.0


def popularity_scores(event_reg_counts: Dict[int, int]) -> Dict[int, float]:
    """
    Normalize registrations to [0..1]
    """
    max_count = max(event_reg_counts.values(), default=0)
    return {
        event_id: normalize(count, max_count)
        for event_id, count in event_reg_counts.items()
    }


def freshness_score(event_start: datetime) -> float:
    """
    Exponential decay: events happening sooner are preferred
    """
    days_until = max((event_start - datetime.utcnow()).days, 0)
    return math.exp(-days_until / 30)
