"""
诊断测试：追踪 auto_write 任务的完整生命周期
"""
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend")

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

def test_auto_write_loop_cancellation_flow():
    """
    测试 auto_write_loop 的取消流程，追踪 cancel_requested 状态
    """
    from app.services.background_task_service import BackgroundTaskService, TaskProgressTracker
    from app.services.auto_write_service import auto_write_loop
    from app.database import get_engine
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from app.models.background_task import BackgroundTask

    async def run_test():
        service = BackgroundTaskService()
        user_id = "test-cancel-user"
        project_id = "test-project-cancel"
        task_id = "test-task-cancel-123"

        # 1. 创建任务
        print("[1] 创建任务记录...")
        engine = await get_engine(user_id)
        AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with AsyncSessionLocal() as session:
            task = BackgroundTask(
                user_id=user_id,
                project_id=project_id,
                task_type="auto_write",
                task_input={"project_id": project_id},
                status="pending",
                progress=0,
                status_message="任务已创建"
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            actual_task_id = task.id
            print(f"[1] 任务已创建: {actual_task_id}, cancel_requested={task.cancel_requested}")

        # 2. 验证 cancel_requested 是 False
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == actual_task_id)
            )
            t = result.scalar_one()
            print(f"[2] 数据库验证: cancel_requested={t.cancel_requested}, status={t.status}")
            assert t.cancel_requested == False, "新任务应该有 cancel_requested=False"
            assert t.status == "pending", "新任务应该有 status=pending"

        # 3. 模拟 spawn_background_task 更新状态为 "即将开始执行..."
        print("[3] 模拟 spawn_background_task 更新状态...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == actual_task_id)
            )
            t = result.scalar_one()
            t.status_message = "即将开始执行..."
            t.progress_details = {"stage": "queued", "queue_size": 0}
            await session.commit()

        # 4. 创建 tracker 并调用 start()
        print("[4] 创建 TaskProgressTracker 并调用 start()...")
        tracker = TaskProgressTracker(actual_task_id, user_id, "自动写作")
        await tracker.start("开始自动写作...")

        # 5. 验证 tracker.start() 后任务状态
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == actual_task_id)
            )
            t = result.scalar_one()
            print(f"[5] tracker.start() 后: status={t.status}, cancel_requested={t.cancel_requested}")

        # 6. 第一次检查 check_cancelled()
        print("[6] 第一次调用 check_cancelled()...")
        is_cancelled = await tracker.check_cancelled()
        print(f"[6] check_cancelled() 返回: {is_cancelled}")
        assert is_cancelled == False, "check_cancelled() 应该返回 False"

        # 7. 模拟用户取消任务
        print("[7] 模拟 stop_auto_write_task...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == actual_task_id)
            )
            t = result.scalar_one()
            t.cancel_requested = True
            t.status = "cancelled"
            t.status_message = "任务已取消"
            await session.commit()
            print(f"[7] 取消后: cancel_requested={t.cancel_requested}, status={t.status}")

        # 8. 再次检查 check_cancelled()
        print("[8] 第二次调用 check_cancelled()...")
        is_cancelled = await tracker.check_cancelled()
        print(f"[8] check_cancelled() 返回: {is_cancelled}")
        assert is_cancelled == True, "check_cancelled() 应该返回 True"

        print("\n✅ 测试通过！cancel_requested 状态变化符合预期")

    asyncio.run(run_test())


def test_auto_write_loop_with_real_logic():
    """
    测试 auto_write_loop 在真实逻辑下的行为
    使用 mock 来避免实际的 AI 调用
    """
    from app.services.background_task_service import TaskProgressTracker

    async def run_test():
        task_id = "test-loop-123"
        user_id = "test-user-loop"
        project_id = "test-project-loop"

        # Mock get_project
        mock_project = MagicMock()
        mock_project.chapter_count = 10
        mock_project.target_words = 30000

        # Mock db
        mock_db = MagicMock()

        # Mock tracker
        tracker = TaskProgressTracker(task_id, user_id, "自动写作")
        await tracker.start("开始自动写作...")

        # 检查 cancel_requested
        is_cancelled = await tracker.check_cancelled()
        print(f"初始 check_cancelled(): {is_cancelled}")

        # 模拟 auto_write_loop 第一次迭代
        print("模拟 auto_write_loop 第一次迭代:")
        print(f"  - tracker.start() 已调用")
        print(f"  - 即将调用 check_cancelled()...")
        is_cancelled = await tracker.check_cancelled()
        print(f"  - check_cancelled() 返回: {is_cancelled}")

        if is_cancelled:
            print("  -> 循环终止（任务被取消）")
        else:
            print("  -> 继续执行...")

    asyncio.run(run_test())


if __name__ == "__main__":
    print("=" * 60)
    print("Auto Write 取消流程诊断测试")
    print("=" * 60)

    tests = [
        test_auto_write_loop_cancellation_flow,
        test_auto_write_loop_with_real_logic,
    ]

    for test in tests:
        print(f"\n📝 Running: {test.__name__}")
        try:
            test()
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()