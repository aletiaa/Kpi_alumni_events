import re
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WS = re.compile(r"\s+")


def _sentences(text: str) -> List[str]:
    text = (text or "").strip()
    text = _WS.sub(" ", text)
    if not text:
        return []
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def generate_short_description(
    title: str,
    description: str,
    *,
    max_sentences: int = 2,
    max_chars: int = 180,
) -> str:
    """
    Lightweight extractive "NLP" summarizer:
    - splits into sentences
    - scores sentences using TF-IDF similarity to full text
    - returns top N sentences, capped to max_chars
    """
    title = (title or "").strip()
    desc = (description or "").strip()

    if not desc:
        return (title[:max_chars]).strip()

    sents = _sentences(desc)
    if not sents:
        combined = f"{title}. {desc}".strip()
        return combined[:max_chars].strip()

    # TF-IDF over sentences + full doc
    doc = " ".join(sents)
    corpus = sents + [doc]

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    X = vec.fit_transform(corpus)

    sent_X = X[:-1]
    doc_X = X[-1]

    # Score = cosine similarity to doc vector (manual; avoids pairwise imports)
    # sim(a,b) = (a·b) / (||a|| ||b||)
    doc_norm = np.linalg.norm(doc_X.toarray())
    scores = []
    for i in range(sent_X.shape[0]):
        s = sent_X[i].toarray()
        s_norm = np.linalg.norm(s)
        if s_norm == 0 or doc_norm == 0:
            scores.append(0.0)
        else:
            scores.append(float((s @ doc_X.toarray().T) / (s_norm * doc_norm)))

    ranked = sorted(range(len(sents)), key=lambda i: scores[i], reverse=True)
    picked = [sents[i] for i in ranked[:max_sentences]]

    out = " ".join(picked).strip()
    if len(out) > max_chars:
        out = out[:max_chars].rstrip()
        if not out.endswith((".", "!", "?")):
            out += "…"

    # If summary equals title or too short, add title prefix
    if title and title.lower() not in out.lower():
        out = f"{title}: {out}"
        out = out[:max_chars].rstrip(" :") + ("…" if len(out) > max_chars else "")

    return out.strip()
