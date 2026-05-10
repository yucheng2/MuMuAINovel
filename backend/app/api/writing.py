"""一键写作 API"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.background_task import BackgroundTask
from app.models.project import Project
from app.services.background_task_service import background_task_service
from app.services.unified_write_service import unified_write_loop
from app.database import get_db
from app.logger import get_logger
from pydantic import BaseModel
from typing import Optional

logger = get_logger(__name__)

router = APIRouter(prefix="/api/writing", tags=["writing"])


class UnifiedWriteRequest(BaseModel):
    project_id: str
    chapters_per_outline: int = 1


async def _run_unified_write_bg(task_id: str, user_id: str, project_id: str, chapters_per_outline: int):
    """后台运行一键写作"""
    import traceback
    from app.database import get_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker

    logger.info(f"[{task_id}] _run_unified_write_bg 开始, user={user_id[:8]}, project={project_id}")
    try:
        engine = await get_engine(user_id)
        AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with AsyncSessionLocal() as db:
            logger.info(f"[{task_id}] 成功创建 session，进入 unified_write_loop")
            await unified_write_loop(task_id, user_id, project_id, chapters_per_outline, db)
            logger.info(f"[{task_id}] unified_write_loop 正常返回")
    except Exception as e:
        logger.error(f"[{task_id}] _run_unified_write_bg 异常: {e}\n{traceback.format_exc()}")


@router.post("/unified-write")
async def create_unified_write_task(
    data: UnifiedWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建一键写作任务"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")

    project_result = await db.execute(select(Project).where(Project.id == data.project_id))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    task = await background_task_service.create_task(
        user_id=user_id,
        project_id=data.project_id,
        task_type="unified_write",
        task_input={
            "project_id": data.project_id,
            "chapters_per_outline": data.chapters_per_outline
        },
        db=db
    )

    await background_task_service.spawn_background_task(
        task_id=task.id,
        user_id=user_id,
        task_func=_run_unified_write_bg,
        project_id=data.project_id,
        chapters_per_outline=data.chapters_per_outline
    )

    return {"task_id": task.id, "status": "running"}


@router.post("/unified-write/{task_id}/stop")
async def stop_unified_write_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """停止一键写作任务"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")

    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.user_id == user_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task.cancel_requested = True
    task.status = "cancelled"
    await db.commit()

    return {"status": "stopped"}
