"""FastAPI 服务依赖。"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from ..api.auth.dependencies import CurrentUser, get_current_user
from ..db.session import get_db
from .review_service import ReviewService
from .storage_service import StorageService


def get_storage_service(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> StorageService:
    return StorageService(db=db, tenant_id=user.tenant_id, user_id=user.id)


def get_review_service(storage: StorageService = Depends(get_storage_service)) -> ReviewService:
    return ReviewService(storage=storage, user_id=storage._user_id)
