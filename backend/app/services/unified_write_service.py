"""一键写作服务 - 生成大纲→展开章节→写内容→分析"""
import asyncio
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.outline import Outline
from app.models.chapter import Chapter
from app.models.memory import PlotAnalysis
from app.services.background_task_service import TaskProgressTracker
from app.services.plot_analyzer import PlotAnalyzer
from app.services.foreshadow_service import foreshadow_service
from app.logger import get_logger

logger = get_logger(__name__)


async def get_project(project_id: str, db: AsyncSession) -> Optional[Project]:
    """获取项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def generate_one_outline(project_id: str, user_id: str, db: AsyncSession, tracker=None):
    """生成1个大纲"""
    from app.api.outlines import continue_outline_generator
    from app.models.outline import Outline as OutlineModel

    project = await get_project(project_id, db)
    if not project:
        return None

    outlines_result = await db.execute(
        select(OutlineModel).where(OutlineModel.project_id == project_id)
    )
    existing_outlines = list(outlines_result.scalars().all())
    current_count = len(existing_outlines)

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

    if tracker:
        await tracker.loading(f"AI构思新章节...（{plot_stage}阶段）", 0.1)

    request_data = {
        "project_id": project_id,
        "chapter_count": 1,
        "mode": "continue",
        "plot_stage": plot_stage,
        "story_direction": "自然延续故事发展",
        "requirements": ""
    }

    from app.api.settings import get_user_ai_service_from_db
    user_ai_service = await get_user_ai_service_from_db(user_id, db)

    try:
        if tracker:
            await tracker.loading("AI构思中...", 0.25)
        async for _ in continue_outline_generator(
            request_data, db, user_ai_service, user_id
        ):
            pass
    except Exception as e:
        logger.warning(f"生成大纲时异常: {e}", exc_info=True)
        if tracker:
            await tracker.error(f"生成大纲失败: {e}")
        return None

    new_outlines_result = await db.execute(
        select(OutlineModel).where(OutlineModel.project_id == project_id)
    )
    new_outlines = list(new_outlines_result.scalars().all())
    if len(new_outlines) > current_count:
        if tracker:
            await tracker.loading("新章节构思完成", 0.35)
        return new_outlines[-1]
    if tracker:
        await tracker.error("生成大纲失败：大纲数量未增加")
    return None


async def expand_outline_to_chapters(outline_id: str, user_id: str, db: AsyncSession, count: int = 1, tracker=None):
    """展开大纲为指定数量章节

    对于 one-to-one 模式：每个大纲直接创建一个章节，chapter_number = outline.order_index
    对于 one-to-many 模式：调用 _run_outline_expansion_background 展开
    """
    from app.api.outlines import _run_outline_expansion_background

    outline_result = await db.execute(select(Outline).where(Outline.id == outline_id))
    outline = outline_result.scalar_one_or_none()
    if not outline:
        return []

    # 获取项目信息，判断 outline_mode
    project_result = await db.execute(select(Project).where(Project.id == outline.project_id))
    project = project_result.scalar_one_or_none()
    outline_mode = project.outline_mode if project else 'one-to-many'

    if tracker:
        await tracker.loading("规划章节结构...", 0.40)

    # 检查是否已有章节（按 outline_id 检查，避免重复创建）
    existing_chapters_result = await db.execute(
        select(Chapter)
        .where(Chapter.outline_id == outline_id)
        .order_by(Chapter.chapter_number)
    )
    existing_chapters = list(existing_chapters_result.scalars().all())

    if existing_chapters:
        logger.info(f"大纲 {outline_id} 已有 {len(existing_chapters)} 个章节，跳过展开")
        if tracker:
            await tracker.loading("章节结构规划完成（复用已有章节）", 0.50)
        return existing_chapters[:count]

    # one-to-one 模式：直接创建章节，chapter_number = outline.order_index
    if outline_mode == 'one-to-one':
        chapter = Chapter(
            project_id=outline.project_id,
            outline_id=outline_id,
            chapter_number=outline.order_index,
            sub_index=1,
            title=outline.title,
            summary=outline.content or "",
            status="draft",
            content=""
        )
        db.add(chapter)
        await db.commit()
        await db.refresh(chapter)
        logger.info(f"one-to-one 模式：为大纲 {outline_id} 创建章节 chapter_number={outline.order_index}")
        if tracker:
            await tracker.loading("章节结构规划完成", 0.50)
        return [chapter]

    # one-to-many 模式：调用展开逻辑
    data = {
        "target_chapter_count": count,
        "auto_create_chapters": True
    }

    await _run_outline_expansion_background(
        task_id=f"unified_expand_{outline_id}",
        user_id=user_id,
        outline_id=outline_id,
        data=data
    )

    if tracker:
        await tracker.loading("章节结构规划完成", 0.50)

    chapters_result = await db.execute(
        select(Chapter)
        .where(Chapter.outline_id == outline_id)
        .order_by(Chapter.sub_index)
    )
    chapters = chapters_result.scalars().all()

    return list(chapters)[:count]


async def write_chapter_content(chapter_id: str, user_id: str, db: AsyncSession, tracker=None, timeout: int = 300) -> bool:
    """写章节内容（直接在当前上下文中执行，不创建独立任务）"""
    from app.api.settings import get_user_ai_service_from_db
    from app.api.chapters import _run_chapter_generation_bg
    from app.database import get_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession as BgAsyncSession

    chapter_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = chapter_result.scalar_one_or_none()
    if not chapter:
        return False

    if chapter.content and len(chapter.content) > 100:
        logger.info(f"章节 {chapter_id} 已有内容（{chapter.word_count}字），跳过生成")
        if tracker:
            await tracker.loading(f"章节写作完成（{chapter.word_count}字）", 0.75)
        return True

    if tracker:
        await tracker.loading("开始写作...", 0.55)

    try:
        # 直接调用章节生成逻辑，不创建独立任务
        engine = await get_engine(user_id)
        AsyncSessionLocal = async_sessionmaker(engine, class_=BgAsyncSession, expire_on_commit=False)

        async with AsyncSessionLocal() as bg_db:
            bg_ai_service = await get_user_ai_service_from_db(user_id, bg_db)

            # 直接使用传入的 tracker，不创建新的（避免任务ID不存在的问题）
            await _run_chapter_generation_bg(
                task_input={
                    "chapter_id": chapter_id,
                    "style_id": None,
                    "target_word_count": 3000,
                    "enable_mcp": False,
                    "model": None,
                    "narrative_perspective": None,
                },
                db=bg_db,
                ai_service=bg_ai_service,
                tracker=tracker,  # 使用传入的 tracker
                user_id=user_id,
                task_id=None,  # 不创建新任务
            )

        # 重新查询章节获取最新状态（避免跨 session refresh 的 greenlet 问题）
        result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        updated_chapter = result.scalar_one_or_none()
        if updated_chapter and updated_chapter.content and len(updated_chapter.content) > 100:
            if tracker:
                await tracker.loading(f"章节写作完成（{updated_chapter.word_count}字）", 0.75)
            logger.info(f"章节 {chapter_id} 内容已生成，字数: {updated_chapter.word_count}")
            return True
        else:
            logger.warning(f"章节 {chapter_id} 生成后仍无内容")
            return False

    except Exception as e:
        logger.warning(f"章节 {chapter_id} 写作失败: {e}", exc_info=True)
        if tracker:
            await tracker.error(f"章节写作失败: {e}")
        return False


async def analyze_one_chapter(
    chapter_id: str,
    user_id: str,
    project_id: str,
    db: AsyncSession,
    tracker=None
) -> bool:
    """分析单个章节"""
    from app.api.settings import get_user_ai_service_from_db

    try:
        if tracker:
            await tracker.loading("开始分析章节...", 0.80)

        chapter_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        chapter = chapter_result.scalar_one_or_none()
        if not chapter:
            logger.warning(f"分析失败：章节不存在 {chapter_id}")
            return False

        if not chapter.content:
            logger.warning(f"分析失败：章节内容为空 {chapter_id}")
            return False

        if tracker:
            await tracker.loading("加载分析服务...", 0.85)

        ai_service = await get_user_ai_service_from_db(user_id, db)

        existing_foreshadows = await foreshadow_service.get_planted_foreshadows_for_analysis(
            db=db,
            project_id=project_id,
            current_chapter_number=chapter.chapter_number
        )

        if tracker:
            await tracker.loading("AI分析中...", 0.90)

        analyzer = PlotAnalyzer(ai_service)
        analysis_result = await analyzer.analyze_chapter(
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            content=chapter.content,
            word_count=chapter.word_count or len(chapter.content),
            existing_foreshadows=existing_foreshadows
        )

        if not analysis_result:
            logger.warning(f"章节 {chapter_id} AI分析失败")
            if tracker:
                await tracker.error("章节分析失败")
            return False

        if tracker:
            await tracker.loading("保存分析结果...", 0.95)

        try:
            await foreshadow_service.clean_chapter_analysis_foreshadows(
                db=db,
                project_id=project_id,
                chapter_id=chapter_id
            )
        except Exception as e:
            logger.warning(f"清理旧伏笔失败: {e}")

        existing_result = await db.execute(
            select(PlotAnalysis).where(PlotAnalysis.chapter_id == chapter_id)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.plot_stage = analysis_result.get('plot_stage', '发展')
            existing.conflict_level = analysis_result.get('conflict', {}).get('level', 0)
            existing.conflict_types = analysis_result.get('conflict', {}).get('types', [])
            existing.emotional_tone = analysis_result.get('emotional_arc', {}).get('primary_emotion', '')
            existing.emotional_intensity = analysis_result.get('emotional_arc', {}).get('intensity', 0) / 10.0
            existing.hooks = analysis_result.get('hooks', [])
            existing.hooks_count = len(analysis_result.get('hooks', []))
            existing.foreshadows = analysis_result.get('foreshadows', [])
            existing.foreshadows_planted = sum(1 for f in analysis_result.get('foreshadows', []) if f.get('type') == 'planted')
            existing.foreshadows_resolved = sum(1 for f in analysis_result.get('foreshadows', []) if f.get('type') == 'resolved')
            existing.plot_points = analysis_result.get('plot_points', [])
            existing.plot_points_count = len(analysis_result.get('plot_points', []))
            existing.character_states = analysis_result.get('character_states', [])
            existing.scenes = analysis_result.get('scenes', [])
            existing.pacing = analysis_result.get('pacing', 'moderate')
            existing.overall_quality_score = analysis_result.get('scores', {}).get('overall', 0)
            existing.pacing_score = analysis_result.get('scores', {}).get('pacing', 0)
            existing.engagement_score = analysis_result.get('scores', {}).get('engagement', 0)
            existing.coherence_score = analysis_result.get('scores', {}).get('coherence', 0)
            existing.analysis_report = analyzer.generate_analysis_summary(analysis_result)
            existing.suggestions = analysis_result.get('suggestions', [])
            existing.dialogue_ratio = analysis_result.get('dialogue_ratio', 0)
            existing.description_ratio = analysis_result.get('description_ratio', 0)
        else:
            plot_analysis = PlotAnalysis(
                chapter_id=chapter_id,
                project_id=project_id,
                plot_stage=analysis_result.get('plot_stage', '发展'),
                conflict_level=analysis_result.get('conflict', {}).get('level', 0),
                conflict_types=analysis_result.get('conflict', {}).get('types', []),
                emotional_tone=analysis_result.get('emotional_arc', {}).get('primary_emotion', ''),
                emotional_intensity=analysis_result.get('emotional_arc', {}).get('intensity', 0) / 10.0,
                hooks=analysis_result.get('hooks', []),
                hooks_count=len(analysis_result.get('hooks', [])),
                foreshadows=analysis_result.get('foreshadows', []),
                foreshadows_planted=sum(1 for f in analysis_result.get('foreshadows', []) if f.get('type') == 'planted'),
                foreshadows_resolved=sum(1 for f in analysis_result.get('foreshadows', []) if f.get('type') == 'resolved'),
                plot_points=analysis_result.get('plot_points', []),
                plot_points_count=len(analysis_result.get('plot_points', [])),
                character_states=analysis_result.get('character_states', []),
                scenes=analysis_result.get('scenes', []),
                pacing=analysis_result.get('pacing', 'moderate'),
                overall_quality_score=analysis_result.get('scores', {}).get('overall', 0),
                pacing_score=analysis_result.get('scores', {}).get('pacing', 0),
                engagement_score=analysis_result.get('scores', {}).get('engagement', 0),
                coherence_score=analysis_result.get('scores', {}).get('coherence', 0),
                analysis_report=analyzer.generate_analysis_summary(analysis_result),
                suggestions=analysis_result.get('suggestions', []),
                dialogue_ratio=analysis_result.get('dialogue_ratio', 0),
                description_ratio=analysis_result.get('description_ratio', 0)
            )
            db.add(plot_analysis)

        await db.commit()

        if tracker:
            await tracker.loading("章节分析完成", 1.0)

        logger.info(f"章节 {chapter_id} 分析完成")
        return True

    except Exception as e:
        logger.warning(f"章节 {chapter_id} 分析失败: {e}", exc_info=True)
        if tracker:
            await tracker.error(f"章节分析失败: {e}")
        return False


async def unified_write_loop(
    task_id: str,
    user_id: str,
    project_id: str,
    chapters_per_outline: int = 1,
    db: AsyncSession = None
):
    """
    一键写作主流程：生成大纲→展开章节→写内容→分析

    所有步骤在同一个后台任务中完成。
    """
    tracker = TaskProgressTracker(task_id, user_id, "一键写作")

    try:
        await tracker.start("开始一键写作...")
        logger.info(f"[{task_id}] unified_write_loop 开始")

        # 检查是否被取消
        is_cancelled = await tracker.check_cancelled()
        if is_cancelled:
            logger.info(f"一键写作任务 {task_id} 被用户取消")
            return

        # 步骤1: 生成大纲 (0-35%)
        # 注意：one-to-one 模式下，每个大纲对应一个章节，需要生成 chapters_per_outline 个大纲
        logger.info(f"[{task_id}] 步骤1: 生成 {chapters_per_outline} 个大纲")
        all_chapters = []
        for i in range(chapters_per_outline):
            outline = await generate_one_outline(project_id, user_id, db, tracker=tracker)
            if not outline:
                logger.warning(f"[{task_id}] 第 {i+1} 个大纲生成失败，跳过")
                continue
            logger.info(f"[{task_id}] 大纲 {i+1}/{chapters_per_outline} 生成成功: {outline.id}, {outline.title}")

            # 检查是否被取消
            is_cancelled = await tracker.check_cancelled()
            if is_cancelled:
                logger.info(f"一键写作任务 {task_id} 被用户取消")
                return

            # 步骤2: 展开为章节 (35-50%)
            logger.info(f"[{task_id}] 步骤2: 展开大纲 {outline.id}")
            chapters = await expand_outline_to_chapters(outline.id, user_id, db, count=1, tracker=tracker)
            if not chapters:
                logger.warning(f"[{task_id}] 大纲 {outline.id} 展开章节失败，跳过")
                continue
            all_chapters.extend(chapters)
            logger.info(f"[{task_id}] 章节展开成功: {[c.id for c in chapters]}")

        if not all_chapters:
            await tracker.error("所有大纲生成和展开均失败")
            return

        logger.info(f"[{task_id}] 共生成 {len(all_chapters)} 个章节")

        # 步骤3-4: 写章节+分析
        for i, chapter in enumerate(all_chapters):
            chapter_progress = 0.50 + (i / len(all_chapters)) * 0.25
            logger.info(f"[{task_id}] 步骤3-{i+1}: 写章节 {chapter.id}")

            # 检查是否被取消
            is_cancelled = await tracker.check_cancelled()
            if is_cancelled:
                logger.info(f"一键写作任务 {task_id} 被用户取消")
                return

            success = await write_chapter_content(chapter.id, user_id, db, tracker=tracker)
            if not success:
                logger.warning(f"章节 {chapter.id} 写作失败，跳过分析")
                continue

            logger.info(f"[{task_id}] 章节 {chapter.id} 写作完成")

            # 检查是否被取消
            is_cancelled = await tracker.check_cancelled()
            if is_cancelled:
                logger.info(f"一键写作任务 {task_id} 被用户取消")
                return

            logger.info(f"[{task_id}] 步骤4-{i+1}: 分析章节 {chapter.id}")
            analysis_success = await analyze_one_chapter(
                chapter.id, user_id, project_id, db, tracker=tracker
            )
            if not analysis_success:
                logger.warning(f"章节 {chapter.id} 分析失败")
                continue

            logger.info(f"[{task_id}] 章节 {chapter.id} 分析完成")

        await tracker.complete("一键写作完成！")
        logger.info(f"[{task_id}] unified_write_loop 完成")

    except Exception as e:
        logger.exception(f"一键写作任务 {task_id} 异常: {e}")
        await tracker.error(str(e))
