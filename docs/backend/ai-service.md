# AI 服务

## 概述

AI 服务是 MuMuAINovel 的核心模块，提供统一的 AI 模型调用接口。

## 支持的模型

| 提供商 | 模型 | 说明 |
|--------|------|------|
| OpenAI | gpt-4, gpt-3.5-turbo | OpenAI GPT 系列 |
| Anthropic | claude-3-opus, claude-3-sonnet | Claude 3 系列 |
| Google | gemini-pro, gemini-pro-vision | Gemini 模型 |
| MiniMax | MiniMax-Text-01 | MiniMax 文本模型 |
| CiYuan | CiYuan-sdk | 磁元 API |

## 使用方式

### 直接调用

```python
from app.services.ai_service import AIService

async def generate_story():
    ai_service = AIService()

    result = await ai_service.generate(
        provider="openai",
        model="gpt-4",
        prompt="请为我的玄幻小说生成第一章的大纲..."
    )

    return result
```

### 使用 Provider

```python
from app.services.ai_providers.openai_provider import OpenAIProvider

provider = OpenAIProvider()
response = await provider.generate(prompt="生成章节内容")
```

## Prompt 模板

### 模板配置

Prompt 模板存储在数据库中，可通过管理界面动态调整。

### 内置模板

| 模板名称 | 用途 |
|----------|------|
| `chapter_generation` | 章节生成 |
| `outline_generation` | 大纲生成 |
| `character_creation` | 角色创建 |
| `cover_prompt` | 封面描述生成 |

## 配置

在 `.env` 中配置默认 AI 提供商：

```env
DEFAULT_AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
MINIMAX_API_KEY=...
```
