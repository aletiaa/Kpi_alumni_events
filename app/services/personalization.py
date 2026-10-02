from datetime import datetime, timedelta
from urllib.parse import urlsplit
import re

from sqlalchemy import func

from app.models import Event, News, PageDuration, Registration
from app.services.interest_topics import topics


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
    explicit = topics(user.interests)
    inferred = {}
    for event in db.query(Event).join(Registration).filter(Registration.user_id == user.id).limit(30):
        for topic in topics(event.title + ' ' + (event.description or '')):
            inferred[topic] = 0.5
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
                for topic in topics(record.title + ' ' + (body or '')[:4000]):
                    inferred[topic] = max(inferred.get(topic, 0), min(seconds / 300, 1) * 0.5)
    # Explicit interests override inferred topics, rather than averaging away intent.
    interests = {topic: 1.0 for topic in explicit} if explicit else inferred
    if not interests:
        return []
    total = sum(section_time.values()) or 1
    ranked = []
    for kind, item, text in candidates:
        if (kind, item.id) in seen:
            continue
        matched = topics(text).intersection(interests)
        if not matched:
            continue
        score = sum(interests[topic] for topic in matched) / sum(interests.values()) * 5
        score += section_time[kind] / total * .25
        score += .15 if kind == section else 0
        ranked.append((score, kind, item))
    ranked.sort(key=lambda row: row[0], reverse=True)
    return [{'kind':kind, 'id':item.id, 'title':item.title,
             'url':f'/{"events" if kind == "event" else "news"}/{item.id}',
             'image':item.image_url or '/static/img/kpi-main.png'} for _, kind, item in ranked[:3]]
