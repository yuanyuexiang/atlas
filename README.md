# Echo 智能客服后端系统

基于 **FastAPI + Milvus + LangChain** 构建的智能客服 RESTful API 后端系统。

## ✨ 核心特性

- 🤖 **智能体管理**: 创建和管理多个 AI 智能体，支持不同领域（法律、医疗、金融等）
- 💬 **客服管理**: 客服与智能体解耦，支持动态切换和共享
- 📚 **知识库管理**: 上传文档（PDF/TXT/MD），自动向量化存储到 Milvus
- 💭 **智能对话**: 基于知识库的 RAG 智能问答
- 🔄 **动态切换**: 支持白班/夜班智能体切换、A/B 测试
- 📊 **统计分析**: 知识库统计、对话记录、切换历史
- 🔐 **JWT 认证**: 完整的用户认证和权限管理系统

## 🏗️ 架构设计

```
前端应用
  ↓ HTTP API
FastAPI 后端
  ├── PostgreSQL（关系数据 - 117.72.204.201:5432）
  ├── Milvus（向量存储 - 117.72.204.201:19530）
  └── 本地文件系统（元数据）
```

### 三层解耦架构

```
Conversation（客服界面层）
    ↓ 绑定关系（可切换）
Agent（智能体能力层）
    ↓ 专属知识库
Knowledge Base（知识存储层 - Milvus）
```

## 🚀 快速开始

### 1. 环境准备

```bash
# Python 3.12+
python --version

# 安装 uv（推荐）
pip install uv
```

### 2. 安装依赖

```bash
# 使用 uv 安装
uv pip install -r pyproject.toml

# 或使用 pip
pip install -e .
```

### 3. 配置环境变量

编辑 `.env` 文件：

```env
# OpenAI Compatible API
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=your-api-key
CHAT_MODEL=openai/gpt-oss-120b
EMBEDDING_MODEL=openai/text-embedding-3-small

# PostgreSQL 数据库
DATABASE_URL=postgresql://postgres:p0stgr3s@117.72.204.201:5432/atlas

# Milvus 向量数据库
MILVUS_HOST=117.72.204.201
MILVUS_PORT=19530

# 本地存储
METADATA_DIR=metadata_store

# JWT 认证（生产环境必须修改）
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. 创建默认管理员

```bash
# 创建默认管理员账户（admin/admin123）
python create_admin.py
```

⚠️ **安全提示**: 首次登录后请立即修改默认密码！

### 5. 启动服务

```bash
# 开发模式（自动重载）
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
python app.py
```

### 5. 启动服务

```bash
# 开发模式（自动重载）
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
python app.py
```

### 6. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## 🔐 认证与授权

系统现已启用 JWT 认证保护所有主要 API 端点。

### 默认管理员账户

```
用户名: admin
密码: admin123
```

### 使用认证

1. **登录获取 Token**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')
```

2. **使用 Token 访问 API**:
```bash
curl http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN"
```

### 受保护的端点

- ✅ `/api/agents/*` - 智能体管理
- ✅ `/api/conversations/*` - 客服管理
- ✅ `/api/knowledge-base/*` - 知识库管理
- ✅ `/api/chat/*` - 对话接口
- ✅ `/api/users/*` - 用户管理（仅管理员）

详细文档请查看 [AUTHENTICATION.md](AUTHENTICATION.md)

## 📚 API 使用示例

**注意**: 以下示例需要在请求头添加 `Authorization: Bearer <token>`

### 1. 创建智能体

```bash
curl -X POST "http://localhost:8000/api/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "legal_expert_v1",
    "display_name": "民法专家",
    "agent_type": "legal"
  }'
```

### 2. 上传知识库文档

```bash
curl -X POST "http://localhost:8000/api/knowledge-base/legal_expert_v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@minfadian.pdf"
```

### 3. 创建客服

```bash
curl -X POST "http://localhost:8000/api/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_service_001",
    "display_name": "客服小李",
    "agent_name": "legal_expert_v1"
  }'
```

### 4. 发送消息

```bash
curl -X POST "http://localhost:8000/api/chat/customer_service_001/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "合同违约如何处理?"
  }'
```

## 🧪 测试

```bash
# 测试认证功能
./test_auth.sh

# 测试受保护的 API
./test_protected_apis.sh
```

## 📁 项目结构

```
doctor/
├── app.py                      # FastAPI 主应用
├── api/                        # API 路由
├── models/                     # 数据模型
├── services/                   # 业务逻辑
├── core/                       # 核心配置
└── metadata_store/             # 元数据
```

## 🔧 技术栈

- **FastAPI**: Web 框架
- **Milvus**: 向量数据库
- **LangChain**: RAG 框架
- **PostgreSQL**: 关系数据库
- **SQLAlchemy**: ORM
- **Pydantic**: 数据验证
- **JWT**: 身份认证
- **bcrypt**: 密码加密

## 📖 文档

- [API 认证指南](AUTHENTICATION.md) - JWT 认证详细说明
- [实施总结](JWT_IMPLEMENTATION_SUMMARY.md) - 认证系统实施细节
- [API 文档](http://localhost:8000/docs) - Swagger 交互式文档

## 📄 许可证

Apache 2.0
