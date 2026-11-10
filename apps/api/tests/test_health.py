"""探针行为：存活恒 200；可用性要能识别未迁移的库。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_does_not_touch_database(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_outdated_schema(client: TestClient) -> None:
    response = client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "schema_outdated"
    assert body["schema"]["current"] is None
    assert body["schema"]["head"] is not None


def test_readyz_is_green_after_migration(migrated_client: TestClient) -> None:
    response = migrated_client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["schema"]["current"] == body["schema"]["head"]
