from datetime import datetime, timedelta
from app.ml.popularity import popularity_scores, freshness_score

def test_popularity_scores_empty():
    assert popularity_scores({}) == {}

def test_popularity_scores_normalizes():
    scores = popularity_scores({1: 10, 2: 5, 3: 0})
    assert scores[1] == 1.0
    assert 0.0 <= scores[2] < 1.0
    assert scores[3] == 0.0

def test_freshness_score_today_close_to_1():
    s = freshness_score(datetime.utcnow())
    assert 0.99 <= s <= 1.0

def test_freshness_score_decreases_with_time():
    s1 = freshness_score(datetime.utcnow() + timedelta(days=7))
    s2 = freshness_score(datetime.utcnow() + timedelta(days=30))
    s3 = freshness_score(datetime.utcnow() + timedelta(days=60))
    assert s1 > s2 > s3
