"""导出 OpenAPI 契约。

用法（在 apps/api 下）：
    .venv/Scripts/python.exe scripts/export_openapi.py [输出路径]

默认输出到仓库根的 packages/contract/openapi.json。
这个文件是前端类型的唯一来源：由 CI 校验它与生成物是否同步。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]
sys.path.insert(0, str(API_DIR / "src"))

from schorder.config import Settings  # noqa: E402
from schorder.main import create_app  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "packages" / "contract" / "openapi.json"


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT

    # 用内存库，导出契约不应该产生任何副作用
    app = create_app(Settings(env="test", database_url="sqlite:///:memory:"))
    spec = app.openapi()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"openapi written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
