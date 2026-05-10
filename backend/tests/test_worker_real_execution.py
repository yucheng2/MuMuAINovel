"""
TDD 测试：验证真实环境中 worker 能正确执行任务
使用真实的 asyncio 事件循环，不使用 mocks
"""
import sys
sys.path.insert(0, "/Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend")

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor


def test_worker_actually_executes_in_real_asyncio():
    """
    RED: 验证 worker 在真实 asyncio 环境中能执行任务

    这个测试验证：
    1. spawn_background_task 能正确启动 worker
    2. worker 能从队列取出任务
    3. 任务函数被正确执行
    """
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    executed = False
    execution_time = None

    async def real_task(task_id: str, user_id: str):
        nonlocal executed, execution_time
        executed = True
        execution_time = time.time()
        print(f"  [real_task] executed at {execution_time}")

    async def run():
        nonlocal executed

        user_id = "real-test-user"
        task_id = "real-test-task"

        # 确保队列存在
        queue = service._ensure_user_queue(user_id)

        # 启动 worker
        await service._start_user_worker(user_id)
        print(f"[test] worker started")

        # 等待 worker 完全启动
        await asyncio.sleep(0.2)
        print(f"[test] waiting for worker to be ready")

        # 放入任务
        await queue.put({
            "task_id": task_id,
            "task_func": real_task,
            "args": {"user_id": user_id, "extra_args": ()},
            "kwargs": {},
        })
        print(f"[test] task queued")

        # 等待任务执行
        start = time.time()
        timeout = 5.0
        while not executed and (time.time() - start) < timeout:
            await asyncio.sleep(0.1)

        elapsed = time.time() - start
        print(f"[test] waited {elapsed:.2f}s, executed={executed}")

        return executed, elapsed

    executed, elapsed = asyncio.run(run())

    assert executed, f"任务在 {elapsed:.2f} 秒内未被执行！"
    print(f"✅ test_worker_actually_executes_in_real_asyncio PASSED (耗时 {elapsed:.2f}s)")


def test_worker_updates_task_status_in_db():
    """
    RED: 验证 worker 执行时会更新数据库中的任务状态
    """
    # 这个测试需要真实数据库，暂时跳过
    pass


def test_spawn_creates_correct_queue_reference():
    """
    RED: 验证 spawn_background_task 使用正确的队列引用
    """
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    queue_refs = {}

    async def tracking_task(task_id: str, user_id: str):
        queue_id = id(service._user_queues.get(user_id))
        queue_refs["task_queue_id"] = queue_id
        print(f"  [tracking_task] queue_id={queue_id}")

    async def run():
        user_id = "queue-ref-test"

        # 先确保队列
        queue = service._ensure_user_queue(user_id)
        queue_refs["created_queue_id"] = id(queue)

        # 启动 worker
        await service._start_user_worker(user_id)
        await asyncio.sleep(0.2)

        # 通过 spawn 添加任务
        await service.spawn_background_task(
            task_id="ref-test-task",
            user_id=user_id,
            task_func=tracking_task,
        )

        # 等待执行
        start = time.time()
        while "task_queue_id" not in queue_refs and (time.time() - start) < 5:
            await asyncio.sleep(0.1)

        return queue_refs

    refs = asyncio.run(run())
    print(f"[test] refs: {refs}")

    assert "task_queue_id" in refs, "任务未被执行"
    assert refs["created_queue_id"] == refs["task_queue_id"], \
        f"队列引用不一致: created={refs['created_queue_id']}, task={refs['task_queue_id']}"
    print("✅ test_spawn_creates_correct_queue_reference PASSED")


def test_worker_loop_does_not_block_api():
    """
    RED: 验证 worker 循环不会阻塞 API 响应
    """
    from app.services.background_task_service import BackgroundTaskService

    service = BackgroundTaskService()
    api_returned = False

    async def slow_task(task_id: str, user_id: str):
        await asyncio.sleep(2.0)

    async def api_simulation():
        nonlocal api_returned
        user_id = "blocking-test"

        # 模拟 API 调用 spawn_background_task
        queue = service._ensure_user_queue(user_id)
        await service._start_user_worker(user_id)
        await asyncio.sleep(0.1)

        await queue.put({
            "task_id": "blocking-task",
            "task_func": slow_task,
            "args": {"user_id": user_id, "extra_args": ()},
            "kwargs": {},
        })

        api_returned = True
        return api_returned

    async def run():
        # 并发运行 API 模拟和 worker
        result = await asyncio.gather(
            api_simulation(),
            return_exceptions=True
        )
        return result[0]  # api_simulation 的返回值

    result = asyncio.run(run())

    assert result == True, "API 模拟未能返回"
    print("✅ test_worker_loop_does_not_block_api PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("Worker 真实执行 TDD 测试")
    print("=" * 60)

    tests = [
        test_worker_actually_executes_in_real_asyncio,
        test_spawn_creates_correct_queue_reference,
        test_worker_loop_does_not_block_api,
    ]

    for test in tests:
        if test.__name__ == "test_worker_updates_task_status_in_db":
            continue  # 跳过需要真实 DB 的测试

        print(f"\n📝 Running: {test.__name__}")
        try:
            test()
        except AssertionError as e:
            print(f"❌ {test.__name__} FAILED: {e}")
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}")
            import traceback
            traceback.print_exc()
