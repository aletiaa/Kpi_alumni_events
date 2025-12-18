from typing import List, Dict

from app.ml.models import Recommendation
from app.ml.nlp_recommender import recommend_events_nlp
from app.ml.popularity import popularity_scores, freshness_score


def hybrid_recommend(
    *,
    user_texts: List[str],
    candidate_events,
    registration_counts: Dict[int, int],
    top_k: int = 3,
    w_nlp: float = 0.6,
    w_popularity: float = 0.25,
    w_freshness: float = 0.15,
) -> List[Recommendation]:
    """
    Hybrid recommender:
      score = NLP + popularity + freshness
    """

    nlp_recs = recommend_events_nlp(
        user_event_texts=user_texts,
        candidate_ids=[e.id for e in candidate_events],
        candidate_texts=[f"{e.title} {e.description}" for e in candidate_events],
        top_k=len(candidate_events),
    )

    pop_scores = popularity_scores(registration_counts)
    event_map = {e.id: e for e in candidate_events}

    hybrid: List[Recommendation] = []

    for rec in nlp_recs:
        event = event_map.get(rec.event_id)
        if not event:
            continue

        final_score = (
            w_nlp * rec.score
            + w_popularity * pop_scores.get(event.id, 0.0)
            + w_freshness * freshness_score(event.start_time)
        )

        hybrid.append(
            Recommendation(
                event_id=rec.event_id,
                score=final_score,
                keywords=rec.keywords,
            )
        )

    hybrid.sort(key=lambda r: r.score, reverse=True)
    return hybrid[:top_k]
