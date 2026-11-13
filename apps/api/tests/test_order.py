"""下单链路：试算、建单、库存、幂等、支付、越权。"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from schorder.dev.seed import DEMO_PASSWORD, sid

STUDENT_PHONE = "13800000001"
MERCHANT_PHONE = "13800000002"

DISH_XIAOCHAOROU = sid("dish-xiaochaorou")
OPT_MILD = sid("dish-xiaochaorou-opt-0-0")
OPT_ADD_EGG = sid("dish-xiaochaorou-opt-1-0")
DISH_FAN = sid("dish-mifan")
DISH_YUTOU = sid("dish-yutou")
OPT_YUTOU_MILD = sid("dish-yutou-opt-0-0")

STALL_CHUANXIANG = sid("stall-chuanxiang")


@pytest.fixture()
def fixed_open_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """把"现在"固定到营业时段内，避免测试依赖真实时钟。"""
    moment = datetime(2026, 11, 13, 12, 0, tzinfo=None)

    class _Fixed(datetime):
        pass

    def _now() -> datetime:
        from datetime import timedelta, timezone

        return moment.replace(tzinfo=timezone(timedelta(hours=8)))

    monkeypatch.setattr("schorder.services.order.now_cn", _now)
    _ = _Fixed


def _login(client: TestClient, phone: str = STUDENT_PHONE) -> str:
    response = client.post("/api/v1/auth/login", json={"phone": phone, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text
    csrf: str = response.json()["data"]["csrfToken"]
    return csrf


def _payload(**overrides: object) -> dict:
    payload = {
        "stallId": STALL_CHUANXIANG,
        "fulfillmentType": "pickup",
        "items": [
            {"dishId": DISH_XIAOCHAOROU, "quantity": 2, "optionIds": [OPT_MILD, OPT_ADD_EGG]}
        ],
        "contactName": "张同学",
        "contactPhone": "13800000001",
        "idempotencyKey": str(uuid.uuid4()),
    }
    payload.update(overrides)
    return payload


def test_preview_prices_server_side(seeded_client: TestClient, fixed_open_time: None) -> None:
    csrf = _login(seeded_client)
    response = seeded_client.post(
        "/api/v1/orders/preview",
        json={
            k: v
            for k, v in _payload().items()
            if k not in ("contactName", "contactPhone", "idempotencyKey")
        },
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    # (1600 + 300) * 2 = 3800；自提无配送费；打包费 100
    assert data["amount"]["itemsAmountCents"] == 3800
    assert data["amount"]["packingFeeCents"] == 100
    assert data["amount"]["deliveryFeeCents"] == 0
    assert data["amount"]["payableCents"] == 3900


def test_preview_ignores_client_price_fields(
    seeded_client: TestClient, fixed_open_time: None
) -> None:
    """请求里塞价格字段应被 extra=forbid 拒绝，而不是被当成真价。"""
    csrf = _login(seeded_client)
    body = {
        "stallId": STALL_CHUANXIANG,
        "items": [{"dishId": DISH_XIAOCHAOROU, "quantity": 1, "priceCents": 1}],
    }
    response = seeded_client.post(
        "/api/v1/orders/preview", json=body, headers={"X-CSRF-Token": csrf}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_order_succeeds(seeded_client: TestClient, fixed_open_time: None) -> None:
    csrf = _login(seeded_client)
    response = seeded_client.post("/api/v1/orders", json=_payload(), headers={"X-CSRF-Token": csrf})

    assert response.status_code == 201, response.text
    order = response.json()["data"]
    assert order["status"] == "pending_payment"
    assert order["amount"]["payableCents"] == 3900
    assert order["canPay"] is True
    assert order["orderNo"].startswith("SO")


def test_create_requires_csrf(seeded_client: TestClient, fixed_open_time: None) -> None:
    _login(seeded_client)
    response = seeded_client.post("/api/v1/orders", json=_payload())

    assert response.status_code == 403


def test_create_rejects_insufficient_stock(
    seeded_client: TestClient, fixed_open_time: None
) -> None:
    csrf = _login(seeded_client)
    payload = _payload(
        items=[{"dishId": DISH_YUTOU, "quantity": 20, "optionIds": [OPT_YUTOU_MILD]}]
    )
    response = seeded_client.post("/api/v1/orders", json=payload, headers={"X-CSRF-Token": csrf})

    # 剁椒鱼头库存 10，要 20 份
    assert response.status_code == 409
    assert "库存不足" in response.json()["error"]["message"]


def test_create_rejects_missing_required_option(
    seeded_client: TestClient, fixed_open_time: None
) -> None:
    csrf = _login(seeded_client)
    payload = _payload(items=[{"dishId": DISH_XIAOCHAOROU, "quantity": 1, "optionIds": []}])
    response = seeded_client.post("/api/v1/orders", json=payload, headers={"X-CSRF-Token": csrf})

    assert response.status_code == 400
    assert "辣度" in response.json()["error"]["message"]


def test_create_is_idempotent(seeded_client: TestClient, fixed_open_time: None) -> None:
    csrf = _login(seeded_client)
    payload = _payload()

    first = seeded_client.post("/api/v1/orders", json=payload, headers={"X-CSRF-Token": csrf})
    second = seeded_client.post("/api/v1/orders", json=payload, headers={"X-CSRF-Token": csrf})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


def test_delivery_requires_address(seeded_client: TestClient, fixed_open_time: None) -> None:
    csrf = _login(seeded_client)
    payload = _payload(fulfillmentType="delivery")
    response = seeded_client.post("/api/v1/orders", json=payload, headers={"X-CSRF-Token": csrf})

    assert response.status_code == 400
    assert "地址" in response.json()["error"]["message"]


def test_delivery_enforces_min_order(seeded_client: TestClient, fixed_open_time: None) -> None:
    csrf = _login(seeded_client)
    payload = _payload(
        fulfillmentType="delivery",
        items=[{"dishId": DISH_FAN, "quantity": 1, "optionIds": []}],
    )
    response = seeded_client.post("/api/v1/orders", json=payload, headers={"X-CSRF-Token": csrf})

    # 米饭 200 < 起送价 1500
    assert response.status_code == 400
    assert "起送" in response.json()["error"]["message"]


def test_pay_then_repay_conflicts(seeded_client: TestClient, fixed_open_time: None) -> None:
    csrf = _login(seeded_client)
    created = seeded_client.post(
        "/api/v1/orders", json=_payload(), headers={"X-CSRF-Token": csrf}
    ).json()["data"]

    paid = seeded_client.post(f"/api/v1/orders/{created['id']}/pay", headers={"X-CSRF-Token": csrf})
    assert paid.status_code == 200
    assert paid.json()["data"]["status"] == "paid"
    assert paid.json()["data"]["paidAt"]

    again = seeded_client.post(
        f"/api/v1/orders/{created['id']}/pay", headers={"X-CSRF-Token": csrf}
    )
    assert again.status_code == 409


def test_cannot_read_other_users_order(seeded_client: TestClient, fixed_open_time: None) -> None:
    csrf = _login(seeded_client)
    created = seeded_client.post(
        "/api/v1/orders", json=_payload(), headers={"X-CSRF-Token": csrf}
    ).json()["data"]

    # 换一个商家账号登录，尝试读学生的订单
    seeded_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    _login(seeded_client, MERCHANT_PHONE)

    response = seeded_client.get(f"/api/v1/orders/{created['id']}")
    assert response.status_code == 404


def test_order_list_and_detail(seeded_client: TestClient, fixed_open_time: None) -> None:
    csrf = _login(seeded_client)
    created = seeded_client.post(
        "/api/v1/orders", json=_payload(), headers={"X-CSRF-Token": csrf}
    ).json()["data"]

    listing = seeded_client.get("/api/v1/orders")
    assert listing.status_code == 200
    body = listing.json()
    assert body["data"][0]["id"] == created["id"]
    assert body["meta"]["total"] >= 1

    detail = seeded_client.get(f"/api/v1/orders/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["items"][0]["dishName"] == "农家小炒肉盖饭"


def test_orders_require_login(seeded_client: TestClient) -> None:
    assert seeded_client.get("/api/v1/orders").status_code == 401
