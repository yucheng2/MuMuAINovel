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
