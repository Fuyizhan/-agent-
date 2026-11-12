"""登录接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...db.models import UserRecord
from ...db.session import get_db
from ..auth.security import create_access_token, verify_password
from ..schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(UserRecord).where(UserRecord.username == request.username))
    ).scalar_one_or_none()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    token = create_access_token(
        subject=user.id,
        role=user.role,
        tenant_id=user.tenant_id,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )
