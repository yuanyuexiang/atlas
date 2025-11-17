"""
Pydantic 数据模型
用于 API 请求和响应的数据验证
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== 智能体 Schema ====================

class AgentCreate(BaseModel):
    """创建智能体请求"""
    name: str = Field(..., min_length=2, max_length=50, pattern="^[a-zA-Z0-9_-]+$",
                      description="智能体唯一标识（字母、数字、下划线、短横线）")
    display_name: str = Field(..., min_length=2, max_length=100, description="显示名称")
    agent_type: str = Field(default="general", description="类型：general/legal/medical/financial/custom")
    system_prompt: Optional[str] = Field(None, description="系统提示词（为空则使用默认）")
    description: Optional[str] = Field(None, description="智能体描述")


class AgentUpdate(BaseModel):
    """更新智能体请求"""
    display_name: Optional[str] = None
    system_prompt: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class KnowledgeBaseInfo(BaseModel):
    """知识库信息"""
    collection_name: str
    total_files: int
    total_vectors: int
    total_size_mb: float = 0.0
    files: List[dict] = []


class AgentResponse(BaseModel):
    """智能体响应"""
    id: str
    name: str
    display_name: str
    agent_type: str
    status: str
    system_prompt: str
    description: Optional[str]
    knowledge_base: KnowledgeBaseInfo
    created_at: datetime
    updated_at: datetime
    conversations_using: List[str] = []  # 使用该智能体的客服列表

    class Config:
        from_attributes = True


# ==================== 客服 Schema ====================

class ConversationCreate(BaseModel):
    """创建客服请求"""
    name: str = Field(..., pattern="^[a-zA-Z0-9_-]+$", description="客服唯一标识")
    display_name: str = Field(..., description="显示名称")
    agent_name: str = Field(..., description="关联的智能体名称")
    avatar: str = Field(default="🤖", description="头像")
    welcome_message: Optional[str] = Field(None, description="欢迎语")
    description: Optional[str] = None


class ConversationUpdate(BaseModel):
    """更新客服请求"""
    display_name: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[str] = None
    welcome_message: Optional[str] = None
    description: Optional[str] = None


class AgentInfo(BaseModel):
    """智能体简要信息"""
    id: str
    name: str
    display_name: str
    agent_type: str


class ConversationResponse(BaseModel):
    """客服响应"""
    id: str
    name: str
    display_name: str
    avatar: str
    status: str
    agent: AgentInfo
    welcome_message: Optional[str]
    message_count: int
    last_active_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 智能体切换 ====================

class AgentSwitchRequest(BaseModel):
    """切换智能体请求"""
    new_agent_name: str = Field(..., description="新智能体名称")
    reason: Optional[str] = Field(default="手动切换", description="切换原因")


class AgentSwitchResponse(BaseModel):
    """切换智能体响应"""
    conversation_name: str
    old_agent: str
    new_agent: str
    switched_at: datetime


# ==================== 消息相关 ====================

class MessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., min_length=1, description="消息内容")
    session_id: Optional[str] = Field(None, description="会话ID")


class MessageResponse(BaseModel):
    """消息响应"""
    role: str = Field(..., description="角色：user/assistant")
    content: str
    timestamp: str
    agent_name: Optional[str] = None
    knowledge_base_used: bool = False


# ==================== 知识库相关 ====================

class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    file_id: str
    filename: str
    chunks_count: int
    upload_time: str


class KnowledgeBaseStats(BaseModel):
    """知识库统计"""
    agent_name: str
    collection_name: str
    total_files: int
    total_vectors: int
    files: List[dict]


# ==================== 通用响应 ====================

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    detail: Optional[str] = None
