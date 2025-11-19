# 部署指南

> ⚠️ **重要**: 应用配置了 ROOT_PATH="/atlas"，所有访问路径需加上 `/atlas` 前缀  
> 详见 [根路径配置说明](ROOT_PATH_GUIDE.md)

## 🔧 系统要求

- Docker 20.10+
- Docker Compose 1.29+
- PostgreSQL 数据库访问（117.72.204.201:5432）
- Milvus 向量数据库访问（117.72.204.201:19530）

## Docker 部署

### 1. 环境变量配置

**重要**: `.env` 文件包含敏感信息，已被 Git 忽略。部署时需要手动配置。

#### 方式一：使用 env_file（本地开发）

```bash
# 1. 复制示例配置
cp .env.example .env

# 2. 编辑 .env 填入真实配置
vim .env

# 3. 使用 docker-compose（会自动读取 .env）
docker-compose up -d
```

#### 方式二：使用环境变量（生产推荐）

```bash
# 直接传递环境变量
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://postgres:p0stgr3s@117.72.204.201:5432/atlas \
  -e MILVUS_HOST=117.72.204.201 \
  -e MILVUS_PORT=19530 \
  -e OPENAI_API_KEY=your-key \
  -e OPENAI_BASE_URL=https://openrouter.ai/api/v1 \
  -e JWT_SECRET_KEY=$(openssl rand -hex 32) \
  -v $(pwd)/metadata_store:/app/metadata_store \
  -v $(pwd)/uploads:/app/uploads \
  --name atlas \
  atlas:latest
```

#### 方式三：使用 docker-compose + 外部环境变量

修改 `docker-compose.yaml`，取消注释 `environment` 部分：

```yaml
services:
  atlas:
    # ...
    environment:
      - DATABASE_URL=postgresql://postgres:p0stgr3s@117.72.204.201:5432/atlas
      - MILVUS_HOST=117.72.204.201
      - MILVUS_PORT=19530
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

然后在 CI/CD 或服务器上设置这些环境变量后运行：

```bash
export OPENAI_API_KEY=your-key
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export JWT_SECRET_KEY=$(openssl rand -hex 32)
docker-compose up -d
```

### 2. 构建镜像

```bash
# 构建镜像
docker build -t atlas:latest .

# 或使用 docker-compose 构建
docker-compose build
```

### 3. 启动服务

```bash
# 使用 docker-compose
docker-compose up -d

# 查看日志
docker-compose logs -f atlas

# 停止服务
docker-compose down
```

### 4. 首次启动

容器首次启动时会自动：
- 初始化 PostgreSQL 数据库表
- 创建默认管理员账户（`admin/admin123`）
- 连接 Milvus 向量数据库

**⚠️ 请在首次登录后立即修改默认密码！**

### 5. 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 登录测试
curl -X POST http://localhost:8000/atlas/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 查看容器健康状态
docker ps
```

## 环境变量说明

| 变量名 | 说明 | 必需 | 默认值 |
|--------|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | ✅ | `postgresql://postgres:p0stgr3s@117.72.204.201:5432/atlas` |
| `MILVUS_HOST` | Milvus 地址 | ✅ | `117.72.204.201` |
| `MILVUS_PORT` | Milvus 端口 | ✅ | `19530` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | ✅ | - |
| `OPENAI_BASE_URL` | API 基础地址 | ✅ | - |
| `CHAT_MODEL` | 对话模型 | ❌ | `openai/gpt-oss-120b` |
| `EMBEDDING_MODEL` | 向量模型 | ❌ | `openai/text-embedding-3-small` |
| `JWT_SECRET_KEY` | JWT 密钥 | ⚠️ | **生产必须修改** |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间 | ❌ | `30` |
| `DEBUG` | 调试模式 | ❌ | `false` |

## 生产环境建议

### 1. 安全性

- **修改 JWT 密钥**：
  ```bash
  # 生成强随机密钥
  openssl rand -hex 32
  ```

- **修改默认管理员密码**：
  ```bash
  curl -X PUT http://localhost:8000/atlas/api/users/me/password \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"old_password":"admin123","new_password":"your-strong-password"}'
  ```

- **使用 HTTPS**（通过 Traefik 或 Nginx）
- **限制 API 访问频率**

### 2. 数据库优化

PostgreSQL 连接池配置（已在 `core/database.py` 中配置）：
- `pool_size`: 10（基础连接数）
- `max_overflow`: 20（最大溢出连接）
- `pool_pre_ping`: True（连接前健康检查）
- `pool_recycle`: 3600（1小时回收连接）

### 3. 性能优化

- **Worker 配置**：Dockerfile 默认 2 workers，根据 CPU 核心数调整
- **缓存**：考虑添加 Redis 缓存层
- **日志**：配置日志轮转和归档

### 4. 监控

- 配置健康检查告警
- 收集应用日志
- 监控数据库和 Milvus 连接状态

### 5. 数据持久化

容器内部路径映射：
- 元数据：`./metadata_store` → `/app/metadata_store`
- 上传文件：`./uploads` → `/app/uploads`

**数据库备份**：
```bash
# 备份 PostgreSQL
docker exec -t atlas pg_dump -U postgres atlas > backup.sql

# 恢复
cat backup.sql | docker exec -i atlas psql -U postgres atlas
```

## 本地开发

### 1. 安装依赖

```bash
# 安装 uv
pip install uv

# 安装项目依赖
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入配置
```

### 3. 初始化数据库

```bash
# 创建管理员账户
uv run python create_admin.py
```

### 4. 启动开发服务器

```bash
# 使用 uv run
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
uv run python app.py
```

## 故障排查

### 容器无法启动

```bash
# 查看日志
docker-compose logs atlas

# 检查环境变量
docker-compose config

# 进入容器排查
docker exec -it atlas sh
```

### PostgreSQL 连接失败

```bash
# 测试数据库连接
docker exec atlas python -c "from core.database import engine; engine.connect()"

# 检查网络连通性
docker exec atlas ping 117.72.204.201

# 手动连接测试
psql postgresql://postgres:p0stgr3s@117.72.204.201:5432/atlas
```

### Milvus 连接失败

```bash
# 检查 Milvus 服务
curl http://117.72.204.201:19530

# 检查容器网络
docker network inspect matrix-network
```

### 健康检查失败

```bash
# 手动测试健康检查端点
docker exec atlas python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 查看应用日志
docker logs atlas
```

## 升级指南

```bash
# 1. 备份数据库
pg_dump -U postgres -h 117.72.204.201 atlas > backup_$(date +%Y%m%d).sql

# 2. 拉取最新代码
git pull

# 3. 重新构建镜像
docker-compose build

# 4. 停止旧容器（保留数据卷）
docker-compose down

# 5. 启动新容器
docker-compose up -d

# 6. 验证
curl http://localhost:8000/health
```

## 使用 uv 启动说明

Dockerfile 使用 `uv run` 启动应用，优势：
- 自动管理虚拟环境
- 确保依赖隔离
- 支持 `pyproject.toml` 和 `uv.lock`
- 启动更快、更可靠

启动脚本 (`entrypoint.sh`) 包含：
1. 等待数据库连接（5秒）
2. 初始化数据库表
3. 创建默认管理员（如不存在）
4. 启动 uvicorn（2 workers + proxy-headers）

