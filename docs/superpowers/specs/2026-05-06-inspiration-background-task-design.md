# 灵感模式后台创建任务设计

## 概述

在灵感模式 `/inspiration` 页面，将确认创建改为支持后台执行。后台创建的任务会显示在右下角浮窗，并展示各个生成阶段的进度。

## 用户交互流程

1. 用户在灵感模式完成对话流程，进入确认步骤
2. 页面显示两个按钮：**确认创建** 和 **后台创建**（并排）
3. 用户点击"后台创建"：
   - 前端：显示 toast 提示"已在后台开始生成"
   - 跳转到主页 `http://localhost:8888`
4. 右下角浮窗自动展开，显示任务进度
5. 任务完成后，显示完成提示

## 阶段划分

灵感模式后台创建包含 4 个阶段，对应现有 wizard-stream 的 4 个步骤：

| 阶段 | 进度范围 | 说明 |
|------|----------|------|
| 项目创建 | 0-25% | 创建项目 + 生成世界观 |
| 职业体系 | 25-50% | 生成职业体系 |
| 角色生成 | 50-75% | 批量生成角色、关系、组织 |
| 大纲生成 | 75-100% | 生成大纲节点 |

每个阶段内部使用 `TaskProgressTracker` 报告详细进度。

## API 设计

### 新建端点

```
POST /api/inspiration/background
```

**请求体：**
```json
{
  "title": "小说标题",
  "description": "小说描述",
  "theme": "主题",
  "genre": "题材",
  "narrative_perspective": "叙事视角",
  "outline_mode": "one-to-one | one-to-many"
}
```

**响应：**
```json
{
  "task_id": "uuid-string",
  "message": "后台任务已创建"
}
```

### 后端处理逻辑

1. 创建 `BackgroundTask` 记录，`task_type = "inspiration"`
2. 使用 `spawn_background_task` 异步执行 `_run_inspiration_bg`
3. `_run_inspiration_bg` 内部依次调用 4 个步骤：
   - `wizard_stream_api.generate_world_building()` → 0-25%
   - `wizard_stream_api.generate_career_system()` → 25-50%
   - `wizard_stream_api.generate_characters()` → 50-75%
   - `wizard_stream_api.generate_outline()` → 75-100%

### 进度详情结构 (progress_details)

```json
{
  "stage": "world_building | career_system | characters | outline",
  "stage_progress": 0.5,
  "message": "正在生成职业体系...",
  "project_id": "uuid-string"
}
```

## 前端改动

### Inspiration.tsx

1. 修改确认步骤的选项数组：
   ```typescript
   // 原来: ['✅ 确认创建', '🔄 重新开始']
   // 现在: ['✅ 确认创建', '🔄 后台创建', '🔄 重新开始']
   ```

2. 处理"后台创建"选项：
   ```typescript
   if (option === '🔄 后台创建') {
     // 调用 POST /api/inspiration/background
     // 显示 toast 提示
     // 跳转到主页
     window.location.href = 'http://localhost:8888';
   }
   ```

### FloatingTaskPanel.tsx

1. 添加 `inspiration` 任务类型的显示支持：
   - 任务类型标签：显示"灵感创建"
   - 图标：使用创意/灯泡图标

### API 客户端

新增 `inspirationBackgroundApi.createBackgroundTask()` 方法。

## 错误处理

- 任务失败：浮窗显示错误状态，可查看错误详情
- 取消任务：用户可点击取消按钮终止后台任务
- 任务中断后：保留已生成的数据，清理未完成的数据

## 数据库改动

无新表创建，复用现有的 `BackgroundTask` 表。

## 风险与注意事项

1. 后台创建可能耗时较长（5-10分钟），需要设置合理的超时时间
2. 任务执行期间用户不能再次创建，需要检查是否有进行中的 `inspiration` 任务
3. 任务完成后需要更新 `project.wizard_status = "completed"`
