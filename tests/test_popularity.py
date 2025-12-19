import pytest
from app.ml.popularity import normalize, popularity_scores, freshness_score
from datetime import datetime, timedelta

def test_normalize():
    assert normalize(5, 10) == 0.5
    assert normalize(0, 10) == 0.0
    assert normalize(10, 10) == 1.0

def test_popularity_scores():
    scores = popularity_scores({1: 10, 2: 20})
    assert set(scores.keys()) == {1, 2}
    assert scores[2] > scores[1]

def test_freshness_score():
    now = datetime.utcnow()
    past = now - timedelta(days=1)
    score = freshness_score(past)
    assert isinstance(score, float)
    assert 0 <= score <= 1
