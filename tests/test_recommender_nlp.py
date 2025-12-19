from app.ml.nlp_recommender import recommend_events_nlp

def test_nlp_recommender_returns_empty_if_no_history():
    recs = recommend_events_nlp(
        user_event_texts=[],
        candidate_ids=[1],
        candidate_texts=["music event in london"],
        min_history=1,
    )
    assert recs == []

def test_nlp_recommender_ranks_relevant_higher():
    user = ["I like machine learning and AI conferences"]
    cand_ids = [1, 2]
    cand_texts = [
        "AI and machine learning meetup with talks",
        "Cooking masterclass pasta and desserts",
    ]
    recs = recommend_events_nlp(
        user_event_texts=user,
        candidate_ids=cand_ids,
        candidate_texts=cand_texts,
        top_k=2,
        explain_top_terms=5,
    )
    assert len(recs) == 2
    assert recs[0].event_id == 1
    assert recs[0].score >= recs[1].score
    # explainability
    assert isinstance(recs[0].keywords, list)
