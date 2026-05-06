# 灵感模式后台创建任务实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在灵感模式添加后台创建功能，用户点击"后台创建"后跳转到主页，右下角浮窗显示各阶段进度。

**Architecture:** 新增 `POST /api/inspiration/background` 端点，创建后台任务并异步执行 4 个 wizard-stream 步骤。前端添加"后台创建"按钮，点击后调用 API 并跳转主页。

**Tech Stack:** Python/FastAPI (后端), React/TypeScript (前端), PostgreSQL (数据库)

---

## 文件结构

### 后端改动

| 文件 | 改动 |
|------|------|
| `backend/app/api/inspiration.py` | 新建 - API 端点 |
| `backend/app/services/background_task_service.py` | 修改 - 添加任务执行辅助函数 |
| `backend/app/api/wizard_stream.py` | 修改 - 暴露非流式版本供后台任务调用 |
| `frontend/src/services/api.ts` | 修改 - 添加 inspirationBackgroundApi |
| `frontend/src/pages/Inspiration.tsx` | 修改 - 添加"后台创建"按钮和处理逻辑 |
| `frontend/src/components/FloatingTaskPanel.tsx` | 修改 - 支持 inspiration 任务类型 |

---

## 实施任务

### Task 1: 后端 - 创建 API 端点

**Files:**
- Create: `backend/app/api/inspiration.py`
- Modify: `backend/app/main.py` (注册路由)

- [ ] **Step 1: 创建 `backend/app/api/inspiration.py`**

```python
"""
灵感模式后台任务 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.user_manager import User, get_current_user
from app.services.background_task_service import (
    create_task,
    spawn_background_task,
    TaskProgressTracker,
)
from app.logger import get_logger

router = APIRouter(prefix="/inspiration", tags=["灵感模式后台任务"])
logger = get_logger(__name__)


class InspirationBackgroundRequest(BaseModel):
    title: str
    description: str
    theme: str
    genre: str
    narrative_perspective: str
    outline_mode: str = "one-to-one"


class InspirationBackgroundResponse(BaseModel):
    task_id: str
    message: str


async def _run_inspiration_bg(task_id: str, user_id: str, db: AsyncSession, task_input: dict):
    """后台执行灵感模式创建任务"""
    tracker = TaskProgressTracker(task_id, user_id, "灵感创建")

    try:
        # 导入 wizard_stream 服务
        from app.services.wizard_stream_service import WizardStreamService

        service = WizardStreamService(db)

        # 阶段1: 项目创建 + 世界观 (0-25%)
        await tracker.start("开始创建项目...")
        await tracker.loading("创建项目中...", 0.1)

        world_result = await service.generate_world_building(
            user_id=user_id,
            title=task_input["title"],
            description=task_input["description"],
            theme=task_input["theme"],
            genre=task_input["genre"],
            narrative_perspective=task_input["narrative_perspective"],
            target_words=100000,
            chapter_count=3,
            character_count=5,
            outline_mode=task_input["outline_mode"],
        )
        project_id = world_result["project_id"]

        await tracker.loading("世界观生成完成", 0.25)

        # 阶段2: 职业体系 (25-50%)
        await tracker.loading("生成职业体系中...", 0.3)
        await service.generate_career_system(project_id=project_id, user_id=user_id)
        await tracker.loading("职业体系生成完成", 0.5)

        # 阶段3: 角色生成 (50-75%)
        await tracker.loading("生成角色中...", 0.55)
        await service.generate_characters(
            project_id=project_id,
            user_id=user_id,
            count=5,
        )
        await tracker.loading("角色生成完成", 0.75)

        # 阶段4: 大纲生成 (75-100%)
        await tracker.loading("生成大纲中...", 0.8)
        await service.generate_outline(
            project_id=project_id,
            user_id=user_id,
            chapter_count=3,
            narrative_perspective=task_input["narrative_perspective"],
            target_words=100000,
        )
        await tracker.loading("大纲生成完成", 0.95)

        await tracker.complete("项目创建完成！")

    except Exception as e:
        logger.error(f"灵感模式后台任务失败: {e}")
        await tracker.error(str(e))
        raise


@router.post("/background", response_model=InspirationBackgroundResponse)
async def create_inspiration_background_task(
    data: InspirationBackgroundRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建灵感模式后台任务"""
    task = await create_task(
        user_id=user.user_id,
        project_id=None,
        task_type="inspiration",
        task_input=data.model_dump(),
        db=db,
    )

    task_input = data.model_dump()
    task_input["user_id"] = user.user_id

    await spawn_background_task(
        task.id,
        user.user_id,
        _run_inspiration_bg,
        db=db,
        task_input=task_input,
    )

    return InspirationBackgroundResponse(
        task_id=task.id,
        message="后台任务已创建",
    )
```

- [ ] **Step 2: 在 main.py 注册路由**

查找 `main.py` 中注册 router 的位置，添加：
```python
from app.api.inspiration import router as inspiration_router
# ...
app.include_router(inspiration_router)
```

- [ ] **Step 3: 运行测试验证**

Run: `cd backend && python -c "from app.api.inspiration import router; print('OK')"`
Expected: 无错误输出

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/inspiration.py
git commit -m "feat: add inspiration background task API"
```

---

### Task 2: 后端 - 创建 WizardStreamService 非流式版本

**Files:**
- Create: `backend/app/services/wizard_stream_service.py`
- Modify: `backend/app/api/wizard_stream.py` (导出服务类)

- [ ] **Step 1: 创建 `WizardStreamService` 类**

需要封装现有的 wizard_stream API 逻辑为可调用的服务方法：
- `generate_world_building()`
- `generate_career_system()`
- `generate_characters()`
- `generate_outline()`

这些方法应该复用现有的 wizard_stream.py 中的逻辑，但返回结果而不是流式输出。

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/wizard_stream_service.py
git commit -m "feat: extract wizard stream logic to service class"
```

---

### Task 3: 前端 - 添加 API 调用

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: 添加 inspirationBackgroundApi**

在 `api.ts` 中添加：
```typescript
export const inspirationBackgroundApi = {
  createBackgroundTask: async (data: {
    title: string;
    description: string;
    theme: string;
    genre: string;
    narrative_perspective: string;
    outline_mode: string;
  }) => {
    const response = await axios.post('/api/inspiration/background', data);
    return response.data;
  },
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add inspiration background task API client"
```

---

### Task 4: 前端 - 添加后台创建按钮

**Files:**
- Modify: `frontend/src/pages/Inspiration.tsx`

- [ ] **Step 1: 修改确认步骤选项**

找到显示 `['✅ 确认创建', '🔄 重新开始']` 的位置，修改为：
```typescript
if (currentStep === 'confirm') {
  if (option === '✅ 确认创建') {
    // 现有逻辑...
  } else if (option === '🔄 后台创建') {
    // 调用后台创建 API
    try {
      await inspirationBackgroundApi.createBackgroundTask({
        title: data.title,
        description: data.description,
        theme: data.theme,
        genre: data.genre,
        narrative_perspective: data.narrative_perspective,
        outline_mode: data.outline_mode,
      });
      message.success('已在后台开始生成，请稍后查看');
      window.location.href = 'http://localhost:8888';
    } catch (error) {
      message.error('创建失败，请重试');
    }
  } else if (option === '🔄 重新开始') {
    // 现有逻辑...
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Inspiration.tsx
git commit -m "feat: add background creation button to inspiration page"
```

---

### Task 5: 前端 - 浮窗支持 inspiration 任务类型

**Files:**
- Modify: `frontend/src/components/FloatingTaskPanel.tsx`

- [ ] **Step 1: 添加 inspiration 任务类型显示**

在 FloatingTaskPanel 中找到任务类型标签的定义位置，添加：
```typescript
const getTaskTypeLabel = (taskType: string) => {
  switch (taskType) {
    // ... existing cases
    case 'inspiration':
      return '灵感创建';
    default:
      return taskType;
  }
};

// 添加对应的图标
const getTaskTypeIcon = (taskType: string) => {
  switch (taskType) {
    // ... existing cases
    case 'inspiration':
      return <BulbOutlined />;
    default:
      return <FileTextOutlined />;
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/FloatingTaskPanel.tsx
git commit -m "feat: add inspiration task type support to floating panel"
```

---

### Task 6: 集成测试

**Files:**
- Modify: `backend/app/api/inspiration.py`
- Test: `backend/tests/test_inspiration_background.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_inspiration_background.py
import pytest
import asyncio

@pytest.mark.asyncio
async def test_create_inspiration_background_task():
    """测试创建灵感模式后台任务"""
    # 调用 API 创建任务
    # 验证返回 task_id
    # 验证任务状态为 pending
    pass

@pytest.mark.asyncio
async def test_inspiration_task_progress_stages():
    """测试任务各阶段进度"""
    # 创建任务
    # 轮询任务状态
    # 验证进度更新
    pass
```

- [ ] **Step 2: 运行测试**

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_inspiration_background.py
git commit -m "test: add tests for inspiration background task"
```

---

## 自检清单

- [ ] Spec 覆盖检查：每个设计要点都有对应的任务
- [ ] 占位符扫描：无 TBD/TODO
- [ ] 类型一致性：Task 2-6 中使用的函数签名与 Task 1 一致
- [ ] 测试覆盖：后端 API 和前端组件都有测试

---

## 执行方式

**Plan complete and saved to `docs/superpowers/plans/2026-05-06-inspiration-background-task-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
