from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.background_task import BackgroundTask
from app.models.project import Project
from app.services.background_task_service import background_task_service
from app.services.auto_write_service import auto_write_loop, get_project_word_count
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/writing", tags=["writing"])

class AutoWriteRequest(BaseModel):
    project_id: str


async def _run_auto_write_bg(task_id: str, user_id: str, project_id: str):
    """后台运行自动写作"""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await auto_write_loop(task_id, user_id, project_id, db)


@router.post("/auto-write")
async def create_auto_write_task(
    data: AutoWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建自动写作任务"""
    user_id = await get_current_user(request)

    # 验证项目存在
    project_result = await db.execute(select(Project).where(Project.id == data.project_id))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 创建后台任务
    task = await background_task_service.create_task(
        user_id=user_id,
        project_id=data.project_id,
        task_type="auto_write",
        task_input={"project_id": data.project_id},
        db=db
    )

    # 启动自动写作循环
    await background_task_service.spawn_background_task(
        task_id=task.id,
        user_id=user_id,
        task_func=_run_auto_write_bg,
        project_id=data.project_id
    )

    return {"task_id": task.id, "status": "running"}


@router.post("/auto-write/{task_id}/stop")
async def stop_auto_write_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """停止自动写作任务"""
    user_id = await get_current_user(request)

    # 获取任务
    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.user_id == user_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 设置取消标志
    task.cancel_requested = True
    task.status = "cancelled"
    await db.commit()

    return {"status": "stopped"}


@router.get("/auto-write/{task_id}/progress")
async def get_auto_write_progress(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取自动写作进度"""
    user_id = await get_current_user(request)

    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.user_id == user_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    current_words = await get_project_word_count(task.project_id, db)
    project = await get_project(task.project_id, db)
    target_words = project.target_words if project else 30000

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress or 0,
        "current_words": current_words,
        "target_words": target_words,
        "message": task.status_message,
        "details": task.progress_details or {}
    }
