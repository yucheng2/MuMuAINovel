"""
诊断测试：模拟完整的 spawn_background_task 流程
"""
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend")

import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch

def test_spawn_background_task_full_flow():
    """模拟完整的 spawn_background_task 流程"""
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    task_executed = False

    async def mock_task_func(task_id: str, user_id: str):
        nonlocal task_executed
        print(f"  [mock_task] 开始执行, task_id={task_id}")
        task_executed = True
        await asyncio.sleep(0.1)
        print(f"  [mock_task] 执行完成, task_id={task_id}")

    async def run_test():
        nonlocal task_executed

        task_id = "test-full-flow-123"
        user_id = "test-user-full"

        print(f"1. 创建任务记录...")
        # 模拟任务创建
        from app.models.background_task import BackgroundTask
        with patch.object(service, 'create_task', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(id=task_id, status="pending")
            print(f"2. 调用 spawn_background_task...")
            await service.spawn_background_task(
                task_id=task_id,
                user_id=user_id,
                task_func=mock_task_func,
                task_type=None
            )
            print(f"3. spawn_background_task 返回，队列状态: {service._user_queues.get(user_id)}")

            # 给一些时间让 worker 启动并执行
            print(f"4. 等待任务执行...")
            for i in range(10):
                await asyncio.sleep(0.1)
                if task_executed:
                    print(f"5. 任务已执行!")
                    break

            return task_executed

    executed = asyncio.run(run_test())
    assert executed, "任务未被执行"
    print("✅ test_spawn_background_task_full_flow PASSED")


def test_worker_runs_without_uvicorn():
    """验证 worker 在独立的 event loop 中能正常运行"""
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    execution_log = []

    async def numbered_task(task_id: str, user_id: str, num: int):
        execution_log.append(f"start-{num}")
        await asyncio.sleep(0.05)
        execution_log.append(f"end-{num}")

    async def run_test():
        user_id = "test-isolated"
        queue = service._ensure_user_queue(user_id)

        # 直接启动 worker
        await service._start_user_worker(user_id)
        await asyncio.sleep(0.1)  # 让 worker 完全启动

        # 放入任务
        for i in range(3):
            await queue.put({
                "task_id": f"task-{i}",
                "task_func": numbered_task,
                "args": {"user_id": user_id, "extra_args": ()},
                "kwargs": {"num": i},
            })

        # 等待执行
        await asyncio.sleep(0.5)
        return execution_log

    log = asyncio.run(run_test())
    print(f"执行日志: {log}")
    expected = ["start-0", "end-0", "start-1", "end-1", "start-2", "end-2"]
    assert log == expected, f"执行顺序不对: {log}"
    print("✅ test_worker_runs_without_uvicorn PASSED")


def test_multiple_spawns_same_user():
    """验证同一用户多次调用 spawn 不会重复启动 worker"""
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    worker_started_count = 0

    async def counting_task(task_id: str, user_id: str):
        nonlocal worker_started_count
        await asyncio.sleep(0.01)

    async def run_test():
        nonlocal worker_started_count

        user_id = "test-multi-spawn"

        # 模拟多次 spawn
        for i in range(3):
            queue = service._ensure_user_queue(user_id)
            # 覆盖 _start_user_worker 来计数
            original_start = service._start_user_worker
            async def counting_start(uid):
                nonlocal worker_started_count
                worker_started_count += 1
                await original_start(uid)
            service._start_user_worker = counting_start

            await service._start_user_worker(user_id)
            await asyncio.sleep(0.05)

        return worker_started_count

    count = asyncio.run(run_test())
    print(f"worker 启动次数: {count}")
    # Worker 应该只启动一次
    assert count == 1, f"worker 应该只启动 1 次，实际: {count}"
    print("✅ test_multiple_spawns_same_user PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("Worker Spawn 诊断测试")
    print("=" * 60)

    tests = [
        test_worker_runs_without_uvicorn,
        test_multiple_spawns_same_user,
        test_spawn_background_task_full_flow,
    ]

    for test in tests:
        print(f"\n📝 Running: {test.__name__}")
        try:
            test()
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
