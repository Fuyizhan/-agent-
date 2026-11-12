"""核心 API 路由。"""

from .auth import router as auth_router
from .health import router as health_router
from .review import router as review_router

__all__ = ["auth_router", "health_router", "review_router"]
