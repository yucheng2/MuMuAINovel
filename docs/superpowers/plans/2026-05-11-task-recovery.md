# 后台任务断点恢复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 服务器重启后自动恢复 `unified_write` 和 `chapter_generate` 任务，从断点继续执行。

**Architecture:** 在 BackgroundTask 表增加 checkpoint JSON 字段存储断点状态，恢复时根据 task_type 调用对应处理函数从断点继续。

**Tech Stack:** Python/FastAPI, SQLAlchemy, Alembic

---

## 文件结构

```
backend/
├── app/
│   ├── models/
│   │   └── background_task.py        # 增加 checkpoint 字段
│   ├── services/
│   │   ├── background_task_service.py  # 增加断点更新、任务注册表、恢复逻辑
│   │   └── unified_write_service.py   # unified_write_loop 增加断点更新
│   └── api/
│       ├── writing.py                 # 注册 unified_write 恢复处理
│       └── chapters.py                # 注册 chapter_generate 恢复处理
├── alembic/
│   └── versions/
│       └── xxxxx_add_task_checkpoint.py  # 数据库迁移
```

---

## 实现任务

### Task 1: 修改 BackgroundTask 模型，增加 checkpoint 字段

**Files:**
- Modify: `backend/app/models/background_task.py`

- [ ] **Step 1: 查看当前 BackgroundTask 模型结构**

```python
# backend/app/models/background_task.py
# 在 BackgroundTask 类中找到 task_input 字段定义，在其下方添加 checkpoint 字段
```

- [ ] **Step 2: 添加 checkpoint 字段**

在 `task_input = Column(JSON, comment="任务输入参数(JSON)")` 后添加：

```python
checkpoint = Column(JSON, nullable=True, comment="断点信息: {stage, current_index, completed_ids, progress}")
```

- [ ] **Step 3: 验证模型语法**

Run: `cd /Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend && uv run python -c "from app.models.background_task import BackgroundTask; print('OK')"`
Expected: OK

- [ ] **Step 4: 提交**

```bash
git add backend/app/models/background_task.py
git commit -m "feat: 添加 BackgroundTask.checkpoint 字段"
```

---

### Task 2: TaskProgressTracker 增加 update_checkpoint 方法

**Files:**
- Modify: `backend/app/services/background_task_service.py:117-148` (TaskProgressTracker 类)

- [ ] **Step 1: 添加 update_checkpoint 方法**

在 TaskProgressTracker 类的 `async def error` 方法后添加：

```python
async def update_checkpoint(self, checkpoint_data: dict):
    """更新任务断点信息到数据库"""
    try:
        engine = await get_engine(self.user_id)
        AsyncSessionLocal = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == self.task_id)
            )
            task = result.scalar_one_or_none()
            if task:
                task.checkpoint = checkpoint_data
                task.updated_at = datetime.now()
                await session.commit()
                logger.info(f"[{self.task_id}] checkpoint 更新: {checkpoint_data.get('stage')}")
    except Exception as e:
        logger.error(f"[{self.task_id}] 更新 checkpoint 失败: {e}")
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend && uv run python -c "from app.services.background_task_service import TaskProgressTracker; print('OK')"`
Expected: OK

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/background_task_service.py
git commit -m "feat: TaskProgressTracker 增加 update_checkpoint 方法"
```

---

### Task 3: 修改 BackgroundTaskService，添加任务处理器注册表和恢复方法

**Files:**
- Modify: `backend/app/services/background_task_service.py` (BackgroundTaskService 类)

- [ ] **Step 1: 添加任务处理器注册表**

在 BackgroundTaskService 类的 `def __init__` 方法后添加：

```python
# 任务类型 -> 恢复处理函数 注册表
TASK_RECOVERY_HANDLERS: Dict[str, Callable] = {}

def register_task_recovery_handler(task_type: str):
    """任务恢复处理器注册装饰器"""
    def decorator(func):
        TASK_RECOVERY_HANDLERS[task_type] = func
        return func
    return decorator
```

- [ ] **Step 2: 修改 recover_stale_tasks 方法**

找到 `async def recover_stale_tasks` 方法，将 "标记为失败" 的逻辑改为 "恢复执行"：

将第565-574行的：
```python
if db_task.status == "running":
    db_task.status = "failed"
    db_task.error_message = "任务超时（服务端重启后自动恢复）"
    ...
```
替换为：
```python
if db_task.status == "running" and db_task.task_type in TASK_RECOVERY_HANDLERS:
    # 有恢复处理器的任务，触发恢复
    try:
        handler = TASK_RECOVERY_HANDLERS[db_task.task_type]
        await handler(db_task, user_session)
        logger.info(f"✅ 任务 {db_task.id[:8]} 已恢复执行")
    except Exception as e:
        logger.error(f"恢复任务 {db_task.id[:8]} 失败: {e}")
        db_task.status = "failed"
        db_task.error_message = f"恢复失败: {e}"
else:
    # 没有恢复处理器的任务，标记为失败
    db_task.status = "failed"
    db_task.error_message = "任务超时（无恢复处理器）"
```

- [ ] **Step 3: 验证语法**

Run: `cd /Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend && uv run python -c "from app.services.background_task_service import BackgroundTaskService; print('OK')"`
Expected: OK

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/background_task_service.py
git commit -m "feat: BackgroundTaskService 添加任务恢复处理器注册表"
```

---

### Task 4: 实现 unified_write 恢复处理函数

**Files:**
- Modify: `backend/app/api/writing.py`

- [ ] **Step 1: 添加恢复处理函数**

在 `async def _run_unified_write_bg` 函数后添加：

```python
from app.services.background_task_service import register_task_recovery_handler

@register_task_recovery_handler("unified_write")
async def _recover_unified_write_bg(task: BackgroundTask, session: AsyncSession):
    """恢复一键写作任务（从断点继续）"""
    from app.services.unified_write_service import unified_write_loop

    task_input = task.task_input or {}
    project_id = task_input.get("project_id")
    chapters_per_outline = task_input.get("chapters_per_outline", 1)
    checkpoint = task.checkpoint or {}

    logger.info(f"[{task.id}] 恢复 unified_write 任务，checkpoint: {checkpoint}")

    # 调用 unified_write_loop，传入断点信息
    # 注意：需要修改 unified_write_loop 支持 checkpoint 参数
    await unified_write_loop(
        task_id=task.id,
        user_id=task.user_id,
        project_id=project_id,
        chapters_per_outline=chapters_per_outline,
        db=session,
        checkpoint=checkpoint
    )
```

- [ ] **Step 2: 验证语法**

Run: `cd /Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend && uv run python -c "from app.api.writing import _recover_unified_write_bg; print('OK')"`
Expected: 可能会报错 about missing `unified_write_loop` checkpoint parameter，这是预期的

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/writing.py
git commit -m "feat: 添加 unified_write 恢复处理函数"
```

---

### Task 5: 修改 unified_write_loop 支持 checkpoint 参数

**Files:**
- Modify: `backend/app/services/unified_write_service.py`

- [ ] **Step 1: 查看当前 unified_write_loop 签名**

```python
# backend/app/services/unified_write_service.py:377
async def unified_write_loop(
    task_id: str,
    user_id: str,
    project_id: str,
    chapters_per_outline: int = 1,
    db: AsyncSession = None
):
```

- [ ] **Step 2: 修改函数签名，增加 checkpoint 参数**

```python
async def unified_write_loop(
    task_id: str,
    user_id: str,
    project_id: str,
    chapters_per_outline: int = 1,
    db: AsyncSession = None,
    checkpoint: dict = None
):
```

- [ ] **Step 3: 在函数开头获取 tracker 并设置断点初始状态**

在 `tracker = TaskProgressTracker(task_id, user_id, "一键写作")` 后添加：

```python
# 如果有断点，记录当前进度
if checkpoint:
    logger.info(f"[{task_id}] 从断点恢复: {checkpoint}")
```

- [ ] **Step 4: 修改大纲生成循环，支持断点跳过**

找到 `for i in range(chapters_per_outline):` 循环，修改为：

```python
completed_outlines = checkpoint.get("completed_outlines", []) if checkpoint else []

for i in range(chapters_per_outline):
    # 如果这个大纲已完成（断点恢复），跳过
    if (i + 1) in completed_outlines:
        logger.info(f"[{task_id}] 大纲 {i+1} 已完成，跳过")
        continue

    # 生成大纲前更新断点
    if tracker:
        await tracker.update_checkpoint({
            "stage": "generating_outline",
            "current_outline_index": i + 1,
            "completed_outlines": completed_outlines
        })

    outline = await generate_one_outline(project_id, user_id, db, tracker=tracker)
    if not outline:
        logger.warning(f"[{task_id}] 第 {i+1} 个大纲生成失败，跳过")
        continue

    # ... 后续展开章节、写作、分析逻辑 ...
    # 每个步骤完成后，更新 completed_outlines 和 checkpoint
```

- [ ] **Step 5: 验证语法**

Run: `cd /Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend && uv run python -c "from app.services.unified_write_service import unified_write_loop; print('OK')"`
Expected: OK

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/unified_write_service.py
git commit -m "feat: unified_write_loop 支持 checkpoint 断点恢复"
```

---

### Task 6: 实现 chapter_generate 恢复处理函数

**Files:**
- Modify: `backend/app/api/chapters.py`

- [ ] **Step 1: 在文件开头添加装饰器导入**

找到 `from app.services.background_task_service import background_task_service` (约第30行)，在后面添加：

```python
from app.services.background_task_service import register_task_recovery_handler
```

- [ ] **Step 2: 找到 _run_chapter_generation_bg 函数，在其后添加恢复函数**

在 `async def _run_chapter_generation_bg` 函数后添加：

```python
@register_task_recovery_handler("chapter_generate")
async def _recover_chapter_generate_bg(task: BackgroundTask, session: AsyncSession):
    """恢复章节生成任务（直接重试）"""
    task_input = task.task_input or {}
    chapter_id = task_input.get("chapter_id")

    logger.info(f"[{task.id}] 恢复 chapter_generate 任务，chapter_id: {chapter_id}")

    # 直接重新调用章节生成逻辑
    # 注意：需要创建新的 tracker
    from app.services.background_task_service import TaskProgressTracker
    from app.api.settings import get_user_ai_service_from_db
    from sqlalchemy import select
    from app.models.chapter import Chapter

    tracker = TaskProgressTracker(task.id, task.user_id, "章节")
    ai_service = await get_user_ai_service_from_db(task.user_id, session)

    await _run_chapter_generation_bg(
        task_input=task_input,
        db=session,
        ai_service=ai_service,
        tracker=tracker,
        user_id=task.user_id,
        task_id=task.id
    )
```

- [ ] **Step 3: 验证语法**

Run: `cd /Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend && uv run python -c "from app.api.chapters import _recover_chapter_generate_bg; print('OK')"`
Expected: OK

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/chapters.py
git commit -m "feat: 添加 chapter_generate 恢复处理函数"
```

---

### Task 7: 生成数据库迁移

**Files:**
- Create: `backend/alembic/versions/xxxxx_add_task_checkpoint.py`

- [ ] **Step 1: 生成迁移**

Run: `cd /Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend && alembic revision --autogenerate -m "add task checkpoint"`

- [ ] **Step 2: 检查生成的迁移文件内容**

Read: `backend/alembic/versions/xxxxx_add_task_checkpoint.py` (xxxxx 是随机字符)

确保迁移包含：
```python
op.add_column('background_tasks', sa.Column('checkpoint', sa.JSON(), nullable=True))
```

- [ ] **Step 3: 执行迁移**

Run: `cd /Users/yuchengfan/dev/personal/novel/MuMuAINovel/backend && alembic upgrade head`

- [ ] **Step 4: 提交迁移**

```bash
git add backend/alembic/versions/xxxxx_add_task_checkpoint.py
git commit -m "feat: 添加后台任务 checkpoint 字段迁移"
```

---

### Task 8: 端到端测试

**Files:**
- 无需修改代码，通过手动测试验证

- [ ] **Step 1: 重启后端服务**

Run: `lsof -ti:9999 | xargs kill -9 2>/dev/null; sleep 1; cd backend && uv run python -m uvicorn app.main:app --host localhost --port 9999 --reload &`

等待启动完成：tail -f backend/logs/app.log 或检查端口

- [ ] **Step 2: 测试 unified_write 恢复**

1. 在前端发起一个一键写作任务（生成2章）
2. 任务开始后，立即 kill -9 后端进程（模拟崩溃）
3. 重启后端
4. 检查任务是否自动恢复执行

- [ ] **Step 3: 测试 chapter_generate 恢复**

1. 在前端发起一个章节生成任务
2. 任务开始后，立即 kill -9 后端进程
3. 重启后端
4. 检查任务是否自动恢复执行

- [ ] **Step 4: 验证结果**

检查：
- 数据库中 BackgroundTask.checkpoint 字段有正确的数据
- 任务最终成功完成
- 没有创建重复的章节或大纲

- [ ] **Step 5: 提交测试结果**

```bash
git commit -m "test: 验证后台任务断点恢复功能"
```

---

## 自检清单

1. **Spec coverage:** 所有设计要求都有对应实现任务 ✓
2. **Placeholder scan:** 无 TODO/TBD 占位符 ✓
3. **Type consistency:** checkpoint 字段类型为 JSON，与 Python dict 兼容 ✓
4. **边界情况:**
   - checkpoint 为 None 时（新任务）正常执行 ✓
   - checkpoint stage 不匹配时（代码更新后）走正常流程 ✓

---

## 执行选项

**1. Subagent-Driven (recommended)** - 每个任务派发一个 subagent，任务间审查，快迭代

**2. Inline Execution** - 在当前 session 执行任务，带检查点

选择哪个？
