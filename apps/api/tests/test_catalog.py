"""目录接口：分类、列表、详情、搜索、分页、错误。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from schorder.dev.seed import STALLS, sid


def test_categories_sorted_by_sort_order(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/categories")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    names = [item["name"] for item in body["data"]]
    assert names[0] == "盖浇饭"
    assert len(names) == 5


def test_stall_list_only_returns_active(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/stalls", params={"limit": 50})

    assert response.status_code == 200
    stalls = response.json()["data"]

    # 种子里 6 个档口，其中 1 个 pending，列表应只出现 5 个
    assert len(stalls) == 5
    assert all(item["name"] != "一食堂 · 煎饼果子" for item in stalls)


def test_stall_list_uses_camel_case_and_derived_fields(seeded_client: TestClient) -> None:
    body = seeded_client.get("/api/v1/stalls", params={"limit": 1}).json()
    item = body["data"][0]

    assert "isOpen" in item
    assert "minOrderCents" in item
    assert "estimatedMinutes" in item
    assert isinstance(item["isOpen"], bool)
    assert item["rating"] >= 0


def test_stall_list_filters_by_category(seeded_client: TestClient) -> None:
    body = seeded_client.get(
        "/api/v1/stalls", params={"categoryId": sid("cat-drink"), "limit": 50}
    ).json()

    assert [item["name"] for item in body["data"]] == ["二食堂 · 手作奶茶"]


def test_stall_list_filters_by_keyword(seeded_client: TestClient) -> None:
    body = seeded_client.get("/api/v1/stalls", params={"keyword": "拉面"}).json()

    assert len(body["data"]) == 1
    assert "拉面" in body["data"][0]["name"]


def test_stall_list_sorts_by_rating(seeded_client: TestClient) -> None:
    body = seeded_client.get("/api/v1/stalls", params={"sort": "rating", "limit": 50}).json()
    ratings = [item["rating"] for item in body["data"]]

    assert ratings == sorted(ratings, reverse=True)


def test_stall_list_paginates_with_cursor(seeded_client: TestClient) -> None:
    first = seeded_client.get("/api/v1/stalls", params={"limit": 2}).json()
    cursor = first["meta"]["nextCursor"]

    assert cursor is not None
    assert len(first["data"]) == 2

    second = seeded_client.get("/api/v1/stalls", params={"limit": 2, "cursor": cursor}).json()
    first_ids = {item["id"] for item in first["data"]}
    second_ids = {item["id"] for item in second["data"]}

    assert first_ids.isdisjoint(second_ids)


def test_stall_list_rejects_invalid_limit(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/stalls", params={"limit": 0})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_stall_detail_returns_menu_without_off_shelf(seeded_client: TestClient) -> None:
    stall_id = sid("stall-salad")
    response = seeded_client.get(f"/api/v1/stalls/{stall_id}")

    assert response.status_code == 200
    detail = response.json()["data"]

    dish_names = [dish["name"] for group in detail["menuGroups"] for dish in group["dishes"]]
    assert "全麦三明治" not in dish_names  # off_shelf 不展示
    assert "鸡胸沙拉" in dish_names
    assert detail["businessHours"]


def test_stall_detail_includes_option_groups(seeded_client: TestClient) -> None:
    detail = seeded_client.get(f"/api/v1/stalls/{sid('stall-chuanxiang')}").json()["data"]

    dishes = [dish for group in detail["menuGroups"] for dish in group["dishes"]]
    spicy = next(dish for dish in dishes if dish["id"] == sid("dish-xiaochaorou"))
    groups = {group["name"]: group for group in spicy["optionGroups"]}

    assert groups["辣度"]["required"] is True
    assert groups["辣度"]["maxSelect"] == 1
    assert [option["name"] for option in groups["辣度"]["options"]] == ["微辣", "中辣", "特辣"]
    assert groups["加料"]["required"] is False
    assert groups["加料"]["options"][0]["priceDeltaCents"] == 300


def test_stall_detail_marks_sold_out(seeded_client: TestClient) -> None:
    detail = seeded_client.get(f"/api/v1/stalls/{sid('stall-malatang')}").json()["data"]

    dishes = {dish["name"]: dish for group in detail["menuGroups"] for dish in group["dishes"]}
    assert dishes["番茄麻辣烫"]["stock"] == 0
    assert dishes["番茄麻辣烫"]["status"] == "sold_out"


def test_stall_detail_hides_pending_stall(seeded_client: TestClient) -> None:
    response = seeded_client.get(f"/api/v1/stalls/{sid('stall-jianbing')}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_stall_detail_unknown_id_returns_404(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/stalls/does-not-exist")

    assert response.status_code == 404


def test_search_matches_stalls_and_dishes(seeded_client: TestClient) -> None:
    body = seeded_client.get("/api/v1/search", params={"q": "面"}).json()["data"]

    assert any("拉面" in stall["name"] for stall in body["stalls"])
    assert any("面" in dish["name"] for dish in body["dishes"])


def test_search_requires_query(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/search")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_search_rejects_blank_query(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/search", params={"q": ""})

    assert response.status_code == 400


def test_seed_is_idempotent(seeded_client: TestClient) -> None:
    """重复灌种子不应该产生重复档口。"""
    from sqlalchemy import func, select

    from schorder.db.engine import create_db_engine
    from schorder.db.models import Stall
    from schorder.db.session import create_session_factory
    from schorder.dev.seed import seed_all

    settings = seeded_client.app.state.settings  # type: ignore[attr-defined]
    engine = create_db_engine(settings.database_url)
    factory = create_session_factory(engine)
    with factory() as session:
        seed_all(session)
        session.commit()
        count = session.scalar(select(func.count()).select_from(Stall))
    engine.dispose()

    assert count == len(STALLS)
