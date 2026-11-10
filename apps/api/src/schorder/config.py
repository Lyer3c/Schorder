"""应用配置：全部来自环境变量，缺失或类型错误时启动即失败。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = API_DIR / "data" / "schorder.db"


class Settings(BaseSettings):
    """运行期配置。

    所有字段都可以用 ``SCHORDER_`` 前缀的环境变量覆盖，
    例如 ``SCHORDER_DATABASE_URL=sqlite:///./tmp.db``。
    """

    model_config = SettingsConfigDict(
        env_prefix="SCHORDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "Schorder API"
    version: str = "0.1.0"

    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    trusted_origins: list[str] = Field(default=["http://127.0.0.1:5173", "http://localhost:5173"])

    cookie_name: str = "sid"
    cookie_secure: bool = False
    session_idle_minutes: int = 30
    session_absolute_hours: int = 12

    max_body_bytes: int = 64 * 1024
    static_dir: Path | None = None

    @field_validator("trusted_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def sqlite_path(self) -> Path | None:
        """返回 SQLite 文件路径（非 SQLite 时为 None），用于建父目录。"""
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return None
        return Path(self.database_url[len(prefix) :])


@lru_cache
def get_settings() -> Settings:
    return Settings()
