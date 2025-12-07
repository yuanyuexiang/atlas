"""
聊天相关的 Pydantic Schema
"""
from pydantic import BaseModel, Field
from typing import Optional


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
