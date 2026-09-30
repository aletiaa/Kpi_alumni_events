from datetime import datetime, timedelta
from app.models import BotCampaign, Event
from app.routers.bots import signer


def token():
    return signer.dumps("admin@test.local")


def test_bot_admin_access(client):
    assert client.get('/admin/bots').status_code == 401
    assert client.get('/admin/bots/events.json').status_code == 401
    assert client.post('/admin/bots/campaigns', data={'body':'x','audience':'all'}).status_code == 401
    assert client.post('/admin/bots/campaigns/1/simulate').status_code == 401


def test_draft_simulation_persistence_and_idempotency(admin_client, db):
    response = admin_client.get('/admin/bots')
    assert response.status_code == 200
    assert 'Telegram' in response.text
    data = {'body':'Test <script>alert(1)</script>', 'audience':'alumni', 'csrf':token()}
    assert admin_client.post('/admin/bots/campaigns', data=data, follow_redirects=False).status_code == 303
    campaign = db.query(BotCampaign).one()
    assert campaign.simulated_at is None
    page = admin_client.get('/admin/bots').text
    assert '&lt;script&gt;' in page
    url = f'/admin/bots/campaigns/{campaign.id}/simulate'
    assert admin_client.post(url, data={'csrf':token()}, follow_redirects=False).status_code == 303
    db.refresh(campaign)
    first_time = campaign.simulated_at
    assert first_time is not None
    admin_client.post(url, data={'csrf':token()})
    db.refresh(campaign)
    assert campaign.simulated_at == first_time
    page = admin_client.get('/admin/bots').text
    assert 'demo-alumni-01' in page and 'demo-student-01' not in page


def test_validation_and_csrf(admin_client, db):
    for data, status in [({'body':'x','audience':'all'},403),
                         ({'body':' ','audience':'all','csrf':token()},400),
                         ({'body':'x','audience':'real','csrf':token()},400),
                         ({'body':'x'*4001,'audience':'all','csrf':token()},422)]:
        assert admin_client.post('/admin/bots/campaigns', data=data).status_code == status
    assert db.query(BotCampaign).count() == 0
    assert admin_client.post('/admin/bots/campaigns/999/simulate', data={'csrf':token()}).status_code == 404
    assert admin_client.get('/admin/bots?source=other&source_id=1').status_code == 404


def test_export_matches_diploma_contract(admin_client, db):
    event = Event(title='Demo event', description='Public description', location='KPI',
                  start_time=datetime.utcnow()+timedelta(days=10), capacity=12)
    db.add(event)
    db.commit()
    response = admin_client.get('/admin/bots/events.json')
    assert response.status_code == 200
    assert response.json() == [{'id':event.id,'title':event.title,'description':event.description,
        'datetime':event.start_time.isoformat(),'max_seats':12,'available_seats':12}]
    assert 'attachment' in response.headers['content-disposition']
    assert 'Public description' in admin_client.get(f'/admin/bots?source=event&source_id={event.id}').text
