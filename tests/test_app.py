import sys
from pathlib import Path

# Make the app package importable without installing it — keeps the demo
# dependency-free beyond Flask itself.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import pytest

from app import app as flask_app


@pytest.fixture()
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c


def test_index_returns_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_health_returns_healthy(client):
    resp = client.get("/health")
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["status"] == "healthy"
    assert "uptime_seconds" in body


def test_list_tasks_returns_seed_data(client):
    resp = client.get("/tasks")
    tasks = resp.get_json()
    assert resp.status_code == 200
    assert len(tasks) >= 3
    assert {"id", "title", "done"} <= tasks[0].keys()


def test_create_task_requires_title(client):
    resp = client.post("/tasks", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_task_success(client):
    resp = client.post("/tasks", json={"title": "Write runbook"})
    assert resp.status_code == 201
    created = resp.get_json()
    assert created["title"] == "Write runbook"
    assert created["done"] is False

    # New task should now show up in the list
    listed = client.get("/tasks").get_json()
    assert any(t["title"] == "Write runbook" for t in listed)
