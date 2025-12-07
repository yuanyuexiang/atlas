"""
客服相关的 Pydantic Schema
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


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
    agent_name: Optional[str] = None
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
