import pytest
from app.routers.admin_events import parse_dt
from datetime import datetime

def test_parse_dt_valid():
    dt_str = "2023-12-19T12:00"
    dt = parse_dt(dt_str)
    assert isinstance(dt, datetime)
    assert dt.year == 2023
    assert dt.month == 12
    assert dt.day == 19

def test_parse_dt_none():
    assert parse_dt(None) is None

def test_parse_dt_invalid():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        parse_dt("not-a-date")
    assert exc_info.value.status_code == 400
