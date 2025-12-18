from dataclasses import dataclass
from typing import List

@dataclass
class Recommendation:
    event_id: int
    score: float
    keywords: List[str]
