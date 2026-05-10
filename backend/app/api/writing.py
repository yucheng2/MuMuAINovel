from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.background_task import BackgroundTask
from app.models.project import Project
from app.services.background_task_service import background_task_service
from app.services.auto_write_service import auto_write_loop
from app.database import get_db
from app.logger import get_logger
from pydantic import BaseModel
from typing import Optional

logger = get_logger(__name__)

router = APIRouter(prefix="/api/writing", tags=["writing"])

class AutoWriteRequest(BaseModel):
    project_id: str


async def _run_auto_write_bg(task_id: str, user_id: str, project_id: str):
    """后台运行自动写作"""
    import traceback
    from app.database import get_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker

    logger.info(f"[{task_id}] _run_auto_write_bg 开始, user={user_id[:8]}, project={project_id}")
    try:
        engine = await get_engine(user_id)
        AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with AsyncSessionLocal() as db:
            logger.info(f"[{task_id}] 成功创建 session，进入 auto_write_loop")
            await auto_write_loop(task_id, user_id, project_id, db)
            logger.info(f"[{task_id}] auto_write_loop 正常返回")
    except Exception as e:
        logger.error(f"[{task_id}] _run_auto_write_bg 异常: {e}\n{traceback.format_exc()}")


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
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")

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
