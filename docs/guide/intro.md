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
