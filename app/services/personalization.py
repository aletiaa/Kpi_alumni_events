from datetime import datetime, timedelta
from urllib.parse import urlsplit
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import func

from app.models import Event, News, PageDuration, Registration


def recommendations(db, user, section, now=None):
    now = now or datetime.utcnow()
    registered = {row[0] for row in db.query(Registration.event_id).filter_by(user_id=user.id)}
    counts = dict(db.query(Registration.event_id, func.count(Registration.id)).group_by(Registration.event_id))
    events = db.query(Event).filter(Event.start_time > now).order_by(Event.start_time).limit(300).all()
    events = [e for e in events if e.id not in registered and counts.get(e.id, 0) < e.capacity
              and (not e.registration_deadline or e.registration_deadline > now)]
    news = db.query(News).filter_by(is_published=True).order_by(News.created_at.desc()).limit(100).all()
    candidates = [('event', e, e.title + ' ' + (e.description or '')) for e in events]
    candidates += [('news', n, n.title + ' ' + (n.content or '')[:4000]) for n in news]
    if not candidates:
        return []
    history = [(' '.join(filter(None, [user.interests, user.skills, user.bio, user.mentorship_topics])), 3.0)]
    for event in db.query(Event).join(Registration).filter(Registration.user_id == user.id).limit(30):
        history.append((event.title + ' ' + (event.description or ''), 1.0))
    section_time = {'event': 0, 'news': 0}
    seen = set()
    durations = db.query(PageDuration.page, func.sum(PageDuration.duration_seconds)).filter(
        PageDuration.user_id == user.id, PageDuration.opened_at >= now - timedelta(days=30)
    ).group_by(PageDuration.page).all()
    for page, seconds in durations:
        path = urlsplit(page).path
        match = re.fullmatch(r'/(events|news)(?:/(\d+))?', path)
        if not match:
            continue
        kind = 'event' if match[1] == 'events' else 'news'
        seconds = min(max(seconds or 0, 0), 3600)
        section_time[kind] += seconds
        if match[2] and seconds > 0:
            record = db.get(Event if kind == 'event' else News, int(match[2]))
            if record and (kind == 'event' or record.is_published):
                seen.add((kind, record.id))
                body = record.description if kind == 'event' else record.content
                history.append((record.title + ' ' + (body or '')[:4000], 1 + np.log1p(seconds)))
    history = [(text, weight) for text, weight in history if text.strip()]
    scores = np.zeros(len(candidates))
    if history:
        try:
            matrix = TfidfVectorizer(ngram_range=(1, 2), max_features=12000).fit_transform(
                [text for text, _ in history] + [text for _, _, text in candidates])
            scores = np.average(cosine_similarity(matrix[len(history):], matrix[:len(history)]),
                                axis=1, weights=[weight for _, weight in history])
        except ValueError:
            pass
    total = sum(section_time.values()) or 1
    ranked = []
    for index, (kind, item, _) in enumerate(candidates):
        if (kind, item.id) in seen:
            continue
        score = float(scores[index]) * 5 + section_time[kind] / total * .25
        score += .15 if kind == section else 0
        ranked.append((score, kind, item))
    ranked.sort(key=lambda row: row[0], reverse=True)
    return [{'kind':kind, 'id':item.id, 'title':item.title,
             'url':f'/{"events" if kind == "event" else "news"}/{item.id}',
             'image':item.image_url or '/static/img/kpi-main.png'} for _, kind, item in ranked[:3]]
