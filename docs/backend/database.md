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
