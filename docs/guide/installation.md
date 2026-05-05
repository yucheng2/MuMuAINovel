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
