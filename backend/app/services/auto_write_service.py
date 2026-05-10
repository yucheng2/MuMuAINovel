import asyncio
import logging
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.outline import Outline
from app.models.chapter import Chapter
from app.models.background_task import BackgroundTask
from app.models.analysis_task import AnalysisTask
from app.models.memory import PlotAnalysis
from app.services.background_task_service import TaskProgressTracker, background_task_service
from app.services.ai_service import AIService
from app.services.plot_analyzer import PlotAnalyzer
from app.services.foreshadow_service import foreshadow_service
from app.database import get_engine

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


async def generate_one_outline(project_id: str, user_id: str, db: AsyncSession, tracker=None):
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

    # 向 tracker 报告阶段
    if tracker:
        logger.info(f"[{tracker.task_id}] generate_one_outline: 调用 tracker.loading AI构思新章节")
        await tracker.loading(f"AI构思新章节...（{plot_stage}阶段）", 0.1)

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
    from app.api.settings import get_user_ai_service_from_db
    user_ai_service = await get_user_ai_service_from_db(user_id, db)

    # consume the generator to trigger actual generation
    try:
        if tracker:
            await tracker.loading("AI构思中...", 0.3)
        async for _ in continue_outline_generator(
            request_data, db, user_ai_service, user_id
        ):
            pass  # SSE events are already handled inside the generator (commits/db operations)
    except Exception as e:
        logger.warning(f"生成大纲时异常: {e}", exc_info=True)
        if tracker:
            await tracker.error(f"生成大纲失败: {e}")
        return None

    # 返回生成的大纲
    new_outlines_result = await db.execute(
        select(OutlineModel).where(OutlineModel.project_id == project_id)
    )
    new_outlines = list(new_outlines_result.scalars().all())
    if len(new_outlines) > current_count:
        if tracker:
            await tracker.loading("新章节构思完成", 0.5)
        return new_outlines[-1]  # 返回最新的大纲
    if tracker:
        await tracker.error("生成大纲失败：大纲数量未增加")
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


async def expand_outline_to_chapters(outline_id: str, user_id: str, db: AsyncSession, count: int = 3, tracker=None):
    """展开大纲为指定数量章节"""
    from app.api.outlines import _run_outline_expansion_background

    outline_result = await db.execute(select(Outline).where(Outline.id == outline_id))
    outline = outline_result.scalar_one_or_none()
    if not outline:
        return []

    if tracker:
        await tracker.loading("规划章节结构...", 0.55)

    # 检查是否已有章节（避免重复创建）
    existing_chapters_result = await db.execute(
        select(Chapter)
        .where(Chapter.outline_id == outline_id)
        .order_by(Chapter.chapter_number)
    )
    existing_chapters = list(existing_chapters_result.scalars().all())

    if existing_chapters:
        logger.info(f"大纲 {outline_id} 已有 {len(existing_chapters)} 个章节，跳过展开")
        if tracker:
            await tracker.loading("章节结构规划完成（复用已有章节）", 0.65)
        return existing_chapters[:count]

    # 调用现有的展开逻辑
    data = {
        "target_chapter_count": count,
        "auto_create_chapters": True
    }

    # 同步调用展开函数
    await _run_outline_expansion_background(
        task_id=f"auto_write_expand_{outline_id}",
        user_id=user_id,
        outline_id=outline_id,
        data=data
    )

    if tracker:
        await tracker.loading("章节结构规划完成", 0.65)

    # 获取生成的章节
    chapters_result = await db.execute(
        select(Chapter)
        .where(Chapter.outline_id == outline_id)
        .order_by(Chapter.sub_index)
    )
    chapters = chapters_result.scalars().all()

    return list(chapters)[:count]


async def write_chapter_content(chapter_id: str, user_id: str, db: AsyncSession, timeout: int = 300, tracker=None) -> bool:
    """写章节内容（同步等待生成完成）"""
    from app.services.background_task_service import background_task_service, TaskProgressTracker
    from app.database import get_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession as BgAsyncSession

    chapter_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = chapter_result.scalar_one_or_none()
    if not chapter:
        return False

    # 如果章节已有内容，跳过生成
    if chapter.content and len(chapter.content) > 100:
        logger.info(f"章节 {chapter_id} 已有内容（{chapter.word_count}字），跳过生成")
        if tracker:
            await tracker.loading(f"章节写作完成（{chapter.word_count}字）", 0.85)
        return True

    if tracker:
        await tracker.loading("开始写作...", 0.66)

    try:
        # 创建任务
        task = await background_task_service.create_task(
            user_id=user_id,
            project_id=chapter.project_id,
            task_type="chapter_generate",
            task_input={
                "chapter_id": chapter_id,
                "style_id": None,
                "target_word_count": 3000,
                "enable_mcp": False,
                "model": None,
                "narrative_perspective": None,
            },
            db=db
        )

        # 后台执行函数
        async def _run_chapter_generation(task_id: str, bg_user_id: str):
            from app.api.settings import get_user_ai_service_from_db
            from app.api.chapters import _run_chapter_generation_bg

            engine = await get_engine(bg_user_id)
            AsyncSessionLocal = async_sessionmaker(engine, class_=BgAsyncSession, expire_on_commit=False)

            async with AsyncSessionLocal() as bg_db:
                inner_tracker = TaskProgressTracker(task_id, bg_user_id, "章节")
                try:
                    await inner_tracker.start()
                    bg_ai_service = await get_user_ai_service_from_db(bg_user_id, bg_db)
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
                        tracker=inner_tracker,
                        user_id=bg_user_id,
                        task_id=task_id,
                    )
                except Exception as e:
                    logger.error(f"后台章节生成失败: {e}", exc_info=True)
                    await inner_tracker.error(str(e))

        # 启动后台任务（不等待完成）
        if tracker:
            await tracker.loading("AI写作中...", 0.70)
        await background_task_service.spawn_background_task(
            task.id, user_id, _run_chapter_generation
        )

        # 轮询等待任务完成
        start_time = asyncio.get_event_loop().time()
        poll_count = 0
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            poll_count += 1
            if poll_count % 12 == 0:  # 每分钟打印一次
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                logger.info(f"等待章节 {chapter_id} 生成中... 已等待 {elapsed} 秒")

            # 向主 tracker 报告进度
            if tracker and poll_count % 4 == 0:  # 每约20秒
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                await tracker.loading(f"写作中...（已等待 {elapsed} 秒）", 0.75)

            # 刷新章节数据
            await db.refresh(chapter)
            if chapter.content and len(chapter.content) > 100:
                if tracker:
                    await tracker.loading(f"章节写作完成（{chapter.word_count}字）", 0.85)
                logger.info(f"章节 {chapter_id} 内容已生成，字数: {chapter.word_count}")
                return True

            # 检查任务状态
            task_result = await db.execute(
                select(BackgroundTask).where(BackgroundTask.id == task.id)
            )
            db_task = task_result.scalar_one_or_none()
            if db_task and db_task.status == "failed":
                logger.warning(f"章节 {chapter_id} 生成失败: {db_task.status_message}")
                if tracker:
                    await tracker.error(f"章节写作失败: {db_task.status_message}")
                return False

            await asyncio.sleep(5)

        logger.warning(f"章节 {chapter_id} 生成超时（{timeout}秒）")
        if tracker:
            await tracker.error(f"章节写作超时（{timeout}秒）")
        return False
    except Exception as e:
        logger.warning(f"章节 {chapter_id} 写作失败: {e}")
        if tracker:
            await tracker.error(f"章节写作失败: {e}")
        return False


async def analyze_one_chapter(
    chapter_id: str,
    user_id: str,
    project_id: str,
    db: AsyncSession,
    tracker=None,
    timeout: int = 300
) -> bool:
    """
    分析单个章节（同步等待分析完成）

    流程：
    1. 获取章节信息和AI服务
    2. 获取已埋入的伏笔列表
    3. 使用PlotAnalyzer分析章节
    4. 保存分析结果到数据库
    """
    from app.api.settings import get_user_ai_service_from_db
    from datetime import datetime

    try:
        if tracker:
            await tracker.loading("开始分析章节...", 0.86)

        # 获取章节信息
        chapter_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        chapter = chapter_result.scalar_one_or_none()
        if not chapter:
            logger.warning(f"分析失败：章节不存在 {chapter_id}")
            return False

        if not chapter.content:
            logger.warning(f"分析失败：章节内容为空 {chapter_id}")
            return False

        if tracker:
            await tracker.loading("加载分析服务...", 0.88)

        # 获取AI服务
        ai_service = await get_user_ai_service_from_db(user_id, db)

        # 获取已埋入的伏笔列表
        existing_foreshadows = await foreshadow_service.get_planted_foreshadows_for_analysis(
            db=db,
            project_id=project_id,
            current_chapter_number=chapter.chapter_number
        )

        if tracker:
            await tracker.loading("AI分析中...", 0.90)

        # 执行分析
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

        # 保存分析结果
        from app.models.memory import PlotAnalysis

        # 清理旧的分析伏笔
        try:
            await foreshadow_service.clean_chapter_analysis_foreshadows(
                db=db,
                project_id=project_id,
                chapter_id=chapter_id
            )
        except Exception as e:
            logger.warning(f"清理旧伏笔失败: {e}")

        # 检查是否已有分析记录
        existing_result = await db.execute(
            select(PlotAnalysis).where(PlotAnalysis.chapter_id == chapter_id)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            # 更新现有记录
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
            # 创建新记录
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
            await tracker.loading(f"章节分析完成", 1.0)

        logger.info(f"章节 {chapter_id} 分析完成")
        return True

    except Exception as e:
        logger.warning(f"章节 {chapter_id} 分析失败: {e}", exc_info=True)
        if tracker:
            await tracker.error(f"章节分析失败: {e}")
        return False


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
        logger.info(f"[{task_id}] auto_write_loop 开始，tracker 已初始化")

        while True:
            # 检查是否被取消
            is_cancelled = await tracker.check_cancelled()
            logger.info(f"[{task_id}] 检查取消状态: is_cancelled={is_cancelled}")
            if is_cancelled:
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

            progress = min(current_words / target_words, 0.99) if target_words > 0 else 0
            await tracker.loading(f"当前 {current_words} / {target_words} 字", progress)

            if current_words >= target_words:
                await tracker.complete("目标字数已达成！")
                break

            # 步骤1: 生成1个大纲
            logger.info(f"[{task_id}] 步骤1: 开始生成大纲")
            outline = await generate_one_outline(project_id, user_id, db, tracker=tracker)
            if not outline:
                logger.warning(f"[{task_id}] 生成大纲返回 None，标记失败")
                await tracker.error("生成大纲失败")
                break
            logger.info(f"[{task_id}] 大纲生成成功: {outline.id}, {outline.title}")

            # 步骤2: 展开为3个章节
            logger.info(f"[{task_id}] 步骤2: 开始展开大纲")
            chapters = await expand_outline_to_chapters(outline.id, user_id, db, count=3, tracker=tracker)
            if not chapters:
                logger.warning(f"[{task_id}] 展开大纲返回空列表，标记失败")
                await tracker.error("展开大纲失败")
                break
            logger.info(f"[{task_id}] 章节展开成功: {[c.id for c in chapters]}")

            # 步骤3-5: 写章节+分析
            for i, chapter in enumerate(chapters):
                chapter_status = f"正在写章节 ({i+1}/3)..."
                logger.info(f"[{task_id}] 步骤3-{i+1}: {chapter_status}")

                success = await write_chapter_content(chapter.id, user_id, db, tracker=tracker)
                if not success:
                    logger.warning(f"章节 {chapter.id} 写作失败，跳过分析")
                    continue

                logger.info(f"[{task_id}] 章节 {chapter.id} 写作完成")

                # 步骤4: 分析刚写完的章节
                analysis_status = f"正在分析章节 ({i+1}/3)..."
                logger.info(f"[{task_id}] 步骤4-{i+1}: {analysis_status}")

                analysis_success = await analyze_one_chapter(
                    chapter.id, user_id, project_id, db, tracker=tracker
                )
                if not analysis_success:
                    logger.warning(f"章节 {chapter.id} 分析失败，继续下一章节")
                    continue

                logger.info(f"[{task_id}] 章节 {chapter.id} 分析完成")

    except Exception as e:
        logger.exception(f"自动写作任务 {task_id} 异常: {e}")
        await tracker.error(str(e))
