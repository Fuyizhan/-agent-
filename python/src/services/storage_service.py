"""基于 PostgreSQL 的审查状态存取。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.crud import get_review, save_review
from ..pipeline.state import ContractReviewState


class StorageService:
    def __init__(self, db: AsyncSession, tenant_id: str = "", user_id: str = "") -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._user_id = user_id

    async def save(self, state: ContractReviewState) -> None:
        await save_review(
            self._db,
            state,
            tenant_id=self._tenant_id,
            user_id=self._user_id,
        )

    async def load(self, review_id: str) -> ContractReviewState | None:
        return await get_review(self._db, review_id, tenant_id=self._tenant_id)
