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
