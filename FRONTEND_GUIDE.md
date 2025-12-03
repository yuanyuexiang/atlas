# Echo 智能客服前端开发指导文档

> ⚠️ **重要提示**: 应用配置了 ROOT_PATH="/atlas"，所有 API 路径需加上 `/atlas` 前缀  
> - 生产环境: `https://atlas.matrix-net.tech/atlas/api/*`  
> - 本地开发: `http://localhost:8000/atlas/api/*`  
> 详细说明请查看 [根路径配置说明](ROOT_PATH_GUIDE.md)

> 🚀 **API UUID 迁移（2025-11-28）**: 所有实体的 CRUD 接口已统一改为使用 UUID 作为路径参数  
> - **重要变更**: 路径参数从 `{entity_name}` 改为 `{entity_id}` (UUID)  
> - **影响范围**: Agent、Conversation、Knowledge Base、Chat 共 24 个接口  
> - **常见错误**: 路径中缺少 UUID 参数会返回 404 错误
> - **示例**: `POST /chat/stream` ❌ → `POST /chat/{conversation_id}/message/stream` ✅

## 📋 目录

- [系统概述](#系统概述)
- [核心概念](#核心概念)
- [API 认证](#api-认证)
- [API 接口文档](#api-接口文档)
- [常见错误](#常见错误)
- [数据模型](#数据模型)
- [开发流程](#开发流程)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

---

## 系统概述

Echo 是一个基于 RAG（检索增强生成）的智能客服系统，采用**三层解耦架构**：

```
客服界面层（Conversation）
    ↓ 可动态切换
智能体能力层（Agent）
    ↓ 独立知识库
向量存储层（Milvus）
```

### 核心特性

- 🤖 多智能体管理
- 💬 客服与智能体解耦
- 📚 知识库独立管理（支持多编码格式）
- 🔄 智能体动态切换
- 🔐 JWT 认证授权
- 📊 大文件上传支持（自动分块处理）

### 技术栈

- **后端**: FastAPI + PostgreSQL + Milvus
- **API**: RESTful
- **认证**: JWT Bearer Token
- **AI**: SiliconFlow API (Qwen/Qwen2.5-7B-Instruct)
- **向量化**: BAAI/bge-large-zh-v1.5
- **文档**: Swagger UI (`/docs`) + ReDoc (`/redoc`)

---

## 核心概念

### 1. Agent（智能体）

**智能体是 AI 能力的抽象单元**，包含：
- 专属知识库（Milvus 向量存储）
- 系统提示词（System Prompt）
- 业务类型（general/legal/medical/financial）

**特点**：
- 一个智能体可被多个客服共享
- 每个智能体有独立的向量集合（collection）
- 支持不同领域的专业配置

**场景示例**：
```
智能体: "法律顾问" → 上传法律法规文档
智能体: "客服-白班" → 上传标准话术
智能体: "客服-夜班" → 上传简化话术
```

### 2. Conversation（客服）

**客服是面向用户的对话界面**，包含：
- 显示名称、头像、欢迎语
- 关联的智能体（可切换）
- 状态管理（online/offline/busy）
- 对话统计

**特点**：
- 客服与智能体是 N:1 关系
- 支持动态切换关联的智能体
- 可以多客服共享一个智能体

**场景示例**：
```
客服 "小张"（白班）→ 绑定智能体 "客服-白班"
       ↓ 下班后切换
客服 "小张"（夜班）→ 绑定智能体 "客服-夜班"
```

### 3. Knowledge Base（知识库）

**每个智能体有独立的知识库**：
- 支持上传 PDF、TXT、MD 文件
- 自动文本切分和向量化
- 存储在 Milvus 向量数据库

**工作流程**：
```
上传文档 → 解析文本 → 切分 chunk → 向量化 → 存入 Milvus
```

---

## API 认证

### 认证流程

1. **注册用户**（可选，也可由管理员创建）
2. **登录获取 Token**
3. **请求头携带 Token**

### 1. 用户注册

```http
POST https://atlas.matrix-net.tech/atlas/api/auth/register
Content-Type: application/json

{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123",
  "full_name": "测试用户"
}
```

**响应**：
```json
{
  "id": "user_uuid",
  "username": "testuser",
  "email": "test@example.com",
  "full_name": "测试用户",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-01-19T08:00:00Z"
}
```

### 2. 用户登录

```http
POST https://atlas.matrix-net.tech/atlas/api/auth/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "password123"
}
```

**响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. 使用 Token

所有需要认证的接口都要在请求头中携带 Token：

```http
GET https://atlas.matrix-net.tech/atlas/api/agents
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 4. 获取当前用户信息

```http
GET https://atlas.matrix-net.tech/atlas/api/auth/me
Authorization: Bearer {token}
```

---

## ⚠️ 最新更新（2025-11-28）

### 接口变更说明

**1. 列表接口返回格式变更** ✅
- **影响接口**: `GET /agents` 和 `GET /conversations`
- **变更**: 直接返回数组而不是分页对象
- **前端影响**: 如果之前处理的是数组格式，无需修改
```javascript
// 现在的响应
const agents = await response.json();  // 直接是数组

// 之前如果是这样处理的（需要修改）
const { agents, total } = await response.json();
```

**2. 客服更新接口新增字段** 🆕
- **影响接口**: `PUT /conversations/{id}`
- **新增**: `agent_name` 可选字段，用于更换智能体
- **前端影响**: 如需支持"更换智能体"功能，可添加此字段
```javascript
// 新功能：更新时同时更换智能体
await updateConversation({
  display_name: "新名称",
  agent_name: "new-agent"  // 可选
});
```

**3. 知识库功能修复** ✅
- 修复了文件上传后 chunks_count 为 0 的问题
- 修复了文件名带智能体前缀的问题
- 优化了空知识库的友好提示
- **前端影响**: 无需修改，功能更稳定

---

## API 接口文档

### 基础信息

- **生产环境 Base URL**: `https://atlas.matrix-net.tech/atlas/api`
- **本地开发 Base URL**: `http://localhost:8000/atlas/api`
- **文档地址**: 
  - Swagger UI (生产): `https://atlas.matrix-net.tech/atlas/docs`
  - Swagger UI (本地): `http://localhost:8000/atlas/docs`
  - ReDoc (生产): `https://atlas.matrix-net.tech/atlas/redoc`
  - ReDoc (本地): `http://localhost:8000/atlas/redoc`
  - 健康检查 (生产): `https://atlas.matrix-net.tech/atlas/health`
  - 健康检查 (本地): `http://localhost:8000/atlas/health`

> 💡 **提示**: 
> - 生产环境访问路径: `https://atlas.matrix-net.tech/atlas/*`
> - 本地开发访问路径: `http://localhost:8000/atlas/*`
> - 应用部署在 `/atlas` 子路径下，所有 API 都需要加上此前缀

---

## 1. 认证接口 `/api/auth`

### 1.1 注册用户

```http
POST https://atlas.matrix-net.tech/atlas/api/auth/register
```

**请求体**：
```json
{
  "username": "string",      // 3-50字符，字母数字下划线
  "email": "user@example.com",
  "password": "string",      // 6-72字符
  "full_name": "string"      // 可选
}
```

### 1.2 用户登录

```http
POST https://atlas.matrix-net.tech/atlas/api/auth/login
```

**请求体**：
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**：
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 1.3 获取当前用户

```http
GET https://atlas.matrix-net.tech/atlas/api/auth/me
Authorization: Bearer {token}
```

### 1.4 更新当前用户

```http
PUT https://atlas.matrix-net.tech/atlas/api/auth/me
Authorization: Bearer {token}
```

**请求体**：
```json
{
  "email": "new@example.com",  // 可选
  "full_name": "新名字",        // 可选
  "password": "newpassword"     // 可选
}
```

---

## 2. 智能体管理 `/api/agents`

### 2.1 创建智能体

```http
POST https://atlas.matrix-net.tech/atlas/api/agents
Authorization: Bearer {token}
```

**请求体**：
```json
{
  "name": "customer-service",           // 唯一标识
  "display_name": "智能客服",            // 显示名称
  "agent_type": "general",              // general/legal/medical/financial/custom
  "system_prompt": "你是一个专业的客服", // 可选，默认有提示词
  "description": "智能客服说明"          // 可选
}
```

**响应**（✨ files 数组包含状态字段）：
```json
{
  "id": "agent_uuid",
  "name": "customer-service",
  "display_name": "智能客服",
  "agent_type": "general",
  "status": "active",
  "system_prompt": "你是一个专业的客服...",
  "description": "智能客服说明",
  "knowledge_base": {
    "collection_name": "kb_customer_service",
    "total_files": 2,
    "total_vectors": 157,
    "total_size_mb": 1.25,
    "files": [
      {
        "id": "c6695de6-68fb-4fb9-875a-33802df96a40",
        "filename": "9b7ebf3a_test_status.txt",
        "upload_time": "2025-12-03 15:30:00",
        "file_size": 1024,
        "chunks_count": 1,
        "file_type": "txt",
        "status": "ready",                    // ✨ 新增：文件状态
        "processing_progress": 100,           // ✨ 新增：处理进度
        "error_message": null,                // ✨ 新增：错误信息
        "updated_at": "2025-12-03 15:30:05"  // ✨ 新增：更新时间
      },
      {
        "id": "abc-def-123",
        "filename": "7e47b4ea_empty.txt",
        "upload_time": "2025-12-03 15:31:00",
        "file_size": 0,
        "chunks_count": 0,
        "file_type": "txt",
        "status": "failed",                   // ✨ 失败状态
        "processing_progress": 0,
        "error_message": "向量化失败：所有文本块都未能添加到向量数据库。\n可能原因：\n1. Embedding API 配置错误或 API Key 无效\n2. 网络连接问题\n3. 向量数据库连接异常",
        "updated_at": "2025-12-03 15:31:02"
      }
    ]
  },
  "created_at": "2025-01-19T08:00:00Z",
  "updated_at": "2025-01-19T08:00:00Z",
  "conversations_using": []  // 使用该智能体的客服列表
}
```

**文件状态字段说明**：
- `status`: 文件处理状态（`processing` | `ready` | `failed`）
- `processing_progress`: 处理进度 0-100
- `error_message`: 失败时的错误详情
- `updated_at`: 状态最后更新时间

### 2.2 获取智能体列表

```http
GET https://atlas.matrix-net.tech/atlas/api/agents?status=active&agent_type=general&skip=0&limit=100
Authorization: Bearer {token}
```

**查询参数**：
- `status`: 筛选状态（active/inactive/training/error）
- `agent_type`: 筛选类型（general/legal/medical/financial/custom）
- `skip`: 跳过记录数（分页）
- `limit`: 返回记录数（最大 1000）

**响应格式**：直接返回数组
```json
[
  {
    "id": "agent_uuid",
    "name": "customer-service",
    "display_name": "智能客服",
    "agent_type": "general",
    "status": "active",
    ...
  }
]
```

> ⚠️ **注意**: 接口直接返回数组，不是分页对象 `{items: [...], total: ...}`

### 2.3 获取智能体详情

```http
GET https://atlas.matrix-net.tech/atlas/api/agents/{agent_id}
Authorization: Bearer {token}
```

> **参数说明**: `agent_id` 是智能体的 UUID，从列表接口或创建接口获取

### 2.4 更新智能体

```http
PUT https://atlas.matrix-net.tech/atlas/api/agents/{agent_id}
Authorization: Bearer {token}
```

> **参数说明**: `agent_id` 是智能体的 UUID

**请求体**：
```json
{
  "display_name": "新名称",       // 可选
  "system_prompt": "新提示词",    // 可选
  "status": "active",            // 可选：active/inactive
  "description": "新描述"         // 可选
}
```

### 2.5 删除智能体

```http
DELETE https://atlas.matrix-net.tech/atlas/api/agents/{agent_id}
Authorization: Bearer {token}
```

> **参数说明**: `agent_id` 是智能体的 UUID

**注意**：删除智能体会同时删除其知识库（Milvus collection）。

---

## 3. 客服管理 `/api/conversations`

### 3.1 创建客服

```http
POST https://atlas.matrix-net.tech/atlas/api/conversations
Authorization: Bearer {token}
```

**请求体**：
```json
{
  "name": "xiaoli",                  // 唯一标识
  "display_name": "小李",             // 显示名称
  "agent_name": "customer-service",  // 关联的智能体名称
  "avatar": "👩‍💼",                   // 头像（emoji 或 URL）
  "welcome_message": "您好，我是小李",// 可选
  "description": "白班客服"           // 可选
}
```

**响应**：
```json
{
  "id": "conversation_uuid",
  "name": "xiaoli",
  "display_name": "小李",
  "avatar": "👩‍💼",
  "status": "online",
  "agent": {
    "id": "agent_uuid",
    "name": "customer-service",
    "display_name": "智能客服",
    "agent_type": "general"
  },
  "welcome_message": "您好，我是小李",
  "message_count": 0,
  "last_active_at": null,
  "created_at": "2025-01-19T08:00:00Z"
}
```

### 3.2 获取客服列表

```http
GET https://atlas.matrix-net.tech/atlas/api/conversations?status=online&skip=0&limit=100
Authorization: Bearer {token}
```

**查询参数**：
- `status`: 筛选状态（online/offline/busy）
- `skip`: 跳过记录数
- `limit`: 返回记录数

**响应格式**：直接返回数组
```json
[
  {
    "id": "conversation_uuid",
    "name": "xiaoli",
    "display_name": "小李",
    "status": "online",
    ...
  }
]
```

> ⚠️ **注意**: 接口直接返回数组，不是分页对象

### 3.3 获取客服详情

```http
GET https://atlas.matrix-net.tech/atlas/api/conversations/{conversation_id}
Authorization: Bearer {token}
```

> **参数说明**: `conversation_id` 是客服的 UUID

### 3.4 更新客服

```http
PUT https://atlas.matrix-net.tech/atlas/api/conversations/{conversation_id}
Authorization: Bearer {token}
```

> **参数说明**: `conversation_id` 是客服的 UUID

**请求体**：
```json
{
  "display_name": "新名称",         // 可选
  "avatar": "🤖",                  // 可选
  "agent_name": "new-agent",       // 🆕 可选：更换关联的智能体
  "status": "online",              // 可选：online/offline/busy
  "welcome_message": "新欢迎语",    // 可选
  "description": "新描述"           // 可选
}
```

**新增功能说明**：
- `agent_name` 字段用于更换客服关联的智能体
- 支持传入智能体的 `name` 或 `id` (UUID)
- 如果不传此字段，保留原有智能体关联
- 这是除了 `switch-agent` 接口外的另一种切换智能体的方式

**使用示例**：
```javascript
// 只修改显示名称，保留原有智能体
await fetch('/api/conversations/xiaoli', {
  method: 'PUT',
  body: JSON.stringify({ display_name: '小李 - 白班' })
});

// 同时修改名称和切换智能体
await fetch('/api/conversations/xiaoli', {
  method: 'PUT',
  body: JSON.stringify({ 
    display_name: '小李 - 夜班',
    agent_name: 'night-shift-agent'
  })
});
```

### 3.5 删除客服

```http
DELETE https://atlas.matrix-net.tech/atlas/api/conversations/{conversation_id}
Authorization: Bearer {token}
```

> **参数说明**: `conversation_id` 是客服的 UUID

### 3.6 切换智能体

```http
POST https://atlas.matrix-net.tech/atlas/api/conversations/{conversation_id}/switch-agent
Authorization: Bearer {token}
```

> **参数说明**: `conversation_id` 是客服的 UUID

**请求体**：
```json
{
  "new_agent_name": "customer-service-night",
  "reason": "切换到夜班智能体"  // 可选
}
```

**响应**：
```json
{
  "conversation_name": "xiaoli",
  "old_agent": "customer-service-day",
  "new_agent": "customer-service-night",
  "switched_at": "2025-01-19T18:00:00Z"
}
```

**应用场景**：
- 白班/夜班切换
- A/B 测试不同智能体
- 升级到新版本智能体

---

## 4. 知识库管理 `/api/knowledge-base`

> ✅ **功能状态**: 已测试验证，所有接口正常工作（2025-11-28 更新）
> 🔧 **最近修复**: 修复了向量化失败导致 chunks_count 为 0 的问题

### 4.1 上传文档

```http
POST https://atlas.matrix-net.tech/atlas/api/knowledge-base/{agent_id}/documents
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

> **参数说明**: `agent_id` 是智能体的 UUID

**请求体**（FormData）：
```javascript
const formData = new FormData();
formData.append('file', fileObject);  // PDF/TXT/MD 文件

fetch('https://atlas.matrix-net.tech/atlas/api/knowledge-base/{agent_id}/documents', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

**响应**（✨ 新增状态字段）：
```json
{
  "file_id": "c6695de6-68fb-4fb9-875a-33802df96a40",
  "filename": "9b7ebf3a_product_manual.pdf",
  "chunks_count": 156,
  "upload_time": "2025-12-03 15:30:00",
  "status": "ready",                    // ✨ 新增：文件处理状态
  "processing_progress": 100,            // ✨ 新增：处理进度（0-100）
  "error_message": null                  // ✨ 新增：错误信息（失败时显示）
}
```

**状态说明**：

| status 值 | 含义 | progress | 说明 |
|-----------|------|----------|------|
| `processing` | 处理中 | 0-99 | 文件正在解析和向量化 |
| `ready` | 已就绪 | 100 | 文件处理完成，可以使用 |
| `failed` | 失败 | 0 | 处理失败，查看 error_message |

**前端实现建议**：

```javascript
// 1. 上传文件
async function uploadDocument(agentId, file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`/atlas/api/knowledge-base/${agentId}/documents`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
  
  const result = await response.json();
  
  // 2. 立即显示上传结果
  if (result.status === 'ready') {
    showSuccess(`文件 ${result.filename} 上传成功！`);
  } else if (result.status === 'failed') {
    showError(`上传失败: ${result.error_message}`);
  } else if (result.status === 'processing') {
    // 对于较大文件，可能需要轮询
    await pollFileStatus(agentId, result.file_id);
  }
}

// 3. 轮询文件状态（可选，用于大文件）
async function pollFileStatus(agentId, fileId) {
  const maxAttempts = 30;  // 最多轮询 30 次（60 秒）
  
  for (let i = 0; i < maxAttempts; i++) {
    await sleep(2000);  // 每 2 秒查询一次
    
    const agent = await fetch(`/atlas/api/agents/${agentId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => r.json());
    
    const file = agent.knowledge_base.files.find(f => f.id === fileId);
    
    if (file.status === 'ready') {
      showSuccess(`文件 ${file.filename} 处理完成！`);
      break;
    } else if (file.status === 'failed') {
      showError(`处理失败: ${file.error_message}`);
      break;
    }
    
    // 更新进度条
    updateProgress(file.processing_progress);
  }
}
```

**UI 展示建议**：

```jsx
// 文件状态徽章
function FileStatusBadge({ status, progress, errorMessage }) {
  if (status === 'ready') {
    return <Badge color="green">✅ 已就绪</Badge>;
  } else if (status === 'failed') {
    return (
      <Tooltip title={errorMessage}>
        <Badge color="red">❌ 失败</Badge>
      </Tooltip>
    );
  } else if (status === 'processing') {
    return (
      <Badge color="yellow">
        ⏳ 处理中 ({progress}%)
      </Badge>
    );
  }
}

// 文件列表项
function FileListItem({ file }) {
  return (
    <div className="file-item">
      <span>{file.filename}</span>
      <FileStatusBadge 
        status={file.status} 
        progress={file.processing_progress}
        errorMessage={file.error_message}
      />
      <span>{file.chunks_count} 个分块</span>
    </div>
  );
}
```

**限制**：
- 最大文件大小：10MB
- 支持格式：PDF、TXT、MD
- 处理时间：小文件 <5 秒，大文件可能需要 10-30 秒

**注意事项**：
- ⚠️ 新创建的智能体需要等待 Milvus 初始化 collection（约 1-3 秒）
- ✅ 上传后文档会自动进行文本切分和向量化（同步处理）
- 📊 **推荐做法**：上传后立即检查返回的 `status` 字段，无需额外轮询
- 🔧 已修复：文件名不再有智能体前缀污染（使用短 UUID）
- 🔧 已修复：向量化失败问题（API 配置和错误处理优化）
- ✨ **新功能**：失败时会自动记录状态，可在文件列表中查看详细错误

**文件名格式**：
- 之前：`test_agent_1763997087284_document.txt`（带 agent 前缀）
- 现在：`a1b2c3d4_document.txt`（短 UUID + 原始文件名）

### 4.2 获取文档列表

```http
GET https://atlas.matrix-net.tech/atlas/api/knowledge-base/{agent_id}/documents
Authorization: Bearer {token}
```

> **参数说明**: `agent_id` 是智能体的 UUID

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "file_id": "doc_20250119_001",
      "filename": "product_manual.pdf",
      "chunks_count": 156,
      "upload_time": "2025-01-19T08:00:00Z"
    }
  ]
}
```

### 4.3 删除文档

```http
DELETE https://atlas.matrix-net.tech/atlas/api/knowledge-base/{agent_id}/documents/{file_id}
Authorization: Bearer {token}
```

> **参数说明**: 
> - `agent_id`: 智能体的 UUID
> - `file_id`: 文档的 UUID（从列表接口获取）

**响应**：
```json
{
  "success": true,
  "message": "文档删除成功",
  "file_id": "doc_20250119_001"
}
```

**注意**：由于 Milvus Lite 的删除限制，建议使用"重建知识库"功能。

### 4.4 获取知识库统计

```http
GET https://atlas.matrix-net.tech/atlas/api/knowledge-base/{agent_id}/stats
Authorization: Bearer {token}
```

> **参数说明**: `agent_id` 是智能体的 UUID

**响应**：
```json
{
  "success": true,
  "data": {
    "agent_name": "customer-service",
    "collection_name": "kb_customer_service",
    "total_files": 3,
    "total_vectors": 458,
    "total_size_mb": 2.5,
    "files": [
      {
        "file_id": "doc_20250119_001",
        "filename": "product_manual.pdf",
        "chunks_count": 156
      }
    ]
  }
}
```

### 4.5 清空知识库

```http
DELETE https://atlas.matrix-net.tech/atlas/api/knowledge-base/{agent_id}/clear
Authorization: Bearer {token}
```

> **参数说明**: `agent_id` 是智能体的 UUID

### 4.6 重建知识库

```http
POST https://atlas.matrix-net.tech/atlas/api/knowledge-base/{agent_id}/rebuild
Authorization: Bearer {token}
```

> **参数说明**: `agent_id` 是智能体的 UUID

**请求体**：
```json
{
  "file_ids": ["doc_20250119_001", "doc_20250119_003"]  // 保留的文件
}
```

**说明**：删除所有文档后重新上传指定文件，解决 Milvus 删除限制问题。

---

## 5. 对话接口 `/api/chat`

### 5.1 发送消息（同步响应）

```http
POST https://atlas.matrix-net.tech/atlas/api/chat/{conversation_id}/message
Authorization: Bearer {token}
Content-Type: application/json
```

> **参数说明**: `conversation_id` 是客服的 UUID
Authorization: Bearer {token}
```

**请求体**：
```json
{
  "content": "你们的产品有什么优势？",
  "session_id": "session_123"  // 可选，用于会话追踪
}
```

**响应**：
```json
{
  "role": "assistant",
  "content": "我们的产品主要有以下优势：\n1. 高性能...\n2. 易用性...",
  "timestamp": "2025-01-19T08:00:00.123Z",
  "agent_name": "customer-service",
  "knowledge_base_used": true
}
```

**工作流程**：
```
用户消息 → 获取客服关联的智能体 → 检索知识库 → LLM 生成回复 → 返回完整结果
```

**空知识库友好提示**：
如果智能体的知识库为空，系统会返回友好提示而不是错误信息：
```json
{
  "content": "您好！我是智能客服助手。目前我的知识库还是空的，请管理员先上传相关文档，我才能更好地为您服务。",
  "knowledge_base_used": true
}
```

**适用场景**：
- ✅ 短文本问答
- ✅ 简单的 Q&A 场景
- ❌ 不适合长文本生成

---

### 5.2 发送消息（流式响应）⚡ 推荐

```http
POST https://atlas.matrix-net.tech/atlas/api/chat/{conversation_id}/message/stream
Authorization: Bearer {token}
Content-Type: application/json
```

> **参数说明**: `conversation_id` 是客服的 UUID

**请求体**：
```json
{
  "content": "请详细介绍一下你们的产品特点和优势",
  "session_id": "session_123"
}
```

**响应格式**：Server-Sent Events (SSE)
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"content": "", "done": false, "agent_name": "customer-service"}

data: {"content": "我们的", "done": false, "agent_name": "customer-service"}

data: {"content": "产品", "done": false, "agent_name": "customer-service"}

data: {"content": "主要有", "done": false, "agent_name": "customer-service"}

data: {"content": "以下", "done": false, "agent_name": "customer-service"}

data: {"content": "特点", "done": false, "agent_name": "customer-service"}

...

data: {"content": "", "done": true, "agent_name": "customer-service"}
```

**数据字段说明**：
- `content`: 本次返回的文本片段（增量内容）
- `done`: 是否结束（`true` 表示生成完成）
- `agent_name`: 智能体名称
- `error`: 错误信息（仅在出错时存在）

**前端实现示例（原生 JavaScript）**：

```javascript
async function sendMessageStream(conversationName, message) {
  const response = await fetch(
    `https://atlas.matrix-net.tech/atlas/api/chat/${conversationName}/message/stream`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content: message })
    }
  );

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullResponse = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.error) {
          console.error('Error:', data.error);
          break;
        }

        if (data.content) {
          fullResponse += data.content;
          // 更新 UI，逐字显示
          updateChatUI(fullResponse);
        }

        if (data.done) {
          console.log('Stream completed');
          return fullResponse;
        }
      }
    }
  }
}
```

**前端实现示例（使用 EventSource）**：

```javascript
function sendMessageStreamSSE(conversationName, message) {
  // 注意：EventSource 不支持 POST，需要后端支持 GET + query params
  // 或使用 fetch API 的方式（推荐上面的方法）
  
  const url = new URL(`https://atlas.matrix-net.tech/atlas/api/chat/${conversationName}/message/stream`);
  const eventSource = new EventSource(url);
  let fullResponse = '';

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.content) {
      fullResponse += data.content;
      updateChatUI(fullResponse);
    }

    if (data.done) {
      eventSource.close();
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE Error:', error);
    eventSource.close();
  };
}
```

**Vue 3 组合式 API 示例**：

```vue
<script setup>
import { ref } from 'vue'

const message = ref('')
const response = ref('')
const isStreaming = ref(false)

async function sendMessage() {
  if (!message.value.trim()) return
  
  isStreaming.value = true
  response.value = ''
  
  try {
    const res = await fetch(
      `https://atlas.matrix-net.tech/atlas/api/chat/customer-service-01/message/stream`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content: message.value })
      }
    )

    const reader = res.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))
          
          if (data.content) {
            response.value += data.content
          }
          
          if (data.done) {
            isStreaming.value = false
          }
        }
      }
    }
  } catch (error) {
    console.error('Stream error:', error)
    isStreaming.value = false
  }
}
</script>

<template>
  <div>
    <input v-model="message" :disabled="isStreaming" />
    <button @click="sendMessage" :disabled="isStreaming">
      {{ isStreaming ? '生成中...' : '发送' }}
    </button>
    <div class="response">{{ response }}</div>
  </div>
</template>
```

**React 示例**：

```jsx
import { useState } from 'react';

function ChatComponent() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = async () => {
    if (!message.trim()) return;
    
    setIsStreaming(true);
    setResponse('');
    
    try {
      const res = await fetch(
        'https://atlas.matrix-net.tech/atlas/api/chat/customer-service-01/message/stream',
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ content: message })
        }
      );

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            
            if (data.content) {
              setResponse(prev => prev + data.content);
            }
            
            if (data.done) {
              setIsStreaming(false);
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      setIsStreaming(false);
    }
  };

  return (
    <div>
      <input 
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        disabled={isStreaming}
      />
      <button onClick={sendMessage} disabled={isStreaming}>
        {isStreaming ? '生成中...' : '发送'}
      </button>
      <div className="response">{response}</div>
    </div>
  );
}
```

**流式响应的优势**：
- ✅ **用户体验极佳**: 类似 ChatGPT 的逐字显示效果
- ✅ **首字响应快**: 无需等待完整生成，立即开始显示
- ✅ **降低等待感知**: 用户看到进度，不会感到焦虑
- ✅ **适合长文本**: 长回答也能快速开始显示
- ✅ **实时反馈**: 生成过程中用户可以随时停止

**注意事项**：
- 流式请求使用 Server-Sent Events (SSE) 协议
- 需要保持连接直到 `done: true`
- 建议添加超时处理（如 60 秒）
- 错误时检查 `error` 字段

---

### 5.3 获取聊天历史

```http
GET https://atlas.matrix-net.tech/atlas/api/chat/{conversation_id}/messages?page=1&page_size=50
Authorization: Bearer {token}
```

> **参数说明**: `conversation_id` 是客服的 UUID

**查询参数**：
- `page`: 页码（从 1 开始，默认 1）
- `page_size`: 每页数量（默认 50，最大 100）

**响应**：
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "role": "assistant",
        "content": "我可以帮你解答关于产品的问题。",
        "timestamp": 1733209845
      },
      {
        "role": "user",
        "content": "你们的产品有什么特点？",
        "timestamp": 1733209842
      },
      {
        "role": "assistant",
        "content": "我们的产品主要有以下特点：...",
        "timestamp": 1733209840
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total": 3,
      "total_pages": 1
    }
  }
}
```

**字段说明**：
- `role`: 消息角色（`user` 用户消息 / `assistant` AI 回复）
- `content`: 消息内容
- `timestamp`: Unix 时间戳（秒，整数，例如 `1733209845`）

**说明**：
- 返回当前会话的所有历史消息（按时间倒序，最新的在前）
- 聊天历史存储在内存中，**服务重启后会清空**
- `timestamp` 为 Unix 时间戳（秒），前端需要乘以 1000 转换为毫秒：`new Date(timestamp * 1000)`
- 同一智能体的所有客服共享聊天历史

**前端示例**：
```javascript
async function getChatHistory(conversationId, page = 1, pageSize = 50) {
  const response = await fetch(
    `https://atlas.matrix-net.tech/atlas/api/chat/${conversationId}/messages?page=${page}&page_size=${pageSize}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const result = await response.json();
  return result.data;
}

// 使用示例
const { messages, pagination } = await getChatHistory('a9342048-b75f-410d-9973-5f2d52b81f48');
console.log(`总共 ${pagination.total} 条消息`);

// 格式化时间戳（Unix 时间戳转换为本地时间）
messages.forEach(msg => {
  const time = msg.timestamp ? new Date(msg.timestamp * 1000).toLocaleString('zh-CN') : '未知时间';
  console.log(`[${time}] ${msg.role}: ${msg.content}`);
});
```

---

### 5.4 清空对话历史

```http
DELETE https://atlas.matrix-net.tech/atlas/api/chat/{conversation_id}/history
Authorization: Bearer {token}
```

> **参数说明**: `conversation_id` 是客服的 UUID

**说明**：仅清空内存中的对话历史，不影响知识库。

---

## 6. 用户管理 `/api/users` (管理员)

### 6.1 获取用户列表

```http
GET https://atlas.matrix-net.tech/atlas/api/users?skip=0&limit=100
Authorization: Bearer {admin_token}
```

### 6.2 获取用户详情

```http
GET https://atlas.matrix-net.tech/atlas/api/users/{user_id}
Authorization: Bearer {admin_token}
```

### 6.3 创建用户

```http
POST https://atlas.matrix-net.tech/atlas/api/users
Authorization: Bearer {admin_token}
```

### 6.4 更新用户

```http
PUT https://atlas.matrix-net.tech/atlas/api/users/{user_id}
Authorization: Bearer {admin_token}
```

### 6.5 删除用户

```http
DELETE https://atlas.matrix-net.tech/atlas/api/users/{user_id}
Authorization: Bearer {admin_token}
```

---

## 数据模型

### Agent（智能体）

```typescript
interface Agent {
  id: string;
  name: string;              // 唯一标识
  display_name: string;      // 显示名称
  agent_type: 'general' | 'legal' | 'medical' | 'financial' | 'custom';
  status: 'active' | 'inactive' | 'training' | 'error';
  system_prompt: string;     // 系统提示词
  description?: string;
  knowledge_base: {
    collection_name: string;
    total_files: number;
    total_vectors: number;
    total_size_mb: number;
    files: Array<{
      file_id: string;
      filename: string;
      chunks_count: number;
    }>;
  };
  created_at: string;        // ISO 8601
  updated_at: string;
  conversations_using: string[];  // 使用该智能体的客服列表
}
```

### Conversation（客服）

```typescript
interface Conversation {
  id: string;
  name: string;              // 唯一标识
  display_name: string;      // 显示名称
  avatar: string;            // emoji 或 URL
  status: 'online' | 'offline' | 'busy';
  agent: {
    id: string;
    name: string;
    display_name: string;
    agent_type: string;
  };
  welcome_message?: string;
  message_count: number;
  last_active_at?: string;
  created_at: string;
}
```

### User（用户）

```typescript
interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}
```

---

## 开发流程

### 典型业务流程

#### 1. 创建智能客服系统

```javascript
// 配置 API 基础地址
const API_BASE_URL = 'https://atlas.matrix-net.tech/atlas/api';

// 1. 注册/登录获取 Token
const authResponse = await fetch(`${API_BASE_URL}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'admin123'
  })
});
const { access_token } = await authResponse.json();

// 2. 创建智能体
const agentResponse = await fetch(`${API_BASE_URL}/agents`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'customer-service',
    display_name: '智能客服',
    agent_type: 'general',
    system_prompt: '你是一个专业的客服人员...'
  })
});

// 3. 上传知识库文档（使用创建时返回的 agent ID）
const formData = new FormData();
formData.append('file', fileInput.files[0]);
const agentId = agentResponse.id;  // 从步骤2获取的 UUID

await fetch(`${API_BASE_URL}/knowledge-base/${agentId}/documents`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${access_token}` },
  body: formData
});

// 4. 创建客服
const conversationResponse = await fetch(`${API_BASE_URL}/conversations`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'xiaoli',
    display_name: '小李',
    agent_name: 'customer-service',
    avatar: '👩‍💼',
    welcome_message: '您好，我是小李，有什么可以帮您？'
  })
});

// 5. 发送消息（使用创建时返回的 conversation ID）
const conversationId = conversationResponse.id;  // 从步骤4获取的 UUID

const chatResponse = await fetch(`${API_BASE_URL}/chat/${conversationId}/message`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    content: '你们的产品有什么特点？'
  })
});
const answer = await chatResponse.json();
console.log(answer.content);
```

#### 2. 智能体切换（白班/夜班）

```javascript
// 创建白班智能体
await createAgent({
  name: 'service-day',
  display_name: '白班客服',
  system_prompt: '你是白班客服，回答要详细专业...'
});

// 创建夜班智能体
await createAgent({
  name: 'service-night',
  display_name: '夜班客服',
  system_prompt: '你是夜班客服，回答要简洁明了...'
});

// 白班时间绑定白班智能体
const supportConv = await createConversation({
  name: 'support',
  display_name: '在线客服',
  agent_name: 'service-day'
});

// 夜班时间切换到夜班智能体（使用 conversation ID）
const conversationId = supportConv.id;  // UUID

await fetch(`https://atlas.matrix-net.tech/atlas/api/conversations/${conversationId}/switch-agent`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    new_agent_name: 'service-night',
    reason: '切换到夜班模式'
  })
});
```

#### 3. 多客服共享智能体

```javascript
// 创建一个通用智能体
const generalAgent = await createAgent({
  name: 'general-support',
  display_name: '通用客服智能体'
});

// 上传知识库（使用 agent UUID）
await uploadDocument(generalAgent.id, 'knowledge.pdf');

// 多个客服共享这个智能体
await createConversation({
  name: 'xiaoli',
  display_name: '小李',
  agent_name: 'general-support'
});

await createConversation({
  name: 'xiaozhang',
  display_name: '小张',
  agent_name: 'general-support'
});

// 两个客服使用相同的知识库和 AI 能力
```

---

## 常见错误

### ❌ 错误 1: 404 Not Found - 路径缺少 UUID

**错误信息**:
```
POST /atlas/api/chat/stream
404 Not Found
```

**原因**: 路径中缺少必需的 `conversation_id` 参数

**❌ 错误代码**:
```javascript
fetch('https://atlas.matrix-net.tech/atlas/api/chat/stream', {
  method: 'POST'
})
```

**✅ 正确代码**:
```javascript
const conversationId = 'db21165e-a6b5-44bd-a2eb-d435a1a6ab9d';
fetch(`https://atlas.matrix-net.tech/atlas/api/chat/${conversationId}/message/stream`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ content: '你好' })
})
```

### ❌ 错误 2: 使用 name 而不是 UUID

**错误信息**:
```
GET /atlas/api/agents/customer-service
404 Not Found
```

**原因**: 接口已迁移到 UUID，不再支持 name 查询

**❌ 错误代码**:
```javascript
const agentName = 'customer-service';
fetch(`/atlas/api/agents/${agentName}`) // 使用 name
```

**✅ 正确代码**:
```javascript
// 1. 先从列表获取 UUID
const agents = await fetch('/atlas/api/agents').then(r => r.json());
const agent = agents.find(a => a.name === 'customer-service');
const agentId = agent.id; // UUID

// 2. 使用 UUID 查询
fetch(`/atlas/api/agents/${agentId}`)
```

### ❌ 错误 3: Token 过期

**错误信息**:
```json
{
  "detail": "无效的认证凭证"
}
```

**解决方案**:
```javascript
// 检查 token 过期时间
const tokenExpiry = localStorage.getItem('token_expiry');
if (Date.now() > tokenExpiry) {
  // 重新登录
  await login();
}
```

### ❌ 错误 4: 文件上传失败 - 编码问题

**错误信息**:
```json
{
  "detail": "上传失败: Error loading uploads/xxx.txt"
}
```

**原因**: 文件使用非 UTF-8 编码（如 GBK）

**解决方案**: 
- 后端已支持多编码自动检测（UTF-8, GBK, GB2312, GB18030）
- 如果仍失败，请检查文件是否损坏
- 大文件会自动分块处理（单块 < 400 字符）

### ❌ 错误 5: 知识库数据不一致

**现象**:
```
文件总数: 0
向量总数: 3,995 ❌
存储大小: 0.00MB
```

**原因**: 删除文件时元数据被删除，但向量数据残留

**检测方法**:
```javascript
// 获取统计信息
const stats = await fetch(`/atlas/api/knowledge-base/${agentId}/stats`)
  .then(r => r.json());

if (!stats.data.is_consistent) {
  console.warn('数据不一致:', stats.data.warning);
  // 显示警告提示用户
}
```

**解决方案 1: 自动修复**（推荐）
```javascript
// 调用修复接口
const result = await fetch(
  `/atlas/api/knowledge-base/${agentId}/fix-inconsistency`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
).then(r => r.json());

console.log('修复结果:', result);
// {
//   success: true,
//   message: "数据不一致已修复，知识库已清空",
//   before: { files: 0, vectors: 3995 },
//   after: { files: 0, vectors: 0 }
// }
```

**解决方案 2: 手动清空**
```javascript
// 完全清空知识库
await fetch(`/atlas/api/knowledge-base/${agentId}/clear`, {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

**预防措施**:
- 后端已增强级联删除机制
- 删除文件时会同时清理向量数据和元数据
- 统计接口会自动检测不一致并返回警告

### ❌ 错误 6: 如何处理文件上传失败？

**场景**: 文件上传后 `status` 返回 `failed`

**错误示例**:
```json
{
  "file_id": "abc-123",
  "filename": "document.txt",
  "status": "failed",
  "processing_progress": 0,
  "error_message": "向量化失败：所有文本块都未能添加到向量数据库。\n可能原因：\n1. Embedding API 配置错误..."
}
```

**解决方案**:
```javascript
async function handleUpload(agentId, file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(
    `/atlas/api/knowledge-base/${agentId}/documents`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    }
  );
  
  const result = await response.json();
  
  // 检查状态
  if (result.status === 'failed') {
    // 显示详细错误
    showError(`上传失败: ${result.error_message}`);
    
    // 常见失败原因及处理
    if (result.error_message.includes('文本块都未能添加')) {
      // 空文件或无法解析的文件
      showTip('请检查文件内容是否为空或格式是否正确');
    } else if (result.error_message.includes('文件不存在')) {
      // 文件路径问题（不太可能）
      showTip('请重新选择文件上传');
    }
    
    // 可选：自动删除失败的文件记录
    await deleteDocument(agentId, result.file_id);
    
    return null;
  } else if (result.status === 'ready') {
    showSuccess(`文件上传成功！已生成 ${result.chunks_count} 个分块`);
    return result;
  }
}
```

**常见失败原因**:
1. **空文件**: 文件内容为空或只有空白字符
2. **格式错误**: PDF 损坏、编码错误（已支持多编码自动检测）
3. **文件过大**: 超过 10MB 限制
4. **API 配置**: Embedding API 暂时不可用（罕见）

**前端 UI 建议**:
```jsx
function FileUploadResult({ file }) {
  if (file.status === 'failed') {
    return (
      <Alert severity="error">
        <AlertTitle>❌ 文件处理失败</AlertTitle>
        <Typography variant="body2">
          文件名: {file.filename}
        </Typography>
        <Accordion>
          <AccordionSummary>查看详细错误</AccordionSummary>
          <AccordionDetails>
            <pre>{file.error_message}</pre>
          </AccordionDetails>
        </Accordion>
        <Button onClick={() => deleteFile(file.id)}>
          删除失败记录
        </Button>
      </Alert>
    );
  }
  
  return <FileSuccessCard file={file} />;
}
```

### ❌ 错误 7: 文件上传后如何确认状态？

**推荐做法**: 检查上传响应的 `status` 字段，无需轮询

```javascript
// ✅ 推荐：直接检查响应
const result = await uploadFile(agentId, file);

if (result.status === 'ready') {
  console.log('✅ 文件已就绪，可立即使用');
  refreshFileList();
} else if (result.status === 'failed') {
  console.error('❌ 处理失败:', result.error_message);
}

// ⚠️ 不推荐：轮询（目前所有文件都是同步处理，< 10 秒完成）
// 除非未来支持异步处理大文件
```

**何时需要轮询？**

目前**不需要轮询**，因为：
- 文件处理是同步的
- 上传响应直接包含最终状态
- 小文件 <5 秒，大文件 <30 秒

如果未来支持异步处理，可使用：
```javascript
async function waitForReady(agentId, fileId) {
  for (let i = 0; i < 30; i++) {
    await sleep(2000);
    const agent = await getAgentDetail(agentId);
    const file = agent.knowledge_base.files.find(f => f.id === fileId);
    
    if (file.status !== 'processing') {
      return file;
    }
  }
  throw new Error('处理超时');
}
```

### ❌ 错误 8: EventSource 不支持 POST

**错误信息**:
```
EventSource 只支持 GET 请求
```

**原因**: 浏览器原生 EventSource API 只支持 GET 方法

**解决方案**: 使用 fetch 手动处理流式响应

**❌ 错误代码**:
```javascript
const eventSource = new EventSource(
  `/atlas/api/chat/${conversationId}/message/stream`,
  {
    method: 'POST',  // ❌ EventSource 不支持 POST
    body: JSON.stringify({ content: '你好' })
  }
);
```

**✅ 正确代码**:
```javascript
const response = await fetch(
  `/atlas/api/chat/${conversationId}/message/stream`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ content: '你好' })
  }
);

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  const lines = text.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') break;
      console.log('收到:', data);
    }
  }
}
```

### ❌ 错误 9: 文件编码问题（已修复）

**原因**: 文件编码不是 UTF-8（已修复，系统现支持多编码）

**支持的编码**: UTF-8, GBK, GB2312, GB18030, Latin-1

**解决方案**: 无需处理，后端自动检测编码

---

## 错误处理

### HTTP 状态码

- `200 OK`: 请求成功
- `201 Created`: 创建成功
- `204 No Content`: 删除成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证或 Token 过期
- `403 Forbidden`: 权限不足
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器错误

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误

#### 1. Token 过期

```json
{
  "detail": "Token 已过期或无效"
}
```

**解决**：重新登录获取新 Token。

#### 2. 资源不存在

```json
{
  "detail": "智能体不存在: unknown-agent"
}
```

**解决**：检查资源名称是否正确。

#### 3. 文件过大

```json
{
  "detail": "文件过大: 12.5MB > 10MB"
}
```

**解决**：压缩文件或分割上传。

#### 4. 客服状态异常

```json
{
  "detail": "客服状态异常: offline"
}
```

**解决**：更新客服状态为 `online`。

---

## 最佳实践

### 1. UUID 管理

```javascript
// ✅ 推荐：使用状态管理存储实体 ID
class EntityStore {
  constructor() {
    this.agents = new Map();      // id -> agent
    this.conversations = new Map(); // id -> conversation
  }

  // 加载并缓存列表
  async loadAgents() {
    const agents = await fetch('/atlas/api/agents').then(r => r.json());
    agents.forEach(agent => {
      this.agents.set(agent.id, agent);
    });
    return agents;
  }

  // 通过 name 查找 ID
  getAgentIdByName(name) {
    for (const [id, agent] of this.agents) {
      if (agent.name === name) return id;
    }
    return null;
  }

  // 通过 ID 获取完整对象
  getAgent(id) {
    return this.agents.get(id);
  }
}

// 使用示例
const store = new EntityStore();
await store.loadAgents();

// 显示：使用 name
console.log(agent.name); // "customer-service"

// API 调用：使用 ID
const agentId = store.getAgentIdByName('customer-service');
fetch(`/atlas/api/agents/${agentId}`)
```

### 2. Token 管理

```javascript
class ApiClient {
  constructor() {
    this.token = localStorage.getItem('access_token');
    this.tokenExpiry = localStorage.getItem('token_expiry');
  }

  async request(url, options = {}) {
    // 检查 Token 是否过期
    if (this.isTokenExpired()) {
      await this.refreshToken();
    }

    // 自动添加基础 URL
    const fullUrl = url.startsWith('http') ? url : `https://atlas.matrix-net.tech${url}`;

    return fetch(fullUrl, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${this.token}`
      }
    });
  }

  isTokenExpired() {
    return Date.now() > this.tokenExpiry;
  }

  async refreshToken() {
    // 重新登录
    const response = await fetch('https://atlas.matrix-net.tech/atlas/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: this.username,
        password: this.password
      })
    });
    const data = await response.json();
    this.setToken(data.access_token, data.expires_in);
  }

  setToken(token, expiresIn) {
    this.token = token;
    this.tokenExpiry = Date.now() + expiresIn * 1000;
    localStorage.setItem('access_token', token);
    localStorage.setItem('token_expiry', this.tokenExpiry);
  }
}
```

### 2. 错误处理

```javascript
async function safeApiCall(apiFunction) {
  try {
    const response = await apiFunction();
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '请求失败');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API 调用失败:', error);
    
    // 根据错误类型处理
    if (error.message.includes('Token')) {
      // Token 过期，重新登录
      window.location.href = '/login';
    } else if (error.message.includes('不存在')) {
      // 资源不存在
      showNotification('资源不存在', 'error');
    } else {
      // 其他错误
      showNotification(error.message, 'error');
    }
    
    throw error;
  }
}
```

### 3. 文件上传进度

```javascript
async function uploadWithProgress(agentId, file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percent = (e.loaded / e.total) * 100;
        onProgress(percent);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error('上传失败'));
      }
    });

    xhr.open('POST', `https://atlas.matrix-net.tech/atlas/api/knowledge-base/${agentId}/documents`);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.send(formData);
  });
}

// 使用（agentId 是智能体的 UUID）
const agentId = 'agent-uuid-from-list';
uploadWithProgress(agentId, file, (percent) => {
  console.log(`上传进度: ${percent}%`);
  updateProgressBar(percent);
});
```

### 4. 实时对话

```javascript
class ChatWidget {
  constructor(conversationId, token) {
    this.conversationId = conversationId;  // 客服的 UUID
    this.token = token;
    this.messages = [];
  }

  async sendMessage(content) {
    // 添加用户消息到界面
    this.addMessage('user', content);

    // 显示加载状态
    this.showTyping();

    try {
      const response = await fetch(
        `https://atlas.matrix-net.tech/atlas/api/chat/${this.conversationId}/message`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ content })
        }
      );

      const data = await response.json();

      // 添加 AI 回复到界面
      this.hideTyping();
      this.addMessage('assistant', data.content);

      return data;
    } catch (error) {
      this.hideTyping();
      this.showError('发送失败，请重试');
      throw error;
    }
  }

  addMessage(role, content) {
    this.messages.push({ role, content, timestamp: new Date() });
    this.renderMessages();
  }

  showTyping() {
    // 显示"正在输入..."动画
  }

  hideTyping() {
    // 隐藏加载状态
  }

  renderMessages() {
    // 渲染消息列表
  }
}
```

### 5. 智能体切换最佳实践

```javascript
class AgentSwitcher {
  constructor(conversationId, token) {
    this.conversationId = conversationId;  // 客服的 UUID
    this.token = token;
  }

  async switchByTime() {
    const hour = new Date().getHours();
    
    // 白班时间（8:00-20:00）
    if (hour >= 8 && hour < 20) {
      await this.switchAgent('service-day', '切换到白班智能体');
    } 
    // 夜班时间（20:00-8:00）
    else {
      await this.switchAgent('service-night', '切换到夜班智能体');
    }
  }

  async switchAgent(newAgentName, reason) {
    const response = await fetch(
      `https://atlas.matrix-net.tech/atlas/api/conversations/${this.conversationId}/switch-agent`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          new_agent_name: newAgentName,
          reason
        })
      }
    );

    const data = await response.json();
    console.log(`智能体切换: ${data.old_agent} → ${data.new_agent}`);
    
    return data;
  }
}

// 定时切换（使用 conversation UUID）
const conversationId = 'conv-uuid-from-list';
const switcher = new AgentSwitcher(conversationId, token);
setInterval(() => {
  switcher.switchByTime();
}, 60 * 60 * 1000);  // 每小时检查一次
```

### 6. 知识库管理最佳实践

```javascript
class KnowledgeBaseManager {
  constructor(agentId, token) {
    this.agentId = agentId;  // 智能体的 UUID
    this.token = token;
  }

  async uploadMultipleFiles(files) {
    const results = [];
    
    for (const file of files) {
      try {
        const result = await this.uploadFile(file);
        results.push({ file: file.name, success: true, ...result });
      } catch (error) {
        results.push({ file: file.name, success: false, error: error.message });
      }
    }
    
    return results;
  }

  async uploadFile(file) {
    // 验证文件
    if (!this.isValidFile(file)) {
      throw new Error('不支持的文件类型');
    }
    
    if (file.size > 10 * 1024 * 1024) {
      throw new Error('文件过大（最大 10MB）');
    }

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `https://atlas.matrix-net.tech/atlas/api/knowledge-base/${this.agentId}/documents`,
      {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.token}` },
        body: formData
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }

    return await response.json();
  }

  isValidFile(file) {
    const validExtensions = ['.pdf', '.txt', '.md'];
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
    return validExtensions.includes(ext);
  }

  async getStats() {
    const response = await fetch(
      `https://atlas.matrix-net.tech/atlas/api/knowledge-base/${this.agentId}/stats`,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );
    
    const result = await response.json();
    return result.data;
  }

  async rebuildWithFiles(fileIdsToKeep) {
    const response = await fetch(
      `https://atlas.matrix-net.tech/atlas/api/knowledge-base/${this.agentId}/rebuild`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file_ids: fileIdsToKeep })
      }
    );

    return await response.json();
  }
}

// 使用示例（agentId 是智能体的 UUID）
const agentId = 'agent-uuid-from-list';
const kbManager = new KnowledgeBaseManager(agentId, token);
await kbManager.uploadMultipleFiles(files);
```

### 6. 文件状态管理最佳实践 ✨

```javascript
class FileStatusManager {
  constructor(agentId, token) {
    this.agentId = agentId;
    this.token = token;
  }

  /**
   * 上传文件并处理所有状态
   */
  async uploadWithStatusHandling(file, callbacks = {}) {
    const {
      onStart = () => {},
      onSuccess = () => {},
      onError = () => {},
      onProgress = () => {}
    } = callbacks;

    try {
      onStart();
      onProgress(0); // 开始上传

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(
        `/atlas/api/knowledge-base/${this.agentId}/documents`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${this.token}` },
          body: formData
        }
      );

      const result = await response.json();

      // 检查上传响应状态
      if (result.status === 'ready') {
        onProgress(100);
        onSuccess(result);
        return {
          success: true,
          file: result
        };
      } else if (result.status === 'failed') {
        onError(result.error_message);
        return {
          success: false,
          error: result.error_message,
          file: result
        };
      } else if (result.status === 'processing') {
        // 如果未来支持异步处理，在这里轮询
        const finalResult = await this.waitForReady(result.file_id, onProgress);
        
        if (finalResult.status === 'ready') {
          onSuccess(finalResult);
          return { success: true, file: finalResult };
        } else {
          onError(finalResult.error_message);
          return { success: false, error: finalResult.error_message };
        }
      }
    } catch (error) {
      onError(error.message);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * 轮询文件状态（可选，用于未来的异步处理）
   */
  async waitForReady(fileId, onProgress = () => {}) {
    const maxAttempts = 30; // 最多 60 秒
    
    for (let i = 0; i < maxAttempts; i++) {
      await this.sleep(2000);
      
      const agent = await this.getAgentDetail();
      const file = agent.knowledge_base.files.find(f => f.id === fileId);
      
      if (!file) {
        throw new Error('文件不存在');
      }
      
      // 更新进度
      onProgress(file.processing_progress);
      
      if (file.status === 'ready' || file.status === 'failed') {
        return file;
      }
    }
    
    throw new Error('处理超时');
  }

  async getAgentDetail() {
    const response = await fetch(
      `/atlas/api/agents/${this.agentId}`,
      { headers: { 'Authorization': `Bearer ${this.token}` } }
    );
    return response.json();
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 批量上传文件
   */
  async uploadBatch(files, onFileComplete = () => {}) {
    const results = [];
    
    for (const file of files) {
      const result = await this.uploadWithStatusHandling(file, {
        onSuccess: (fileResult) => {
          console.log(`✅ ${file.name} 上传成功`);
          onFileComplete(file.name, true, fileResult);
        },
        onError: (error) => {
          console.error(`❌ ${file.name} 上传失败: ${error}`);
          onFileComplete(file.name, false, { error });
        }
      });
      
      results.push(result);
    }
    
    return results;
  }

  /**
   * 获取所有失败的文件
   */
  async getFailedFiles() {
    const agent = await this.getAgentDetail();
    return agent.knowledge_base.files.filter(f => f.status === 'failed');
  }

  /**
   * 重试失败的文件（需要重新上传）
   */
  async retryFailedFiles() {
    const failedFiles = await this.getFailedFiles();
    console.log(`发现 ${failedFiles.length} 个失败文件`);
    
    // 注意：需要用户重新选择文件，这里只是示例
    for (const file of failedFiles) {
      console.log(`需要重新上传: ${file.filename}`);
      // await this.deleteDocument(file.id); // 可选：删除失败记录
    }
    
    return failedFiles;
  }

  async deleteDocument(fileId) {
    await fetch(
      `/atlas/api/knowledge-base/${this.agentId}/documents/${fileId}`,
      {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );
  }
}

// React 组件示例
function FileUploadComponent({ agentId, token }) {
  const [uploadProgress, setUploadProgress] = React.useState({});
  const [uploadResults, setUploadResults] = React.useState([]);
  const fileManager = new FileStatusManager(agentId, token);

  const handleUpload = async (files) => {
    const fileArray = Array.from(files);
    
    // 初始化进度
    const progress = {};
    fileArray.forEach(file => {
      progress[file.name] = { status: 'uploading', progress: 0 };
    });
    setUploadProgress(progress);

    // 上传文件
    for (const file of fileArray) {
      await fileManager.uploadWithStatusHandling(file, {
        onStart: () => {
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'uploading', progress: 0 }
          }));
        },
        onProgress: (percent) => {
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'uploading', progress: percent }
          }));
        },
        onSuccess: (result) => {
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'success', progress: 100, result }
          }));
          setUploadResults(prev => [...prev, result]);
        },
        onError: (error) => {
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: { status: 'failed', progress: 0, error }
          }));
        }
      });
    }
  };

  return (
    <div>
      <input 
        type="file" 
        multiple 
        onChange={(e) => handleUpload(e.target.files)} 
      />
      
      {Object.entries(uploadProgress).map(([name, data]) => (
        <div key={name}>
          <span>{name}</span>
          {data.status === 'success' && <span>✅ 成功</span>}
          {data.status === 'failed' && (
            <span>❌ 失败: {data.error}</span>
          )}
          {data.status === 'uploading' && (
            <ProgressBar value={data.progress} />
          )}
        </div>
      ))}
    </div>
  );
}
```

**关键点**：
1. ✅ **同步处理**：目前所有文件都是同步处理的，上传响应直接包含最终状态
2. ✅ **无需轮询**：检查 `response.status` 即可，不需要额外的状态查询
3. ✅ **错误处理**：失败时自动记录到元数据，可在列表中查看
4. ✅ **进度反馈**：虽然是同步的，但可以用上传进度 + 固定的处理时间估算
5. ⚠️ **未来扩展**：如果支持异步处理，可使用 `waitForReady()` 方法轮询

---

## 测试示例

### 完整测试脚本

```javascript
// test-api.js

const BASE_URL = 'https://atlas.matrix-net.tech/atlas/api';
let token = '';
let agentId = '';
let conversationId = '';

// 1. 登录
async function login() {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'admin',
      password: 'admin123'
    })
  });
  const data = await response.json();
  token = data.access_token;
  console.log('✅ 登录成功');
}

// 2. 创建智能体
async function createAgent() {
  const response = await fetch(`${BASE_URL}/agents`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: 'test-agent',
      display_name: '测试智能体',
      agent_type: 'general'
    })
  });
  const data = await response.json();
  agentId = data.id;  // 保存 UUID
  console.log('✅ 创建智能体:', data.name, 'ID:', data.id);
}

// 3. 创建客服
async function createConversation() {
  const response = await fetch(`${BASE_URL}/conversations`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: 'test-chat',
      display_name: '测试客服',
      agent_name: 'test-agent',
      avatar: '🤖'
    })
  });
  const data = await response.json();
  conversationId = data.id;  // 保存 UUID
  console.log('✅ 创建客服:', data.name, 'ID:', data.id);
}

// 4. 发送消息（使用 conversation UUID）
async function sendMessage() {
  const response = await fetch(`${BASE_URL}/chat/${conversationId}/message`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      content: '你好'
    })
  });
  const data = await response.json();
  console.log('✅ AI 回复:', data.content);
}

// 运行测试
(async () => {
  await login();
  await createAgent();
  await createConversation();
  await sendMessage();
  console.log('\n✅ 所有测试通过！');
  console.log('Agent ID:', agentId);
  console.log('Conversation ID:', conversationId);
})();
```

---

## 附录

### A. API 环境配置

前端项目建议配置环境变量：

```javascript
// .env.production
VITE_API_BASE_URL=https://atlas.matrix-net.tech/atlas/api

// .env.development
VITE_API_BASE_URL=http://localhost:8000/api
```

使用示例：
```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

fetch(`${API_BASE_URL}/agents`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### B. CORS 配置

后端已配置 CORS 允许所有来源，前端可直接调用 API。

生产环境 CORS 配置：
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
```

### C. 后端环境变量

后端使用以下环境变量（仅供参考，前端无需关心）：

```bash
# OpenAI API
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# 数据库
DATABASE_URL=postgresql://user:password@host:5432/atlas

# Milvus 向量数据库
MILVUS_HOST=your-milvus-host
MILVUS_PORT=19530

# JWT 认证配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

> ⚠️ **安全提示**: 以上为示例配置，实际部署时请使用安全的密钥和连接信息。

### D. 在线文档

- **Swagger UI**: https://atlas.matrix-net.tech/atlas/docs
- **ReDoc**: https://atlas.matrix-net.tech/atlas/redoc
- **健康检查**: https://atlas.matrix-net.tech/atlas/health

### E. 常用工具

- **Postman Collection**: 可导入 Swagger JSON
- **cURL 示例**:

```bash
# 登录
curl -X POST "https://atlas.matrix-net.tech/atlas/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 获取智能体列表
curl -X GET "https://atlas.matrix-net.tech/atlas/api/agents" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 健康检查（无需认证）
curl https://atlas.matrix-net.tech/atlas/health
```

---

## 联系支持

如有问题，请查看：
- 📚 在线文档：https://atlas.matrix-net.tech/atlas/docs
- 🐛 GitHub Issues：提交 Bug 或功能请求
- 📧 Email：技术支持邮箱

---

## 更新日志

### v0.3.1 (2025-12-03) ✨

**🆕 新功能**：
- ✅ **文件状态管理**：上传接口新增 `status`、`processing_progress`、`error_message` 字段
- ✅ **失败记录追踪**：失败的文件会自动记录状态和详细错误信息
- ✅ **实时状态反馈**：上传响应直接包含处理状态，无需轮询
- ✅ **完善的错误处理**：失败原因分类（空文件、格式错误、API 问题等）

**📝 API 变更**：
- `POST /knowledge-base/{agent_id}/documents` 响应新增 3 个字段
- `GET /agents/{agent_id}` 中的 files 数组新增状态字段
- 向后兼容：老版本前端仍可正常使用（新字段可选）

**📚 文档更新**：
- 新增"文件状态管理最佳实践"章节
- 新增 FAQ："如何处理文件上传失败"
- 新增 FAQ："文件上传后如何确认状态"
- 更新上传接口说明和响应示例
- 添加 React 组件示例代码

**🎯 使用建议**：
- 推荐做法：检查上传响应的 `status` 字段即可
- 无需轮询：所有文件都是同步处理（< 30 秒）
- 失败处理：显示 `error_message` 并提供重试选项

### v0.3.0 (2025-11-28)

**🚀 重大更新**：
- ✅ **UUID 迁移**：所有 24 个 API 接口统一使用 UUID 作为路径参数
- ✅ **文件上传优化**：支持多编码（UTF-8, GBK, GB2312, GB18030）
- ✅ **大文件支持**：自动分块处理，支持 1.4MB+ 文件
- ✅ **模型更新**：切换到 Qwen/Qwen2.5-7B-Instruct
- ✅ **文档完善**：添加常见错误和最佳实践

**⚠️ 破坏性变更**：
- 路径参数从 `{entity_name}` 改为 `{entity_id}` (UUID)
- 需要更新所有 API 调用代码
- 详见 [API UUID 迁移指南](API_UUID_MIGRATION.md)

**🐛 Bug 修复**：
- 修复知识库删除失败问题
- 修复文件编码导致的加载错误
- 修复 Embedding API token 限制问题
- 修复批次大小超限问题

### v0.2.2 (2025-11-24)

**功能更新**：
- 修复文件上传向量化问题
- 列表接口改为返回数组格式
- 客服更新接口新增 agent_name 字段
- 优化空知识库友好提示
- 修复文件名污染问题

---

**文档版本**: v0.3.0  
**最后更新**: 2025-11-28  
**后端 API 版本**: v0.3.0  
**兼容性**: 前端需更新所有 API 调用以支持 UUID
