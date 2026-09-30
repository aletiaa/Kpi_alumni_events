import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit, urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.models import Event, KpiImportItem, KpiImportState, News

FEED_URL = "https://kpi.ua/rss.xml"
MAX_BYTES = 2 * 1024 * 1024
logger = logging.getLogger(__name__)


def strip_body_label(value):
    if not value:
        return value
    return re.sub(r'^\s*(?:Текст|Text)(?:\s*[:：]\s*|\s+)[✓✔✅\ufe0f\s]*', '', value, count=1)


def clean_saved_import_labels(db):
    changed = 0
    for item in db.query(KpiImportItem).all():
        targets = [(item, ('excerpt',))]
        if item.news_id:
            targets.append((db.get(News, item.news_id), ('content', 'short_description')))
        if item.event_id:
            targets.append((db.get(Event, item.event_id), ('description', 'short_description')))
        for record, fields in targets:
            if record is None:
                continue
            for field in fields:
                original = getattr(record, field)
                cleaned = strip_body_label(original)
                if cleaned != original:
                    setattr(record, field, cleaned)
                    changed += 1
    return changed


def source_url(value):
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"kpi.ua", "www.kpi.ua"}:
        raise ValueError("Invalid KPI source URL")
    if parsed.username or parsed.password or parsed.port not in {None, 80, 443}:
        raise ValueError("Invalid KPI source URL")
    return urlunsplit(("https", "kpi.ua", parsed.path or "/", parsed.query, ""))


class KpiRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, source_url(newurl))


class DescriptionText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.body_parts = []
        self.in_body = False
        self.hidden = 0
        self.image_url = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'img' and attributes.get('src') and not self.image_url:
            try:
                self.image_url = source_url(urljoin(FEED_URL, attributes.get('src', '')))
            except ValueError:
                pass
        if tag in {"script", "style"}:
            self.hidden += 1
        if "field--name-body" in dict(attrs).get("class", "").split():
            self.in_body = True

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
            if self.in_body:
                self.body_parts.append(data)


def plain_text(html):
    parser = DescriptionText()
    parser.feed(html)
    result = " ".join(" ".join(parser.body_parts or parser.parts).split())
    # Drupal RSS descriptions can include the visible field label before the body.
    return strip_body_label(result)


def fetch_feed():
    request = Request(FEED_URL, headers={"User-Agent": "AlumnixHub/1.0 (KPI RSS reader)", "Accept": "application/rss+xml, application/xml"})
    with build_opener(KpiRedirectHandler()).open(request, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("RSS response is too large")
    return data


def parse_feed(data):
    # RSS does not need DTDs or entities; reject them before XML parsing.
    if len(data) > MAX_BYTES or b"<!doctype" in data.lower() or b"<!entity" in data.lower() or b"\x00" in data:
        raise ValueError("Unsupported RSS document")
    root = ElementTree.fromstring(data)
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise ValueError("Expected an RSS feed")
    result = {}
    for item in channel.findall("item")[:100]:
        try:
            url = source_url(item.findtext("link", ""))
        except ValueError:
            continue
        title = plain_text(item.findtext("title", ""))[:200]
        if not title or len(url) > 500:
            continue
        published = None
        try:
            value = parsedate_to_datetime(item.findtext("pubDate", ""))
            published = value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc).replace(tzinfo=None)
        except (ValueError, TypeError, OverflowError):
            pass
        description = DescriptionText()
        description.feed(item.findtext("description", ""))
        result[url] = {"source_url": url, "title": title, "image_url": description.image_url,
                       "excerpt": plain_text(item.findtext("description", ""))[:800],
                       "source_published": published}
    return list(result.values())


def ensure_state(db):
    state = db.get(KpiImportState, 1)
    if state is None:
        try:
            db.add(KpiImportState(id=1))
            db.commit()
        except IntegrityError:
            db.rollback()
        state = db.get(KpiImportState, 1)
    return state


def run_import(session_factory, force=False, fetcher=fetch_feed, now=None):
    now = now or datetime.utcnow()
    with session_factory() as db:
        ensure_state(db)
        query = db.query(KpiImportState).filter(KpiImportState.id == 1,
            or_(KpiImportState.lease_until.is_(None), KpiImportState.lease_until < now))
        if not force:
            query = query.filter(KpiImportState.enabled == True, KpiImportState.next_run <= now)
        if not query.update({KpiImportState.lease_until: now + timedelta(minutes=5)}, synchronize_session=False):
            db.rollback()
            return "skipped"
        db.commit()
        try:
            items = parse_feed(fetcher())
            added = 0
            for item in items:
                existing = db.query(KpiImportItem).filter_by(source_url=item["source_url"]).first()
                if existing:
                    existing.image_url = existing.image_url or item.get("image_url")
                    if existing.status == "pending":
                        existing.excerpt = item["excerpt"]
                    if existing.news_id:
                        news = db.get(News, existing.news_id)
                        if news:
                            if not news.image_url and existing.image_url:
                                news.image_url = existing.image_url
                                news.image_source_url = existing.source_url
                            for field in ('content', 'short_description'):
                                value = getattr(news, field) or ''
                                setattr(news, field, strip_body_label(value))
                    continue
                db.add(KpiImportItem(**item))
                added += 1
            state = db.get(KpiImportState, 1)
            state.last_success = now
            state.next_run = now + timedelta(days=1)
            state.last_error = None
            state.added = added
            state.lease_until = None
            db.commit()
            return "success"
        except Exception:
            db.rollback()
            logger.exception("KPI RSS import failed")
            state = db.get(KpiImportState, 1)
            state.last_error = "Не вдалося отримати стрічку КПІ. Наступна спроба через годину."
            state.next_run = now + timedelta(hours=1)
            state.lease_until = None
            db.commit()
            return "failed"


async def import_loop(session_factory):
    while True:
        try:
            await asyncio.to_thread(run_import, session_factory)
        except Exception:
            logger.exception("KPI import scheduler failed")
        await asyncio.sleep(60)


if __name__ == "__main__":
    from app.db import SessionLocal, engine

    KpiImportState.__table__.create(engine, checkfirst=True)
    KpiImportItem.__table__.create(engine, checkfirst=True)
    result = run_import(SessionLocal)
    print(result)
    raise SystemExit(1 if result == "failed" else 0)
