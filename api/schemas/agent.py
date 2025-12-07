"""
智能体相关的 Pydantic Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


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
    conversations_using: List[str] = []

    class Config:
        from_attributes = True
