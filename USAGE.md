# Echo 智能客服后端系统 - 使用指南

> ⚠️ **重要**: 应用配置了 ROOT_PATH="/atlas"，所有 API 路径需加上 `/atlas` 前缀  
> - 本地开发: `http://localhost:8000/atlas/api/*`  
> - 生产环境: `https://atlas.matrix-net.tech/atlas/api/*`  
> 详见 [根路径配置说明](ROOT_PATH_GUIDE.md)

## 快速开始

### 1. 启动服务器

```bash
# 使用虚拟环境的 uvicorn 启动
.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000

# 或使用 reload 模式（开发环境）
.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 访问 API 文档

服务器启动后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## 完整工作流程示例

### 步骤 1: 创建智能体（Agent）

```bash
curl -X POST http://localhost:8000/atlas/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_service_agent",
    "display_name": "客服助手",
    "agent_type": "general",
    "system_prompt": "你是一个专业的客服助手，态度友好，回答准确。",
    "milvus_collection": "customer_service_kb"
  }'
```

**响应示例：**
```json
{
  "id": "411beae1-9254-4c28-b3aa-232290cf2141",
  "name": "customer_service_agent",
  "display_name": "客服助手",
  "agent_type": "general",
  "status": "active",
  "system_prompt": "你是一个专业的客服助手，态度友好，回答准确。",
  "knowledge_base": {
    "collection_name": "agent_customer_service_agent",
    "total_files": 0,
    "total_vectors": 0
  }
}
```

### 步骤 2: 上传知识库文档

```bash
# 创建测试文档
cat > service_guide.txt << EOF
公司服务指南

我们提供以下服务：
1. 技术支持 - 7x24小时在线
2. 产品咨询 - 专业团队解答
3. 售后服务 - 快速响应

联系方式：
客服热线: 400-123-4567
邮箱: support@example.com
工作时间: 周一至周日 9:00-21:00
EOF

# 上传文档
curl -X POST http://localhost:8000/atlas/api/knowledge-base/customer_service_agent/documents \
  -F "file=@service_guide.txt"
```

**响应示例：**
```json
{
  "file_id": "43fa6d29-ec24-45e2-9dc4-e61a73ba5d3c",
  "filename": "customer_service_agent_service_guide.txt",
  "chunks_count": 1,
  "upload_time": "2025-11-17 15:05:58"
}
```

### 步骤 3: 查看知识库统计

```bash
curl http://localhost:8000/atlas/api/knowledge-base/customer_service_agent/stats
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "agent_name": "customer_service_agent",
    "collection_name": "agent_customer_service_agent",
    "total_files": 1,
    "total_chunks": 1,
    "total_vectors": 1,
    "total_size_mb": 0.13,
    "files": [
      {
        "id": "43fa6d29-ec24-45e2-9dc4-e61a73ba5d3c",
        "filename": "customer_service_agent_service_guide.txt",
        "upload_time": "2025-11-17 15:05:58",
        "file_size": 133,
        "chunks_count": 1,
        "file_type": "txt"
      }
    ]
  }
}
```

### 步骤 4: 创建对话（Conversation）

```bash
curl -X POST http://localhost:8000/atlas/api/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_conv_001",
    "display_name": "客户咨询001",
    "agent_name": "customer_service_agent",
    "welcome_message": "您好！我是智能客服，很高兴为您服务。请问有什么可以帮助您？"
  }'
```

**响应示例：**
```json
{
  "id": "b764d368-88bf-42e8-b88b-354026b6989f",
  "name": "customer_conv_001",
  "display_name": "客户咨询001",
  "avatar": "🤖",
  "status": "online",
  "agent": {
    "id": "411beae1-9254-4c28-b3aa-232290cf2141",
    "name": "customer_service_agent",
    "display_name": "客服助手",
    "agent_type": "general"
  },
  "welcome_message": "您好！我是智能客服，很高兴为您服务。请问有什么可以帮助您？",
  "message_count": 0,
  "created_at": "2025-11-17T07:05:59.135533"
}
```

### 步骤 5: 发送消息并获取回复

```bash
# 发送第一条消息
curl -X POST http://localhost:8000/atlas/api/chat/customer_conv_001/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "你们提供哪些服务？"
  }'

# 发送第二条消息
curl -X POST http://localhost:8000/atlas/api/chat/customer_conv_001/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "客服电话是多少？"
  }'
```

**响应示例：**
```json
{
  "role": "assistant",
  "content": "您好！😊\n根据我们的服务指南，我们为您提供以下服务：\n\n1. **技术支持** - 7x24小时在线，随时为您解决技术问题\n2. **产品咨询** - 专业团队为您提供详细的产品信息和建议\n3. **售后服务** - 快速响应您的售后需求\n\n如需联系我们，欢迎拨打客服热线 **400-123-4567**（工作时间：周一至周日 9:00-21:00），或发送邮件至 support@example.com。祝您生活愉快！",
  "timestamp": "2025-11-17T07:06:01.799462",
  "agent_name": "customer_service_agent",
  "knowledge_base_used": true
}
```

### 步骤 6: 管理资源

```bash
# 列出所有智能体
curl http://localhost:8000/atlas/api/agents

# 获取特定智能体详情
curl http://localhost:8000/atlas/api/agents/customer_service_agent

# 停用智能体
curl -X POST http://localhost:8000/atlas/api/agents/customer_service_agent/deactivate

# 激活智能体
curl -X POST http://localhost:8000/atlas/api/agents/customer_service_agent/activate

# 列出所有对话
curl http://localhost:8000/atlas/api/conversations

# 获取对话详情
curl http://localhost:8000/atlas/api/conversations/customer_conv_001

# 切换对话使用的智能体
curl -X POST http://localhost:8000/atlas/api/conversations/customer_conv_001/switch-agent \
  -H "Content-Type: application/json" \
  -d '{
    "new_agent_name": "another_agent",
    "reason": "用户需要更专业的服务"
  }'

# 查看智能体切换历史
curl http://localhost:8000/atlas/api/conversations/customer_conv_001/agent-history

# 删除对话历史
curl -X DELETE http://localhost:8000/atlas/api/chat/customer_conv_001/history

# 清空知识库
curl -X DELETE http://localhost:8000/atlas/api/knowledge-base/customer_service_agent/clear
```

## 支持的文件类型

知识库支持以下文件格式：
- PDF (.pdf)
- 文本文件 (.txt)
- Markdown (.md)

## Agent 类型

系统预定义了以下智能体类型：
- `general` - 通用
- `legal` - 法律
- `medical` - 医疗
- `financial` - 金融
- `custom` - 自定义

## 环境变量配置

关键配置项（在 `.env` 文件中）：

```env
# Milvus 配置
MILVUS_HOST=117.72.204.201
MILVUS_PORT=19530
MILVUS_USER=
MILVUS_PASSWORD=
MILVUS_DB_NAME=default

# OpenAI/OpenRouter 配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
CHAT_MODEL=openai/gpt-oss-120b
EMBEDDING_MODEL=openai/text-embedding-3-small

# 数据库配置
DATABASE_URL=sqlite:///./doctor.db

# 其他配置
METADATA_DIR=metadata_store
DEBUG=false
```

## 架构说明

```
┌──────────────┐
│ Conversation │  (用户界面层)
└──────┬───────┘
       │ 1:1
       ▼
┌──────────────┐
│    Agent     │  (AI 能力层)
└──────┬───────┘
       │ 1:1
       ▼
┌──────────────┐
│ Knowledge Base│  (知识存储层 - Milvus)
└──────────────┘
```

- **Conversation**: 代表一个对话会话，可以动态切换 Agent
- **Agent**: 封装 AI 能力和系统提示词，关联一个知识库
- **Knowledge Base**: Milvus Collection，存储向量化的知识文档

## 故障排查

### 问题 1: Milvus 连接失败

```
❌ Milvus 连接失败: Fail connecting to server
```

**解决方法:**
1. 检查 Milvus 服务器是否运行
2. 验证 `.env` 中的 `MILVUS_HOST` 和 `MILVUS_PORT` 配置
3. 检查网络连接和防火墙设置

### 问题 2: 数据库文件权限错误

```
sqlite3.OperationalError: attempt to write a readonly database
```

**解决方法:**
```bash
chmod 644 doctor.db
```

### 问题 3: 依赖安装失败

**解决方法:**
```bash
# 清理虚拟环境
rm -rf .venv

# 重新创建并安装
uv venv
uv pip install pymilvus langchain-milvus fastapi uvicorn sqlalchemy \
  python-multipart python-dotenv pydantic pydantic-settings \
  langchain langchain-community langchain-openai \
  langchain-text-splitters beautifulsoup4 lxml pypdf
```

## 性能优化建议

1. **向量检索优化**: 调整 Milvus 的 `index_type` 和 `nlist` 参数
2. **并发处理**: 使用 `uvicorn` 的 `--workers` 参数启动多个工作进程
3. **缓存**: 考虑添加 Redis 缓存常见问题答案
4. **数据库**: 生产环境建议使用 PostgreSQL 替换 SQLite

## 生产部署

### 使用 Docker

```bash
# 构建镜像
docker build -t echo-backend:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e MILVUS_HOST=117.72.204.201 \
  -e MILVUS_PORT=19530 \
  -e OPENAI_API_KEY=your_key \
  -e OPENAI_BASE_URL=https://openrouter.ai/api/v1 \
  --name echo-backend \
  echo-backend:latest
```

### 使用 systemd

创建 `/etc/systemd/system/echo-backend.service`:

```ini
[Unit]
Description=Echo Backend Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/doctor
ExecStart=/path/to/doctor/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl enable echo-backend
sudo systemctl start echo-backend
sudo systemctl status echo-backend
```

## 后续开发建议

1. **身份认证**: 添加 JWT 或 OAuth2 认证
2. **速率限制**: 使用 slowapi 添加 API 速率限制
3. **监控**: 集成 Prometheus + Grafana
4. **日志**: 使用结构化日志（如 structlog）
5. **测试**: 编写单元测试和集成测试
6. **文档**: 添加更多 API 使用示例

## 技术支持

如有问题，请查看：
- API 文档: http://localhost:8000/docs
- 项目 README: README.md
- 代码结构: PROJECT_REPORT.md
