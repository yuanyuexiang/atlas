"""
ORM 数据实体
定义智能体、客服、切换日志的数据库模型
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AgentStatus(str, Enum):
    """智能体状态"""
    ACTIVE = "active"        # 活跃
    INACTIVE = "inactive"    # 停用
    TRAINING = "training"    # 训练中
    ERROR = "error"          # 错误


class AgentType(str, Enum):
    """智能体类型"""
    GENERAL = "general"      # 通用
    LEGAL = "legal"          # 法律
    MEDICAL = "medical"      # 医疗
    FINANCIAL = "financial"  # 金融
    CUSTOM = "custom"        # 自定义


class Agent(Base):
    """智能体实体（AI 能力单元）"""
    __tablename__ = "agents"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    agent_type = Column(SQLEnum(AgentType), default=AgentType.GENERAL)
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.ACTIVE)
    
    # AI 配置
    system_prompt = Column(Text, nullable=False)
    model_name = Column(String(100))
    temperature = Column(Integer, default=0)
    
    # 知识库配置
    milvus_collection = Column(String(200))  # Milvus Collection 名称
    embedding_model = Column(String(100))
    
    # 元数据
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    conversations = relationship("Conversation", back_populates="agent")


class ConversationStatus(str, Enum):
    """客服状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


class Conversation(Base):
    """客服实体（会话界面）"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    avatar = Column(String(200), default="🤖")
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ONLINE)
    
    # 关联的智能体
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    agent = relationship("Agent", back_populates="conversations")
    
    # 会话配置
    welcome_message = Column(Text)
    auto_reply = Column(Boolean, default=True)
    
    # 统计信息
    message_count = Column(Integer, default=0)
    last_active_at = Column(DateTime)
    
    # 元数据
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentSwitchLog(Base):
    """智能体切换日志"""
    __tablename__ = "agent_switch_logs"
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"))
    old_agent_id = Column(String(36))
    new_agent_id = Column(String(36))
    switch_reason = Column(Text)
    switched_at = Column(DateTime, default=datetime.utcnow)
