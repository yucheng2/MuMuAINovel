# 灵感后台模式实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在首页添加"灵感后台"入口，用户输入一句话想法，AI自动生成所有答案并创建后台任务，全程无需用户确认。

**Architecture:** 后端新增 `POST /inspiration/auto` 端点，内部依次调用AI生成title/description/theme/genre，然后创建后台任务。前端新增模态框组件和书架页按钮，调用该API后显示任务创建成功提示。

**Tech Stack:** React + TypeScript + Ant Design (frontend), FastAPI + SQLAlchemy (backend)

---

## Task 1: 后端 - 新增 `POST /inspiration/auto` 端点

**Files:**
- Modify: `backend/app/api/inspiration.py:712` (after the retry endpoint)

### 步骤 1: 添加 request/response model

在 `InspirationRetryResponse` 之后添加:

```python
class InspirationAutoRequest(BaseModel):
    initial_idea: str


class InspirationAutoResponse(BaseModel):
    task_id: str
    message: str
```

### 步骤 2: 添加 auto 端点

由于 `generate_options` 使用 FastAPI `Depends` 依赖注入，直接调用会导致循环依赖问题。因此在新端点中直接实现生成逻辑（参考 `generate_options` 的实现，不使用重试机制）。

在 `retry_inspiration_task` 之后添加:

```python
async def _generate_single_option(
    step: str,
    context: Dict[str, Any],
    user_id: str,
    db: AsyncSession,
    ai_service: AIService
) -> str:
    """内部辅助函数：生成单个选项（不重试）"""
    template_key_map = {
        "title": ("INSPIRATION_TITLE_SYSTEM", "INSPIRATION_TITLE_USER"),
        "description": ("INSPIRATION_DESCRIPTION_SYSTEM", "INSPIRATION_DESCRIPTION_USER"),
        "theme": ("INSPIRATION_THEME_SYSTEM", "INSPIRATION_THEME_USER"),
        "genre": ("INSPIRATION_GENRE_SYSTEM", "INSPIRATION_GENRE_USER")
    }
    template_keys = template_key_map.get(step)
    if not template_keys:
        raise ValueError(f"不支持的步骤: {step}")

    system_key, user_key = template_keys
    system_template = await PromptService.get_template(system_key, user_id, db)
    user_template = await PromptService.get_template(user_key, user_id, db)

    format_params = {
        "initial_idea": context.get("initial_idea", context.get("description", "")),
        "title": context.get("title", ""),
        "description": context.get("description", ""),
        "theme": context.get("theme", "")
    }
    system_prompt = system_template.format(**format_params)
    user_prompt = user_template.format(**format_params)

    temperature = TEMPERATURE_SETTINGS.get(step, 0.7)
    accumulated_text = ""
    async for chunk in ai_service.generate_text_stream(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=temperature
    ):
        accumulated_text += chunk

    cleaned_content = ai_service._clean_json_response(accumulated_text)
    result = loads_json(cleaned_content)

    if "options" in result and result["options"]:
        return result["options"][0]
    raise ValueError(f"生成{step}失败")


@router.post("/auto", response_model=InspirationAutoResponse)
async def create_inspiration_auto_task(
    data: InspirationAutoRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """一键灵感后台模式：AI自动生成所有答案并创建后台任务"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="需要登录")

    ai_service = await get_user_ai_service(request, db)

    context = {
        "initial_idea": data.initial_idea,
        "title": "",
        "description": "",
        "theme": ""
    }

    # 1. 生成书名
    try:
        title = await _generate_single_option("title", context, user_id, db, ai_service)
        context["title"] = title
    except Exception as e:
        logger.error(f"书名生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"书名生成失败: {str(e)}")

    # 2. 生成简介
    try:
        description = await _generate_single_option("description", context, user_id, db, ai_service)
        context["description"] = description
    except Exception as e:
        logger.error(f"简介生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"简介生成失败: {str(e)}")

    # 3. 生成主题
    try:
        theme = await _generate_single_option("theme", context, user_id, db, ai_service)
        context["theme"] = theme
    except Exception as e:
        logger.error(f"主题生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"主题生成失败: {str(e)}")

    # 4. 生成类型
    try:
        genre = await _generate_single_option("genre", context, user_id, db, ai_service)
    except Exception as e:
        logger.error(f"类型生成失败: {e}")
        genre = "都市"  # 默认类型

    # 构建后台任务输入
    task_input = {
        "title": title,
        "description": description,
        "theme": theme,
        "genre": genre,
        "narrative_perspective": "第一人称",
        "outline_mode": "one-to-one",
    }

    # 创建后台任务
    task = await BackgroundTaskService.create_task(
        user_id=user_id,
        project_id=None,
        task_type="inspiration",
        task_input=task_input,
        db=db,
    )

    task_input["user_id"] = user_id
    await background_task_service.spawn_background_task(
        task.id,
        user_id,
        _run_inspiration_bg,
        task_input=task_input,
        task_type="inspiration",
    )

    return InspirationAutoResponse(
        task_id=task.id,
        message="后台任务已创建",
    )
```

---

## Task 2: 前端 - 新增 API 方法

**Files:**
- Modify: `frontend/src/services/api.ts` (在 `inspirationBackgroundApi` 之后添加)

### 步骤 1: 添加 `inspirationAutoApi`

在 `inspirationBackgroundApi` 定义之后添加:

```typescript
export const inspirationAutoApi = {
  createAutoTask: async (initialIdea: string) => {
    const response = await api.post<{ initial_idea: string }, { task_id: string; message: string }>(
      '/inspiration/auto',
      { initial_idea: initialIdea }
    );
    return response;
  },
};
```

---

## Task 3: 前端 - 新建 InspirationAutoModal 组件

**Files:**
- Create: `frontend/src/components/InspirationAutoModal.tsx`

### 步骤 1: 创建组件

```tsx
import React, { useState } from 'react';
import { Modal, Input, Space, Typography, message } from 'antd';
import { BulbOutlined } from '@ant-design/icons';
import { inspirationAutoApi } from '../services/api';
import { eventBus } from '../store/eventBus';

const { TextArea } = Input;
const { Text } = Typography;

interface InspirationAutoModalProps {
  open: boolean;
  onClose: () => void;
}

export const InspirationAutoModal: React.FC<InspirationAutoModalProps> = ({
  open,
  onClose,
}) => {
  const [idea, setIdea] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!idea.trim()) {
      message.warning('请输入创作想法');
      return;
    }

    setLoading(true);
    try {
      const result = await inspirationAutoApi.createAutoTask(idea.trim());
      message.success('灵感后台任务已创建');
      eventBus.emit('background-task-created');
      setIdea('');
      onClose();
    } catch (error: any) {
      console.error('创建灵感后台任务失败:', error);
      message.error(error?.response?.data?.detail || '创建失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (!loading) {
      setIdea('');
      onClose();
    }
  };

  return (
    <Modal
      title={
        <Space>
          <BulbOutlined style={{ color: '#faad14' }} />
          <span>灵感后台创建</span>
        </Space>
      }
      open={open}
      onCancel={handleCancel}
      closable={!loading}
      maskClosable={!loading}
      keyboard={!loading}
      footer={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            将自动生成书名、简介、主题等全部内容
          </Text>
          <Space>
            <Button onClick={handleCancel} disabled={loading}>
              取消
            </Button>
            <Button type="primary" onClick={handleCreate} loading={loading}>
              开始创建
            </Button>
          </Space>
        </Space>
      }
      width={500}
      centered
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          输入你的创作想法：
        </Text>
        <TextArea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="例如：写一个穿越到古代成为王妃的故事"
          rows={4}
          maxLength={500}
          showCount
          disabled={loading}
        />
      </div>
    </Modal>
  );
};

export default InspirationAutoModal;
```

---

## Task 4: 前端 - 在书架页添加灵感后台按钮

**Files:**
- Modify: `frontend/src/pages/BookshelfPage.tsx` (在 `onOpenInspiration` 定义之后添加 `onOpenInspirationAuto`)

### 步骤 1: 导入新组件和图标

在 `BookshelfPage.tsx` 顶部找到:
```tsx
import { RocketOutlined, BulbOutlined } from '@ant-design/icons';
```

改为:
```tsx
import { RocketOutlined, BulbOutlined, ThunderboltOutlined } from '@ant-design/icons';
```

找到:
```tsx
import { InspirationMode } from '../components/InspirationMode';
```

在之后添加:
```tsx
import { InspirationAutoModal } from '../components/InspirationAutoModal';
```

### 步骤 2: 添加 state 和 handler

找到 `const [isInspirationOpen, setIsInspirationOpen] = useState(false);`，在其后添加:

```tsx
const [isInspirationAutoOpen, setIsInspirationAutoOpen] = useState(false);
```

找到 `const onOpenInspiration = () => setIsInspirationOpen(true);`，在其后添加:

```tsx
const onOpenInspirationAuto = () => setIsInspirationAutoOpen(true);
```

### 步骤 3: 添加按钮

在灵感模式按钮之后添加:

```tsx
<Button
  size={isMobile ? 'middle' : 'large'}
  icon={<ThunderboltOutlined />}
  onClick={onOpenInspirationAuto}
  style={{
    height: isMobile ? 42 : 52,
    fontSize: isMobile ? '14px' : '16px',
    borderRadius: 10,
    borderColor: alphaColor(token.colorWarning, isDark ? 0.34 : 0.5),
    color: `color-mix(in srgb, ${token.colorWarning} ${isDark ? 78 : 72}%, ${token.colorText} ${isDark ? 22 : 28}%)`,
    background: `linear-gradient(180deg, ${alphaColor(token.colorWarning, isDark ? 0.12 : 0.12)} 0%, ${alphaColor(token.colorWarning, isDark ? 0.2 : 0.2)} 100%)`,
  }}
  block
>
  灵感后台
</Button>
```

### 步骤 4: 添加模态框组件

在 InspirationMode 组件之后添加:

```tsx
<InspirationAutoModal
  open={isInspirationAutoOpen}
  onClose={() => setIsInspirationAutoOpen(false)}
/>
```

---

## Task 5: 测试验证

### 步骤 1: 启动后端服务

```bash
cd backend && uv run python -m uvicorn app.main:app --host localhost --port 8000 --reload
```

### 步骤 2: 启动前端服务

```bash
cd frontend && pnpm dev
```

### 步骤 3: 测试流程

1. 访问首页 `http://localhost:8888`
2. 点击"灵感后台"按钮
3. 弹出模态框，输入创作想法
4. 点击"开始创建"
5. 等待 API 调用完成，显示"灵感后台任务已创建"
6. 模态框关闭，右下角显示任务浮窗
7. 观察任务进度（世界观生成 → 职业体系 → 角色生成 → 大纲生成）
8. 任务完成后在书架页查看新创建的项目
