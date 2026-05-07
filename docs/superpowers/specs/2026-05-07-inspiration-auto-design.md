# 灵感后台模式设计文档

> **Goal:** 在首页添加"灵感后台"入口，用户输入一句话想法，AI自动生成所有答案并创建后台任务，全程无需用户确认。

## Architecture

用户点击"灵感后台"后，系统自动完成以下流程：
1. AI生成书名 (title)
2. AI生成简介 (description)
3. AI生成主题 (theme)
4. AI生成类型标签 (genre)
5. 使用默认值：视角=第一人称，大纲模式=一对一
6. 创建后台任务

默认配置：
- 目标字数：100000
- 章节数：3
- 角色数：5

## UI Components

### 1. 书架页新增按钮

**File:** `frontend/src/pages/BookshelfPage.tsx`

在现有的"快速开始"和"灵感模式"按钮旁边新增"灵感后台"按钮。

### 2. 灵感后台模态框

**New File:** `frontend/src/components/InspirationAutoModal.tsx`

模态框包含：
- 标题："灵感后台创建"
- 大文本输入框：placeholder="输入你的创作想法，如：写一个穿越到古代成为王妃的故事"
- 提示文字："将自动生成书名、简介、主题等全部内容并在后台创建项目"
- 取消按钮
- 开始创建按钮

### 3. 后端API

**New Endpoint:** `POST /inspiration/auto`

**Request:**
```json
{
  "initial_idea": "string"
}
```

**Response:**
```json
{
  "task_id": "string",
  "message": "后台任务已创建"
}
```

**File:** `backend/app/api/inspiration.py`

内部逻辑：
1. 调用 `generate_options("title", {initial_idea})` 获取第一个选项作为title
2. 调用 `generate_options("description", {initial_idea, title})` 获取第一个选项作为description
3. 调用 `generate_options("theme", {initial_idea, title, description})` 获取第一个选项作为theme
4. 调用 `generate_options("genre", {initial_idea, title, description, theme})` 获取标签作为genre
5. 使用默认值：`narrative_perspective="第一人称"`, `outline_mode="one-to-one"`
6. 调用 `_run_inspiration_bg()` 创建后台任务

## File Changes

### Frontend
- `frontend/src/pages/BookshelfPage.tsx` - 新增灵感后台按钮
- `frontend/src/components/InspirationAutoModal.tsx` - 新建模态框组件
- `frontend/src/services/api.ts` - 新增 `inspirationAutoApi.createAutoTask(initial_idea)` 方法

### Backend
- `backend/app/api/inspiration.py` - 新增 `POST /inspiration/auto` 端点

## Interaction Flow

1. 用户在首页点击"灵感后台"
2. 弹出模态框，用户输入创作想法
3. 点击"开始创建"
4. 显示 loading 状态："正在生成内容..."
5. 调用后端API，后端依次调用AI生成各字段
6. 后端创建后台任务，返回 task_id
7. 前端显示成功提示："灵感后台任务已创建"
8. 模态框关闭
9. 右下角浮窗自动显示任务进度
10. 用户可继续在首页操作，任务在后台执行

## Error Handling

- AI生成失败：返回错误提示，任务不创建
- 网络错误：显示重试按钮
- 后台任务创建失败：提示用户重试

## Task Progress Stages

与现有灵感后台任务一致：
- 0-25%: 项目创建+世界观生成
- 25-50%: 职业体系生成
- 50-75%: 角色生成
- 75-100%: 大纲生成
