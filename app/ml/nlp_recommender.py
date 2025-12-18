from __future__ import annotations

from typing import List, Optional
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.ml.models import Recommendation


def _safe_text(s: Optional[str]) -> str:
    return (s or "").strip()


def recommend_events_nlp(
    user_event_texts: List[str],
    candidate_ids: List[int],
    candidate_texts: List[str],
    *,
    top_k: int = 5,
    min_history: int = 1,
    explain_top_terms: int = 6,
    ngram_range=(1, 2),
) -> List[Recommendation]:
    """
    Pure content-based NLP recommender.

    - TF-IDF (1–2 grams)
    - Time-weighted user profile
    - Cosine similarity
    - Explainable keywords
    """

    if len(user_event_texts) < min_history:
        return []

    if not candidate_ids or not candidate_texts:
        return []

    if len(candidate_ids) != len(candidate_texts):
        return []

    user_texts = [_safe_text(t) for t in user_event_texts]
    cand_texts = [_safe_text(t) for t in candidate_texts]

    if not any(user_texts):
        return []

    corpus = user_texts + cand_texts

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=ngram_range,
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )

    X = vectorizer.fit_transform(corpus)

    user_X = X[: len(user_texts)]
    cand_X = X[len(user_texts) :]

    # ----- Time-weighted user profile -----
    if user_X.shape[0] == 1:
        user_profile = user_X.mean(axis=0)
    else:
        weights = np.linspace(0.5, 1.0, user_X.shape[0])
        user_profile = (user_X.T @ weights).T / weights.sum()

    user_profile = np.asarray(user_profile).reshape(1, -1)

    similarities = cosine_similarity(user_profile, cand_X).flatten()

    feature_names = vectorizer.get_feature_names_out()

    recommendations: List[Recommendation] = []

    for idx, (event_id, score) in enumerate(zip(candidate_ids, similarities)):
        cand_vec = cand_X[idx].toarray().ravel()
        contrib = (user_profile.ravel() * cand_vec)

        if contrib.size == 0:
            keywords = []
        else:
            top_idx = np.argsort(contrib)[-explain_top_terms:][::-1]
            keywords = [
                feature_names[i]
                for i in top_idx
                if contrib[i] > 0
            ][:explain_top_terms]

        recommendations.append(
            Recommendation(
                event_id=int(event_id),
                score=float(score),
                keywords=keywords,
            )
        )

    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations[:top_k]
