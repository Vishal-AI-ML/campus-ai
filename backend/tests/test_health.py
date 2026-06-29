"""Smoke tests: the app boots and its probes answer."""


def test_root_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_db_check_ok(client):
    resp = client.get("/db-check")
    assert resp.status_code == 200
    assert resp.json() == {"database": "connected"}
