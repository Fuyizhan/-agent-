"""数据库 engine、session 工厂和 FastAPI 依赖。"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    global engine, async_session_factory
    kwargs = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if not database_url.startswith("sqlite"):
        kwargs.update(
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=1800,
        )
    engine = create_async_engine(database_url, **kwargs)
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("数据库连接已初始化")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if async_session_factory is None:
        raise RuntimeError("数据库尚未初始化")
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
    engine = None
    async_session_factory = None
    logger.info("数据库连接已关闭")
