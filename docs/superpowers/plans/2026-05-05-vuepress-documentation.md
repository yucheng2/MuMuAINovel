# VuePress 文档站点实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 MuMuAINovel 项目创建完整的 VuePress 文档站点，放在根目录 `docs/` 下，使用简体中文。

**Architecture:** 使用 VuePress 2.x (最新版本) + Vite 构建，遵循 VuePress 默认主题约定，创建完整的项目文档体系。

**Tech Stack:** VuePress 2.x, pnpm, Vue 3, TypeScript

---

## 文件结构规划

```
docs/
├── .vuepress/                    # VuePress 配置目录
│   ├── config.ts                 # 主配置文件
│   ├── theme.ts                  # 主题配置
│   ├── nav.ts                    # 导航栏配置
│   ├── sidebar.ts                # 侧边栏配置
│   └── styles/                   # 自定义样式
│       └── index.scss
├── index.md                      # 首页
├── guide/                       # 指南
│   ├── README.md                # 指南首页
│   ├── intro.md                  # 项目介绍
│   ├── quick-start.md            # 快速开始
│   ├── installation.md          # 安装指南
│   └── deployment.md             # 部署说明
├── backend/                      # 后端文档
│   ├── README.md                # 后端文档首页
│   ├── api.md                   # API 文档
│   ├── architecture.md           # 架构说明
│   ├── ai-service.md             # AI 服务
│   ├── mcp.md                    # MCP 插件系统
│   └── database.md               # 数据库
├── frontend/                    # 前端文档
│   ├── README.md
│   ├── components.md             # 组件
│   ├── pages.md                  # 页面
│   └── state.md                  # 状态管理
├── config/                      # 配置文档
│   ├── README.md
│   ├── environment.md            # 环境变量
│   └── ai-providers.md           # AI 提供商配置
└── public/                       # 静态资源
```

---

## Task 1: 初始化 VuePress 项目

**Files:**
- Create: `docs/package.json`
- Create: `docs/pnpm-lock.yaml` (自动生成)
- Create: `docs/.gitignore`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "mumuainovel-docs",
  "version": "1.0.0",
  "description": "MuMuAINovel 智能小说创作助手文档",
  "scripts": {
    "dev": "vuepress dev docs",
    "build": "vuepress build docs",
    "clean": "vuepress clean docs"
  },
  "devDependencies": {
    "vuepress": "^2.0.0-rc.0",
    "@vuepress/theme-default": "^2.0.0-rc.0",
    "vuepress-plugin-search-pro": "^2.0.0-rc.0"
  }
}
```

- [ ] **Step 2: 创建 .gitignore**

```
node_modules/
.vuepress/
dist/
.cache/
```

- [ ] **Step 3: 安装依赖**

Run: `cd docs && pnpm install`
Expected: 依赖安装成功

- [ ] **Step 4: 初始化 git 子模块（可选）**

如果需要在主项目中也管理 docs，可以初始化为 git 子模块，否则跳过。

- [ ] **Step 5: 提交**

```bash
cd docs && git init && git add package.json .gitignore && git commit -m "docs: 初始化 VuePress 项目结构"
```

---

## Task 2: 配置 VuePress 主配置

**Files:**
- Create: `docs/.vuepress/config.ts`
- Create: `docs/.vuepress/theme.ts`
- Create: `docs/.vuepress/nav.ts`
- Create: `docs/.vuepress/sidebar.ts`

- [ ] **Step 1: 创建主配置文件**

```typescript
import { defineUserConfig } from 'vuepress'
import { defaultTheme } from '@vuepress/theme-default'
import { navbar, sidebar } from './configs'

export default defineUserConfig({
  lang: 'zh-CN',
  title: 'MuMuAINovel',
  description: 'AI 智能小说创作助手',

  base: '/',

  head: [
    ['link', { rel: 'icon', href: '/images/logo.png' }],
    ['meta', { name: 'theme-color', content: '#3eaf7c' }],
  ],

  theme: defaultTheme({
    logo: '/images/logo.png',
    repo: 'yucheng2/MuMuAINovel',
    docsDir: 'docs',
    editLink: true,
    editLinkText: '编辑此页',
    lastUpdated: true,
    lastUpdatedText: '上次更新',
    contributors: false,
    navbar,
    sidebar,
    colorModeSwitch: true,
  }),

  plugins: [],
})
```

- [ ] **Step 2: 创建 configs 目录和导出文件**

```typescript
// docs/.vuepress/configs/index.ts
export * from './navbar'
export * from './sidebar'
```

- [ ] **Step 3: 创建导航栏配置**

```typescript
// docs/.vuepress/configs/navbar.ts
import { navbar } from '@vuepress/theme-default'

export const navbarConfig = navbar([
  { text: '指南', link: '/guide/' },
  { text: '后端', link: '/backend/' },
  { text: '前端', link: '/frontend/' },
  { text: '配置', link: '/config/' },
  {
    text: '更多',
    children: [
      { text: '更新日志', link: '/CHANGELOG.md' },
      { text: 'GitHub', link: 'https://github.com/yucheng2/MuMuAINovel' },
    ],
  },
])
```

- [ ] **Step 4: 创建侧边栏配置**

```typescript
// docs/.vuepress/configs/sidebar.ts
import { sidebar } from '@vuepress/theme-default'

export const sidebarConfig = {
  '/guide/': [
    {
      text: '指南',
      children: [
        '/guide/README.md',
        '/guide/intro.md',
        '/guide/quick-start.md',
        '/guide/installation.md',
        '/guide/deployment.md',
      ],
    },
  ],
  '/backend/': [
    {
      text: '后端文档',
      children: [
        '/backend/README.md',
        '/backend/architecture.md',
        '/backend/api.md',
        '/backend/ai-service.md',
        '/backend/mcp.md',
        '/backend/database.md',
      ],
    },
  ],
  '/frontend/': [
    {
      text: '前端文档',
      children: [
        '/frontend/README.md',
        '/frontend/components.md',
        '/frontend/pages.md',
        '/frontend/state.md',
      ],
    },
  ],
  '/config/': [
    {
      text: '配置文档',
      children: [
        '/config/README.md',
        '/config/environment.md',
        '/config/ai-providers.md',
      ],
    },
  ],
}
```

- [ ] **Step 5: 提交**

```bash
git add .vuepress/config.ts .vuepress/configs/ && git commit -m "docs: 添加 VuePress 核心配置"
```

---

## Task 3: 创建首页和基础页面

**Files:**
- Create: `docs/index.md`
- Create: `docs/guide/README.md`
- Create: `docs/guide/intro.md`
- Create: `docs/public/images/` (目录)

- [ ] **Step 1: 创建首页**

```markdown
---
home: true
heroImage: /images/logo.png
heroText: MuMuAINovel
tagline: AI 智能小说创作助手

features:
  - title: 多 AI 模型支持
    details: 支持 OpenAI、Claude、Gemini、MiniMax 等多种 AI 模型，提供统一的调用接口
    emoji: 🤖
  - title: 智能章节生成
    details: 基于大纲和上下文，批量生成高质量小说章节
    emoji: 📖
  - title: 角色关系管理
    details: 可视化角色关系图谱，管理人物设定和剧情关联
    emoji: 👥
  - title: MCP 插件扩展
    details: 支持 Model Context Protocol 插件系统，可扩展更多功能
    emoji: 🔌
  - title: 封面自动生成
    details: 基于 AI 生成小说封面图片
    emoji: 🎨
  - title: 向量记忆系统
    details: 借助 ChromaDB 实现长期记忆，保持创作一致性
    emoji: 🧠

footer: MIT License | Copyright © 2024-present
```

- [ ] **Step 2: 创建指南首页**

```markdown
---
title: 指南
---

# 指南

欢迎使用 MuMuAINovel 文档！

## 目录

- [项目介绍](./intro.md) - 了解 MuMuAINovel 是什么
- [快速开始](./quick-start.md) - 快速上手使用
- [安装指南](./installation.md) - 详细安装步骤
- [部署说明](./deployment.md) - 生产环境部署
```

- [ ] **Step 3: 创建项目介绍页**

```markdown
# 项目介绍

MuMuAINovel 是一个基于 AI 的智能小说创作助手，旨在帮助作者更高效地创作小说。

## 核心功能

### 多 AI 模型支持
支持 OpenAI GPT、Anthropic Claude、Google Gemini、MiniMax、磁元等多种 AI 模型。

### 智能创作
- **大纲生成**: 根据设定自动生成故事大纲
- **章节创作**: 基于大纲和上下文批量生成章节
- **角色管理**: 管理人物设定、性格、外貌等属性
- **关系图谱**: 可视化角色之间的关系

### 插件扩展
基于 Model Context Protocol (MCP) 的插件系统，支持自定义扩展。

## 技术栈

### 后端
- FastAPI - Python Web 框架
- SQLAlchemy - ORM
- PostgreSQL - 数据库
- LangChain - AI 工具链
- ChromaDB - 向量数据库

### 前端
- React 18 + TypeScript
- Ant Design 5 - UI 组件库
- Zustand - 状态管理
- Vite - 构建工具
```

- [ ] **Step 4: 提交**

```bash
git add index.md guide/ public/images/ && git commit -m "docs: 添加首页和指南基础页面"
```

---

## Task 4: 创建快速开始和安装指南

**Files:**
- Create: `docs/guide/quick-start.md`
- Create: `docs/guide/installation.md`

- [ ] **Step 1: 创建快速开始页面**

```markdown
# 快速开始

本指南将帮助你快速启动并运行 MuMuAINovel。

## 前置要求

- Node.js >= 18
- Python >= 3.10
- PostgreSQL >= 14 (或使用 Docker)
- pnpm >= 8

## 快速启动

### 1. 克隆项目

```bash
git clone https://github.com/yucheng2/MuMuAINovel.git
cd MuMuAINovel
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host localhost --port 8000 --reload
```

### 3. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

### 4. 访问应用

打开浏览器访问 http://localhost:3000

## 使用 Docker 快速启动

```bash
docker-compose up -d
```

访问 http://localhost:3000

## 下一步

- 详细安装说明: [安装指南](./installation.md)
- 了解系统架构: [架构说明](../backend/architecture.md)
```

- [ ] **Step 2: 创建安装指南页面**

```markdown
# 安装指南

详细的安装和配置步骤。

## 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Node.js | 18.x | 20.x |
| Python | 3.10 | 3.11 |
| PostgreSQL | 14 | 16 |
| pnpm | 8.x | 9.x |

## 后端安装

### 1. 创建虚拟环境

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/mumuainovel
OPENAI_API_KEY=your-api-key
DEFAULT_AI_PROVIDER=openai
```

### 4. 数据库设置

```bash
# 运行迁移
alembic upgrade head

# 创建初始数据 (可选)
python scripts/init_db.py
```

### 5. 启动服务

```bash
python -m uvicorn app.main:app --host localhost --port 8000 --reload
```

## 前端安装

### 1. 安装依赖

```bash
cd frontend
pnpm install
```

### 2. 配置 API 地址

如果后端不在 localhost:8000，修改 `src/services/api.ts` 中的 baseURL。

### 3. 启动开发服务器

```bash
pnpm dev
```

## Docker 安装

### 使用 docker-compose

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 手动 Docker 构建

```bash
# 构建镜像
docker build -t mumuainovel .

# 运行容器
docker run -d -p 3000:3000 -p 8000:8000 mumuainovel
```

## 验证安装

访问 http://localhost:3000 (前端) 和 http://localhost:8000/docs (API 文档) 验证服务是否正常运行。
```

- [ ] **Step 3: 提交**

```bash
git add guide/quick-start.md guide/installation.md && git commit -m "docs: 添加快速开始和安装指南"
```

---

## Task 5: 创建后端文档

**Files:**
- Create: `docs/backend/README.md`
- Create: `docs/backend/architecture.md`
- Create: `docs/backend/api.md`

- [ ] **Step 1: 创建后端文档首页**

```markdown
# 后端文档

后端采用 FastAPI 框架，使用 Python 3.10+，提供 RESTful API 接口。

## 目录

- [架构说明](./architecture.md) - 系统架构设计
- [API 文档](./api.md) - API 接口文档
- [AI 服务](./ai-service.md) - AI 模型集成
- [MCP 插件](./mcp.md) - 插件系统
- [数据库](./database.md) - 数据库设计

## 技术栈

- **框架**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **数据库**: PostgreSQL
- **迁移工具**: Alembic
- **AI 集成**: LangChain

## 项目结构

```
backend/
├── app/
│   ├── api/              # API 路由
│   ├── models/          # 数据模型
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 业务逻辑
│   └── main.py           # 应用入口
├── alembic/             # 数据库迁移
└── scripts/             # 工具脚本
```
```

- [ ] **Step 2: 创建架构说明页**

```markdown
# 系统架构

## 整体架构

MuMuAINovel 采用分层架构设计：

```
┌─────────────────────────────────────────┐
│              Frontend (React)           │
└─────────────────┬───────────────────────┘
                  │ HTTP/REST
┌─────────────────▼───────────────────────┐
│           API Layer (FastAPI)           │
│  ┌─────────────────────────────────┐    │
│  │  Auth | Projects | Chapters    │    │
│  │  Characters | Outlines | AI    │    │
│  └─────────────────────────────────┘    │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Service Layer                    │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ AI Service  │  │Memory Svc   │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│     Data Layer (SQLAlchemy + PG)        │
└─────────────────────────────────────────┘
```

## API 层

### 路由模块

| 路由 | 说明 |
|------|------|
| `/api/auth` | 用户认证 |
| `/api/projects` | 项目管理 |
| `/api/chapters` | 章节管理 |
| `/api/characters` | 角色管理 |
| `/api/outlines` | 大纲管理 |
| `/api/ai` | AI 服务调用 |

## 服务层

### AI 服务

统一的 AI 服务入口，支持多种 Provider：

```python
# 调用示例
from app.services.ai_service import AIService

ai_service = AIService()
result = await ai_service.generate(
    provider="openai",
    prompt="生成一段小说开头"
)
```

### MCP 插件服务

基于 Model Context Protocol 的插件系统。

## 数据层

### SQLAlchemy 模型关系

```
Project (1) ──┬── (*) Chapter
              ├── (*) Character
              ├── (*) Outline
              └── (*) WorldSetting
```

## 中间件

- **认证中间件**: JWT Token 验证
- **请求 ID 中间件**: 请求追踪
- **CORS 中间件**: 跨域资源共享
```

- [ ] **Step 3: 创建 API 文档页**

```markdown
# API 文档

基于 OpenAPI 规范的 API 文档，访问 http://localhost:8000/docs 查看交互式文档。

## 认证

API 使用 JWT Token 认证。

### 登录

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 使用 Token

```http
GET /api/projects
Authorization: Bearer <token>
```

## 项目接口

### 获取项目列表

```http
GET /api/projects
```

### 创建项目

```http
POST /api/projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "我的小说",
  "description": "小说描述"
}
```

### 获取项目详情

```http
GET /api/projects/{project_id}
```

### 删除项目

```http
DELETE /api/projects/{project_id}
```

## 章节接口

### 获取章节列表

```http
GET /api/projects/{project_id}/chapters
```

### 生成章节

```http
POST /api/projects/{project_id}/chapters/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "outline_id": 1,
  "count": 5
}
```

### 更新章节内容

```http
PUT /api/chapters/{chapter_id}
Content-Type: application/json

{
  "title": "新的标题",
  "content": "新的内容..."
}
```

## 错误响应

```json
{
  "detail": "错误信息描述"
}
```

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
```

## 速率限制

API 默认速率限制为 60 请求/分钟。
```

- [ ] **Step 4: 提交**

```bash
git add backend/ && git commit -m "docs: 添加后端架构和 API 文档"
```

---

## Task 6: 创建 AI 服务、MCP、数据库文档

**Files:**
- Create: `docs/backend/ai-service.md`
- Create: `docs/backend/mcp.md`
- Create: `docs/backend/database.md`

- [ ] **Step 1: 创建 AI 服务文档**

```markdown
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

```python
from app.services.prompt_service import PromptService

prompt_service = PromptService()
template = prompt_service.get_template("chapter_generation")
rendered = template.render(
    title="第一章 觉醒",
    outline="故事背景设定..."
)
```

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
```

- [ ] **Step 2: 创建 MCP 插件文档**

```markdown
# MCP 插件系统

## 概述

MCP (Model Context Protocol) 是一种扩展 AI 模型能力的协议，允许接入外部工具和数据源。

## 架构

```
┌─────────────┐     MCP      ┌─────────────┐
│   AI Model  │◄────────────►│  MCP Server │
└─────────────┘              └──────┬──────┘
                                    │
                             ┌──────▼──────┐
                             │   Plugin    │
                             │  (Python)   │
                             └─────────────┘
```

## 内置插件

### 1. Search Plugin
提供网络搜索能力。

```python
# 使用示例
result = await mcp_server.call_tool("search", {
    "query": "最新科技新闻",
    "count": 5
})
```

### 2. Image Generation Plugin
图片生成功能。

```python
result = await mcp_server.call_tool("generate_image", {
    "prompt": "一个穿着古装的年轻人站在山顶",
    "style": "水墨画"
})
```

## 开发插件

### 插件结构

```
mcp_plugins/
└── my_plugin/
    ├── __init__.py
    ├── plugin.py        # 插件主类
    └── manifest.json    # 插件配置
```

### 示例插件

```python
# plugin.py
from mcp_plugin import Plugin, Tool

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "1.0.0"

    def get_tools(self):
        return [
            Tool(
                name="hello",
                description="打招呼",
                input_schema={"type": "object", "properties": {}}
            )
        ]

    async def execute(self, tool_name, arguments):
        if tool_name == "hello":
            return "你好！"
```

## 插件管理

在管理界面中可以：
- 查看已安装插件
- 启用/禁用插件
- 配置插件参数
```

- [ ] **Step 3: 创建数据库文档**

```markdown
# 数据库设计

## 概述

使用 PostgreSQL 数据库，通过 SQLAlchemy ORM 进行数据操作。

## ER 图

```
┌─────────────┐     ┌─────────────┐
│    User     │     │   Project   │
├─────────────┤     ├─────────────┤
│ id          │────►│ id          │
│ email       │     │ user_id (FK)│
│ password    │     │ name        │
│ created_at  │     │ description │
└─────────────┘     │ created_at  │
                     └──────┬──────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
   ┌───────────┐     ┌───────────┐     ┌───────────┐
   │  Chapter  │     │ Character │     │  Outline  │
   ├───────────┤     ├───────────┤     ├───────────┤
   │ id        │     │ id        │     │ id        │
   │ project_id│     │ project_id│     │ project_id│
   │ title     │     │ name      │     │ title     │
   │ content   │     │ role      │     │ content   │
   │ order     │     │ traits    │     │ parent_id │
   └───────────┘     └───────────┘     └───────────┘
```

## 主要表说明

### User 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| email | VARCHAR(255) | 邮箱（唯一） |
| password_hash | VARCHAR(255) | 密码哈希 |
| created_at | TIMESTAMP | 创建时间 |

### Project 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 所属用户 |
| name | VARCHAR(255) | 项目名称 |
| description | TEXT | 项目描述 |

### Chapter 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID | 所属项目 |
| title | VARCHAR(255) | 章节标题 |
| content | TEXT | 章节内容 |
| order_index | INTEGER | 章节顺序 |

## 迁移

### 创建迁移

```bash
alembic revision --autogenerate -m "add_chapter_table"
```

### 执行迁移

```bash
alembic upgrade head
```

### 回滚

```bash
alembic downgrade -1
```
```

- [ ] **Step 4: 提交**

```bash
git add backend/ai-service.md backend/mcp.md backend/database.md && git commit -m "docs: 添加 AI 服务、MCP、数据库文档"
```

---

## Task 7: 创建前端和配置文档

**Files:**
- Create: `docs/frontend/README.md`
- Create: `docs/frontend/components.md`
- Create: `docs/frontend/pages.md`
- Create: `docs/config/README.md`
- Create: `docs/config/environment.md`
- Create: `docs/config/ai-providers.md`

- [ ] **Step 1: 创建前端文档首页和组件文档**

```markdown
# 前端文档

基于 React 18 + TypeScript 构建的单页应用。

## 技术栈

- React 18 + TypeScript
- Vite 7 - 构建工具
- Ant Design 5 - UI 组件库
- Zustand 5 - 状态管理
- React Router DOM 6 - 路由
- @xyflow/react - 流程图/关系图

## 项目结构

```
frontend/src/
├── pages/           # 页面组件
│   ├── BookshelfPage.tsx   # 书架
│   ├── Chapters.tsx         # 章节编辑
│   ├── Characters.tsx       # 角色管理
│   └── ...
├── components/      # 通用组件
├── services/        # API 调用
└── store/           # 状态管理
```

---

## 组件文档

### ChapterReader

章节阅读器组件，用于展示和编辑章节内容。

```tsx
import { ChapterReader } from '@/components/ChapterReader'

<ChapterReader
  content={chapterContent}
  onSave={handleSave}
  readonly={false}
/>
```

### CharacterCard

角色卡片组件，展示角色信息。

```tsx
import { CharacterCard } from '@/components/CharacterCard'

<CharacterCard
  character={characterData}
  onEdit={handleEdit}
  onDelete={handleDelete}
/>
```

### RelationshipGraph

角色关系图谱组件。

```tsx
import { RelationshipGraph } from '@/components/RelationshipGraph'

<RelationshipGraph
  characters={characterList}
  relationships={relationshipData}
/>
```
```

- [ ] **Step 2: 创建前端页面文档**

```markdown
# 页面说明

## 书架页面 (BookshelfPage)

项目列表页面，展示用户的所有小说项目。

**路由**: `/`

**功能**:
- 展示项目卡片列表
- 创建新项目
- 删除项目
- 搜索筛选

## 章节页面 (Chapters)

核心章节编辑页面。

**路由**: `/project/:id/chapters`

**功能**:
- 章节列表展示
- 批量生成章节
- 章节内容编辑
- 章节重排序

**核心组件**:
- `ChapterList` - 章节列表
- `ChapterEditor` - 富文本编辑器
- `GenerationPanel` - AI 生成面板

## 角色管理页面 (Characters)

**路由**: `/project/:id/characters`

**功能**:
- 角色 CRUD
- 角色关系管理
- 角色属性配置

## 大纲页面 (Outline)

**路由**: `/project/:id/outline`

**功能**:
- 故事大纲编辑
- 章节规划
- 伏笔管理
```

- [ ] **Step 3: 创建配置文档首页和环境变量文档**

```markdown
# 配置文档

## 目录

- [环境变量](./environment.md) - 环境变量配置
- [AI 提供商](./ai-providers.md) - AI 模型配置
```

---

```markdown
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
```

- [ ] **Step 4: 创建 AI 提供商配置文档**

```markdown
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
```

- [ ] **Step 5: 提交**

```bash
git add frontend/ config/ && git commit -m "docs: 添加前端和配置文档"
```

---

## Task 8: 创建部署文档并验证构建

**Files:**
- Create: `docs/guide/deployment.md`
- Modify: `docs/package.json` (添加启动脚本)

- [ ] **Step 1: 创建部署文档**

```markdown
# 部署说明

## Docker 部署 (推荐)

### 使用 docker-compose

```bash
# 克隆项目
git clone https://github.com/yucheng2/MuMuAINovel.git
cd MuMuAINovel

# 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库和 API Keys

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

访问 http://localhost:3000

### 环境变量配置

生产环境必须配置：

```env
DATABASE_URL=postgresql://user:password@db:5432/mumuainovel
SECRET_KEY=your-production-secret-key
OPENAI_API_KEY=sk-xxx
```

## 手动部署

### 后端部署

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 配置环境变量
export DATABASE_URL=postgresql://...
export SECRET_KEY=production-secret

# 使用 gunicorn 运行
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

### 前端部署

```bash
cd frontend

# 构建生产版本
pnpm build

# 输出在 dist/ 目录
# 可使用 nginx 或 caddy 托管
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

## 常见问题

### 数据库连接失败

检查：
1. PostgreSQL 服务是否运行
2. `DATABASE_URL` 是否正确
3. 数据库是否已创建

### AI API 调用失败

检查：
1. API Key 是否正确配置
2. API Key 余额是否充足
3. 网络是否能访问 AI 服务商
```

- [ ] **Step 2: 更新 package.json 添加 docs 脚本到主项目**

修改主项目的 `package.json` 添加文档相关脚本，或告知用户单独在 docs 目录运行。

- [ ] **Step 3: 测试构建**

```bash
cd docs
pnpm dev
```

验证文档站点能否正常启动和访问。

- [ ] **Step 4: 提交**

```bash
git add guide/deployment.md && git commit -m "docs: 添加部署说明文档"
```

---

## Task 9: 最终检查和清理

**Files:**
- Create: `docs/README.md` (链接到主项目 README)
- Verify: `docs/.vuepress/` 完整配置

- [ ] **Step 1: 验证所有必要文件存在**

检查清单：
- [ ] `docs/package.json`
- [ ] `docs/index.md`
- [ ] `docs/.vuepress/config.ts`
- [ ] `docs/guide/` 完整
- [ ] `docs/backend/` 完整
- [ ] `docs/frontend/` 完整
- [ ] `docs/config/` 完整

- [ ] **Step 2: 测试开发服务器**

```bash
cd docs && pnpm dev
```

确认 http://localhost:8080 能正常访问。

- [ ] **Step 3: 提交所有更改**

```bash
git add -A && git commit -m "docs: 完成 VuePress 文档站点建设"
```

---

## 验证清单

| 检查项 | 状态 |
|--------|------|
| VuePress 初始化成功 | ⬜ |
| 导航栏配置正确 | ⬜ |
| 侧边栏配置正确 | ⬜ |
| 首页正常显示 | ⬜ |
| 所有指南页面完整 | ⬜ |
| 所有后端文档完整 | ⬜ |
| 所有前端文档完整 | ⬜ |
| 所有配置文档完整 | ⬜ |
| 开发服务器运行正常 | ⬜ |
