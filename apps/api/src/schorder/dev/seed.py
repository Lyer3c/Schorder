"""种子数据：演示用的分类、档口、菜单、账号。

设计要点：
- **幂等**：所有主键由 uuid5(namespace, key) 确定性生成，重复执行是覆盖而不是新增
- **有边界**：故意放入售罄（stock=0）、下架（off_shelf）、待审核（pending）三种状态，
  M1 的列表/详情页必须能正确处理它们
- 账号密码统一为 schorder123（仅演示环境）

命令行入口在 scripts/seed.py；测试直接调用 seed_all(session)。
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from schorder.db.models import (
    Category,
    Dish,
    DishOption,
    DishOptionGroup,
    MenuGroup,
    Stall,
    StallBusinessHour,
    User,
)
from schorder.infra.clock import utc_now_iso
from schorder.infra.security import hash_password

SEED_NS = uuid.UUID("01920000-0000-7000-8000-000000000000")
DEMO_PASSWORD = "schorder123"  # noqa: S105 - 仅演示环境


def sid(key: str) -> str:
    """确定性主键：同一 key 永远得到同一个 UUID，保证 seed 可重复执行。"""
    return str(uuid.uuid5(SEED_NS, key))


USERS: list[dict[str, Any]] = [
    {
        "key": "student-1",
        "phone": "13800000001",
        "nickname": "张同学",
        "role": "student",
    },
    {
        "key": "merchant-1",
        "phone": "13800000002",
        "nickname": "川湘小炒 · 王师傅",
        "role": "merchant",
    },
    {
        "key": "merchant-2",
        "phone": "13800000003",
        "nickname": "兰州拉面 · 李阿姨",
        "role": "merchant",
    },
    {
        "key": "admin-1",
        "phone": "13800000009",
        "nickname": "平台管理员",
        "role": "admin",
    },
]

CATEGORIES: list[tuple[str, str]] = [
    ("cat-rice", "盖浇饭"),
    ("cat-noodle", "面食"),
    ("cat-snack", "小吃"),
    ("cat-light", "轻食"),
    ("cat-drink", "饮品"),
]

STALLS: list[dict[str, Any]] = [
    {
        "key": "stall-chuanxiang",
        "owner": "merchant-1",
        "category": "cat-rice",
        "name": "三食堂 · 川湘小炒",
        "description": "现炒锅气，辣度可选",
        "notice": "高峰期出餐约 20 分钟，建议提前下单",
        "min_order": 1500,
        "packing": 100,
        "delivery": 200,
        "status": "active",
        "sales": 940,
        "rating": [4.6, 128],
        "hours": [("10:30", "20:30")],
        "groups": [
            (
                "招牌",
                [
                    {
                        "key": "dish-xiaochaorou",
                        "name": "农家小炒肉盖饭",
                        "price": 1600,
                        "stock": 30,
                        "options": [
                            ("辣度", True, 1, 1, [("微辣", 0), ("中辣", 0), ("特辣", 0)]),
                            ("加料", False, 0, 3, [("加蛋", 300), ("加青菜", 200), ("加肉", 600)]),
                        ],
                    },
                    {
                        "key": "dish-yutou",
                        "name": "剁椒鱼头饭",
                        "price": 2200,
                        "stock": 10,
                        "options": [("辣度", True, 1, 1, [("微辣", 0), ("中辣", 0)])],
                    },
                ],
            ),
            (
                "主食",
                [
                    {
                        "key": "dish-fanqie",
                        "name": "番茄炒蛋盖饭",
                        "price": 1400,
                        "stock": 40,
                        "options": [],
                    },
                    {
                        "key": "dish-mifan",
                        "name": "米饭",
                        "price": 200,
                        "stock": 100,
                        "options": [],
                    },
                ],
            ),
        ],
    },
    {
        "key": "stall-lamian",
        "owner": "merchant-2",
        "category": "cat-noodle",
        "name": "二食堂 · 兰州拉面",
        "description": "手工拉制，汤清面劲",
        "notice": "面条现拉，出餐约 10 分钟",
        "min_order": 1200,
        "packing": 100,
        "delivery": 200,
        "status": "active",
        "sales": 1620,
        "rating": [4.8, 356],
        "hours": [("07:00", "21:00")],
        "groups": [
            (
                "面食",
                [
                    {
                        "key": "dish-niurou",
                        "name": "牛肉拉面",
                        "price": 1800,
                        "stock": 25,
                        "options": [
                            ("面型", True, 1, 1, [("细面", 0), ("宽面", 0), ("毛细", 0)]),
                            ("加料", False, 0, 2, [("加牛肉", 800), ("加蛋", 300)]),
                        ],
                    },
                    {
                        "key": "dish-fanqiemian",
                        "name": "番茄鸡蛋面",
                        "price": 1500,
                        "stock": 20,
                        "options": [],
                    },
                ],
            ),
            (
                "小菜",
                [
                    {
                        "key": "dish-huanggua",
                        "name": "凉拌黄瓜",
                        "price": 600,
                        "stock": 15,
                        "options": [],
                    }
                ],
            ),
        ],
    },
    {
        "key": "stall-malatang",
        "owner": "merchant-2",
        "category": "cat-snack",
        "name": "一食堂 · 麻辣烫",
        "description": "自选配菜，按份计价",
        "min_order": 1000,
        "packing": 100,
        "delivery": 200,
        "status": "active",
        "sales": 2100,
        "rating": [4.3, 512],
        "hours": [("10:00", "22:00")],
        "groups": [
            (
                "套餐",
                [
                    {
                        "key": "dish-malatang",
                        "name": "经典麻辣烫",
                        "price": 1500,
                        "stock": 50,
                        "options": [
                            ("辣度", True, 1, 1, [("微辣", 0), ("中辣", 0), ("特辣", 0)]),
                            ("加料", False, 0, 3, [("丸子", 500), ("豆皮", 200)]),
                        ],
                    },
                    {
                        "key": "dish-fanqie-malatang",
                        "name": "番茄麻辣烫",
                        "price": 1600,
                        "stock": 0,  # 售罄，用来验证前端置灰
                        "options": [],
                    },
                ],
            ),
            (
                "饮品",
                [
                    {
                        "key": "dish-suanmeitang",
                        "name": "酸梅汤",
                        "price": 500,
                        "stock": 30,
                        "options": [],
                    }
                ],
            ),
        ],
    },
    {
        "key": "stall-salad",
        "owner": "merchant-1",
        "category": "cat-light",
        "name": "三食堂 · 轻食沙拉",
        "description": "低卡轻食，酱料另选",
        "min_order": 1800,
        "packing": 150,
        "delivery": 300,
        "status": "active",
        "sales": 320,
        "rating": [4.7, 64],
        "hours": [("09:00", "19:30")],
        "groups": [
            (
                "沙拉",
                [
                    {
                        "key": "dish-jixiong",
                        "name": "鸡胸沙拉",
                        "price": 2200,
                        "stock": 12,
                        "options": [
                            (
                                "酱料",
                                True,
                                1,
                                1,
                                [("油醋汁", 0), ("千岛酱", 0), ("芝麻酱", 0)],
                            )
                        ],
                    },
                    {
                        "key": "dish-niuyouguo",
                        "name": "牛油果沙拉",
                        "price": 2600,
                        "stock": 8,
                        "options": [],
                    },
                    {
                        "key": "dish-sanmingzhi",
                        "name": "全麦三明治",
                        "price": 1500,
                        "stock": 20,
                        "status": "off_shelf",  # 下架，验证列表过滤
                        "options": [],
                    },
                ],
            )
        ],
    },
    {
        "key": "stall-naicha",
        "owner": "merchant-1",
        "category": "cat-drink",
        "name": "二食堂 · 手作奶茶",
        "description": "现萃茶底，可选糖度",
        "min_order": 800,
        "packing": 50,
        "delivery": 200,
        "status": "active",
        "sales": 3800,
        "rating": [4.5, 920],
        "hours": [("09:30", "21:30")],
        "groups": [
            (
                "奶茶",
                [
                    {
                        "key": "dish-zhenzhu",
                        "name": "珍珠奶茶",
                        "price": 1200,
                        "stock": 60,
                        "options": [
                            ("温度", True, 1, 1, [("常温", 0), ("少冰", 0), ("去冰", 0)]),
                            ("糖度", True, 1, 1, [("全糖", 0), ("半糖", 0), ("无糖", 0)]),
                            ("加料", False, 0, 2, [("珍珠", 200), ("椰果", 200)]),
                        ],
                    },
                    {
                        "key": "dish-yuni",
                        "name": "芋泥啵啵",
                        "price": 1500,
                        "stock": 40,
                        "options": [],
                    },
                    {
                        "key": "dish-ningmeng",
                        "name": "柠檬茶",
                        "price": 1000,
                        "stock": 50,
                        "options": [],
                    },
                ],
            )
        ],
    },
    {
        "key": "stall-jianbing",
        "owner": "merchant-2",
        "category": "cat-snack",
        "name": "一食堂 · 煎饼果子",
        "description": "新入驻，等待平台审核",
        "min_order": 600,
        "packing": 50,
        "delivery": 200,
        "status": "pending",  # 待审核，验证列表不展示、管理端能看到
        "sales": 0,
        "rating": [0.0, 0],
        "hours": [("06:30", "10:30")],
        "groups": [
            (
                "煎饼",
                [
                    {
                        "key": "dish-jianbing",
                        "name": "经典煎饼",
                        "price": 800,
                        "stock": 30,
                        "options": [],
                    },
                    {
                        "key": "dish-jianbing-chang",
                        "name": "加肠煎饼",
                        "price": 1200,
                        "stock": 20,
                        "options": [],
                    },
                ],
            )
        ],
    },
]


def seed_users(session: Session) -> None:
    password_hash, algo = hash_password(DEMO_PASSWORD)
    for item in USERS:
        session.merge(
            User(
                id=sid(item["key"]),
                phone=item["phone"],
                password_hash=password_hash,
                password_algo=algo,
                nickname=item["nickname"],
                role=item["role"],
                status="active",
            )
        )
    session.flush()


def seed_catalog(session: Session) -> None:
    for index, (key, name) in enumerate(CATEGORIES):
        session.merge(Category(id=sid(key), name=name, sort_order=index, is_active=True))
    session.flush()

    for stall_data in STALLS:
        stall_id = sid(stall_data["key"])
        rating_sum = round(stall_data["rating"][0] * stall_data["rating"][1])
        session.merge(
            Stall(
                id=stall_id,
                owner_user_id=sid(stall_data["owner"]),
                category_id=sid(stall_data["category"]),
                name=stall_data["name"],
                description=stall_data.get("description"),
                notice=stall_data.get("notice"),
                contact_phone="021-0000-0000",
                min_order_cents=stall_data["min_order"],
                packing_fee_cents=stall_data["packing"],
                delivery_fee_cents=stall_data["delivery"],
                rating_sum=rating_sum,
                rating_count=stall_data["rating"][1],
                monthly_sales=stall_data["sales"],
                monthly_sales_period=utc_now_iso()[:7],
                status=stall_data["status"],
                reviewed_by=sid("admin-1") if stall_data["status"] == "active" else None,
                reviewed_at=utc_now_iso() if stall_data["status"] == "active" else None,
                created_at=utc_now_iso(),
                updated_at=utc_now_iso(),
            )
        )
        session.flush()

        # 营业时段：默认周一到周日同一段
        for weekday in range(1, 8):
            for open_time, close_time in stall_data["hours"]:
                session.merge(
                    StallBusinessHour(
                        id=sid(f"{stall_data['key']}-hour-{weekday}-{open_time}"),
                        stall_id=stall_id,
                        weekday=weekday,
                        open_time=open_time,
                        close_time=close_time,
                    )
                )

        for group_index, (group_name, dishes) in enumerate(stall_data["groups"]):
            group_id = sid(f"{stall_data['key']}-group-{group_index}")
            session.merge(
                MenuGroup(id=group_id, stall_id=stall_id, name=group_name, sort_order=group_index)
            )
            session.flush()

            for dish_index, dish in enumerate(dishes):
                dish_id = sid(dish["key"])
                session.merge(
                    Dish(
                        id=dish_id,
                        stall_id=stall_id,
                        group_id=group_id,
                        name=dish["name"],
                        description=dish.get("description"),
                        price_cents=dish["price"],
                        stock=dish["stock"],
                        status=dish.get("status", "on_sale" if dish["stock"] > 0 else "sold_out"),
                        sort_order=dish_index,
                        created_at=utc_now_iso(),
                        updated_at=utc_now_iso(),
                    )
                )
                session.flush()

                for opt_index, (opt_name, required, min_sel, max_sel, options) in enumerate(
                    dish["options"]
                ):
                    opt_group_id = sid(f"{dish['key']}-opt-{opt_index}")
                    session.merge(
                        DishOptionGroup(
                            id=opt_group_id,
                            dish_id=dish_id,
                            name=opt_name,
                            required=required,
                            min_select=min_sel,
                            max_select=max_sel,
                            sort_order=opt_index,
                        )
                    )
                    session.flush()
                    for o_index, (o_name, delta) in enumerate(options):
                        session.merge(
                            DishOption(
                                id=sid(f"{dish['key']}-opt-{opt_index}-{o_index}"),
                                group_id=opt_group_id,
                                name=o_name,
                                price_delta_cents=delta,
                                sort_order=o_index,
                            )
                        )
        session.flush()


def seed_all(session: Session) -> None:
    """提交由调用方负责——测试里常用事务回滚。"""
    seed_users(session)
    seed_catalog(session)
