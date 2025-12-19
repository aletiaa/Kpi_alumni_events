def test_admin_events_requires_admin(client):
    r = client.get("/admin/events")
    # some apps redirect to login (302/307); others return 401/403
    assert r.status_code in (401, 403, 302, 307)


def test_admin_events_ok_for_admin(admin_client):
    r = admin_client.get("/admin/events")
    # Could be HTML or JSON; we only care access is granted
    assert r.status_code == 200
