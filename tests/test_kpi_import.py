from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from app.deps import require_identity
from app.models import Event, KpiImportItem, KpiImportState, News
from app.routers.kpi_import import signer
from app.services.kpi_import import ensure_state, parse_feed, run_import

FEED = b'''<rss version="2.0"><channel><item><title>Webinar</title>
<link>https://kpi.ua/webinar#top</link><pubDate>Tue, 22 Sep 2026 12:28:54 +0000</pubDate>
<description>&lt;p&gt;Join the webinar.&lt;/p&gt;&lt;script&gt;evil()&lt;/script&gt;</description>
</item></channel></rss>'''


def token():
    return signer.dumps("admin@test.local")


def test_parse_source_dates_and_strip_html():
    item = parse_feed(FEED)[0]
    assert item["source_url"] == "https://kpi.ua/webinar"
    assert item["excerpt"] == "Join the webinar."
    assert item["source_published"] == datetime(2026, 9, 22, 12, 28, 54)
    assert parse_feed(FEED.replace(b'https://kpi.ua/webinar#top', b'https://evil.example/test')) == []


@pytest.mark.parametrize('label', ['Текст: ', 'Текст : ', 'Текст\u00a0', 'Text: ', 'Текст ✔ ', 'Текст: ✅ '])
def test_body_label_variants(label):
    from app.services.kpi_import import plain_text
    assert plain_text(f'<div>{label}Article body</div>') == 'Article body'


def test_saved_labels_cleaned_without_touching_unrelated_news(db):
    from app.services.kpi_import import clean_saved_import_labels
    imported = News(title='Imported', content='Текст: Article', short_description='Text: Preview')
    unrelated = News(title='Manual', content='Text: intentional label')
    db.add_all([imported, unrelated])
    db.flush()
    db.add(KpiImportItem(title='Imported', excerpt='Текст: Article', source_url='https://kpi.ua/old', news_id=imported.id))
    db.commit()
    assert clean_saved_import_labels(db) == 3
    db.commit()
    assert imported.content == 'Article'
    assert imported.short_description == 'Preview'
    assert unrelated.content == 'Text: intentional label'
    assert clean_saved_import_labels(db) == 0


def test_rss_image_and_field_label():
    from app.services.kpi_import import plain_text
    assert plain_text('<div>Текст ✔ Actual article</div>') == 'Actual article'
    feed = FEED.replace(b'&lt;p&gt;', b'&lt;img src="/files/news.jpg"&gt;&lt;p&gt;')
    assert parse_feed(feed)[0]['image_url'] == 'https://kpi.ua/files/news.jpg'
    assert parse_feed(feed.replace(b'/files/news.jpg', b'https://evil.example/a.jpg'))[0]['image_url'] is None


def test_publish_import_is_visible_and_retains_image(admin_client, db):
    item = KpiImportItem(**parse_feed(FEED)[0])
    item.image_url = 'https://kpi.ua/files/news.jpg'
    db.add(item)
    db.commit()
    for _ in range(2):
        response = admin_client.post(f'/admin/kpi-import/{item.id}/review',
            data={'csrf': token(), 'action': 'publish'}, follow_redirects=False)
        assert response.status_code == 303
    news = db.query(News).one()
    assert news.is_published
    assert news.image_url == item.image_url
    assert admin_client.get(f'/news/{news.id}').status_code == 200


@pytest.mark.parametrize("data", [b'<html>Unavailable</html>', b'<!DOCTYPE rss><rss/>', b'<!ENTITY x "x"><rss/>', b'<rss>'])
def test_reject_unsafe_or_invalid_xml(data):
    with pytest.raises(Exception):
        parse_feed(data)


def test_daily_import_deduplication_and_failure_retry(db):
    factory = sessionmaker(bind=db.get_bind())
    now = datetime(2026, 9, 22, 12)
    ensure_state(db).next_run = now
    db.commit()
    assert run_import(factory, fetcher=lambda: FEED, now=now) == "success"
    assert run_import(factory, fetcher=lambda: FEED, now=now) == "skipped"
    assert run_import(factory, force=True, fetcher=lambda: FEED, now=now) == "success"
    assert db.query(KpiImportItem).count() == 1
    assert db.query(News).count() == 0
    assert run_import(factory, force=True, fetcher=lambda: b'broken', now=now) == "failed"
    db.expire_all()
    state = db.get(KpiImportState, 1)
    assert state.next_run == now + timedelta(hours=1)
    assert state.last_success == now
    assert state.last_error and state.lease_until is None
    assert db.query(KpiImportItem).count() == 1


def test_disabled_schedule_and_active_lease(db):
    factory = sessionmaker(bind=db.get_bind())
    state = ensure_state(db)
    state.enabled = False
    db.commit()
    assert run_import(factory, fetcher=lambda: FEED) == "skipped"
    state.lease_until = datetime.utcnow() + timedelta(minutes=5)
    db.commit()
    assert run_import(factory, force=True, fetcher=lambda: FEED) == "skipped"


def test_refresh_backfills_image_without_overwriting_edited_article(db):
    factory = sessionmaker(bind=db.get_bind())
    news = News(title='Edited title', content='Edited article', short_description='Текст ✔ Original', is_published=True)
    db.add(news)
    db.flush()
    item = KpiImportItem(**parse_feed(FEED)[0], news_id=news.id, status='news')
    db.add(item)
    db.commit()
    feed = FEED.replace(b'&lt;p&gt;', b'&lt;img src="/files/news.jpg"&gt;&lt;p&gt;')
    assert run_import(factory, force=True, fetcher=lambda: feed) == 'success'
    db.expire_all()
    assert news.content == 'Edited article'
    assert news.short_description == 'Original'
    assert news.image_url == 'https://kpi.ua/files/news.jpg'
    assert db.query(News).count() == 1


def test_import_requires_admin(client):
    assert client.get('/admin/kpi-import').status_code == 401
    client.app.dependency_overrides[require_identity] = lambda: SimpleNamespace(role="alumni")
    assert client.get('/admin/kpi-import').status_code == 403
    assert client.post('/admin/kpi-import/run', data={"csrf": token()}).status_code == 403


def test_admin_csrf_settings_and_manual_run(admin_client, db, monkeypatch):
    assert admin_client.get('/admin/kpi-import').status_code == 200
    assert admin_client.post('/admin/kpi-import/settings', data={"csrf": "bad"}).status_code == 403
    response = admin_client.post('/admin/kpi-import/settings', data={"csrf": token()}, follow_redirects=False)
    assert response.status_code == 303
    assert db.get(KpiImportState, 1).enabled is False
    calls = []
    monkeypatch.setattr('app.routers.kpi_import.run_import', lambda factory, force: calls.append(force) or 'success')
    assert admin_client.post('/admin/kpi-import/run', data={"csrf": token()}, follow_redirects=False).status_code == 303
    assert calls == [True]


def test_review_news_is_draft_and_idempotent(admin_client, db):
    item = KpiImportItem(**parse_feed(FEED)[0])
    db.add(item)
    db.commit()
    for _ in range(2):
        response = admin_client.post(f'/admin/kpi-import/{item.id}/review', data={"csrf": token(), "action": "news"}, follow_redirects=False)
        assert response.status_code == 303
    news = db.query(News).one()
    assert news.is_published is False
    assert item.source_url in news.content
    db.refresh(item)
    assert item.status == "news" and item.news_id == news.id
    assert admin_client.get(f'/news/{news.id}').status_code == 404


def test_event_requires_explicit_date_and_dismiss_stays_deduplicated(admin_client, db):
    item = KpiImportItem(**parse_feed(FEED)[0])
    db.add(item)
    db.commit()
    response = admin_client.post(f'/admin/kpi-import/{item.id}/review', data={"csrf": token(), "action": "event"}, follow_redirects=False)
    assert 'invalid_event' in response.headers['location']
    assert db.query(Event).count() == 0
    response = admin_client.post(f'/admin/kpi-import/{item.id}/review', data={"csrf": token(), "action": "event", "start_time": "2026-10-01T18:00", "location": "Online", "capacity": "20"}, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(Event).one().start_time == datetime(2026, 10, 1, 18)
    other = KpiImportItem(source_url="https://kpi.ua/skip", title="Skip", excerpt="")
    db.add(other)
    db.commit()
    admin_client.post(f'/admin/kpi-import/{other.id}/review', data={"csrf": token(), "action": "dismiss"})
    db.refresh(other)
    assert other.status == "dismiss"
