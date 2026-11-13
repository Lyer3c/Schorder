"""应用装配。

create_app() 是唯一入口：测试里可以传入自定义 Settings 拿到一个隔离实例，
生产由 uvicorn 通过 ``schorder.main:app`` 加载模块级实例。
"""

from __future__ import annotations

from fastapi import FastAPI

from schorder.api.errors import register_exception_handlers
from schorder.api.middleware import (
    OriginCheckMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from schorder.api.routers import auth, catalog, health, meta, order
from schorder.config import Settings, get_settings
from schorder.db.engine import create_db_engine
from schorder.db.session import create_session_factory
from schorder.infra.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    configure_logging(resolved.env)

    app = FastAPI(
        title=resolved.app_name,
        version=resolved.version,
        openapi_url="/api/v1/openapi.json",
        docs_url=None if resolved.is_prod else "/docs",
        redoc_url=None,
        redirect_slashes=False,
        servers=[{"url": "/", "description": "同源部署"}],
    )

    engine = create_db_engine(resolved.database_url)
    app.state.settings = resolved
    app.state.engine = engine
    app.state.sessionmaker = create_session_factory(engine)

    # 后加的在外层：安全头必须包住 413 等由内层中间件直接返回的响应
    app.add_middleware(OriginCheckMiddleware, trusted_origins=list(resolved.trusted_origins))
    app.add_middleware(RequestContextMiddleware, max_body_bytes=resolved.max_body_bytes)
    app.add_middleware(SecurityHeadersMiddleware, is_prod=resolved.is_prod)

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(meta.router, prefix="/api/v1")
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(order.router, prefix="/api/v1")

    return app


app = create_app()
