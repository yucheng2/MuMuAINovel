"""自动写作 API - 创建和管理自动写作任务"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models.background_task import BackgroundTask
from app.services.background_task_service import background_task_service
from app.logger import get_logger

router = APIRouter(prefix="/api/writing", tags=["writing"])
logger = get_logger(__name__)


class AutoWriteRequest(BaseModel):
    project_id: str

from pydantic import BaseModel


@router.post("/auto-write")
async def create_auto_write_task(
    data: AutoWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建自动写作任务"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    # TODO: 实现任务创建逻辑
    pass


@router.post("/auto-write/{task_id}/stop")
async def stop_auto_write_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """停止自动写作任务"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    # TODO: 实现停止逻辑
    pass


@router.get("/auto-write/{task_id}/progress")
async def get_auto_write_progress(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取自动写作进度"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    # TODO: 实现进度查询
    pass
