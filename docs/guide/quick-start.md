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
