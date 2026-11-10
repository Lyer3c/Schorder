"""结构化日志。开发态用彩色控制台，生产态用 JSON 便于采集。

不引入额外依赖：structlog 足够，且能把 request_id 通过 contextvars 自动带到每条日志。
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(env: str) -> None:
    level = logging.DEBUG if env == "dev" else logging.INFO

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    renderer: structlog.typing.Processor = (
        structlog.dev.ConsoleRenderer() if env == "dev" else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
