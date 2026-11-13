"""认证与会话：注册、登录、会话、登出、改密、CSRF、锁定。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from schorder.dev.seed import DEMO_PASSWORD

STUDENT_PHONE = "13800000001"


def _login(client: TestClient, phone: str = STUDENT_PHONE, password: str = DEMO_PASSWORD) -> dict:
    response = client.post("/api/v1/auth/login", json={"phone": phone, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_register_creates_session_and_cookie(seeded_client: TestClient) -> None:
    response = seeded_client.post(
        "/api/v1/auth/register",
        json={"phone": "13900001111", "password": "abc12345", "nickname": "新同学"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user"]["role"] == "student"
    assert data["user"]["nickname"] == "新同学"
    assert data["csrfToken"]
    assert seeded_client.cookies.get("sid")

    session = seeded_client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json()["data"]["user"]["phone"] == "13900001111"


def test_register_rejects_duplicate_phone(seeded_client: TestClient) -> None:
    response = seeded_client.post(
        "/api/v1/auth/register",
        json={"phone": STUDENT_PHONE, "password": "abc12345", "nickname": "重复"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_register_rejects_bad_phone(seeded_client: TestClient) -> None:
    response = seeded_client.post(
        "/api/v1/auth/register",
        json={"phone": "12345", "password": "abc12345", "nickname": "x"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_requires_letter_and_digit(seeded_client: TestClient) -> None:
    response = seeded_client.post(
        "/api/v1/auth/register",
        json={"phone": "13900002222", "password": "abcdefgh", "nickname": "纯字母"},
    )

    assert response.status_code == 400


def test_login_success_sets_cookie(seeded_client: TestClient) -> None:
    data = _login(seeded_client)

    assert data["user"]["phone"] == STUDENT_PHONE
    assert data["csrfToken"]
    assert seeded_client.cookies.get("sid")


def test_login_wrong_password_is_generic(seeded_client: TestClient) -> None:
    response = seeded_client.post(
        "/api/v1/auth/login", json={"phone": STUDENT_PHONE, "password": "wrong1234"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_login_unknown_phone_looks_identical(seeded_client: TestClient) -> None:
    response = seeded_client.post(
        "/api/v1/auth/login", json={"phone": "13911112222", "password": "wrong1234"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert response.json()["error"]["message"] == "手机号或密码错误"


def test_login_locks_after_five_failures(seeded_client: TestClient) -> None:
    for _ in range(5):
        response = seeded_client.post(
            "/api/v1/auth/login", json={"phone": STUDENT_PHONE, "password": "wrong1234"}
        )
        assert response.status_code == 401

    locked = seeded_client.post(
        "/api/v1/auth/login", json={"phone": STUDENT_PHONE, "password": DEMO_PASSWORD}
    )

    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "RATE_LIMITED"


def test_session_requires_cookie(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/auth/session")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


def test_session_returns_csrf_token(seeded_client: TestClient) -> None:
    login_data = _login(seeded_client)
    response = seeded_client.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.json()["data"]["csrfToken"] == login_data["csrfToken"]


def test_logout_requires_csrf(seeded_client: TestClient) -> None:
    _login(seeded_client)
    response = seeded_client.post("/api/v1/auth/logout")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_logout_with_csrf_invalidates_cookie(seeded_client: TestClient) -> None:
    data = _login(seeded_client)
    response = seeded_client.post(
        "/api/v1/auth/logout", headers={"X-CSRF-Token": data["csrfToken"]}
    )

    assert response.status_code == 200
    assert seeded_client.get("/api/v1/auth/session").status_code == 401


def test_csrf_token_mismatch_rejected(seeded_client: TestClient) -> None:
    _login(seeded_client)
    response = seeded_client.post(
        "/api/v1/auth/logout", headers={"X-CSRF-Token": "not-the-real-token"}
    )

    assert response.status_code == 403


def test_foreign_origin_rejected(seeded_client: TestClient) -> None:
    response = seeded_client.post(
        "/api/v1/auth/login",
        json={"phone": STUDENT_PHONE, "password": DEMO_PASSWORD},
        headers={"Origin": "https://evil.example.com"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_TOKEN_INVALID"


def test_trusted_origin_allowed(seeded_client: TestClient) -> None:
    response = seeded_client.post(
        "/api/v1/auth/login",
        json={"phone": STUDENT_PHONE, "password": DEMO_PASSWORD},
        headers={"Origin": "http://127.0.0.1:5173"},
    )

    assert response.status_code == 200


def test_change_password_revokes_all_sessions(seeded_client: TestClient) -> None:
    data = _login(seeded_client)
    response = seeded_client.post(
        "/api/v1/auth/password",
        json={"oldPassword": DEMO_PASSWORD, "newPassword": "newpass123"},
        headers={"X-CSRF-Token": data["csrfToken"]},
    )

    assert response.status_code == 200
    assert seeded_client.get("/api/v1/auth/session").status_code == 401

    old = seeded_client.post(
        "/api/v1/auth/login", json={"phone": STUDENT_PHONE, "password": DEMO_PASSWORD}
    )
    assert old.status_code == 401

    new = seeded_client.post(
        "/api/v1/auth/login", json={"phone": STUDENT_PHONE, "password": "newpass123"}
    )
    assert new.status_code == 200


def test_login_rotates_previous_session(seeded_client: TestClient) -> None:
    first = _login(seeded_client)
    first_token = seeded_client.cookies.get("sid")

    second = _login(seeded_client)

    assert first["csrfToken"] != second["csrfToken"]
    assert seeded_client.cookies.get("sid") != first_token
