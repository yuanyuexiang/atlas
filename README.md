# Atlas 智能客服后端系统

> 基于 **FastAPI + PostgreSQL + Milvus + LangChain** 构建的企业级智能客服 API 系统  
> 采用 **Repository + Manager + Service + Facade** 四层架构，代码精简 46%

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Milvus](https://img.shields.io/badge/Milvus-2.3+-orange.svg)](https://milvus.io/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

> 🌐 **重要提示**: 应用部署在 `/atlas` 子路径下  
> 生产环境访问地址: `https://atlas.matrix-net.tech/atlas/api/*`  
> 本地开发访问地址: `http://localhost:8000/atlas/api/*`  
> 详见 [根路径配置说明](ROOT_PATH_GUIDE.md)

## ✨ 核心特性

### 🏗️ 架构特性
- **四层架构设计**: Repository (数据访问) + Manager (实例管理) + Service (业务逻辑) + Facade (协调器)
- **依赖注入**: 全局单例 + 构造函数注入，提高可测试性
- **代码精简 46%**: AgentService 从 460 行优化到 250 行，职责清晰
- **异步处理**: FastAPI BackgroundTasks，解决大文件阻塞（6.4MB PDF）
- **状态追踪**: Document 表实现 processing → ready/failed 状态机

### 🤖 业务特性
- **智能体管理**: 创建和管理多个 AI 智能体，支持不同领域（通用、法律、医疗、金融等）
- **客服管理**: 客服与智能体解耦，支持动态切换和共享智能体
- **知识库管理**: 上传文档（PDF/TXT/MD），自动向量化存储到 Milvus
- **智能对话**: 基于 RAG（检索增强生成）的三阶段智能问答
  - 🔄 **查询改写**: 将口语化问题转换为 3 条多角度检索查询
  - 🔍 **文档检索**: 多查询合并去重，提高召回率
  - ✅ **答案验证**: 可选的事实核查，确保答案有据可依
- **真流式响应**: 基于 `astream_events` 的 token 级流式输出
  - 🌊 **Token 级流式**: 逐字逐句实时显示，类似 ChatGPT 打字机效果
  - ⚡ **双 LLM 架构**: 主流程流式输出 + 工具调用非流式执行
  - 📡 **SSE 推送**: Server-Sent Events 标准，前端实时接收
- **动态切换**: 支持白班/夜班智能体切换、A/B 测试、版本升级
- **统计分析**: 知识库统计、对话记录、文档处理状态追踪

### 🔐 安全特性
- **JWT 认证**: 完整的用户认证和权限管理系统
- **密码加密**: bcrypt 密码哈希存储
- **Token 过期**: 可配置的 Token 有效期（默认 30 分钟）
- **路由保护**: 中间件级别的认证拦截

### 🚀 运维特性
- **Docker 部署**: 开箱即用的容器化部署方案
- **反向代理支持**: 应用部署在 `/atlas` 子路径，支持 Nginx
- **健康检查**: `/health` 端点监控服务状态
- **数据库连接池**: PostgreSQL 连接池优化（pool_size=10）
- **向量检索优化**: Milvus IVF_FLAT 索引 + COSINE 相似度
- **列表查询性能优化**: 
  - 🚀 **50 倍性能提升**: agents 列表从 5-6 秒优化到 <0.1 秒
  - 📊 **预加载优化**: 使用 `joinedload` 避免 N+1 查询
  - ⚡ **零 Milvus 调用**: 列表接口使用估算值，详情接口查询精确值

## 💡 项目功能原理

### RAG（检索增强生成）工作流程

Atlas 采用**三阶段优化 RAG** 技术实现智能问答，核心流程如下：

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. 文档处理与向量化                            │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
   用户上传文档 (PDF/TXT/MD)
         ↓
   文档解析 → 提取文本内容
         ↓
   文本切分 (Chunk)
   • 每个 chunk 约 500-1000 字符
   • 保留上下文重叠（overlap）
         ↓
   向量化 (Embedding)
   • 使用 OpenAI text-embedding-3-small
   • 每段文本转换为 1536 维向量
         ↓
   存储到 Milvus 向量数据库
   • 每个智能体独立的 collection
   • 支持高效的相似度搜索

┌─────────────────────────────────────────────────────────────────┐
│                 2. 用户问答流程（三阶段优化）                      │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
   用户提问："合同违约怎么处理？"
         ↓
   【第1步：查询改写】🔄
   • 使用 LLM 将口语化问题改写为 3 条检索查询
   • 多角度表达：["合同违约处理", "违约责任规定", "合同不履行后果"]
   • 提高召回率：同义词扩展、关键术语提取
         ↓
   【第2步：文档检索】🔍
   • 使用 3 条查询分别检索 Milvus（每条返回 Top-3）
   • 合并结果并去重（按文档ID去重，保留最高分）
   • 按相似度排序，返回最终 Top-3 文档
         ↓
   检索结果示例：
   ┌──────────────────────────────────────┐
   │ [文档1] (相似度: 0.89)               │
   │ 《民法典》第577条：合同违约责任...   │
   │                                      │
   │ [文档2] (相似度: 0.85)               │
   │ 《民法典》第579条：违约金规定...     │
   │                                      │
   │ [文档3] (相似度: 0.78)               │
   │ 合同法案例：违约处理流程...          │
   └──────────────────────────────────────┘
         ↓
   【第3步：答案生成】💬
   • LLM 基于检索到的文档生成答案
   • 流式输出（逐 token 显示，打字机效果）
   • 自然引用："根据资料显示..."
         ↓
   【第4步：答案验证（可选）】✅
   • 检查答案是否有充分文档证据支撑
   • 返回 VERIFIED 或 UNVERIFIED + 问题说明
   • 用于重要事实的二次核查
         ↓
   返回给用户（流式输出）
   "根据《民法典》第577条规定，当事人一方不履行
    合同义务或者履行合同义务不符合约定的，应当承担
    继续履行、采取补救措施或者赔偿损失等违约责任..."
```

### 核心技术说明

#### 1. 文档向量化

```python
# 文本切分策略
RecursiveCharacterTextSplitter(
    chunk_size=1000,        # 每段约 1000 字符
    chunk_overlap=200,      # 段落间重叠 200 字符，保持上下文连贯
    separators=["\n\n", "\n", "。", "！", "？", "；"]  # 优先按自然段落分割
)

# 向量化模型
OpenAIEmbeddings(
    model="text-embedding-3-small",  # 1536 维向量
    dimensions=1536
)
```

#### 2. 向量检索

```python
# Milvus 相似度搜索
vector_store.similarity_search_with_score(
    query=question,          # 用户问题
    k=4,                     # 返回最相关的 4 个片段
    score_threshold=0.7      # 相似度阈值（可选）
)

# 返回格式：
# [
#   (Document(page_content="..."), 0.95),  # 相似度 95%
#   (Document(page_content="..."), 0.89),  # 相似度 89%
#   ...
# ]
```

#### 3. Prompt 构建

```python
# 系统提示词 + 检索内容 + 用户问题
prompt = f"""
{system_prompt}

知识库内容：
{retrieved_context}

用户问题：{user_question}

请基于上述知识库内容回答用户问题。
"""
```

### 智能体与客服的解耦设计

#### 为什么要解耦？

**传统设计问题**：
```
客服 A → 知识库 A
客服 B → 知识库 B  ❌ 重复维护，资源浪费
客服 C → 知识库 C
```

**Atlas 的解耦设计**：
```
客服 A ──┐
客服 B ──┼→ 智能体 X → 知识库 X  ✅ 共享知识，统一管理
客服 C ──┘

客服 D → 智能体 Y → 知识库 Y
```

**实际应用场景**：

1. **白班/夜班切换**
   ```
   客服"小李"（8:00-20:00）→ 智能体"详细版"
                ↓ 20:00 自动切换
   客服"小李"（20:00-8:00）→ 智能体"简化版"
   ```

2. **A/B 测试**
   ```
   客服组 A → 智能体 v1.0（旧版）
   客服组 B → 智能体 v2.0（新版）
   → 对比效果，选择最优版本
   ```

3. **多客服共享**
   ```
   客服"小张"、"小李"、"小王" → 智能体"法律顾问"
   → 三个客服共享同一知识库，回答一致
   ```

### 数据流转过程

```
┌──────────────┐
│  前端应用     │  Vue/React
└──────┬───────┘
       │ HTTP REST API
       ↓
┌──────────────────────────────┐
│  FastAPI 路由层               │
│  • JWT 认证中间件             │
│  • 请求参数验证（Pydantic）   │
└──────┬───────────────────────┘
       │
       ↓
┌──────────────────────────────┐
│  业务逻辑层 (Service)         │
### 核心组件说明

#### 1. **数据访问层** (repository/)

**repository/agent_repository.py** (150 行)
- **职责**: 纯 CRUD 操作，隔离数据库细节
- **模式**: Repository 模式
- **实现**: 
  - `AgentRepository`: Agent 表操作
  - `DocumentRepository`: Document 表操作
- **优势**: 易于测试、数据库无关、单一职责

```python
# repository/agent_repository.py
class AgentRepository:
    @staticmethod
    def create(db: Session, agent: Agent) -> Agent
    def get_by_id(db: Session, agent_id: str) -> Optional[Agent]
    def get_by_name(db: Session, name: str) -> Optional[Agent]
    def list_all(db: Session, ...) -> List[Agent]
    def update(db: Session, agent: Agent, update_data: dict) -> Agent
    def delete(db: Session, agent: Agent) -> bool
```

#### 2. **领域层** (domain/)

**domain/entities.py** (领域实体 - ORM 模型)
- **职责**: 业务领域实体的 ORM 映射
- **模式**: SQLAlchemy ORM
- **实体**: Agent（智能体）、Document（文档）、Conversation（客服）
- **特点**: 包含业务标识、生命周期、关系映射

**domain/auth.py** (认证实体)
- **职责**: 用户认证相关的领域实体
- **实体**: User（用户）
- **包含**: 用户名、密码哈希、权限标识

**domain/managers/rag_agent_manager.py** (130 行 - 实例生命周期管理)
- **职责**: RAG Agent 生命周期管理
- **模式**: Singleton + 内存缓存
- **缓存策略**: `Dict[agent_name, RAGAgent]`
- **核心方法**:
  - `get_or_create()`: 获取或创建 RAG 实例
  - `reload()`: 重新加载（更新提示词后）
  - `remove()`: 移除实例
  - `clear_all()`: 清空缓存

**domain/processors/document_processor.py** (文档处理引擎)
- **职责**: 文档加载、文本切分、内容过滤
- **支持格式**: PDF、TXT、MD
- **切分策略**: RecursiveCharacterTextSplitter
  - chunk_size: 800
  - chunk_overlap: 200
- **过滤规则**: 长度过滤、内容去重

**domain/processors/vector_store_manager.py** (向量存储管理)
- **职责**: 向量数据库操作封装
- **核心方法**:
  - `add_documents()`: 批量添加文档向量
  - `delete_by_file_id()`: 按文件 ID 删除
  - `get_statistics()`: 获取集合统计信息
- **封装优势**: 隐藏 Milvus 细节，易于切换向量库

#### 3. **应用服务层** (application/)

**application/agent_service.py** (250 行 - Facade 协调器)
- **职责**: 统一的智能体管理入口，协调各子系统
- **模式**: Facade 模式 + 依赖注入
- **依赖**: AgentRepository, RAGAgentManager, KnowledgeBaseService
- **核心方法**:
  - `create_agent()`: 创建智能体（DB + RAG 实例）
  - `get_agent()`: 查询智能体
  - `list_agents()`: 列表查询
  - `update_agent()`: 更新智能体
  - `delete_agent()`: 删除智能体（级联删除知识库）

**application/knowledge_base_service.py** (240 行 - 知识库服务)
- **职责**: 知识库业务逻辑协调
- **模式**: Service 模式 + 依赖注入
- **依赖**: DocumentProcessor, VectorStoreManager, DocumentRepository
- **核心流程**:
  1. 创建 Document 记录（status: processing）
  2. 文档处理（加载、切分、过滤）
  3. 向量化存储（Milvus）
  4. 更新状态（ready/failed）

**application/rag_agent.py** (RAG 核心逻辑)
- **职责**: 基于 LangChain 的 RAG Agent 实现
- **框架**: 使用 `create_agent()` 创建 Agent，支持 `.invoke()` 和 `.astream_events()` 调用
- **核心功能**:
  - ✅ **三阶段 RAG 流程**:
    1. **查询改写** (rewrite_query)：口语化问题 → 3 条多角度检索查询（JSON 数组）
    2. **文档检索** (retrieve_context)：多查询合并去重，按相似度排序（返回 Top-3）
    3. **答案生成**：基于检索文档，LLM 流式生成答案
    4. **答案验证** (verify_answer)：可选的事实核查（VERIFIED/UNVERIFIED）
  - ✅ **双 LLM 架构**:
    - `llm_streaming`: Agent 主流程，逐 token 流式输出
    - `llm_non_streaming`: 工具内部调用，同步返回完整结果
  - ✅ **Token 级流式输出**: 通过 `.astream_events(version="v2")` 实现
  - ✅ **对话历史管理**: `messages` 列表维护上下文
- **工具定义**: 使用 `StructuredTool.from_function()` 定义，完整的签名和描述
- **检索策略**: Milvus 相似度搜索 + COSINE 相似度 + 相似度排序

#### 4. **API 路由层 + Schema** (api/)

**API 路由** (api/*.py)

**API Schema** (api/schemas/)
- **职责**: Pydantic DTO，API 请求/响应验证
- **按业务模块拆分**:
  - `agent.py` - 智能体相关 Schema（AgentCreate, AgentResponse 等）
  - `conversation.py` - 客服相关 Schema（ConversationCreate, AgentSwitchRequest 等）
  - `knowledge_base.py` - 知识库相关 Schema（DocumentUploadResponse, KnowledgeBaseStats）
  - `chat.py` - 聊天相关 Schema（MessageRequest, MessageResponse）
  - `auth.py` - 认证相关 Schema（UserCreate, UserLogin, Token）
  - `common.py` - 通用 Schema（SuccessResponse, ErrorResponse）
- **设计理念**: Schema 与 API 路由放在同一层，强调内聚性和 Python 社区实践

**api/agents.py** (智能体管理 API)
- POST `/agents` - 创建智能体
- GET `/agents` - 列表查询
- GET `/agents/{agent_id}` - 详情查询
- PUT `/agents/{agent_id}` - 更新智能体
- DELETE `/agents/{agent_id}` - 删除智能体

**api/knowledge_base.py** (知识库管理 API)
- POST `/knowledge-base/{agent_id}/documents` - 上传文档（异步）
- GET `/knowledge-base/{agent_name}/documents` - 文档列表
- GET `/knowledge-base/{agent_name}/statistics` - 统计信息
- DELETE `/knowledge-base/{agent_name}/documents/{file_id}` - 删除文档

**重要改进**：
- ✅ **异步文档上传**: 使用 FastAPI BackgroundTasks
  - 立即返回 `status: processing`
  - 后台异步处理（独立数据库会话）
  - 避免大文件阻塞（解决 6.4MB PDF 卡死问题）
  
```python
@router.post("/{agent_id}/documents")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ...
):
    # 1. 保存临时文件
    temp_path = save_upload_file(file)
    
    # 2. 创建 DB 记录（status: processing）
    doc = create_document_record(db, agent_id, file.filename)
    
    # 3. 添加后台任务
    background_tasks.add_task(
        process_document_background,  # 异步处理函数
        agent_name,
        temp_path,
        doc.id
    )
    
    # 4. 立即返回（不等待处理完成）
    return {
        "status": "processing",
        "file_id": doc.id,
        "filename": file.filename,
        "chunks_count": 0  # 处理完成后更新
    }
```

**api/chat.py** (对话管理 API)
- POST `/chat` - 发送消息（支持流式）
- GET `/chat/history/{conversation_id}` - 历史记录

**api/conversations.py** (客服管理 API)
- POST `/conversations` - 创建客服
- GET `/conversations` - 列表查询
- PUT `/conversations/{conv_id}/agent` - 切换智能体

**api/auth.py** (认证授权 API)
- POST `/auth/register` - 用户注册
- POST `/auth/login` - 用户登录
- GET `/auth/me` - 当前用户信息

#### 3. **数据模型层** (models/)

**models/entities.py** (ORM 实体)
```python
class Agent(Base):
    """智能体实体"""
    id, name, description, system_prompt, business_type
    created_by_id, created_at, updated_at
    
    # 关系
    conversations = relationship("Conversation")
    documents = relationship("Document", cascade="all, delete-orphan")

class Document(Base):
    """文档实体（新增）"""
    id, agent_id, filename, file_size, file_type
    status, chunks_count, processing_progress, error_message
    created_at, updated_at
    
    # 状态枚举
    class DocumentStatus(str, Enum):
        processing = "processing"  # 处理中
        ready = "ready"            # 就绪
        failed = "failed"          # 失败

class Conversation(Base):
    """客服实体"""
    id, name, avatar_url, welcome_message, status
    agent_id, message_count, last_active_at

class User(Base):
    """用户实体"""
    id, username, email, hashed_password
    is_active, is_superuser, created_at
```

**models/schemas.py** (Pydantic 响应模型)
```python
class KnowledgeBaseInfo(BaseModel):
    """知识库信息（修复字段名称）"""
    collection_name: str         # 集合名称
    total_files: int            # 文件总数（原 file_count）
    total_vectors: int          # 向量总数（原 vector_count）

class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    system_prompt: str
    business_type: str
    knowledge_base: KnowledgeBaseInfo  # 嵌套信息
    created_at: datetime
    updated_at: datetime

class DocumentUploadResponse(BaseModel):
    file_id: str
    filename: str
    status: str                 # processing/ready/failed
    chunks_count: int          # 处理完成后更新
    message: Optional[str]
```

#### 4. **配置层** (core/)

**core/config.py** (全局配置)
- 数据库连接字符串
- JWT 密钥和过期时间
- LLM 配置（模型、温度、最大 token）
- 文件上传限制

**core/database.py** (数据库会话)
- SQLAlchemy 引擎和会话工厂
- 依赖注入 `get_db()`

**core/milvus_config.py** (Milvus 配置)
- 连接参数
- 集合配置（维度、索引类型、距离度量）

**core/auth_config.py** (认证配置)
- 密码哈希工具
- JWT token 生成和验证
- 权限装饰器

### 核心数据模型

#### 1. Agent（智能体）

```python
Agent {
    id: UUID                    # 主键
    name: "legal-advisor"       # 唯一标识（用于 API）
    description: "法律咨询专家"  # 描述
    system_prompt: "你是..."    # 系统提示词（定义角色）
    business_type: "legal"      # 业务类型：general/legal/medical/financial
    created_by_id: UUID         # 创建者
    created_at: datetime
    updated_at: datetime
    
    # 关联的 Milvus Collection
    collection_name: "agent_legal_advisor"
    
    # 关系
    documents: List[Document]   # 知识库文档（级联删除）
    conversations: List[Conversation]  # 关联客服
}
```

#### 2. Document（文档）

```python
Document {
    id: UUID                    # 主键
    agent_id: UUID              # 所属智能体（外键）
    filename: "法律法规.pdf"    # 文件名
    file_size: 6728192          # 文件大小（字节）
    file_type: "pdf"            # 文件类型
    status: DocumentStatus      # processing/ready/failed
    chunks_count: 85            # 切片数量
    processing_progress: 100    # 处理进度（%）
    error_message: null         # 错误信息
    created_at: datetime
    updated_at: datetime
    
    # 状态机
    processing → ready ✅
             ↘ failed ❌
}
```

#### 3. Conversation（客服）

```python
Conversation {
    id: UUID                    # 主键
    name: "customer-service-01" # 唯一标识
    avatar_url: "https://..."   # 头像 URL
    welcome_message: "您好..."  # 欢迎语
    agent_id: UUID              # 关联的智能体 ID（外键）
    status: "online"            # online/offline/busy
    message_count: 1523         # 消息计数
    last_active_at: datetime    # 最后活跃时间
    created_at: datetime
    updated_at: datetime
}
```

#### 4. User（用户）

```python
User {
    id: UUID                    # 主键
    username: "admin"           # 用户名（唯一）
    email: "admin@example.com"  # 邮箱（唯一）
    hashed_password: "..."      # 密码哈希（bcrypt）
    is_active: true             # 激活状态
    is_superuser: false         # 超级管理员
    created_at: datetime
}
```
}
```

#### 3. 知识库文档

### 性能优化策略

#### 1. 异步文档处理（解决大文件阻塞）

**问题**: 6.4MB PDF 上传导致应用卡死，HTTP 超时

**解决方案**: FastAPI BackgroundTasks 异步处理

```python
# api/knowledge_base.py
@router.post("/{agent_id}/documents")
async def upload_document(
    background_tasks: BackgroundTasks,
    agent_id: str,
    file: UploadFile = File(...)
):
    # 1. 立即创建 DB 记录（status: processing）
    doc = DocumentRepository().create(
        db,
        agent_id=agent_id,
        filename=file.filename,
        status=DocumentStatus.processing,
        chunks_count=0
    )
    
    # 2. 保存临时文件
    temp_path = save_upload_file(file)
    
    # 3. 添加后台任务（不等待完成）
    background_tasks.add_task(
        process_document_background,  # 独立会话
        agent_name,
        temp_path,
        doc.id
    )
    
    # 4. 立即返回（不阻塞主线程）
    return DocumentUploadResponse(
        file_id=doc.id,
        filename=file.filename,
        status="processing",  # 前端可轮询查询状态
        chunks_count=0
    )

# 后台处理函数（独立数据库会话）
def process_document_background(agent_name: str, file_path: str, doc_id: str):
    from core.database import SessionLocal
    db = SessionLocal()  # 新会话，避免线程冲突
    
    try:
        # 1. 加载文档
        docs = DocumentProcessor().process_file(file_path)
        
        # 2. 向量化存储
        VectorStoreManager().add_documents(agent_name, docs, doc_id)
        
        # 3. 更新状态
        DocumentRepository().update_status(
            db, doc_id, 
            status=DocumentStatus.ready,
            chunks_count=len(docs)
        )
    except Exception as e:
        DocumentRepository().update_status(
            db, doc_id,
            status=DocumentStatus.failed,
            error_message=str(e)
        )
    finally:
        db.close()
```

**优势**:
- ✅ **立即响应**: 上传接口秒级返回，不阻塞
- ✅ **独立会话**: 后台任务使用独立 DB 会话，避免线程冲突
- ✅ **状态追踪**: 前端可轮询 `/documents/{file_id}` 查询处理状态
- ✅ **错误恢复**: 失败记录在 DB，可手动重试

#### 2. 向量检索优化

**索引策略**:
```python
# Milvus 集合配置
collection_config = {
    "index_type": "IVF_FLAT",      # 倒排文件索引
    "metric_type": "COSINE",       # 余弦相似度
    "nlist": 1024,                 # 聚类中心数
    "nprobe": 16                   # 查询时探测的聚类数
}
```

**检索优化**:
- Top-K 限制: 默认检索前 5 个最相关片段
- 相似度阈值: 过滤低于 0.7 的结果
- 缓存策略: RAG Agent 实例内存缓存（RAGAgentManager）

#### 3. 数据库连接池

```python
# core/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # 基础连接池大小
    max_overflow=20,        # 最大溢出连接
    pool_pre_ping=True,     # 连接健康检查
    pool_recycle=3600,      # 连接回收时间（1 小时）
    echo=False              # 生产环境关闭 SQL 日志
)
```

#### 4. 服务层职责分离（代码精简 46%）

**重构前**: AgentService 460 行，混合 4 种职责
**重构后**: 
- AgentRepository: 150 行（CRUD）
- RAGAgentManager: 130 行（实例管理）
- KnowledgeBaseService: 240 行（业务逻辑）
- AgentService: 250 行（Facade 协调）

**优势**:
- ✅ 单一职责，易于维护
- ✅ 依赖注入，易于测试
- ✅ 代码复用，减少重复

### 安全性设计

#### 1. JWT 认证
```python
# Token 生成
access_token = create_access_token(
    data={"sub": username, "user_id": user_id},
    expires_delta=timedelta(minutes=30)
)

# Token 验证（依赖注入）
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # 验证 Token 有效性
    # 解析用户信息
    # 检查用户状态
```

#### 2. 密码加密
```python
# 使用 bcrypt 加密
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
```

#### 3. API 权限控制
- 普通用户：可访问智能体、客服、对话接口
- 管理员：可管理用户、系统配置

## 🏗️ 架构设计

### 系统架构（标准 DDD 四层架构）

Atlas 采用**领域驱动设计(DDD)**的标准四层架构，清晰的目录结构直观反映各层职责：

```
┌─────────────────────────────────────────────────────────────────┐
│                    API 路由层 (api/)                             │
│  • JWT 认证中间件 (get_current_user)                            │
│  • 请求参数验证 (Pydantic DTO from schemas/)                    │
│  • HTTP 响应处理 (JSON/SSE Stream)                              │
│                                                                  │
│  api/agents.py, api/chat.py, api/knowledge_base.py ...         │
└────────────────────────┬────────────────────────────────────────┘
                         │ 依赖注入
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              应用服务层 (application/) - Application Service      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  AgentService (Facade 协调器)                            │   │
│  │  • 协调 Repository、Manager、KnowledgeBaseService        │   │
│  │  • 业务流程编排，不包含业务规则                           │   │
│  │  • 代码量: 250 行 (从 460 行精简 46%)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ KnowledgeBase    │  │ RAGAgent         │                    │
│  │ Service          │  │ (LangChain RAG)  │                    │
│  │ • 文档上传编排    │  │ • 检索增强生成    │                    │
│  │ • 向量化协调      │  │ • 对话历史        │                    │
│  │ • 状态追踪        │  │ • 流式响应        │                    │
│  └──────────────────┘  └──────────────────┘                    │
└────────────────────────┬────────────────────────────────────────┘
                         │ 依赖注入
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   领域层 (domain/) - Domain Layer                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  domain/managers/ - 领域管理器（生命周期管理）             │  │
│  │  • RAGAgentManager: RAG 实例生命周期管理（130 行）        │  │
│  │  • 内存缓存: Dict[agent_name, RAGAgent]                  │  │
│  │  • 单例模式: 全局唯一管理器                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ domain/          │  │ domain/          │                    │
│  │ processors/      │  │ processors/      │                    │
│  │ DocumentProcessor│  │ VectorStore      │                    │
│  │ • 文档加载        │  │ Manager          │                    │
│  │ • 文本切分        │  │ • 向量存储操作    │                    │
│  │ • 内容过滤        │  │ • 集合管理        │                    │
│  └──────────────────┘  └──────────────────┘                    │
└────────────────────────┬────────────────────────────────────────┘
                         │ 依赖注入
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              数据访问层 (repository/) - Repository/DAO           │
│                                                                  │
│  ┌────────────────────────────────────────┐                    │
│  │  repository/agent_repository.py         │                    │
│  │  • AgentRepository: 纯 CRUD (150 行)   │                    │
│  │  • DocumentRepository: 文件元数据       │                    │
│  │  • 数据库操作封装，零业务逻辑            │                    │
│  └────────────────────────────────────────┘                    │
│                                                                  │
│  ┌────────────────────────────────────────┐                    │
│  │  application/milvus_service.py         │                    │
│  │  • Collection 管理                      │                    │
│  │  • 向量检索封装                          │                    │
│  │  • 统计查询                              │                    │
│  └────────────────────────────────────────┘                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────┬─────────────────────────────────────────┐
│                      │                                          │
│   PostgreSQL         │          Milvus                          │
│   (关系数据库)       │        (向量数据库)                      │
│   models/entities.py │    application/milvus_service.py         │
│                      │                                          │
│  • User (用户)       │  • agent_{name} collections              │
│  • Agent (智能体)    │  • 文档向量 (1536 维)                    │
│  • Document (文档)   │  • 语义检索                               │
│  • Conversation      │  • 相似度计算                             │
└──────────────────────┴─────────────────────────────────────────┘
```

### 目录结构与 DDD 分层对应

```
┌──────────────────┬─────────────────────────────────────────┐
│  DDD 层级         │  项目目录                                │
├──────────────────┼─────────────────────────────────────────┤
│  表现层           │  api/                                   │
│  (Presentation)  │  • agents.py, chat.py, auth.py ...     │
├──────────────────┼─────────────────────────────────────────┤
│  应用服务层       │  application/                           │
│  (Application)   │  • agent_service.py (Facade)            │
│                  │  • knowledge_base_service.py            │
│                  │  • auth_service.py, user_service.py     │
│                  │  • rag_agent.py (RAG 核心逻辑)          │
├──────────────────┼─────────────────────────────────────────┤
│  领域层           │  domain/                                │
│  (Domain)        │  ├── managers/                          │
│                  │  │   └── rag_agent_manager.py          │
│                  │  └── processors/                        │
│                  │      ├── document_processor.py          │
│                  │      └── vector_store_manager.py        │
├──────────────────┼─────────────────────────────────────────┤
│  数据访问层       │  repository/                            │
│  (Infrastructure)│  └── agent_repository.py                │
│                  │                                         │
│                  │  application/milvus_service.py (向量库) │
├──────────────────┼─────────────────────────────────────────┤
│  DTO 层          │  schemas/                               │
│  (Data Transfer) │  ├── schemas.py (业务 DTO)              │
│                  │  └── auth_schemas.py (认证 DTO)         │
├──────────────────┼─────────────────────────────────────────┤
│  领域模型         │  models/                                │
│  (Domain Model)  │  ├── entities.py (ORM 实体)             │
│                  │  └── auth.py (用户实体)                 │
└──────────────────┴─────────────────────────────────────────┘
```

**设计原则**：
- ✅ **依赖倒置**: 高层模块不依赖低层模块，都依赖抽象
- ✅ **单一职责**: 每个模块只负责一种职责
- ✅ **开闭原则**: 对扩展开放，对修改关闭
- ✅ **接口隔离**: 通过依赖注入解耦
- ✅ **标准命名**: application(应用层) / domain(领域层) / repository(数据层) / schemas(DTO层)

### 架构模式详解

#### 1. Repository 模式（数据访问层）

**职责**: 纯 CRUD 操作，隔离数据库细节

```python
# services/agent_repository.py (150 行)
class AgentRepository:
    """智能体数据访问层 - 纯 CRUD"""
    
    def create(self, db: Session, agent: Agent) -> Agent
    def get_by_id(self, db: Session, agent_id: str) -> Optional[Agent]
    def get_by_name(self, db: Session, name: str) -> Optional[Agent]
    def list_all(self, db: Session, ...) -> List[Agent]
    def update(self, db: Session, agent: Agent) -> Agent
    def delete(self, db: Session, agent_id: str) -> bool
```

**优势**:
- ✅ 单一职责：只负责数据库操作
- ✅ 易于测试：可以 mock Repository
- ✅ 数据库无关：切换数据库只需修改 Repository

#### 2. Manager 模式（领域管理层）

**职责**: 管理特定领域的生命周期和状态

```python
# services/rag_agent_manager.py (130 行)
class RAGAgentManager:
    """RAG Agent 生命周期管理器"""
    
    def __init__(self):
        self._agents: Dict[str, RAGAgent] = {}  # 内存缓存
    
    def get_or_create(self, agent_name: str, system_prompt: str) -> RAGAgent
    def get(self, agent_name: str) -> Optional[RAGAgent]
    def remove(self, agent_name: str) -> bool
    def reload(self, agent_name: str, new_prompt: str) -> RAGAgent
    def clear_all(self) -> None
```

**优势**:
- ✅ 单例管理：全局唯一的 Agent 实例
- ✅ 内存缓存：避免重复创建
- ✅ 生命周期控制：统一管理创建/销毁

#### 3. Service 模式（业务服务层）

**职责**: 封装复杂的业务逻辑，协调多个领域对象

```python
# services/knowledge_base_service.py (240 行)
class KnowledgeBaseService:
    """知识库管理服务"""
    
    def __init__(
        self,
        doc_processor: DocumentProcessor,
        vector_manager: VectorStoreManager
    ):
        self.doc_processor = doc_processor
        self.vector_manager = vector_manager
        self.doc_repo = DocumentRepository()
    
    def upload_file(self, db, agent_id, agent_name, file_path):
        # 1. 创建 DB 记录 (processing 状态)
        # 2. 文档处理 (DocumentProcessor)
        # 3. 向量化存储 (VectorStoreManager)
        # 4. 更新状态 (ready/failed)
```

**优势**:
- ✅ 业务编排：协调多个领域对象完成复杂流程
- ✅ 事务管理：统一处理业务事务
- ✅ 错误处理：集中处理业务异常

#### 4. Facade 模式（外观协调层）

**职责**: 为复杂子系统提供简单统一的接口

```python
# services/agent_service.py (250 行，精简 46%)
class AgentService:
    """智能体服务 - Facade 协调器"""
    
    def __init__(
        self,
        rag_manager: RAGAgentManager,
        kb_service: KnowledgeBaseService
    ):
        self.agent_repo = AgentRepository()
        self.rag_manager = rag_manager
        self.kb_service = kb_service
    
    def create_agent(self, db, agent_data):
        # 1. Repository: 创建数据库记录
        # 2. RAGAgentManager: 初始化 RAG 实例
        # 3. 返回响应
    
    def upload_file(self, db, agent_name, file_path):
        # 委托给 KnowledgeBaseService
        return self.kb_service.upload_file(...)
```

**优势**:
- ✅ 简化接口：API 层只需调用 AgentService
- ✅ 解耦依赖：隐藏内部复杂性
- ✅ 易于维护：修改内部实现不影响外部调用

### 数据持久化设计

#### 新增 Document 表（文件元数据）

```python
# models/entities.py
class Document(Base):
    """文档实体 - 知识库文件元数据"""
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"))
    
    # 文件信息
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer)  # 字节
    file_type = Column(String(20))  # pdf, txt, md
    
    # 处理状态
    status = Column(Enum(DocumentStatus))  # processing, ready, failed
    chunks_count = Column(Integer, default=0)
    processing_progress = Column(Integer, default=0)
    error_message = Column(Text)
    
    # 关系
    agent = relationship("Agent", back_populates="documents")
```

**状态机流转**:
```
upload → processing → ready ✅
                   ↘ failed ❌
```

### 依赖注入设计

所有服务通过**构造函数注入**,提高可测试性：

```python
# 全局单例 (Singleton Pattern)
_kb_service = None

def get_kb_service() -> KnowledgeBaseService:
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService(
            doc_processor=DocumentProcessor(),
            vector_manager=VectorStoreManager()
        )
    return _kb_service

# API 层使用
agent_service = get_agent_service()  # 依赖注入
```

### 三层业务解耦

Atlas 保留了创新的三层业务解耦设计，实现界面、能力和数据的分离：

```
┌────────────────────────────────────┐
│  Conversation（客服界面层）         │
│  • 显示名称、头像、欢迎语            │
│  • 状态管理（online/offline/busy）  │
│  • 消息统计和活跃时间                │
└──────────────┬─────────────────────┘
               │
               │ 可动态切换（1:1 绑定）
               ↓
┌────────────────────────────────────┐
│  Agent（智能体能力层）              │
│  • 系统提示词（角色设定）            │
│  • 业务类型（通用/专业领域）         │
│  • 专属知识库（独立隔离）            │
└──────────────┬─────────────────────┘
               │
               │ 专属存储（1:1 关系）
               ↓
┌────────────────────────────────────┐
│  Knowledge Base（知识存储层）       │
│  • Milvus 向量集合                  │
│  • 文档切片和向量化                  │
│  • 语义检索和相似度匹配              │
│  • Document 表（文件元数据）         │
└────────────────────────────────────┘
```

**架构优势**：
- ✅ **灵活切换**: 客服可随时切换不同智能体（白班/夜班、A/B 测试）
- ✅ **资源共享**: 多个客服可共享同一智能体及其知识库
- ✅ **独立管理**: 智能体的知识库完全隔离，互不干扰
- ✅ **易于扩展**: 可独立升级智能体能力而不影响客服界面
- ✅ **状态追踪**: Document 表记录文档处理状态和元数据

## 🚀 快速开始

### 方式一：本地开发（推荐）

#### 1. 环境准备

```bash
# 确认 Python 版本（需要 3.12+）
python --version

# 安装 uv（现代化的 Python 包管理器）
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或使用 pip
pip install uv
```

#### 2. 克隆项目

```bash
git clone https://github.com/yuanyuexiang/atlas.git
cd atlas
```

#### 3. 安装依赖

```bash
# 使用 uv 安装（推荐，更快）
uv sync

# 或使用 pip
pip install -e .
```

#### 4. 配置环境变量

复制示例配置文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：

```env
# OpenAI Compatible API（必需）
OPENAI_API_KEY=sk-or-v1-xxxxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
CHAT_MODEL=openai/gpt-oss-120b
EMBEDDING_MODEL=openai/text-embedding-3-small

# PostgreSQL 数据库（必需）
DATABASE_URL=postgresql://user:password@host:5432/database

# Milvus 向量数据库（必需）
MILVUS_HOST=localhost
MILVUS_PORT=19530

# JWT 认证（生产环境必须修改）
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用配置
DEBUG=false
METADATA_DIR=metadata_store
```

**生成安全的 JWT 密钥**：
```bash
openssl rand -hex 32
```

#### 5. 初始化数据库

```bash
# 创建默认管理员账户（用户名: admin, 密码: admin123）
uv run python create_admin.py
```

> ⚠️ **安全提示**: 首次登录后请立即修改默认密码！

#### 6. 启动服务

```bash
# 开发模式（支持热重载）
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 7. 访问文档

启动成功后，访问以下地址：

- 🏠 **主页**: http://localhost:8000
- 📚 **Swagger UI**: http://localhost:8000/atlas/docs（交互式 API 文档）
- 📖 **ReDoc**: http://localhost:8000/atlas/redoc（美观的 API 文档）
- ❤️ **健康检查**: http://localhost:8000/atlas/health

### 方式二：Docker 部署

#### 1. 使用 Docker Compose（最简单）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 2. 单独构建 Docker 镜像

```bash
# 构建镜像
docker build -t atlas:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name atlas \
  atlas:latest
```

### 方式三：生产部署

生产环境建议使用 GitHub Actions 自动部署到云服务器。

详细配置请参考：
- [GitHub Secrets 配置](.github/SECRETS_SETUP.md)
- [数据库迁移指南](MIGRATION_SUMMARY.md)

## 🔐 认证与授权

系统采用 JWT（JSON Web Token）认证机制，保护所有业务 API。

### 默认管理员账户

首次运行 `create_admin.py` 会创建：

```
用户名: admin
密码: admin123
邮箱: admin@example.com
```

> ⚠️ **重要**: 生产环境首次登录后，请立即修改默认密码！

### 认证流程

#### 1. 注册新用户（可选）

```bash
curl -X POST "http://localhost:8000/atlas/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "full_name": "测试用户"
  }'
```

#### 2. 登录获取 Token

```bash
# 登录并获取 Token
TOKEN=$(curl -s -X POST "http://localhost:8000/atlas/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

**响应示例**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 3. 使用 Token 访问 API

所有需要认证的 API 都需要在请求头中携带 Token：

```bash
curl "http://localhost:8000/atlas/api/agents" \
  -H "Authorization: Bearer $TOKEN"
```

#### 4. 获取当前用户信息

```bash
curl "http://localhost:8000/atlas/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

### 受保护的端点

所有业务 API 都需要认证：

| 端点 | 说明 | 权限要求 |
|------|------|----------|
| `/api/auth/*` | 认证接口（登录/注册/用户信息） | 部分公开 |
| `/api/agents/*` | 智能体管理 | 需要认证 |
| `/api/conversations/*` | 客服管理 | 需要认证 |
| `/api/knowledge-base/*` | 知识库管理 | 需要认证 |
| `/api/chat/*` | 对话接口 | 需要认证 |
| `/api/users/*` | 用户管理 | **仅管理员** |

### Token 管理

- **有效期**: 默认 30 分钟（可通过 `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` 配置）
- **刷新策略**: Token 过期后需要重新登录
- **存储建议**: 前端应将 Token 存储在内存或 localStorage

详细认证文档：[AUTHENTICATION.md](AUTHENTICATION.md)

## 📚 API 使用示例

### 完整业务流程

以下是一个完整的智能客服创建和使用流程。

#### 步骤 1: 登录获取 Token

```bash
# 登录并保存 Token
TOKEN=$(curl -s -X POST "http://localhost:8000/atlas/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')
```

#### 步骤 2: 创建智能体

```bash
# 创建一个法律领域的智能体
curl -X POST "http://localhost:8000/atlas/api/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "legal-advisor",
    "description": "专业的法律咨询智能体",
    "business_type": "legal",
    "system_prompt": "你是一位专业的法律顾问，精通中国法律法规，擅长解答民事、商事法律问题。"
  }'
```

**响应**：
```json
{
  "id": "69999c94-6b9f-4652-9795-0224e0903d82",
  "name": "legal-advisor",
  "description": "专业的法律咨询智能体",
  "business_type": "legal",
  "system_prompt": "你是一位专业的法律顾问...",
  "knowledge_base": {
    "collection_name": "agent_legal_advisor",
    "total_files": 0,
    "total_vectors": 0
  },
  "created_at": "2025-01-19T08:00:00Z",
  "updated_at": "2025-01-19T08:00:00Z"
}
```

#### 步骤 3: 上传知识库文档（异步处理）

```bash
# 上传法律法规文档（支持 PDF/TXT/MD）
curl -X POST "http://localhost:8000/atlas/api/knowledge-base/{agent_id}/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/legal_document.pdf"
```

**立即响应（异步处理）**：
```json
{
  "file_id": "doc-uuid-xxx",
  "filename": "legal_document.pdf",
  "status": "processing",    # 处理中
  "chunks_count": 0,         # 处理完成后更新
  "message": "文档正在后台处理中..."
}
```

**轮询查询处理状态**：
```bash
# 查询文档列表（包含处理状态）
curl "http://localhost:8000/atlas/api/knowledge-base/legal-advisor/documents" \
  -H "Authorization: Bearer $TOKEN"
```

**响应示例**：
```json
{
  "agent_name": "legal-advisor",
  "documents": [
    {
      "id": "doc-uuid-xxx",
      "filename": "legal_document.pdf",
      "file_size": 6728192,
      "file_type": "pdf",
      "status": "ready",           # processing → ready/failed
      "chunks_count": 1250,        # 处理完成后更新
      "processing_progress": 100,  # 处理进度
      "error_message": null,
      "created_at": "2025-01-19T08:00:00Z",
      "updated_at": "2025-01-19T08:05:00Z"
    }
  ],
  "total_files": 1,
  "total_size": 6728192
}
```

**状态机流转**：
```
upload → processing (立即返回)
            ↓ (后台异步处理)
         ready ✅ (成功)
         failed ❌ (失败，查看 error_message)
```

#### 步骤 4: 查看知识库统计

```bash
# 查看知识库统计信息
curl "http://localhost:8000/atlas/api/knowledge-base/legal-advisor/statistics" \
  -H "Authorization: Bearer $TOKEN"
```

**响应**：
```json
{
  "agent_name": "legal-advisor",
  "collection_name": "agent_legal_advisor",
  "total_files": 3,
  "total_vectors": 3850,
  "total_size": 18927364,  # 字节
  "files": [
    {
      "filename": "legal_document.pdf",
      "chunks_count": 1250,
      "status": "ready"
    },
    {
      "filename": "contract_template.pdf",
      "chunks_count": 2100,
      "status": "ready"
    },
    {
      "filename": "law_guide.md",
      "chunks_count": 500,
      "status": "processing"  # 仍在处理中
    }
  ]
}
```

#### 步骤 5: 创建客服

```bash
# 创建客服并绑定智能体
curl -X POST "http://localhost:8000/atlas/api/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "legal-chat",
    "display_name": "法律咨询客服",
    "agent_name": "legal-advisor",
    "avatar": "⚖️",
    "welcome_message": "您好！我是法律咨询客服，很高兴为您解答法律问题。"
  }'
```

#### 步骤 6: 发送消息进行对话

##### 方式 1: 同步响应（传统方式）

```bash
# 向客服发送问题（等待完整回答）
curl -X POST "http://localhost:8000/atlas/api/chat/legal-chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "签订合同后，对方不履行义务怎么办？"
  }'
```

**响应**：
```json
{
  "role": "assistant",
  "content": "根据《中华人民共和国民法典》的相关规定，如果对方不履行合同义务，您可以采取以下措施...",
  "timestamp": "2025-01-19T08:05:00Z",
  "agent_name": "legal-advisor",
  "knowledge_base_used": true
}
```

##### 方式 2: 流式响应（推荐，类似 ChatGPT）

```bash
# 向客服发送问题（逐字返回，体验更佳）
curl -N -X POST "http://localhost:8000/atlas/api/chat/legal-chat/message/stream" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "签订合同后，对方不履行义务怎么办？"
  }'
```

**流式响应示例**（Server-Sent Events）：
```
data: {"content": "", "done": false, "agent_name": "legal-advisor"}

data: {"content": "根据", "done": false, "agent_name": "legal-advisor"}

data: {"content": "《中华人民共和国", "done": false, "agent_name": "legal-advisor"}

data: {"content": "民法典》", "done": false, "agent_name": "legal-advisor"}

data: {"content": "的相关规定", "done": false, "agent_name": "legal-advisor"}

...

data: {"content": "", "done": true, "agent_name": "legal-advisor"}
```

**流式响应优势**：
- ✅ **逐字显示**: 类似 ChatGPT 的打字效果
- ✅ **首字响应快**: 无需等待完整生成
- ✅ **用户体验好**: 降低等待焦虑感
- ✅ **适合长文本**: 长回答也能快速开始显示
  "timestamp": "2025-01-19T08:05:00Z",
  "agent_name": "legal-advisor",
  "knowledge_base_used": true
}
```

### 高级功能示例

#### 智能体切换（白班/夜班）

```bash
# 切换客服绑定的智能体
curl -X POST "http://localhost:8000/atlas/api/conversations/legal-chat/switch-agent" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_agent_name": "legal-advisor-night",
    "reason": "切换到夜班智能体"
  }'
```

#### 获取智能体列表（带筛选）

```bash
# 获取所有活跃的法律类智能体
curl "http://localhost:8000/atlas/api/agents?status=active&agent_type=legal" \
  -H "Authorization: Bearer $TOKEN"
```

#### 清空对话历史

```bash
# 清空客服的对话历史
curl -X DELETE "http://localhost:8000/atlas/api/chat/legal-chat/history" \
  -H "Authorization: Bearer $TOKEN"
```

#### 重建知识库

```bash
# 重建知识库，只保留指定文档
curl -X POST "http://localhost:8000/atlas/api/knowledge-base/legal-advisor/rebuild" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_ids": ["doc_20250119_001", "doc_20250119_003"]
  }'
```

## 🧪 测试脚本

项目提供了多个测试脚本：

```bash
# 测试认证功能
./test_auth.sh

# 测试受保护的 API
./test_protected_apis.sh

# 完整 API 测试
./test_api.sh
```

### 自定义测试

创建测试脚本 `test.sh`：

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/atlas/api"

# 1. 登录
echo "1. 登录..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# 2. 创建智能体
echo "2. 创建智能体..."
curl -X POST "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-agent",
    "display_name": "测试智能体",
    "agent_type": "general"
  }'

# 3. 获取智能体列表
echo "3. 获取智能体列表..."
curl "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN"
```

## 📁 项目结构

```
atlas/
├── app.py                      # FastAPI 主应用入口
├── create_admin.py             # 创建默认管理员脚本
├── pyproject.toml              # 项目依赖配置
├── Dockerfile                  # Docker 镜像构建
├── docker-compose.yaml         # Docker Compose 配置
│
├── api/                        # 🎯 API 路由层（表现层）
│   ├── __init__.py
│   ├── agents.py               # 智能体管理接口
│   ├── conversations.py        # 客服管理接口
│   ├── knowledge_base.py       # 知识库管理接口（异步上传）
│   ├── chat.py                 # 对话接口（支持流式）
│   ├── auth.py                 # 认证授权接口
│   ├── users.py                # 用户管理接口
│   │
│   └── schemas/                # Pydantic DTO 层
│       ├── __init__.py
│       ├── agent.py            # 智能体相关 Schema
│       ├── conversation.py     # 客服相关 Schema
│       ├── knowledge_base.py   # 知识库相关 Schema
│       ├── chat.py             # 聊天相关 Schema
│       ├── auth.py             # 认证相关 Schema
│       └── common.py           # 通用 Schema
│
├── application/                # 🎯 应用服务层（业务流程编排）
│   ├── __init__.py
│   ├── agent_service.py        # Agent Facade 协调器（250 行）
│   ├── knowledge_base_service.py  # 知识库业务逻辑（240 行）
│   ├── conversation_service.py # 客服服务
│   ├── auth_service.py         # 认证服务（JWT Token）
│   ├── user_service.py         # 用户服务
│   ├── rag_agent.py            # RAG 核心逻辑（LangChain Agent）
│   └── milvus_service.py       # Milvus 向量库操作
│
├── domain/                     # 🎯 领域层（DDD 核心）
│   ├── __init__.py
│   ├── entities.py             # ORM 实体（Agent/Document/Conversation）
│   ├── auth.py                 # 认证实体（User ORM）
│   │
│   ├── managers/               # 领域管理器（生命周期管理）
│   │   ├── __init__.py
│   │   └── rag_agent_manager.py  # RAG Agent 实例管理器（内存缓存）
│   │
│   └── processors/             # 领域处理器（业务工具）
│       ├── __init__.py
│       ├── document_processor.py    # 文档处理（PDF/TXT/MD 解析）
│       └── vector_store_manager.py  # 向量存储管理（Milvus 操作封装）
│
├── repository/                 # 🎯 数据访问层（Repository 模式）
│   ├── __init__.py
│   └── agent_repository.py     # Agent + Document Repository（CRUD）
│
├── config/                     # 🎯 配置层
│   ├── __init__.py
│   ├── settings.py             # 全局配置（Pydantic Settings）
│   ├── database.py             # PostgreSQL 连接池配置
│   ├── auth.py                 # JWT 认证配置
│   └── milvus.py               # Milvus 向量库配置
│
├── metadata_store/             # 元数据存储（本地 JSON）
│   └── [agent_name]/
│       └── file_metadata.json
│
├── uploads/                    # 文档上传临时目录
│   └── [agent_name]/
│
├── .github/                    # GitHub Actions CI/CD
│   └── workflows/
│       └── main.yml
│
└── 📚 文档
    ├── README.md               # 本文档
    ├── FRONTEND_GUIDE.md       # 前端开发指南
    ├── AUTHENTICATION.md       # JWT 认证详解
    ├── MIGRATION_SUMMARY.md    # 数据库迁移指南
    └── USAGE.md                # 使用指南

🎯 = 四层架构核心层
```

**架构分层说明**：
1. **API 层** (api/) - HTTP 请求处理、参数验证、响应格式化
2. **应用层** (application/) - 业务流程编排、多个 service 协调、Facade 模式
3. **领域层** (domain/) - DDD 核心，包含实体、管理器、处理器
4. **基础设施层** (repository/ + config/) - 数据访问、外部服务配置

## 🔧 技术栈

### 后端框架
- **FastAPI** `0.104+`: 高性能 Python Web 框架
- **Uvicorn**: ASGI 服务器
- **Pydantic** `2.0+`: 数据验证和序列化

### 数据库
- **PostgreSQL** `17.6`: 关系型数据库（用户、配置）
- **Milvus** `2.3+`: 向量数据库（知识库向量存储）
- **SQLAlchemy** `2.0+`: Python ORM

### AI / RAG
- **LangChain** `1.0+`: RAG 框架
- **OpenAI API**: LLM 和 Embedding（支持兼容接口）
- **文档解析**: PyPDF2、docx、markdown

### 认证安全
- **PyJWT**: JWT Token 生成和验证
- **bcrypt**: 密码哈希加密
- **passlib**: 密码处理工具

### 开发工具
- **uv**: 现代化 Python 包管理器
- **Docker**: 容器化部署
- **GitHub Actions**: CI/CD 自动部署

## 📖 文档资源

### 开发文档
- 📘 [前端开发指南](FRONTEND_GUIDE.md) - **推荐**: 完整的 API 接口文档和前端对接指南
- 🔐 [认证系统说明](AUTHENTICATION.md) - JWT 认证实现细节
- 📊 [数据库迁移指南](MIGRATION_SUMMARY.md) - SQLite 到 PostgreSQL 迁移
- 📝 [使用指南](USAGE.md) - 业务功能使用说明

### 在线文档
- 🌐 **Swagger UI**: https://atlas.matrix-net.tech/docs
- 📚 **ReDoc**: https://atlas.matrix-net.tech/redoc
- ❤️ **健康检查**: https://atlas.matrix-net.tech/health

### 部署文档
- 🐳 [Docker 部署指南](Dockerfile)
- ⚙️ [GitHub Actions 配置](.github/workflows/main.yml)
- 🔑 [Secrets 配置指南](.github/SECRETS_SETUP.md)

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 开发流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 Python 代码规范
- 使用类型注解（Type Hints）
- 添加必要的注释和文档字符串
- 更新相关文档

## 📜 更新日志

### v0.5.0 (2025-12-08) - 流式输出与性能优化 🚀

**🌊 真流式响应实现**
- ✅ **Token 级流式输出**: 从 `stream_mode="values"` 改为 `astream_events v2`
- ✅ **双 LLM 架构**: 
  - `llm_streaming`: Agent 主流程，逐 token 流式输出
  - `llm_non_streaming`: 工具调用（查询改写、答案验证），同步返回完整结果
- ✅ **事件过滤优化**: 只输出 `on_chat_model_stream` 事件，过滤工具调用日志
- ✅ **前端体验提升**: 真正的打字机效果，无需等待工具调用完成

**⚡ 列表查询性能优化**
- ✅ **50 倍性能提升**: `/api/agents?status=active` 从 5-6 秒优化到 <0.1 秒
- ✅ **移除 Milvus 查询**: `_to_response_lite` 不再查询 Milvus 统计
- ✅ **预加载优化**: Repository 使用 `joinedload(Agent.documents)` 避免 N+1 查询
- ✅ **估算策略**: 列表使用估算值（文件数 × 100），详情查询精确值

**🔧 RAG 工作流优化**
- ✅ **三阶段流程**: 查询改写 → 文档检索 → 答案生成（+ 可选验证）
- ✅ **多查询检索**: `rewrite_query` 生成 3 条多角度查询
- ✅ **合并去重**: `retrieve_context` 合并多条查询结果，按相似度排序
- ✅ **顺序执行**: 系统提示词强调禁止并行调用工具

**📝 代码质量提升**
- ✅ **多行字符串缩进优化**: 提示词和消息模板统一缩进格式
- ✅ **注释完善**: 添加双 LLM 架构说明和性能优化注释
- ✅ **日志优化**: 工具函数添加开始/完成日志（🔧/✅ 标记）

**🐛 Bug 修复**
- ✅ 修复流式输出返回原始文档而非 AI 答案的问题
- ✅ 修复 `agent_service.py` 缩进错误（KnowledgeBaseInfo 重复行）
- ✅ 修复列表查询性能问题（移除不必要的 `db.refresh`）

### v0.4.0 (2025-01-22) - DDD 标准化改造 🏗️

**🔄 目录结构重构**
- ✅ **services/ → application/** - 应用服务层标准命名（符合 DDD 术语）
- ✅ **models/ → domain/** - ORM 实体归属领域层（符合 DDD 实体定义）
- ✅ **schemas/ → api/schemas/** - Schema 归属表现层，按业务模块拆分（7个文件）
- ✅ **domain/ 完善** - 领域层包含实体（entities.py/auth.py）、管理器（managers/）、处理器（processors/）
- ✅ **repository/ 标准化** - Repository 模式（AgentRepository + DocumentRepository）

**📐 架构模式强化**
- ✅ **四层架构完善**: API → Application → Domain → Repository
- ✅ **DDD 分层对应**:
  - 表现层 (Presentation) → `api/` + `api/schemas/`
  - 应用服务层 (Application) → `application/`
  - 领域层 (Domain) → `domain/`（含实体、管理器、处理器）
  - 基础设施层 (Infrastructure) → `repository/` + `config/`
- ✅ **设计原则**: 标准命名、清晰分层、实用主义、Python 社区最佳实践

**🛠️ 重构工具**
- ✅ 自动化重构脚本 3 个
  - refactor_to_standard_ddd.py（services → application）
  - refactor_models_to_domain.py（models → domain）
  - refactor_schemas_to_api.py（schemas → api/schemas，按模块拆分）
- ✅ 批量更新 40+ 文件的 import 语句
- ✅ Schema 按业务模块拆分（7 个文件）
- ✅ 语法验证和功能测试通过

**📚 文档更新**
- ✅ README 架构设计章节全面更新
- ✅ 项目结构树反映新目录（application/ 和 schemas/）
- ✅ 核心组件说明更新（DTO 层独立说明）
- ✅ 版本日志更新（记录重构历程）

### v0.3.0 (2025-12-07) - 架构重构版

**🏗️ 架构重大升级**
- ✅ **四层架构重构**: Repository + Manager + Service + Facade 模式
- ✅ **代码精简 46%**: AgentService 从 460 行优化到 250 行
- ✅ **依赖注入设计**: 提高可测试性和可维护性
- ✅ **职责清晰分离**: 6 个新服务模块，单一职责原则

**🚀 性能优化**
- ✅ **异步文档上传**: FastAPI BackgroundTasks，解决大文件阻塞问题
- ✅ **独立数据库会话**: 后台任务使用独立会话，避免线程冲突
- ✅ **状态追踪机制**: Document 表实现 processing → ready/failed 状态机
- ✅ **RAG 实例缓存**: RAGAgentManager 单例 + 内存缓存

**💾 数据持久化**
- ✅ **Document 表**: 文件元数据持久化（文件名、大小、状态、切片数）
- ✅ **DocumentStatus 枚举**: 规范化状态管理
- ✅ **级联删除**: Agent 删除时自动清理关联文档

**🐛 Bug 修复**
- ✅ 修复 KnowledgeBaseInfo 字段名称不匹配问题
- ✅ 修复 6.4MB PDF 上传导致应用卡死
- ✅ 修复异步上传后台任务数据库会话冲突
- ✅ 优化错误处理和日志输出

**📚 文档更新**
- ✅ 完整更新架构设计图（四层架构）
- ✅ 新增架构模式详解（Repository/Manager/Service/Facade）
- ✅ 更新 API 使用示例（异步上传流程）
- ✅ 更新项目结构说明（新增模块）

### v0.2.0 (2025-01-19)
- ✅ 完整的 JWT 认证系统
- ✅ SQLite 迁移到 PostgreSQL
- ✅ Docker 多阶段构建优化
- ✅ GitHub Actions CI/CD 部署
- ✅ 完整的前端开发文档
- ✅ 知识库重建功能

### v0.1.0 (2024-12-01)
- ✅ 基础 RAG 智能客服功能
- ✅ 智能体和客服解耦架构
- ✅ Milvus 向量存储
- ✅ 知识库上传管理

## 📄 许可证

本项目采用 [Apache License 2.0](LICENSE) 开源许可证。

## 🙏 致谢

感谢以下开源项目：
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangChain](https://www.langchain.com/)
- [Milvus](https://milvus.io/)
- [PostgreSQL](https://www.postgresql.org/)

## 📧 联系方式

- **项目主页**: https://github.com/yuanyuexiang/atlas
- **在线演示**: https://atlas.matrix-net.tech
- **问题反馈**: [GitHub Issues](https://github.com/yuanyuexiang/atlas/issues)

---

⭐ 如果这个项目对你有帮助，请给一个 Star！
