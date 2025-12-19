import pytest
from app.services.seeding import seed_events_if_empty
from unittest.mock import MagicMock

def test_seed_events_if_empty_returns_int():
    db = MagicMock()
    result = seed_events_if_empty(db)
    assert isinstance(result, int)
