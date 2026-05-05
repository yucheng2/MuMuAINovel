# 环境变量

## 配置方式

在 `backend/.env` 文件中配置。

## 必填变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql://user:pass@localhost:5432/db` |

## AI 相关变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | 当使用 OpenAI 时 |
| `ANTHROPIC_API_KEY` | Anthropic API Key | 当使用 Claude 时 |
| `GEMINI_API_KEY` | Google Gemini API Key | 当使用 Gemini 时 |
| `MINIMAX_API_KEY` | MiniMax API Key | 当使用 MiniMax 时 |
| `DEFAULT_AI_PROVIDER` | 默认 AI 提供商 | 是 |

## 服务变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `API_HOST` | `localhost` | API 服务地址 |
| `API_PORT` | `8000` | API 服务端口 |
| `FRONTEND_PORT` | `3000` | 前端服务端口 |

## 安全变量

| 变量名 | 说明 |
|--------|------|
| `SECRET_KEY` | JWT 签名密钥 |
| `ALGORITHM` | JWT 算法，默认 `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间 |
