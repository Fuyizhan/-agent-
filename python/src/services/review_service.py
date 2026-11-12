"""单文件合同审查任务编排。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..db.crud import get_review, save_review
from ..db import session as db_session
from ..pipeline.graph import create_review_pipeline, set_progress_callback
from ..pipeline.state import ContractReviewState, ReviewStatus
from .storage_service import StorageService

logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_BACKGROUND_TASKS: set[asyncio.Task] = set()


class ReviewService:
    def __init__(self, storage: StorageService, user_id: str = "") -> None:
        self._storage = storage
        self._tenant_id = storage._tenant_id
        self._user_id = user_id

    async def start_from_file(self, filename: str, content: bytes, user_id: str = "") -> str:
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {extension}")

        review_id = str(uuid.uuid4())
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{review_id}{extension}"
        file_path.write_bytes(content)

        self._user_id = user_id or self._user_id
        state = ContractReviewState(
            review_id=review_id,
            status=ReviewStatus.PENDING,
            document_path=str(file_path),
            original_filename=filename,
        )
        await self._persist_detached(state)
        self._dispatch(state)
        return review_id

    def _dispatch(self, state: ContractReviewState) -> None:
        task = asyncio.create_task(self._run_pipeline(state))
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)

    async def _run_pipeline(self, initial_state: ContractReviewState) -> None:
        review_id = initial_state.review_id

        async def on_progress(state: ContractReviewState) -> None:
            state.updated_at = datetime.now()
            await self._persist_detached(state)

        set_progress_callback(review_id, on_progress)
        try:
            initial_state.status = ReviewStatus.IN_PROGRESS
            initial_state.updated_at = datetime.now()
            await self._persist_detached(initial_state)

            pipeline = create_review_pipeline()
            result = await pipeline.ainvoke(
                initial_state.model_dump(mode="json"),
                config={"configurable": {"thread_id": review_id}},
            )
            final_state = ContractReviewState.model_validate(result)
            final_state.status = ReviewStatus.COMPLETED
            final_state.current_step = ""
            final_state.progress = 1.0
            final_state.updated_at = datetime.now()
            await self._persist_detached(final_state)
            logger.info("审查完成 review_id=%s", review_id)
        except Exception as exc:
            logger.exception("审查流水线失败 review_id=%s", review_id)
            failed = await self._load_detached(review_id) or initial_state
            message = f"审查流水线失败: {exc}"
            if message not in failed.errors:
                failed.errors.append(message)
            if message not in failed.warnings:
                failed.warnings.append(message)
            failed.status = ReviewStatus.FAILED
            failed.current_step = ""
            failed.updated_at = datetime.now()
            await self._persist_detached(failed)
        finally:
            set_progress_callback(review_id, None)

    async def get(self, review_id: str) -> ContractReviewState | None:
        return await self._storage.load(review_id)

    async def _persist_detached(self, state: ContractReviewState) -> None:
        if db_session.async_session_factory is None:
            raise RuntimeError("数据库尚未初始化")
        async with db_session.async_session_factory() as session:
            async with session.begin():
                await save_review(
                    session,
                    state,
                    tenant_id=self._tenant_id,
                    user_id=self._user_id,
                )

    async def _load_detached(self, review_id: str) -> ContractReviewState | None:
        if db_session.async_session_factory is None:
            return None
        async with db_session.async_session_factory() as session:
            return await get_review(session, review_id, tenant_id=self._tenant_id)
