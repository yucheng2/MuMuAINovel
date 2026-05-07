# AI 全自动写作流水线实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现一键启动的AI全自动写作流程，循环执行：生成大纲→展开3章→写章节→分析，直到目标字数达标

**Architecture:**
- 新增 `POST /api/writing/auto-write` API 创建自动写作任务
- 新增 `auto_write_loop()` 函数作为主循环，复用现有的后台任务框架
- 使用 `TaskProgressTracker` 更新进度
- 使用 `cancel_requested` 标志支持停止

**Tech Stack:** Python/FastAPI 后端 + React 前端

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `backend/app/api/writing.py` | 新增自动写作 API 端点 |
| `backend/app/services/auto_write_service.py` | 新增自动写作循环逻辑 |
| `backend/app/api/tasks.py` | 添加任务状态查询 |
| `frontend/src/pages/Outline.tsx` | 添加「AI自动写作」按钮 |
| `frontend/src/services/backgroundTaskService.ts` | 添加轮询和任务创建 |

---

## 任务分解

### Task 1: 创建自动写作 API 端点

**Files:**
- Create: `backend/app/api/writing.py`

- [ ] **Step 1: 创建 `backend/app/api/writing.py` 文件**

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.background_task import BackgroundTask
from app.services.background_task_service import background_task_service
from app.database import get_db
from app.api.outlines import _build_outline_continue_context
from app.api.chapters import analyze_chapter_background
from app.services.ai_service import AIService
from app.middleware.auth_middleware import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/writing", tags=["writing"])

class AutoWriteRequest(BaseModel):
    project_id: str

@router.post("/auto-write")
async def create_auto_write_task(
    data: AutoWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建自动写作任务"""
    user_id = await get_current_user(request)
    # TODO: 实现任务创建逻辑

@router.post("/auto-write/{task_id}/stop")
async def stop_auto_write_task(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """停止自动写作任务"""
    user_id = await get_current_user(request)
    # TODO: 实现停止逻辑

@router.get("/auto-write/{task_id}/progress")
async def get_auto_write_progress(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """获取自动写作进度"""
    user_id = await get_current_user(request)
    # TODO: 实现进度查询
```

- [ ] **Step 2: 提交代码**

```bash
git add backend/app/api/writing.py
git commit -m "feat: 创建自动写作API端点骨架"
```

---

### Task 2: 实现自动写作循环主函数

**Files:**
- Create: `backend/app/services/auto_write_service.py`
- Modify: `backend/app/api/writing.py`

- [ ] **Step 1: 创建 `auto_write_service.py`**

```python
import asyncio
import logging
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_task import BackgroundTask
from app.models.project import Project
from app.models.outline import Outline
from app.models.chapter import Chapter
from app.services.task_progress_tracker import TaskProgressTracker
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

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

        while True:
            # 检查是否被取消
            if tracker.check_cancelled():
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

            await tracker.loading(f"当前 {current_words} / {target_words} 字", current_words / target_words)

            if current_words >= target_words:
                await tracker.complete("目标字数已达成！")
                break

            # 步骤1: 生成1个大纲
            await tracker.loading("正在生成大纲...")
            outline = await generate_one_outline(project_id, user_id, db)
            if not outline:
                await tracker.error("生成大纲失败")
                break

            # 步骤2: 展开为3个章节
            await tracker.loading("正在展开大纲...")
            chapters = await expand_outline_to_chapters(outline.id, user_id, db, count=3)
            if not chapters:
                await tracker.error("展开大纲失败")
                break

            # 步骤3-5: 写章节+分析
            for i, chapter in enumerate(chapters):
                chapter_status = f"正在写章节 ({i+1}/3)..."
                await tracker.loading(chapter_status, (i * 33 + 33) / 100)

                success = await write_chapter_content(chapter.id, user_id, db)
                if not success:
                    logger.warning(f"章节 {chapter.id} 写作失败，跳过分析")
                    continue

                await tracker.loading(f"正在分析章节 ({i+1}/3)...")
                await analyze_chapter_background(
                    chapter_id=chapter.id,
                    user_id=user_id,
                    project_id=project_id,
                    task_id=task_id
                )

            # 更新进度详情
            await update_task_progress_details(task_id, db, {
                "current_round": outline.order_index,
                "completed_outlines": outline.order_index,
                "completed_chapters": len(chapters)
            })

    except Exception as e:
        logger.exception(f"自动写作任务 {task_id} 异常: {e}")
        await tracker.error(str(e))


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


async def generate_one_outline(project_id: str, user_id: str, db: AsyncSession):
    """生成1个大纲"""
    # TODO: 调用现有的 continue_outline_generator，传入 chapter_count=1
    pass


async def expand_outline_to_chapters(outline_id: str, user_id: str, db: AsyncSession, count: int = 3):
    """展开大纲为指定数量章节"""
    # TODO: 调用现有的展开大纲逻辑
    pass


async def write_chapter_content(chapter_id: str, user_id: str, db: AsyncSession) -> bool:
    """写章节内容"""
    # TODO: 调用现有的章节生成逻辑
    pass
```

- [ ] **Step 2: 提交代码**

```bash
git add backend/app/services/auto_write_service.py
git commit -m "feat: 创建自动写作循环主函数骨架"
```

---

### Task 3: 注册自动写作路由

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 在 main.py 中注册新路由**

找到 `main.py` 中注册其他 API 路由的位置，添加：

```python
from app.api.writing import router as writing_router

# 在 app.include_router 处添加
app.include_router(writing_router, prefix="/api")
```

- [ ] **Step 2: 提交代码**

```bash
git add backend/app/main.py
git commit -m "feat: 注册自动写作API路由"
```

---

### Task 4: 前端添加「AI自动写作」按钮

**Files:**
- Modify: `frontend/src/pages/Outline.tsx`

- [ ] **Step 1: 添加按钮**

在「AI生成/续写」按钮旁边添加：

```tsx
import { RocketOutlined } from '@ant-design/icons';

// 在 Outline 组件中添加状态
const [isAutoWriting, setIsAutoWriting] = useState(false);

// 添加按钮
<Button
  icon={<RocketOutlined />}
  onClick={handleAutoWrite}
  loading={isAutoWriting}
>
  AI自动写作
</Button>

// 添加处理函数
const handleAutoWrite = async () => {
  if (!currentProject?.id) {
    message.warning('请先选择一个项目');
    return;
  }
  // TODO: 调用自动写作 API
};
```

- [ ] **Step 2: 提交代码**

```bash
git add frontend/src/pages/Outline.tsx
git commit -m "feat: 前端添加AI自动写作按钮"
```

---

### Task 5: 前端添加后台任务轮询

**Files:**
- Modify: `frontend/src/services/backgroundTaskService.ts`

- [ ] **Step 1: 添加自动写作相关函数**

```typescript
export async function createAutoWriteTask(
  projectId: string,
  onProgress: TaskProgressCallback,
  onComplete: TaskCompleteCallback,
  onError: TaskErrorCallback
): Promise<() => void> {
  const response = await fetch('/api/writing/auto-write', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId }),
  });

  if (!response.ok) {
    throw new Error('创建自动写作任务失败');
  }

  const { task_id } = await response.json();

  // 轮询任务状态
  const intervalId = setInterval(async () => {
    const statusResponse = await fetch(`/api/writing/auto-write/${task_id}/progress`);
    const status = await statusResponse.json();

    if (status.status === 'completed') {
      clearInterval(intervalId);
      onComplete(status.result);
    } else if (status.status === 'failed') {
      clearInterval(intervalId);
      onError(status.error);
    } else {
      onProgress(status);
    }
  }, 2000);

  // 返回取消函数
  return () => {
    clearInterval(intervalId);
    fetch(`/api/writing/auto-write/${task_id}/stop`, { method: 'POST' });
  };
}
```

- [ ] **Step 2: 提交代码**

```bash
git add frontend/src/services/backgroundTaskService.ts
git commit -m "feat: 添加自动写作任务创建和轮询"
```

---

### Task 6: 实现 generate_one_outline 逻辑

**Files:**
- Modify: `backend/app/services/auto_write_service.py`

- [ ] **Step 1: 实现大纲生成**

复用 `continue_outline_generator` 或 `continue_outline_api` 的逻辑：

```python
async def generate_one_outline(project_id: str, user_id: str, db: AsyncSession):
    """生成1个大纲"""
    from app.api.outlines import continue_outline_generator
    from app.schemas.outline import OutlineGenerateRequest

    # 获取项目信息
    project = await get_project(project_id, db)
    if not project:
        return None

    # 构建请求
    request_data = {
        "project_id": project_id,
        "chapter_count": 1,  # 每次只生成1个大纲
        "mode": "continue",
        "plot_stage": _auto_determine_plot_stage(
            len(await get_outlines(project_id, db)),
            project.chapter_count or 30
        ),
        "story_direction": "自然延续故事发展",
        "requirements": ""
    }

    # 调用现有的 continue_outline_generator
    user_ai_service = await AIService.create(user_id, db)
    result = await continue_outline_generator(
        request_data, db, user_ai_service, user_id
    )

    # 返回生成的大纲
    outlines = await get_outlines(project_id, db)
    return outlines[-1] if outlines else None
```

- [ ] **Step 2: 提交代码**

```bash
git add backend/app/services/auto_write_service.py
git commit -m "feat: 实现generate_one_outline逻辑"
```

---

### Task 7: 实现 expand_outline_to_chapters 逻辑

**Files:**
- Modify: `backend/app/services/auto_write_service.py`

- [ ] **Step 1: 实现大纲展开**

```python
async def expand_outline_to_chapters(outline_id: str, user_id: str, db: AsyncSession, count: int = 3):
    """展开大纲为指定数量章节"""
    from app.api.outlines import _run_outline_expansion_background

    outline_result = await db.execute(select(Outline).where(Outline.id == outline_id))
    outline = outline_result.scalar_one_or_none()
    if not outline:
        return []

    # 复用现有的展开逻辑
    data = {
        "expand_count": count,
        "auto_create_chapters": True
    }

    await _run_outline_expansion_background(
        task_id=f"auto_write_expand_{outline_id}",
        user_id=user_id,
        outline_id=outline_id,
        data=data
    )

    # 获取生成的章节
    chapters_result = await db.execute(
        select(Chapter)
        .where(Chapter.outline_id == outline_id)
        .order_by(Chapter.order_index)
    )
    chapters = chapters_result.scalars().all()

    return list(chapters)[:count]
```

- [ ] **Step 2: 提交代码**

```bash
git add backend/app/services/auto_write_service.py
git commit -m "feat: 实现expand_outline_to_chapters逻辑"
```

---

### Task 8: 实现 write_chapter_content 逻辑

**Files:**
- Modify: `backend/app/services/auto_write_service.py`

- [ ] **Step 1: 实现章节写作**

```python
async def write_chapter_content(chapter_id: str, user_id: str, db: AsyncSession) -> bool:
    """写章节内容"""
    from app.api.chapters import generate_chapter_content_background

    chapter_result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = chapter_result.scalar_one_or_none()
    if not chapter:
        return False

    # 调用现有的章节生成逻辑
    await generate_chapter_content_background(
        chapter_id=chapter_id,
        user_id=user_id,
        project_id=chapter.project_id,
        force_regenerate=False,
        target_words=3000
    )

    return True
```

- [ ] **Step 2: 提交代码**

```bash
git add backend/app/services/auto_write_service.py
git commit -m "feat: 实现write_chapter_content逻辑"
```

---

### Task 9: 完善 API 端点实现

**Files:**
- Modify: `backend/app/api/writing.py`

- [ ] **Step 1: 实现 create_auto_write_task**

```python
@router.post("/auto-write")
async def create_auto_write_task(
    data: AutoWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建自动写作任务"""
    user_id = await get_current_user(request)

    # 验证项目存在
    project = await db.execute(select(Project).where(Project.id == data.project_id))
    if not project.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="项目不存在")

    # 创建后台任务
    task = await background_task_service.create_task(
        user_id=user_id,
        project_id=data.project_id,
        task_type="auto_write",
        task_input={"project_id": data.project_id},
        db=db
    )

    # 启动自动写作循环
    await background_task_service.spawn_background_task(
        task_id=task.id,
        user_id=user_id,
        task_func=_run_auto_write_bg,
        project_id=data.project_id
    )

    return {"task_id": task.id, "status": "running"}
```

- [ ] **Step 2: 实现 stop_auto_write_task**

```python
@router.post("/auto-write/{task_id}/stop")
async def stop_auto_write_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """停止自动写作任务"""
    user_id = await get_current_user(request)

    # 获取任务
    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.user_id == user_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 设置取消标志
    task.cancel_requested = True
    task.status = "cancelled"
    await db.commit()

    return {"status": "stopped"}
```

- [ ] **Step 3: 实现 get_auto_write_progress**

```python
@router.get("/auto-write/{task_id}/progress")
async def get_auto_write_progress(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取自动写作进度"""
    user_id = await get_current_user(request)

    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.user_id == user_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    current_words = await get_project_word_count(task.project_id, db)
    project = await get_project(task.project_id, db)
    target_words = project.target_words if project else 30000

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress or 0,
        "current_words": current_words,
        "target_words": target_words,
        "message": task.status_message,
        "details": task.progress_details or {}
    }
```

- [ ] **Step 4: 添加辅助函数**

```python
async def _run_auto_write_bg(task_id: str, user_id: str, project_id: str):
    """后台运行自动写作"""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await auto_write_loop(task_id, user_id, project_id, db)
```

- [ ] **Step 5: 提交代码**

```bash
git add backend/app/api/writing.py
git commit -m "feat: 实现自动写作API端点完整逻辑"
```

---

### Task 10: 集成前端按钮与 API

**Files:**
- Modify: `frontend/src/pages/Outline.tsx`

- [ ] **Step 1: 实现 handleAutoWrite 函数**

```tsx
const handleAutoWrite = async () => {
  if (!currentProject?.id) {
    message.warning('请先选择一个项目');
    return;
  }

  Modal.confirm({
    title: '启动AI自动写作',
    content: (
      <div>
        <p>目标字数：{currentProject.target_words || 30000} 字</p>
        <p>将自动循环执行：生成大纲→展开→写章节→分析</p>
      </div>
    ),
    onOk: async () => {
      setIsAutoWriting(true);
      try {
        await createAutoWriteTask(
          currentProject.id,
          (progress) => {
            // 更新进度显示
            message.info(progress.message || '自动写作中...');
          },
          (result) => {
            setIsAutoWriting(false);
            message.success('自动写作完成！');
            refreshOutlines();
          },
          (error) => {
            setIsAutoWriting(false);
            message.error('自动写作失败: ' + error);
          }
        );
      } catch (error) {
        setIsAutoWriting(false);
        message.error('启动失败');
      }
    }
  });
};
```

- [ ] **Step 2: 提交代码**

```bash
git add frontend/src/pages/Outline.tsx
git commit -m "feat: 前端集成自动写作按钮和API调用"
```

---

## 依赖关系

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8 → Task 9 → Task 10
```

## 成功标准

1. [ ] 点击「AI自动写作」按钮创建后台任务
2. [ ] 后台任务循环执行：生成大纲→展开3章→写章节→分析
3. [ ] 每轮正确更新进度
4. [ ] 目标字数达标后自动停止
5. [ ] 用户可以手动停止
6. [ ] 前端正确显示进度信息
