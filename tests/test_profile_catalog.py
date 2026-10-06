from types import SimpleNamespace
import pytest
from app.deps import require_identity, require_admin
from app.models import User, ProfileReference, SpecialtyDefinition
from app.services.profile_catalog import countries, seed_specialties, legacy_location
from app.services.operational_security import token


def identity(client, db):
    seed_specialties(db)
    user = User(email='catalog@example.test', full_name='Catalog User', role='alumni',
                password_hash='unused', is_active=True)
    db.add(user)
    db.commit()
    ident = SimpleNamespace(role='alumni', user_id=user.id, email=user.email, full_name=user.full_name)
    client.app.dependency_overrides[require_identity] = lambda: ident
    return user, ident


def test_country_catalog():
    rows = countries()
    assert len(rows) == 249
    assert len({r['alpha2'] for r in rows}) == 249
    assert legacy_location('Україна, Київ') == ('UA', 'Київ')
    assert legacy_location('Ukraine, Kyiv') == ('UA', 'Kyiv')
    assert legacy_location('Задзеркалля')[0] is None
    assert all(r['name_uk'] and r['name_en'] and r['transliteration'] for r in rows)


def test_bilingual_helpers_escape_and_hide_invalid_legacy_values():
    from datetime import date
    from app.services.profile_catalog import bilingual, display_location, professional_status, graduation_display, role_label
    user = SimpleNamespace(city_country='Україна, Київ', status='alumni',
                           graduation_year=1905, birth_date=None)
    assert 'Ukraine, Kyiv' in str(display_location(user))
    assert professional_status(user) == '' and graduation_display(user) == ''
    assert 'data-ops-uk="Випускник"' in str(role_label('alumni'))
    user.city_country = 'Задзеркалля'
    assert display_location(user) == ''
    assert '<script>' not in str(bilingual('<script>', 'Safe'))
    user.birth_date, user.graduation_year = date(2000, 1, 1), 2014
    assert graduation_display(user) == ''
    user.graduation_year = 2015
    assert graduation_display(user) == 2015


@pytest.mark.parametrize('code', ['legacy:6.050103', '2015:121', '2025:F2'])
def test_profile_saves_real_diploma_code(client, db, code):
    user, _ = identity(client, db)
    response = client.post('/profile', data={'full_name': user.full_name, 'specialty': code,
        'location_fields': 'yes', 'country_code': 'UA', 'city': 'Київ', 'status': 'Шукаю роботу'}, follow_redirects=False)
    assert response.status_code == 303
    db.refresh(user)
    assert user.specialty.startswith(code.split(':')[1] + ' - ')
    reference = db.get(ProfileReference, user.id)
    assert reference.country_code == 'UA' and reference.specialty_key == code


@pytest.mark.parametrize('fields', [
    {'country_code': 'XX', 'location_fields': 'yes'},
    {'city': 'Kyiv', 'location_fields': 'yes'},
    {'city_country': 'Задзеркалля'}, {'specialty': '2025:INVALID'}, {'specialty': 'Invented specialty'},
])
def test_invalid_catalog_values_rejected(client, db, fields):
    user, _ = identity(client, db)
    response = client.post('/profile', data={'full_name': 'Changed', **fields}, follow_redirects=False)
    assert response.status_code == 400
    db.refresh(user)
    assert user.full_name == 'Catalog User'


def test_form_lists_all_classifications(client, db):
    identity(client, db)
    text = client.get('/profile').text
    assert all(code in text for code in ['6.050103', '2015:121', '2025:F2', 'country_code'])
    assert 'user.role' not in text


def test_inactive_specialty_preserves_existing_profile(client, db):
    user, _ = identity(client, db)
    item = db.get(SpecialtyDefinition, '2025:F2')
    user.specialty = item.code + ' - ' + item.name_uk
    item.is_active = False
    db.add(ProfileReference(user_id=user.id, specialty_key=item.key))
    db.commit()
    assert f'value="{user.specialty}" selected' in client.get('/profile').text
    response = client.post('/profile', data={'full_name': user.full_name, 'specialty': user.specialty}, follow_redirects=False)
    assert response.status_code == 303
    assert db.get(ProfileReference, user.id).specialty_key == item.key


def test_admin_can_add_specialty_and_csrf_required(client, db):
    _, ident = identity(client, db)
    ident.role = 'admin'
    client.app.dependency_overrides[require_admin] = lambda: ident
    values = {'classification': '2025', 'code': 'F9', 'name_uk': 'Нова спеціальність',
              'name_en': 'New specialty', 'active': 'yes'}
    assert client.post('/admin/operations/specialties', data=values).status_code == 403
    response = client.post('/admin/operations/specialties', data={**values, 'csrf': token(ident)}, follow_redirects=False)
    assert response.status_code == 303
    assert db.get(SpecialtyDefinition, '2025:F9').is_active


def test_seed_preserves_admin_changes_and_disabled_catalog(db):
    from app.services.specialties import specialty_options
    seed_specialties(db)
    count = db.query(SpecialtyDefinition).count()
    item = db.get(SpecialtyDefinition, '2025:F2')
    item.name_en = 'Administrator edit'
    for row in db.query(SpecialtyDefinition):
        row.is_active = False
    db.commit()
    seed_specialties(db)
    assert db.query(SpecialtyDefinition).count() == count
    assert item.name_en == 'Administrator edit'
    assert specialty_options(db) == []


def test_reference_migration_is_repeatable_and_preserves_data():
    from sqlalchemy import create_engine, inspect, text
    from app.services.migrate import ensure_alumni_profile_columns
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY)'))
        connection.execute(text('CREATE TABLE profile_references (user_id INTEGER PRIMARY KEY, country_code VARCHAR(2))'))
        connection.execute(text("INSERT INTO profile_references VALUES (1, 'UA')"))
    ensure_alumni_profile_columns(engine)
    ensure_alumni_profile_columns(engine)
    assert 'admission_year' in {c['name'] for c in inspect(engine).get_columns('profile_references')}
    with engine.connect() as connection:
        assert connection.execute(text('SELECT country_code FROM profile_references')).scalar() == 'UA'
    engine.dispose()


def test_catalog_admin_page_is_not_public(client):
    assert client.get('/admin/operations/specialties').status_code in {401, 403}


@pytest.mark.parametrize('classification,code', [('legacy', 'F2'), ('2015', 'F2'),
    ('2025', '121'), ('other', 'F2'), ('2025', '<script>')])
def test_admin_rejects_invalid_code_format(client, db, classification, code):
    _, ident = identity(client, db)
    ident.role = 'admin'
    client.app.dependency_overrides[require_admin] = lambda: ident
    count = db.query(SpecialtyDefinition).count()
    result = client.post('/admin/operations/specialties', data={'classification': classification,
        'code': code, 'name_uk': 'Назва', 'name_en': 'Name', 'csrf': token(ident)})
    assert result.status_code == 400
    assert db.query(SpecialtyDefinition).count() == count
