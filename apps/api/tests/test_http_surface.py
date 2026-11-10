"""HTTP 表面一致性：错误包、安全头、请求标识、体量上限。

这些是全局契约，任何新增路由都不能破坏。
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert body["error"]["traceId"]


def test_security_headers_are_present(client: TestClient) -> None:
    headers = client.get("/healthz").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["Cache-Control"] == "no-store"


def test_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-Id": "trace-123"})

    assert response.headers["X-Request-Id"] == "trace-123"


def test_request_id_is_generated_when_missing(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.headers["X-Request-Id"]


def test_oversized_body_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/healthz",
        content=b"x" * (64 * 1024 + 1),
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
