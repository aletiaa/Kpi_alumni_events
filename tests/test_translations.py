from types import SimpleNamespace

import pytest

from app.deps import get_current_identity
from app.models import ContentTranslation, KpiImportItem, News
from app.services import translation
from app.services.localization import content_text


def test_cache_reuse_and_edited_text_invalidation(db, monkeypatch):
    calls = []
    def provider(texts):
        calls.append(texts)
        return ['Translated ' + str(len(calls)) for _ in texts]
    monkeypatch.setattr(translation, 'deepl_translate', provider)
    fields = {'title': 'Новий матеріал', 'preview': 'Новий матеріал', 'location': 'Online'}
    first = translation.translate_fields(db, fields)
    assert first['title'] == first['preview'] == 'Translated 1'
    assert first['location'] == 'Online'
    assert translation.translate_fields(db, fields) == first
    assert len(calls) == 1
    assert db.query(ContentTranslation).count() == 1
    translation.translate_fields(db, {'title': 'Змінений матеріал'})
    assert len(calls) == 2


def test_provider_not_configured_is_explicit(db, monkeypatch):
    monkeypatch.setattr(translation, 'DEEPL_API_KEY', '')
    with pytest.raises(translation.TranslationUnavailable, match='not_configured'):
        translation.translate_fields(db, {'title': 'Новий матеріал'})
    assert db.query(ContentTranslation).count() == 0


def test_public_translation_and_draft_privacy(client, db, monkeypatch):
    public = News(title='Новина', content='Текст новини', is_published=True)
    private = News(title='Чернетка', content='Приватний текст', is_published=False)
    db.add_all([public, private])
    db.commit()
    monkeypatch.setattr(translation, 'deepl_translate', lambda texts: ['English text' for _ in texts])
    assert client.get(f'/api/translations/news/{private.id}').status_code == 404
    response = client.get(f'/api/translations/news/{public.id}')
    assert response.status_code == 200
    assert response.json()['fields']['title'] == 'English text'
    db.refresh(public)
    assert public.title == 'Новина'
    assert client.get(f'/news/{public.id}').status_code == 200
    assert 'data-content-field="title"' in client.get(f'/news/{public.id}').text


def test_kpi_translation_requires_admin(client, db, monkeypatch):
    item = KpiImportItem(title='Анонс', excerpt='Текст', source_url='https://kpi.ua/test')
    db.add(item)
    db.commit()
    assert client.get(f'/api/translations/kpi/{item.id}').status_code == 403
    client.app.dependency_overrides[get_current_identity] = lambda: SimpleNamespace(role='admin')
    monkeypatch.setattr(translation, 'DEEPL_API_KEY', '')
    response = client.get(f'/api/translations/kpi/{item.id}')
    assert response.status_code == 503
    assert response.json()['detail'] == 'not_configured'


def test_content_markup_escapes_input():
    rendered = str(content_text('news', 1, 'title', '<script>alert(1)</script>'))
    assert '<script>' not in rendered
    assert '&lt;script&gt;' in rendered


def test_profile_card_fields_are_independently_translatable(client, db, monkeypatch):
    from app.models import User
    user = User(email='card@example.com', full_name='Test', password_hash='unused',
        role='alumni', is_active=True, is_profile_public=True, is_mentor=True,
        status='Інженер', city_country='Україна, Київ', help_topics='Співбесіди', company='Компанія')
    db.add(user)
    db.commit()
    for path in ['/alumni', '/mentors']:
        html = client.get(path).text
        assert '<span>Факультет не вказано</span>' in html
        assert 'data-content-field="city_country"' in html
        assert 'data-content-field="company"' in html
    assert '<span>Статус:</span>' in client.get('/alumni').text
    monkeypatch.setattr(translation, 'deepl_translate', lambda texts: ['Translated' for _ in texts])
    fields = client.get(f'/api/translations/profile/{user.id}').json()['fields']
    assert fields['position'] == 'Translated'
    assert fields['help_topics'] == 'Translated'
    assert fields['company'] == 'Translated'


def test_english_name_escapes_and_preserves_both_languages():
    from app.services.localization import display_name, display_datetime
    from datetime import datetime
    user = SimpleNamespace(full_name='Ігор', full_name_en='Ihor <test>')
    rendered = str(display_name(user))
    assert 'data-name-uk="Ігор"' in rendered
    assert 'data-name-en="Ihor &lt;test&gt;"' in rendered
    assert '28.09.2026, 13:45' in str(display_datetime(datetime(2026, 9, 28, 13, 45, 30, 873363)))


def test_profile_saves_english_name(client, db):
    from app.models import User
    from app.deps import require_identity
    user = User(email='name@example.com', full_name='Ігор', password_hash='unused', role='alumni', is_active=True)
    db.add(user)
    db.commit()
    client.app.dependency_overrides[require_identity] = lambda: SimpleNamespace(role='alumni', user_id=user.id)
    response = client.post('/profile', data={'full_name': 'Ігор', 'full_name_en': 'Ihor', 'is_profile_public': '1'}, follow_redirects=False)
    assert response.status_code == 303
    db.refresh(user)
    assert user.full_name_en == 'Ihor'
    assert 'data-name-en="Ihor"' in client.get('/alumni').text


def test_admin_messages_does_not_redirect_home(client):
    from app.deps import require_identity
    client.app.dependency_overrides[require_identity] = lambda: SimpleNamespace(role='admin', user_id=None, full_name='Admin')
    response = client.get('/messages', follow_redirects=False)
    assert response.status_code == 200
    assert 'Для листування потрібен особистий профіль користувача.' in response.text


def test_provider_errors_do_not_expose_credentials(monkeypatch):
    monkeypatch.setattr(translation, 'DEEPL_API_KEY', 'private-key:fx')
    def fail(*args, **kwargs):
        raise RuntimeError('private-key:fx')
    monkeypatch.setattr(translation, 'urlopen', fail)
    with pytest.raises(translation.TranslationUnavailable) as caught:
        translation.deepl_translate(['Новина'])
    assert str(caught.value) == 'temporarily_unavailable'
