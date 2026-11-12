"""命令行入口：把演示数据灌进当前配置指向的数据库。

用法：
    .venv/Scripts/python.exe scripts/seed.py

重复执行是安全的：种子数据的主键由 uuid5 确定性生成，已存在则覆盖。
"""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR / "src"))

from sqlalchemy import func, select  # noqa: E402

from schorder.config import Settings  # noqa: E402
from schorder.db.engine import create_db_engine  # noqa: E402
from schorder.db.models import Category, Dish, DishOption, Stall, User  # noqa: E402
from schorder.db.session import create_session_factory  # noqa: E402
from schorder.dev.seed import DEMO_PASSWORD, seed_all  # noqa: E402


def main() -> int:
    settings = Settings()
    engine = create_db_engine(settings.database_url)
    factory = create_session_factory(engine)

    with factory() as session:
        seed_all(session)
        session.commit()

    with factory() as session:
        counts = {
            "users": session.scalar(select(func.count()).select_from(User)),
            "categories": session.scalar(select(func.count()).select_from(Category)),
            "stalls": session.scalar(select(func.count()).select_from(Stall)),
            "dishes": session.scalar(select(func.count()).select_from(Dish)),
            "options": session.scalar(select(func.count()).select_from(DishOption)),
        }

    engine.dispose()
    print("seed done:", counts)
    print(f"演示账号密码：{DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
