from datetime import datetime, timedelta
from types import SimpleNamespace

from app.deps import require_identity
from app.models import Event, News, PageDuration, User, Registration
from app.services.personalization import recommendations


def setup_user(client, db):
    user=User(full_name='Tester', email='engage@example.com', password_hash='x', is_active=True,
              is_email_verified=True, interests='Python data analytics', notifications_enabled=False)
    db.add(user); db.commit()
    client.app.dependency_overrides[require_identity]=lambda: SimpleNamespace(user_id=user.id,role='alumni',full_name=user.full_name)
    return user


def event(db, title='Python workshop', **kwargs):
    values=dict(title=title, description=title, start_time=datetime.utcnow()+timedelta(days=10),capacity=30,location='Online')
    values.update(kwargs)
    item=Event(**values); db.add(item); db.commit(); return item


def test_summary_admin_only_and_empty_vocabulary(client, admin_client):
    assert admin_client.post('/admin/description-preview',data={'body':'the and or'}).json()['summary']=='the and or'
    from app.deps import require_admin
    client.app.dependency_overrides.pop(require_admin)
    assert client.post('/admin/description-preview',data={'body':'Description'}).status_code==401


def test_qr_auth_content_and_no_registration(client, db):
    item=event(db)
    assert client.get(f'/events/{item.id}').status_code==200
    assert client.get(f'/events/{item.id}/registration-qr').status_code==401
    user=setup_user(client,db)
    response=client.get(f'/events/{item.id}/registration-qr')
    assert response.status_code==200 and response.content.startswith(b'\x89PNG')
    assert db.query(Registration).count()==0
    assert client.get('/api/personal-suggestions?section=other').status_code==400


def test_suggestions_filter_and_user_interests(client, db):
    user=setup_user(client,db)
    wanted=event(db)
    event(db,'Past',start_time=datetime.utcnow()-timedelta(days=1))
    full=event(db,'Full',capacity=0)
    news=News(title='Secret draft',content='Python',is_published=False);db.add(news);db.commit()
    results=recommendations(db,user,'event')
    assert results[0]['id']==wanted.id
    assert all(x['id']!=full.id for x in results)
    assert all(x['title']!='Secret draft' for x in results)


def test_reading_time_changes_recommendation_and_is_private(client,db):
    user=setup_user(client,db);user.interests='';db.commit()
    source=News(title='Robotics sensors',content='Robotics sensors',is_published=True)
    db.add(source);db.commit()
    unrelated=event(db,'Literature poetry')
    relevant=event(db,'Robotics sensors workshop')
    db.add(PageDuration(user_id=user.id,session_id='one',page=f'/news/{source.id}',
        opened_at=datetime.utcnow(),closed_at=datetime.utcnow(),duration_seconds=500));db.commit()
    assert recommendations(db,user,'event')[0]['id']==relevant.id
    other=SimpleNamespace(id=999,interests='',skills='',bio='',mentorship_topics='')
    assert recommendations(db,other,'event')[0]['id']==unrelated.id


def test_autumn_schedule_preserves_duration():
    from scripts.schedule_autumn import reschedule
    start=datetime(2026,6,1,12)
    events=[SimpleNamespace(start_time=start,end_time=start+timedelta(hours=2),registration_deadline=start-timedelta(days=1)) for _ in range(12)]
    reschedule(events)
    assert events[0].start_time.month==10 and events[-1].start_time.month==11
    assert len({e.start_time for e in events})==12
    assert all(e.end_time-e.start_time==timedelta(hours=2) for e in events)
