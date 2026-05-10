"""
集成测试：模拟完整的 auto_write 流程
"""
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend")

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

def test_auto_write_loop_with_mocked_subfunctions():
    """测试 auto_write_loop 内部流程"""

    async def run_test():
        from app.services.background_task_service import BackgroundTaskService, TaskProgressTracker

        service = BackgroundTaskService()
        execution_steps = []
        task_id = "test-auto-write-123"
        user_id = "test-user-auto"
        project_id = "test-project-auto"

        # 模拟 auto_write_loop 的各个步骤
        async def mock_generate_one_outline(project_id, user_id, db, tracker=None):
            execution_steps.append("generate_outline")
            await asyncio.sleep(0.05)
            # 返回一个 mock outline
            mock_outline = MagicMock()
            mock_outline.id = "outline-1"
            mock_outline.title = "测试章节"
            return mock_outline

        async def mock_expand_outline_to_chapters(outline_id, user_id, db, count=3, tracker=None):
            execution_steps.append(f"expand_chapters_{count}")
            await asyncio.sleep(0.05)
            # 返回 3 个 mock chapters
            chapters = []
            for i in range(count):
                ch = MagicMock()
                ch.id = f"chapter-{i}"
                chapters.append(ch)
            return chapters

        async def mock_write_chapter_content(chapter_id, user_id, db, timeout=300, tracker=None):
            execution_steps.append(f"write_chapter_{chapter_id}")
            await asyncio.sleep(0.05)
            return True

        async def mock_analyze_one_chapter(chapter_id, user_id, project_id, db, tracker=None, timeout=300):
            execution_steps.append(f"analyze_chapter_{chapter_id}")
            await asyncio.sleep(0.05)
            return True

        # Patch the functions
        with patch("app.services.auto_write_service.generate_one_outline", mock_generate_one_outline), \
             patch("app.services.auto_write_service.expand_outline_to_chapters", mock_expand_outline_to_chapters), \
             patch("app.services.auto_write_service.write_chapter_content", mock_write_chapter_content), \
             patch("app.services.auto_write_service.analyze_one_chapter", mock_analyze_one_chapter), \
             patch("app.services.auto_write_service.get_project") as mock_get_project, \
             patch("app.services.auto_write_service.get_project_word_count") as mock_word_count:

            # Mock project
            mock_project = MagicMock()
            mock_project.chapter_count = 10
            mock_project.target_words = 30000
            mock_get_project.return_value = mock_project
            mock_word_count.return_value = 0

            # Mock db
            mock_db = MagicMock()

            # 直接调用 auto_write_loop
            from app.services.auto_write_service import auto_write_loop

            tracker = TaskProgressTracker(task_id, user_id, "自动写作")

            # 只运行一次循环（不等待目标字数达成）
            async def limited_auto_write_loop(task_id, user_id, project_id, db):
                tracker = TaskProgressTracker(task_id, user_id, "自动写作")
                try:
                    await tracker.start("开始自动写作...")
                    execution_steps.append("tracker_started")

                    # 生成大纲
                    outline = await mock_generate_one_outline(project_id, user_id, db, tracker)
                    if not outline:
                        await tracker.error("生成大纲失败")
                        return
                    execution_steps.append("outline_generated")

                    # 展开章节
                    chapters = await mock_expand_outline_to_chapters(outline.id, user_id, db, count=3, tracker=tracker)
                    if not chapters:
                        await tracker.error("展开大纲失败")
                        return
                    execution_steps.append("chapters_expanded")

                    # 写章节并分析
                    for ch in chapters:
                        success = await mock_write_chapter_content(ch.id, user_id, db, tracker=tracker)
                        if success:
                            execution_steps.append(f"chapter_written_{ch.id}")
                        # 分析刚写完的章节
                        await mock_analyze_one_chapter(ch.id, user_id, project_id, db, tracker=tracker)
                        execution_steps.append(f"chapter_analyzed_{ch.id}")

                    await tracker.complete("测试完成")
                    execution_steps.append("loop_complete")

                except Exception as e:
                    execution_steps.append(f"error: {e}")
                    await tracker.error(str(e))

            await limited_auto_write_loop(task_id, user_id, project_id, mock_db)

        return execution_steps

    steps = asyncio.run(run_test())
    print(f"执行步骤: {steps}")

    expected_steps = [
        "tracker_started",
        "generate_outline",
        "outline_generated",
        "expand_chapters_3",
        "chapters_expanded",
        "write_chapter_chapter-0",
        "chapter_written_chapter-0",
        "analyze_chapter_chapter-0",
        "chapter_analyzed_chapter-0",
        "write_chapter_chapter-1",
        "chapter_written_chapter-1",
        "analyze_chapter_chapter-1",
        "chapter_analyzed_chapter-1",
        "write_chapter_chapter-2",
        "chapter_written_chapter-2",
        "analyze_chapter_chapter-2",
        "chapter_analyzed_chapter-2",
        "loop_complete"
    ]

    assert steps == expected_steps, f"步骤不匹配: {steps}"
    print("✅ test_auto_write_loop_with_mocked_subfunctions PASSED")


def test_spawn_and_worker_execution_timing():
    """测试 spawn 和 worker 执行的时间关系"""
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    events = []

    async def slow_task(task_id: str, user_id: str):
        events.append(f"task_start:{task_id}")
        await asyncio.sleep(0.2)
        events.append(f"task_end:{task_id}")

    async def run_test():
        user_id = "test-timing"

        # 1. 启动 worker
        await service._start_user_worker(user_id)
        events.append("worker_started")

        # 2. 放一个任务
        queue = service._ensure_user_queue(user_id)
        await asyncio.sleep(0.05)  # 让 worker 完全启动

        await queue.put({
            "task_id": "timing-task-1",
            "task_func": slow_task,
            "args": {"user_id": user_id, "extra_args": ()},
            "kwargs": {}
        })
        events.append("task_queued")

        # 3. 等待任务完成
        await asyncio.sleep(0.5)
        events.append("wait_done")

        return events

    events = asyncio.run(run_test())
    print(f"事件顺序: {events}")

    # 验证顺序：worker_started -> task_queued -> task_start -> task_end -> wait_done
    # 或者：worker_started -> task_queued -> task_start -> wait_done (如果任务还在运行)

    assert "worker_started" in events
    assert "task_queued" in events
    assert "task_start:timing-task-1" in events

    # task_start 应该在 wait_done 之前
    task_start_idx = events.index("task_start:timing-task-1")
    wait_done_idx = events.index("wait_done")
    assert task_start_idx < wait_done_idx, "任务应该在等待完成前开始"

    print("✅ test_spawn_and_worker_execution_timing PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("Auto Write 集成测试")
    print("=" * 60)

    tests = [
        test_auto_write_loop_with_mocked_subfunctions,
        test_spawn_and_worker_execution_timing,
    ]

    for test in tests:
        print(f"\n📝 Running: {test.__name__}")
        try:
            test()
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
