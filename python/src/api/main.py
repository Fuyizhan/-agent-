"""FastAPI 应用入口：初始化数据库、加载种子并注册核心路由。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from ..config import settings
from ..db import session as db_session
from ..db.models import Base
from ..logging_config import setup_logging
from .exceptions import register_exception_handlers
from .middleware import register_middleware
from .rate_limit import register_rate_limit
from .routers import auth_router, health_router, review_router

setup_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)
_SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "seed.sql"


def _split_sql_statements(sql: str) -> list[str]:
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    return [statement.strip() for statement in "\n".join(lines).split(";") if statement.strip()]


async def _seed_if_needed(conn) -> None:
    if not settings.SEED_ON_STARTUP:
        return
    user_count = (await conn.execute(text("SELECT COUNT(*) FROM users"))).scalar() or 0
    if user_count > 0:
        return
    if not _SEED_FILE.is_file():
        raise RuntimeError(f"种子文件不存在: {_SEED_FILE}")
    for statement in _split_sql_statements(_SEED_FILE.read_text(encoding="utf-8")):
        await conn.execute(text(statement))
    logger.info("已加载默认用户种子数据")


@asynccontextmanager
async def lifespan(_: FastAPI):
    security_problems = settings.validate_security()
    if security_problems:
        raise RuntimeError("启动被拒绝：" + "；".join(security_problems))

    # 空数据库首次启动时由 SQLAlchemy 创建全部核心表。
    db_session.init_db(settings.DATABASE_URL)
    async with db_session.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _seed_if_needed(conn)
    logger.info("数据库表结构已就绪")

    yield
    await db_session.close_db()


def _cors_origins(value: str) -> list[str]:
    if value.strip() == "*":
        return ["*"]
    return [item.strip() for item in value.split(",") if item.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title="多 Agent 智能合同审查系统",
        description="登录、上传合同、四 Agent 审查和 PDF 报告",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(settings.CORS_ORIGINS),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    register_rate_limit(app)
    register_middleware(app)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(review_router)
    return app


app = create_app()
