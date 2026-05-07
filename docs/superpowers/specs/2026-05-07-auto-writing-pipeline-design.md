# AI 全自动写作流水线设计

## 需求背景

用户希望实现一键启动的 AI 全自动写作流程，无需人工干预，按顺序执行：生成大纲→展开→写章节→分析→循环，直到目标字数达标。

## 核心流程

```
┌─────────────────────────────────────────────────────────┐
│  点击「AI自动写作」→ 创建后台任务                        │
│                                                         │
│  循环直到目标字数达标：                                  │
│                                                         │
│  ┌─────────────┐                                       │
│  │ 1. 生成大纲  │  生成1个新大纲                        │
│  └──────┬──────┘                                       │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 2. 展开大纲  │  将新大纲展开为3个章节                 │
│  └──────┬──────┘                                       │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 3. 写章节1  │  生成章节内容（约3000字）              │
│  └──────┬──────┘                                       │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 4. 分析章节1 │  更新伏笔、关系、职业等               │
│  └──────┬──────┘                                       │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 5. 写章节2  │  生成章节内容                          │
│  └──────┬──────┘                                       │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 6. 分析章节2 │                                      │
│  └──────┬──────┘                                       │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 7. 写章节3  │  生成章节内容                          │
│  └──────┬──────┘                                       │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 8. 分析章节3 │                                      │
│  └──────┬──────┘                                       │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 字数达标？  │  否 → 继续循环                          │
│  └──────┬──────┘                                       │
│         │ 是                                            │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │   完成     │                                        │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

## 每轮产出

- 1 个新大纲
- 3 个展开的章节
- 3 个章节各约 3000 字
- 每轮约增加 9000 字

## 终止条件

**目标字数达标时自动停止**：当 `已写字数 >= project.target_words` 时，结束循环。

## 技术实现

### 新增 API

**1. 创建自动写作任务**

```
POST /api/writing/auto-write
```

Request:
```json
{
  "project_id": "uuid"
}
```

Response:
```json
{
  "task_id": "uuid",
  "status": "running"
}
```

**2. 停止自动写作任务**

```
POST /api/writing/auto-write/{task_id}/stop
```

**3. 获取自动写作进度**

```
GET /api/writing/auto-write/{task_id}/progress
```

Response:
```json
{
  "status": "running",
  "progress": 45,
  "current_step": "正在写章节",
  "current_round": 2,
  "total_rounds": 8,
  "words_written": 18000,
  "target_words": 30000,
  "completed_outlines": 4,
  "completed_chapters": 12
}
```

### 后端实现

**文件：** `backend/app/api/writing.py` (新增)

```python
@router.post("/auto-write")
async def create_auto_write_task(project_id: str, db: AsyncSession):
    """创建自动写作任务"""
    # 1. 创建后台任务记录
    # 2. 启动自动写作循环（异步）

@router.post("/auto-write/{task_id}/stop")
async def stop_auto_write_task(task_id: str, db: AsyncSession):
    """停止自动写作任务"""

@router.get("/auto-write/{task_id}/progress")
async def get_auto_write_progress(task_id: str, db: AsyncSession):
    """获取自动写作进度"""
```

**自动写作循环函数：**

```python
async def auto_write_loop(project_id: str, task_id: str, db: AsyncSession):
    """自动写作主循环"""
    while True:
        # 检查是否停止
        if await task_should_stop(task_id):
            break

        # 检查字数
        current_words = await get_project_word_count(project_id)
        target_words = await get_project_target_words(project_id)
        if current_words >= target_words:
            break

        # 步骤1: 生成1个大纲
        await generate_one_outline(project_id, task_id, db)

        # 步骤2: 展开为3个章节
        await expand_latest_outline_to_chapters(project_id, 3, task_id, db)

        # 步骤3-6: 写章节+分析（循环3次）
        chapters = await get_latest_unwritten_chapters(project_id, 3)
        for chapter in chapters:
            await write_chapter_content(chapter.id, task_id, db)
            await analyze_chapter_background(chapter.id, task_id, db)

        # 更新任务进度
        await update_task_progress(task_id, ...)

    # 任务完成
    await mark_task_completed(task_id)
```

### 前端实现

**文件：** `frontend/src/pages/Outline.tsx`

新增按钮：
```tsx
<Button
  icon={<RocketOutlined />}
  onClick={handleAutoWrite}
  loading={isAutoWriting}
>
  AI自动写作
</Button>
```

**后台任务面板扩展：**

```tsx
// 显示自动写作进度
{
  task.type === 'auto_write' && (
    <div>
      <Progress percent={progress} />
      <Text>当前：{currentStep}</Text>
      <Text>已写 {wordsWritten} / {targetWords} 字</Text>
      <Text>已完成 {completedOutlines} 个大纲，{completedChapters} 个章节</Text>
      <Button onClick={stopAutoWrite}>停止</Button>
    </div>
  )
}
```

## 现有 API 复用

| 步骤 | 复用 API | 说明 |
|------|----------|------|
| 生成大纲 | `continue_outline_generator` | 一次生成1个 |
| 展开大纲 | `expand_outline` | 传入数量参数3 |
| 写章节 | 现有章节生成逻辑 | 生成约3000字 |
| 分析 | `analyze_chapter_background` | 逐章节分析 |
| 字数统计 | 需新增查询 | sum(chapter.word_count) |

## 数据库模型

**新增 BackgroundTask.type 枚举值：**
- `'auto_write'` - 自动写作任务

**BackgroundTask.extra_data 存储：**
```json
{
  "project_id": "uuid",
  "target_words": 30000,
  "current_words": 0,
  "current_round": 0,
  "completed_outlines": 0,
  "completed_chapters": 0,
  "current_step": "",
  "stopped": false
}
```

## 涉及文件

| 文件 | 改动 |
|------|------|
| `backend/app/api/writing.py` | 新增自动写作 API |
| `backend/app/api/chapters.py` | 可能需要添加展开数量参数 |
| `backend/app/models/background_task.py` | 添加 auto_write 类型 |
| `backend/app/main.py` | 注册新路由 |
| `frontend/src/pages/Outline.tsx` | 添加按钮和进度显示 |
| `frontend/src/services/backgroundTaskService.ts` | 添加轮询逻辑 |

## 成功标准

1. [ ] 点击「AI自动写作」后，后台任务开始执行
2. [ ] 按顺序执行：生成大纲→展开→写章节→分析
3. [ ] 每轮正确处理1个大纲+3个章节
4. [ ] 后台任务面板正确显示进度
5. [ ] 字数达标后自动停止
6. [ ] 用户可以手动停止
