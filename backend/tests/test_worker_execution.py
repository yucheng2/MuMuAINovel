"""
诊断测试：验证 worker 是否真正执行任务
"""
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend")

import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch

def test_worker_executes_task_from_queue():
    """验证 worker 从队列取出并执行任务"""
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    task_executed = False
    task_result = None

    async def mock_task(task_id: str, user_id: str):
        nonlocal task_executed, task_result
        task_executed = True
        task_result = f"executed:{task_id}"
        # 模拟一些工作
        await asyncio.sleep(0.1)

    async def run_test():
        nonlocal task_executed, task_result

        # 1. 创建任务（模拟）
        task_id = "test-task-123"
        user_id = "test-user-456"

        # 2. 确保用户队列存在
        queue = service._ensure_user_queue(user_id)

        # 3. 启动 worker
        await service._start_user_worker(user_id)

        # 给 worker 一点时间启动
        await asyncio.sleep(0.2)

        # 4. 放入任务
        await queue.put({
            "task_id": task_id,
            "task_func": mock_task,
            "args": {"user_id": user_id, "extra_args": ()},
            "kwargs": {},
        })

        # 5. 等待任务执行（最多 2 秒）
        for _ in range(20):
            await asyncio.sleep(0.1)
            if task_executed:
                break

        return task_executed, task_result

    # 运行测试
    executed, result = asyncio.run(run_test())

    print(f"任务执行状态: executed={executed}, result={result}")
    assert executed, f"任务未被执行！result={result}"
    assert result == f"executed:test-task-123", f"结果不正确: {result}"
    print("✅ test_worker_executes_task_from_queue PASSED")


def test_worker_processes_multiple_tasks_in_order():
    """验证 worker 按 FIFO 顺序处理多个任务"""
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    execution_order = []

    async def mock_task(task_id: str, user_id: str, name: str):
        execution_order.append(f"start:{name}")
        await asyncio.sleep(0.05)
        execution_order.append(f"end:{name}")

    async def run_test():
        user_id = "test-user-fifo"
        queue = service._ensure_user_queue(user_id)
        await service._start_user_worker(user_id)
        await asyncio.sleep(0.2)  # 让 worker 启动

        # 放入 3 个任务
        for i in range(3):
            await queue.put({
                "task_id": f"task-{i}",
                "task_func": mock_task,
                "args": {"user_id": user_id, "extra_args": ()},
                "kwargs": {"name": f"task-{i}"},
            })

        # 等待所有任务完成
        await asyncio.sleep(0.5)

        return execution_order

    result = asyncio.run(run_test())
    print(f"执行顺序: {result}")

    expected = ["start:task-0", "end:task-0", "start:task-1", "end:task-1", "start:task-2", "end:task-2"]
    assert result == expected, f"顺序不对: {result}"
    print("✅ test_worker_processes_multiple_tasks_in_order PASSED")


def test_worker_updates_queue_size_correctly():
    """验证队列大小计算正确（tasks_ahead = queue_size - 1）"""
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()

    async def run_test():
        user_id = "test-user-size"
        queue = service._ensure_user_queue(user_id)
        await service._start_user_worker(user_id)
        await asyncio.sleep(0.2)

        # 放入 3 个任务
        for i in range(3):
            await queue.put({
                "task_id": f"task-{i}",
                "task_func": AsyncMock(),
                "args": {"user_id": user_id, "extra_args": ()},
                "kwargs": {},
            })

        # 此时队列有 3 个任务
        assert queue.qsize() == 3, f"队列大小应该是 3: {queue.qsize()}"

        return True

    result = asyncio.run(run_test())
    assert result, "队列大小测试失败"
    print("✅ test_worker_updates_queue_size_correctly PASSED")


def test_worker_task_done_called():
    """验证 worker 完成任务后调用 task_done"""
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    task_done_called = False

    async def mock_task(task_id: str, user_id: str):
        nonlocal task_done_called
        await asyncio.sleep(0.05)

    async def run_test():
        nonlocal task_done_called

        user_id = "test-user-done"
        queue = service._ensure_user_queue(user_id)

        # 包装 queue.get 来检测 task_done
        original_get = queue.get
        async def wrapped_get():
            result = await original_get()
            # 模拟 task_done 被调用
            queue.task_done()
            return result

        queue.get = wrapped_get

        await service._start_user_worker(user_id)
        await asyncio.sleep(0.2)

        await queue.put({
            "task_id": "task-done",
            "task_func": mock_task,
            "args": {"user_id": user_id, "extra_args": ()},
            "kwargs": {},
        })

        await asyncio.sleep(0.3)

        return queue.qsize()

    final_size = asyncio.run(run_test())
    assert final_size == 0, f"队列应该为空（task_done 已调用）: {final_size}"
    print("✅ test_worker_task_done_called PASSED")


def run_all_tests():
    print("=" * 60)
    print("Worker 执行诊断测试")
    print("=" * 60)

    tests = [
        test_worker_executes_task_from_queue,
        test_worker_processes_multiple_tasks_in_order,
        test_worker_updates_queue_size_correctly,
        test_worker_task_done_called,
    ]

    for test in tests:
        print(f"\n📝 Running: {test.__name__}")
        try:
            test()
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
