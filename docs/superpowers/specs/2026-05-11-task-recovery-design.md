# 后台任务断点恢复设计

## 目标

服务器重启后，自动恢复 `running` 状态的后台任务，让用户无需手动重试。

## 范围

- `unified_write` - AI一键写作任务
- `chapter_generate` - 章节生成任务

## 方案

### 1. 数据模型变更

在 `BackgroundTask` 表增加 `checkpoint` JSON 字段：

```python
checkpoint = Column(JSON, nullable=True, comment="断点信息: {stage, current_index, completed_ids, progress}")
```

#### unified_write 断点结构

```json
{
  "stage": "writing_content",  // generating_outline | expanding_chapters | writing_content | analyzing
  "current_outline_index": 2,  // 当前处理到第几个大纲（从1开始）
  "completed_outlines": [1],    // 已完成的大纲索引列表
  "current_chapter_id": "xxx",  // 当前正在处理的章节ID（用于断点续传）
  "completed_chapters": ["yyy", "zzz"]  // 已完成的章节ID列表
}
```

#### chapter_generate 断点结构

单章节生成不需要细粒度断点，恢复时直接重试整个任务。

### 2. 断点更新时机

在 `unified_write_loop` 中，每个步骤开始前更新断点：

```python
# 生成大纲前
await tracker.update_checkpoint({"stage": "generating_outline", "current_outline_index": i + 1})

# 展开章节前
await tracker.update_checkpoint({"stage": "expanding_chapters", "current_outline_index": i + 1})

# 写章节内容前
await tracker.update_checkpoint({"stage": "writing_content", "current_chapter_id": chapter.id})

# 分析章节前
await tracker.update_checkpoint({"stage": "analyzing", "current_chapter_id": chapter.id})
```

### 3. 恢复流程

#### TaskProgressTracker 增加断点更新方法

```python
async def update_checkpoint(self, checkpoint_data: dict):
    """更新任务断点信息"""
    engine = await get_engine(self.user_id)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BackgroundTask).where(BackgroundTask.id == self.task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.checkpoint = checkpoint_data
            task.updated_at = datetime.now()
            await session.commit()
```

#### recover_stale_tasks 修改

```python
async def recover_stale_tasks(self, stale_minutes: int = 5):
    """恢复超时任务 - 后端重启后调用"""
    # ... 查找超时任务 ...

    for task in stale_tasks:
        # 根据 task_type 决定恢复策略
        if task.task_type == "unified_write":
            await self._recover_unified_write_task(task)
        elif task.task_type == "chapter_generate":
            await self._recover_chapter_generate_task(task)
```

#### 任务处理器注册表

在 `BackgroundTaskService` 中注册任务处理器：

```python
TASK_HANDLERS = {
    "unified_write": _recover_unified_write_task,
    "chapter_generate": _recover_chapter_generate_task,
}
```

### 4. unified_write 恢复逻辑

```python
async def _recover_unified_write_task(self, task: BackgroundTask):
    """恢复一键写作任务"""
    checkpoint = task.checkpoint or {}
    stage = checkpoint.get("stage", "generating_outline")
    current_index = checkpoint.get("current_outline_index", 1)
    completed_chapters = checkpoint.get("completed_chapters", [])

    # 从断点继续执行
    # 1. 如果是 generating_outline 或 expanding_chapters 阶段，重新调用 expand_outline_to_chapters
    # 2. 如果是 writing_content 阶段，跳过已完成的章节，继续写当前章节
    # 3. 如果是 analyzing 阶段，跳过已完成的分析，继续分析当前章节
```

### 5. chapter_generate 恢复逻辑

```python
async def _recover_chapter_generate_task(self, task: BackgroundTask):
    """恢复章节生成任务 - 直接重试"""
    task_input = task.task_input
    chapter_id = task_input.get("chapter_id")

    # 重新调用 _run_chapter_generation_bg
    await self.spawn_background_task(
        task_id=task.id,
        user_id=task.user_id,
        task_func=_run_chapter_generation_bg,
        task_input=task_input,
        task_type="chapter_generate"
    )
```

## 实现步骤

1. 修改 `BackgroundTask` 模型，增加 `checkpoint` 字段
2. 修改 `TaskProgressTracker`，增加 `update_checkpoint` 方法
3. 修改 `BackgroundTaskService`，增加任务处理器注册表和恢复方法
4. 修改 `unified_write_loop`，在每个步骤更新断点
5. 修改 `recover_stale_tasks`，根据任务类型选择恢复策略
6. 生成数据库迁移脚本

## 测试

1. 启动一键写作任务，人工中断后端服务，验证任务恢复
2. 启动章节生成任务，人工中断后端服务，验证任务恢复
3. 验证断点记录正确（数据库 checkpoint 字段）
4. 验证恢复后进度百分比正确
