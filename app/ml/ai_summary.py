from __future__ import annotations
from functools import lru_cache

from transformers import pipeline


@lru_cache(maxsize=1)
def _summarizer():
    # Good balance of quality vs size.
    # If your machine is weak, swap to "t5-small" with a different pipeline pattern.
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")


def generate_short_description_ai(
    title: str,
    description: str,
    *,
    max_chars: int = 180,
) -> str:
    title = (title or "").strip()
    desc = (description or "").strip()

    if not desc:
        return title[:max_chars].strip()

    # If input is very short, summarizers can return identical text.
    # In that case we *still* want a "teaser-like" line:
    if len(desc) < 120:
        base = desc
    else:
        summarizer = _summarizer()
        # Model params: tune for “short teaser”
        out = summarizer(
            desc,
            max_length=55,   # tokens, not chars
            min_length=18,
            do_sample=False,
        )[0]["summary_text"].strip()
        base = out

    # Teaser formatting
    teaser = base.replace("\n", " ").strip()
    if title and title.lower() not in teaser.lower():
        teaser = f"{title}: {teaser}"

    # hard cap
    if len(teaser) > max_chars:
        teaser = teaser[:max_chars].rstrip()
        if not teaser.endswith(("…", ".", "!", "?")):
            teaser += "…"

    return teaser
