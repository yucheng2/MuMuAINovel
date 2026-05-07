import asyncio
import logging
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_task import BackgroundTask
from app.models.project import Project
from app.models.outline import Outline
from app.models.chapter import Chapter
from app.services.background_task_service import TaskProgressTracker
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


async def get_project(project_id: str, db: AsyncSession) -> Optional[Project]:
    """获取项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def get_project_word_count(project_id: str, db: AsyncSession) -> int:
    """获取项目已写字数"""
    result = await db.execute(
        select(func.coalesce(func.sum(Chapter.word_count), 0))
        .where(Chapter.project_id == project_id)
    )
    return result.scalar() or 0


async def generate_one_outline(project_id: str, user_id: str, db: AsyncSession):
    """生成1个大纲"""
    from app.api.outlines import continue_outline_generator
    from app.models.outline import Outline as OutlineModel

    # 获取项目信息
    project = await get_project(project_id, db)
    if not project:
        return None

    # 计算当前已有大纲数量
    outlines_result = await db.execute(
        select(OutlineModel).where(OutlineModel.project_id == project_id)
    )
    existing_outlines = list(outlines_result.scalars().all())
    current_count = len(existing_outlines)

    # 自动判断情节阶段
    if project.chapter_count and project.chapter_count > 0:
        progress = current_count / project.chapter_count
        if progress < 0.5:
            plot_stage = "development"
        elif progress < 0.8:
            plot_stage = "climax"
        else:
            plot_stage = "ending"
    else:
        plot_stage = "development"

    # 构建请求
    request_data = {
        "project_id": project_id,
        "chapter_count": 1,  # 每次只生成1个大纲
        "mode": "continue",
        "plot_stage": plot_stage,
        "story_direction": "自然延续故事发展",
        "requirements": ""
    }

    # 调用现有的 continue_outline_generator
    user_ai_service = await AIService.create(user_id, db)

    # consume the generator to trigger actual generation
    async for _ in continue_outline_generator(
        request_data, db, user_ai_service, user_id
    ):
        pass  # SSE events are already handled inside the generator (commits/db operations)

    # 返回生成的大纲
    new_outlines_result = await db.execute(
        select(OutlineModel).where(OutlineModel.project_id == project_id)
    )
    new_outlines = list(new_outlines_result.scalars().all())
    if len(new_outlines) > current_count:
        return new_outlines[-1]  # 返回最新的大纲
    return None


async def get_outlines(project_id: str, db: AsyncSession):
    """获取项目所有大纲"""
    from app.models.outline import Outline as OutlineModel
    result = await db.execute(
        select(OutlineModel)
        .where(OutlineModel.project_id == project_id)
        .order_by(OutlineModel.order_index)
    )
    return list(result.scalars().all())


async def expand_outline_to_chapters(outline_id: str, user_id: str, db: AsyncSession, count: int = 3):
    """展开大纲为指定数量章节"""
    # TODO: 调用现有的展开大纲逻辑
    pass


async def write_chapter_content(chapter_id: str, user_id: str, db: AsyncSession) -> bool:
    """写章节内容"""
    # TODO: 调用现有的章节生成逻辑
    pass


async def auto_write_loop(
    task_id: str,
    user_id: str,
    project_id: str,
    db: AsyncSession
):
    """
    自动写作主循环

    流程：
    1. 生成1个大纲
    2. 展开为3个章节
    3. 写章节1 → 分析
    4. 写章节2 → 分析
    5. 写章节3 → 分析
    6. 检查字数 → 未达标则继续循环
    """
    tracker = TaskProgressTracker(task_id, user_id, "自动写作")

    try:
        await tracker.start("开始自动写作...")

        while True:
            # 检查是否被取消
            if tracker.check_cancelled():
                logger.info(f"自动写作任务 {task_id} 被用户取消")
                break

            # 获取项目信息
            project = await get_project(project_id, db)
            if not project:
                await tracker.error("项目不存在")
                break

            # 检查字数是否达标
            current_words = await get_project_word_count(project_id, db)
            target_words = project.target_words or 30000

            await tracker.loading(f"当前 {current_words} / {target_words} 字", current_words / target_words)

            if current_words >= target_words:
                await tracker.complete("目标字数已达成！")
                break

            # 步骤1: 生成1个大纲
            await tracker.loading("正在生成大纲...")
            outline = await generate_one_outline(project_id, user_id, db)
            if not outline:
                await tracker.error("生成大纲失败")
                break

            # 步骤2: 展开为3个章节
            await tracker.loading("正在展开大纲...")
            chapters = await expand_outline_to_chapters(outline.id, user_id, db, count=3)
            if not chapters:
                await tracker.error("展开大纲失败")
                break

            # 步骤3-5: 写章节+分析
            for i, chapter in enumerate(chapters):
                chapter_status = f"正在写章节 ({i+1}/3)..."
                await tracker.loading(chapter_status, (i * 33 + 33) / 100)

                success = await write_chapter_content(chapter.id, user_id, db)
                if not success:
                    logger.warning(f"章节 {chapter.id} 写作失败，跳过分析")
                    continue

                await tracker.loading(f"正在分析章节 ({i+1}/3)...")
                # analyze_chapter_background(chapter_id, user_id, project_id, task_id)

            # 更新进度详情
            task_result = await db.execute(select(BackgroundTask).where(BackgroundTask.id == task_id))
            task = task_result.scalar_one_or_none()
            if task:
                task.progress_details = {
                    "current_round": outline.order_index,
                    "completed_outlines": outline.order_index,
                    "completed_chapters": len(chapters)
                }
                await db.commit()

    except Exception as e:
        logger.exception(f"自动写作任务 {task_id} 异常: {e}")
        await tracker.error(str(e))
