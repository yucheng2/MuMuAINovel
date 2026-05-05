# AI 提供商配置

## 配置多提供商

MuMuAINovel 支持同时配置多个 AI 提供商。

## OpenAI 配置

```env
OPENAI_API_KEY=sk-xxxxx
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

## Anthropic 配置

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-opus-20240229
```

## Google Gemini 配置

```env
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-pro
```

## MiniMax 配置

```env
MINIMAX_API_KEY=your-minimax-key
MINIMAX_MODEL=MiniMax-Text-01
```

## 切换提供商

### 通过 API 切换

```http
POST /api/ai/generate
Content-Type: application/json

{
  "provider": "anthropic",
  "model": "claude-3-sonnet",
  "prompt": "你的 prompt"
}
```

### 通过前端切换

在设置页面选择默认 AI 提供商。
