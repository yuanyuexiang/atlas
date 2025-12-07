"""
API Schema 层
包含所有 API 请求/响应的 Pydantic 模型
"""
from api.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse, KnowledgeBaseInfo
)
from api.schemas.conversation import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    AgentInfo, AgentSwitchRequest, AgentSwitchResponse
)
from api.schemas.knowledge_base import (
    DocumentUploadResponse, KnowledgeBaseStats
)
from api.schemas.chat import (
    MessageRequest, MessageResponse
)
from api.schemas.auth import (
    UserCreate, UserUpdate, UserResponse, UserLogin,
    Token, TokenData
)
from api.schemas.common import (
    SuccessResponse, ErrorResponse
)

__all__ = [
    # Agent
    "AgentCreate", "AgentUpdate", "AgentResponse", "KnowledgeBaseInfo",
    # Conversation
    "ConversationCreate", "ConversationUpdate", "ConversationResponse",
    "AgentInfo", "AgentSwitchRequest", "AgentSwitchResponse",
    # Knowledge Base
    "DocumentUploadResponse", "KnowledgeBaseStats",
    # Chat
    "MessageRequest", "MessageResponse",
    # Auth
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin",
    "Token", "TokenData",
    # Common
    "SuccessResponse", "ErrorResponse",
]
