# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

MuMuAINovel 是一个基于 AI 的智能小说创作助手，支持多 AI 模型（OpenAI/Gemini/Claude）、项目管理、大纲生成、角色关系管理、章节创作等功能。

## 开发命令

### 前端（使用 pnpm，禁止使用 npm）

```bash
cd frontend
pnpm install          # 安装依赖
pnpm dev              # 开发模式
pnpm build            # 生产构建
pnpm lint             # 代码检查
pnpm preview          # 预览构建结果
```

### 后端（使用 uv 管理 Python 版本）

```bash
cd backend
uv pip install --system -r requirements.txt   # 安装依赖（使用 uv 管理 Python 版本）
uv run python -m uvicorn app.main:app --host localhost --port 8000 --reload   # 开发模式
```

或者直接使用系统 Python 安装依赖后运行：
```bash
cd backend
pip install -r requirements.txt   # 安装依赖
python -m uvicorn app.main:app --host localhost --port 8000 --reload   # 开发模式
```

### Docker 部署

```bash
docker-compose up -d          # 启动服务
docker-compose logs -f        # 查看日志
docker-compose down            # 停止服务
```

### 数据库迁移

```bash
cd backend
alembic upgrade head           # 执行迁移
alembic revision --autogenerate -m "描述"  # 生成新迁移
```

## 架构

### 后端架构 (FastAPI)

```
backend/
├── app/
│   ├── api/              # API 路由（按功能模块组织）
│   │   ├── auth.py       # 认证（OAuth2 本地登录）
│   │   ├── chapters.py   # 章节管理
│   │   ├── characters.py # 角色管理
│   │   ├── projects.py   # 项目管理
│   │   ├── outlines.py   # 大纲管理
│   │   └── ...
│   ├── models/           # SQLAlchemy 数据模型
│   ├── schemas/          # Pydantic 请求/响应模型
│   ├── services/         # 业务逻辑层
│   │   ├── ai_service.py        # AI 服务统一入口
│   │   ├── ai_clients/          # AI 客户端（OpenAI/Gemini/Anthropic）
│   │   └── ai_providers/        # AI Provider 实现
│   ├── middleware/       # 中间件（认证、请求ID）
│   └── mcp/             # MCP 插件系统
├── alembic/             # 数据库迁移
└── scripts/            # 工具脚本
```

### 前端架构 (React + TypeScript)

```
frontend/src/
├── pages/               # 页面组件（按路由组织）
│   ├── BookshelfPage.tsx    # 书架/项目列表
│   ├── Chapters.tsx         # 章节编辑页（核心页面）
│   ├── Characters.tsx       # 角色管理页
│   └── ...
├── components/          # 通用组件
│   ├── ChapterReader.tsx    # 章节阅读器
│   └── ...
├── services/            # API 调用层
│   ├── api.ts           # axios 实例和 API 方法
│   └── ...
└── store/              # Zustand 状态管理
```

### AI 服务架构

AI 服务采用客户端-提供者模式：
- `ai_clients/` - 各模型 SDK 封装（OpenAI、Gemini、Anthropic）
- `ai_providers/` - 统一接口实现，适配不同模型
- `ai_service.py` - 统一入口，根据配置调用对应 Provider

### MCP 插件系统

位于 `backend/app/mcp/`，使用 Model Context Protocol 实现插件扩展，参考 `backend/app/mcp/README`。

## 配置

环境变量配置通过 `backend/.env` 文件管理，参考 `backend/.env.example`。

关键配置项：
- `DATABASE_URL` - PostgreSQL 连接字符串
- `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` - AI 服务密钥
- `DEFAULT_AI_PROVIDER` - 默认 AI 提供商
- `LOCAL_AUTH_ENABLED` - 是否启用本地账户登录

## 重要文件

- `backend/app/main.py` - FastAPI 应用入口、路由注册
- `backend/database.py` - 数据库连接和会话管理
- `backend/app/config.py` - 应用配置（Pydantic Settings）
- `backend/app/services/prompt_service.py` - Prompt 模板服务
- `frontend/src/services/api.ts` - 前端 API 调用封装
