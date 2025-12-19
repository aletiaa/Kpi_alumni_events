from sqlalchemy import text

def test_iot_post_visit_ok(client, db):
    r = client.post(
        "/api/iot/visits",
        headers={"X-IoT-Key": "test-key"},
        json={"event_id": 1, "device_id": "esp32-01", "direction": "in", "delta": 1},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    count = db.execute(text("SELECT COUNT(*) FROM iot_visits")).scalar_one()
    assert count == 1

def test_iot_post_visit_wrong_key(client):
    r = client.post(
        "/api/iot/visits",
        headers={"X-IoT-Key": "bad"},
        json={"event_id": 1, "device_id": "esp32-01", "direction": "in", "delta": 1},
    )
    assert r.status_code == 401

def test_iot_post_visit_bad_direction(client):
    r = client.post(
        "/api/iot/visits",
        headers={"X-IoT-Key": "test-key"},
        json={"event_id": 1, "device_id": "esp32-01", "direction": "side", "delta": 1},
    )
    assert r.status_code == 400

def test_iot_post_visit_bad_delta(client):
    r = client.post(
        "/api/iot/visits",
        headers={"X-IoT-Key": "test-key"},
        json={"event_id": 1, "device_id": "esp32-01", "direction": "in", "delta": 2},
    )
    assert r.status_code == 400

def test_iot_event_stats(client):
    # 2 входи, 1 вихід → net = 1
    for payload in [
        {"event_id": 1, "device_id": "esp32-01", "direction": "in", "delta": 1},
        {"event_id": 1, "device_id": "esp32-01", "direction": "in", "delta": 1},
        {"event_id": 1, "device_id": "esp32-01", "direction": "out", "delta": -1},
    ]:
        client.post("/api/iot/visits", headers={"X-IoT-Key": "test-key"}, json=payload)

    r = client.get("/api/iot/events/1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["event_id"] == 1
    assert data["in"] == 2
    assert data["out"] == 1
    assert data["net"] == 1
