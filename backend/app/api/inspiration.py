"""
灵感模式后台任务 API
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.user_manager import User
from app.services.background_task_service import (
    TaskProgressTracker,
    BackgroundTaskService,
    background_task_service,
)
from app.logger import get_logger

router = APIRouter(prefix="/inspiration", tags=["灵感模式后台任务"])
logger = get_logger(__name__)


class InspirationBackgroundRequest(BaseModel):
    title: str
    description: str
    theme: str
    genre: str
    narrative_perspective: str
    outline_mode: str = "one-to-one"


class InspirationBackgroundResponse(BaseModel):
    task_id: str
    message: str


async def _run_inspiration_bg(task_id: str, user_id: str, db: AsyncSession, task_input: dict):
    """后台执行灵感模式创建任务"""
    tracker = TaskProgressTracker(task_id, user_id, "灵感创建")

    try:
        # 导入 wizard_stream 服务
        from app.services.wizard_stream_service import WizardStreamService

        service = WizardStreamService(db)

        # 阶段1: 项目创建 + 世界观 (0-25%)
        await tracker.start("开始创建项目...")
        await tracker.loading("创建项目中...", 0.1)

        world_result = await service.generate_world_building(
            user_id=user_id,
            title=task_input["title"],
            description=task_input["description"],
            theme=task_input["theme"],
            genre=task_input["genre"],
            narrative_perspective=task_input["narrative_perspective"],
            target_words=100000,
            chapter_count=3,
            character_count=5,
            outline_mode=task_input["outline_mode"],
        )
        project_id = world_result["project_id"]

        await tracker.loading("世界观生成完成", 0.25)

        # 阶段2: 职业体系 (25-50%)
        await tracker.loading("生成职业体系中...", 0.3)
        await service.generate_career_system(project_id=project_id, user_id=user_id)
        await tracker.loading("职业体系生成完成", 0.5)

        # 阶段3: 角色生成 (50-75%)
        await tracker.loading("生成角色中...", 0.55)
        await service.generate_characters(
            project_id=project_id,
            user_id=user_id,
            count=5,
        )
        await tracker.loading("角色生成完成", 0.75)

        # 阶段4: 大纲生成 (75-100%)
        await tracker.loading("生成大纲中...", 0.8)
        await service.generate_outline(
            project_id=project_id,
            user_id=user_id,
            chapter_count=3,
            narrative_perspective=task_input["narrative_perspective"],
            target_words=100000,
        )
        await tracker.loading("大纲生成完成", 0.95)

        await tracker.complete("项目创建完成！")

    except Exception as e:
        logger.error(f"灵感模式后台任务失败: {e}")
        await tracker.error(str(e))
        raise


@router.post("/background", response_model=InspirationBackgroundResponse)
async def create_inspiration_background_task(
    data: InspirationBackgroundRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """创建灵感模式后台任务"""
    # 从认证中间件获取用户ID
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="需要登录")

    task = await BackgroundTaskService.create_task(
        user_id=user_id,
        project_id=None,
        task_type="inspiration",
        task_input=data.model_dump(),
        db=db,
    )

    task_input = data.model_dump()
    task_input["user_id"] = user_id

    await background_task_service.spawn_background_task(
        task.id,
        user_id,
        _run_inspiration_bg,
        db=db,
        task_input=task_input,
    )

    return InspirationBackgroundResponse(
        task_id=task.id,
        message="后台任务已创建",
    )