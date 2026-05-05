# API 文档

基于 OpenAPI 规范的 API 文档，访问 http://localhost:8000/docs 查看交互式文档。

## 认证

API 使用 JWT Token 认证。

### 登录

```
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

```
GET /api/projects
Authorization: Bearer <token>
```

## 项目接口

### 获取项目列表

```
GET /api/projects
```

### 创建项目

```
POST /api/projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "我的小说",
  "description": "小说描述"
}
```

### 获取项目详情

```
GET /api/projects/{project_id}
```

### 删除项目

```
DELETE /api/projects/{project_id}
```

## 章节接口

### 获取章节列表

```
GET /api/projects/{project_id}/chapters
```

### 生成章节

```
POST /api/projects/{project_id}/chapters/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "outline_id": 1,
  "count": 5
}
```

### 更新章节内容

```
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

## 速率限制

API 默认速率限制为 60 请求/分钟。
