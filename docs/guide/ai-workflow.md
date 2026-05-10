# AI 创作流程详解

本文档详细介绍 MuMuAINovel 中 AI 生成故事大纲、大纲展开为章节、章节分析的技术流程。

## 目录

- [1. 生成大纲](#1-生成大纲)
- [2. 从大纲生成章节](#2-从大纲生成章节)
- [3. 分析章节](#3-分析章节)
- [4. 伏笔系统](#4-伏笔系统)
- [5. 关键技术组件](#5-关键技术组件)

---

## 1. 生成大纲

### API 端点

| 端点 | 函数 | 用途 |
|------|------|------|
| `POST /api/outlines` | `create_outline` | 手动创建大纲 |
| `POST /api/outlines/generate` | `new_outline_generator` (SSE) | AI 生成新大纲 |
| `POST /api/outlines/continue` | `continue_outline_generator` (SSE) | AI 续写大纲 |
| `POST /api/outlines/generate-background` | 后台任务包装器 | 异步生成大纲 |
| `POST /api/outlines/continue-background` | 后台任务包装器 | 异步续写大纲 |

### 服务层

**PromptService** (`backend/app/services/prompt_service.py`):
- 使用模板: `OUTLINE_CREATE`, `OUTLINE_CONTINUE`

**PlotExpansionService** (`backend/app/services/plot_expansion_service.py`):
- 核心章节展开逻辑

### 数据流

```
Frontend (Outline.tsx)
    │
    ├── handleGenerate() / handleContinue()
    │   └── generateOutlineBackground() → POST /api/outlines/generate-background
    │
Backend API
    │
    ├── new_outline_generator() 或 continue_outline_generator()
    │   ├── 加载项目 + 角色信息
    │   ├── PromptService 构建提示词 (OUTLINE_CREATE / OUTLINE_CONTINUE)
    │   ├── 调用 AI (user_ai_service.generate_text_stream())
    │   ├── 解析 AI 响应 (_parse_ai_response())
    │   ├── 保存到 DB (_save_outlines())
    │   └── 验证角色/组织 (_check_and_create_missing_*)
    │
    └── TaskProgressTracker 追踪后台任务进度
```

### 核心函数

**outlines.py**:
- `new_outline_generator()` - 生成新大纲（SSE 流式）
- `continue_outline_generator()` - 续写现有大纲（SSE 流式）
- `_parse_ai_response()` - 解析 AI 返回的 JSON
- `_save_outlines()` - 保存大纲到数据库

---

## 2. 从大纲生成章节

### API 端点

| 端点 | 函数 | 用途 |
|------|------|------|
| `POST /api/outlines/{id}/expand-background` | `expand_outline_to_chapters_background` | 异步展开单个大纲 |
| `POST /api/outlines/{id}/expand-stream` | `expand_outline_to_chapters_stream` | SSE 展开单个大纲 |
| `POST /api/outlines/batch-expand-background` | `batch_expand_outlines_background` | 异步批量展开所有大纲 |
| `POST /api/outlines/batch-expand-stream` | `batch_expand_outlines_stream` | SSE 批量展开所有大纲 |
| `GET /api/outlines/{id}/chapters` | `get_outline_chapters` | 获取大纲下的章节 |

### 服务层

**PlotExpansionService** (`backend/app/services/plot_expansion_service.py`):

```python
analyze_outline_for_chapters(outline, project, db, target_chapter_count, ...)
    ├── target_chapter_count ≤ 5: _generate_chapters_single_batch()
    │   └── 使用 OUTLINE_EXPAND_SINGLE 模板
    │
    └── target_chapter_count > 5: _generate_chapters_in_batches()
        └── 使用 OUTLINE_EXPAND_MULTI 模板（包含前章上下文）

create_chapters_from_plans(outline_id, chapter_plans, project_id, db, ...)
    ├── 自动计算起始章节号（基于前一个大纲的章节数）
    ├── 创建 Chapter 记录（保存 expansion_plan JSON）
    └── 重排后续章节号

_renumber_subsequent_chapters(project_id, current_outline_id, db)
    └── 确保章节号连续
```

### 数据流

```
Frontend (Outline.tsx)
    │
    ├── handleExpandOutline(outlineId) → POST /api/outlines/{id}/expand-background
    │   └── 显示展开弹窗，提交后台任务
    │
    └── handleBatchExpandOutlines() → POST /api/outlines/batch-expand-background
        └── 批量展开所有大纲
            ↓
Backend: _run_outline_expansion_background()
            ↓
PlotExpansionService.analyze_outline_for_chapters()
    ├── 分析大纲结构
    ├── 生成章节规划（key_events, character_focus, scenes 等）
    └── 创建章节记录
```

### expansion_plan JSON 结构

每个章节记录保存的展开规划：

```json
{
  "key_events": ["事件1", "事件2"],
  "character_focus": ["角色名"],
  "emotional_tone": "紧张",
  "narrative_goal": "建立冲突",
  "conflict_type": "人际冲突",
  "estimated_words": 3000,
  "scenes": [
    {
      "location": "场景地点",
      "characters": ["角色1", "角色2"],
      "purpose": "场景目的"
    }
  ]
}
```

---

## 3. 分析章节

### 服务层

**PlotAnalyzer** (`backend/app/services/plot_analyzer.py`):
- `analyze_chapter()` - 主分析函数，支持重试机制（最多 3 次）
- `_parse_analysis_response()` - 解析 AI JSON 响应

### 数据流

```
用户触发分析 → analyze_chapter()
    │
    ├── 截断内容到 8000 字符（如需要）
    ├── 获取 PLOT_ANALYSIS 模板
    ├── 构建已埋伏笔上下文
    ├── 调用 AI（带重试）
    └── 返回分析结果
```

### 分析结果结构

```python
{
    "plot_stage": "发展",           # 情节阶段
    "conflict": {
        "level": 5,                # 冲突等级 0-10
        "types": ["人际冲突"]       # 冲突类型
    },
    "emotional_arc": {
        "primary_emotion": "紧张",
        "intensity": 7              # 0-10
    },
    "hooks": [                     # 悬念/钩子
        {"type": "cliffhanger", "description": "..."}
    ],
    "foreshadows": [               # 伏笔
        {"type": "planted", "content": "...", "target_chapter": 5}
    ],
    "plot_points": [                # 关键情节点
        {"event": "...", "significance": "..."}
    ],
    "character_states": [           # 角色状态
        {"name": "角色名", "state": "...", "arc": "..."}
    ],
    "scenes": [                    # 场景分析
        {"location": "...", "tension": 7, "purpose": "..."}
    ],
    "scores": {                     # 质量评分
        "overall": 8,
        "pacing": 7,
        "dialogue": 6,
        "coherence": 8
    },
    "suggestions": ["改进建议1", "改进建议2"]
}
```

### 调用位置

章节分析在 `Chapters.tsx` 页面触发，用户选中章节后点击「分析」按钮。

---

## 4. 伏笔系统

### 服务层

**ForeshadowService** (`backend/app/services/foreshadow_service.py`):

| 函数 | 用途 |
|------|------|
| `get_project_foreshadows()` | 获取项目所有伏笔 |
| `get_planted_foreshadows_for_analysis()` | 获取待匹配的伏笔列表 |
| `create_foreshadow()` | 手动创建伏笔 |
| `update_foreshadow()` | 更新伏笔 |
| `resolve_foreshadow()` | 标记伏笔为已回收 |
| `build_chapter_context()` | 构建章节上下文（包含待回收伏笔） |

### 数据模型

**Foreshadow** (`backend/app/models/foreshadow.py`):

| 字段 | 用途 |
|------|------|
| `id` | 伏笔 ID |
| `project_id` | 所属项目 |
| `title` | 伏笔标题 |
| `content` | 伏笔内容 |
| `status` | 状态: pending / resolved |
| `source_type` | 来源: manual / analysis |
| `plant_chapter_number` | 埋入章节号 |
| `target_resolve_chapter_number` | 计划回收章节号 |

### 伏笔追踪流程

```
1. 章节分析时
   └── PlotAnalyzer.analyze_chapter() 识别伏笔
       └── 保存到 PlotAnalysis.foreshadows

2. 章节生成时
   └── ForeshadowService.build_chapter_context()
       └── 将待回收伏笔注入上下文
       └── AI 在生成时考虑伏笔回收

3. 手动伏笔管理
   └── 用户可在伏笔页面创建/编辑/回收伏笔
```

---

## 5. 关键技术组件

### PromptService

提示词模板服务，统一管理所有 AI 提示词。

**模板类型**:
- `OUTLINE_CREATE` - 新建大纲
- `OUTLINE_CONTINUE` - 续写大纲
- `OUTLINE_EXPAND_SINGLE` - 展开为章节（少量）
- `OUTLINE_EXPAND_MULTI` - 展开为章节（多量，含前章上下文）
- `PLOT_ANALYSIS` - 章节分析

### TaskProgressTracker

后台任务进度追踪器 (`backend/app/services/background_task_service.py`)。

```python
class TaskProgressTracker:
    async def start(message)      # 任务开始
    async def loading(message)    # 加载中
    async def preparing(message)  # 准备中
    async def generating(...)    # 生成中
    async def parsing(message)   # 解析中
    async def saving(...)       # 保存中
    async def complete(message)  # 完成
    async def error(message)     # 错误
    async def check_cancelled()  # 检查是否被取消
```

### AI 服务架构

```
ai_service.py (统一入口)
    │
    ├── OpenAI 客户端
    ├── Gemini 客户端
    ├── Claude 客户端
    └── MiniMax 客户端
```

---

## 前端集成

### 后台任务服务

`frontend/src/services/backgroundTaskService.ts`:

| 函数 | 用途 |
|------|------|
| `pollTaskUntilComplete()` | 轮询任务状态（每 2 秒） |
| `getProjectTasks()` | 获取项目所有任务 |
| `cancelTask()` | 取消运行中的任务 |

### 事件总线

`frontend/src/store/eventBus.ts`:

```typescript
eventBus.emit('background-task-created')  // 通知任务面板刷新
```

### Outline.tsx 关键函数

| 函数 | 用途 |
|------|------|
| `showGenerateModal()` | 打开生成弹窗 |
| `handleGenerate()` | 触发新大纲生成 |
| `handleContinue()` | 触发大纲续写 |
| `handleExpandOutline()` | 展开大纲为章节 |
| `handleBatchExpandOutlines()` | 批量展开大纲 |

---

## 相关文件索引

| 功能 | 文件路径 |
|------|---------|
| 大纲 API | `backend/app/api/outlines.py` |
| 章节展开服务 | `backend/app/services/plot_expansion_service.py` |
| 章节分析服务 | `backend/app/services/plot_analyzer.py` |
| 伏笔服务 | `backend/app/services/foreshadow_service.py` |
| 提示词服务 | `backend/app/services/prompt_service.py` |
| 后台任务服务 | `backend/app/services/background_task_service.py` |
| 前端大纲页 | `frontend/src/pages/Outline.tsx` |
| 前端任务服务 | `frontend/src/services/backgroundTaskService.ts` |
| 大纲数据模型 | `backend/app/models/outline.py` |
| 章节数据模型 | `backend/app/models/chapter.py` |
| 伏笔数据模型 | `backend/app/models/foreshadow.py` |
| 分析结果模型 | `backend/app/models/memory.py` (PlotAnalysis) |
