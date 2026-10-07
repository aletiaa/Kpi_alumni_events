"""Create local staff test accounts, never reuse real contact emails as logins."""
import argparse
import csv
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from app.db import Base, SessionLocal, engine
from app.models import User, ProfileReference
from app.security import hash_password
from app.services.migrate import ensure_alumni_profile_columns
from app.services.staff_directory import staff_records


def create_accounts(db, records):
    credentials = []
    for record in records:
        email = record['login_email']
        if not email.endswith('@faculty.example.test'):
            raise ValueError('Only reserved test login addresses may be imported')
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            if existing.full_name not in {record['full_name'], record.get('source_full_name', record['full_name'])}:
                raise ValueError('Existing account does not match the imported staff member')
            if existing.full_name == record.get('source_full_name'):
                existing.full_name = record['full_name']
                existing.full_name_en = record['full_name_en']
            if not (existing.status or '').strip():
                existing.status = 'Викладач університету'
            continue
        password = secrets.token_urlsafe(24)
        user = User(email=email, full_name=record['full_name'], full_name_en=record['full_name_en'],
            password_hash=hash_password(password), role='guest', is_active=True, is_blocked=False,
            is_email_verified=True, is_profile_public=True, is_mentor=True,
            notifications_enabled=False, preferred_language='uk',
            status='Викладач університету',
            avatar_url=record['photo_url'], current_position=record['position'],
            faculty='НН ІАТЕ', company='КПІ ім. Ігоря Сікорського', city_country='Україна, Київ',
            specialty=record.get('diploma_specialty'),
            bio='Викладач кафедри інженерії програмного забезпечення в енергетиці. Академічні напрями: ' + record['areas_uk'] + '.',
            skills=record['areas_uk'], mentorship_topics=record['areas_uk'])
        db.add(user)
        db.flush()
        db.add(ProfileReference(user_id=user.id, country_code='UA', city='Київ'))
        credentials.append({'full_name': user.full_name, 'login_email': email,
                            'initial_password': password, 'password_hash': user.password_hash})
    return credentials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    records = staff_records()
    if len(records) != 15:
        raise ValueError('Expected the 15 requested staff records')
    if not args.apply:
        print(f'Ready to import {len(records)} staff test profiles')
        return
    if engine.url.get_backend_name() != 'sqlite':
        raise ValueError('Use this importer only with the local SQLite database')
    private = Path(__file__).resolve().parents[1] / '.private'
    private.mkdir(exist_ok=True)
    database = Path(engine.url.database).resolve()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if database.exists():
        with sqlite3.connect(database) as source, sqlite3.connect(private / ('before-staff-' + stamp + '.db')) as target:
            source.backup(target)
    Base.metadata.create_all(engine)
    ensure_alumni_profile_columns(engine)
    with SessionLocal() as db:
        credentials = create_accounts(db, records)
        if credentials:
            path = private / ('kpi-staff-logins-' + stamp + '.csv')
            with path.open('x', encoding='utf-8-sig', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(credentials[0]))
                writer.writeheader()
                writer.writerows(credentials)
            db.commit()
            print(f'Created {len(credentials)} accounts. Private credentials: {path}')
        else:
            db.commit()
            print('All requested accounts already exist; passwords were not changed.')


if __name__ == '__main__':
    main()
