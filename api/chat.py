"""
对话 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from models.schemas import MessageRequest, MessageResponse
from models.auth import User
from services.conversation_service import ConversationService
from services.multi_rag_manager import get_rag_manager
from services.auth_service import get_current_active_user
from core.database import get_db

router = APIRouter(prefix="/chat", tags=["对话"])
conversation_service = ConversationService()
rag_manager = get_rag_manager()


@router.post("/{conversation_name}/message", response_model=MessageResponse, summary="发送消息")
async def send_message(
    conversation_name: str,
    message: MessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    向客服发送消息并获取AI回复
    
    流程：
    1. 验证客服状态
    2. 获取客服关联的智能体
    3. 从智能体的知识库检索
    4. LLM 生成回复
    5. 更新活跃时间和消息计数
    """
    try:
        # 获取客服信息
        conversation = conversation_service.get_conversation(db, conversation_name)
        
        # 检查状态
        if conversation.status != "online":
            raise HTTPException(400, f"客服状态异常: {conversation.status}")
        
        # 获取智能体名称
        agent_name = conversation.agent.name
        
        # 获取 RAG Agent 并回答
        rag_agent = rag_manager.get_agent(agent_name)
        answer = rag_agent.ask(message.content)
        
        # 更新活跃时间
        conversation_service.update_activity(db, conversation_name)
        
        return MessageResponse(
            role="assistant",
            content=answer,
            timestamp=datetime.utcnow().isoformat(),
            agent_name=agent_name,
            knowledge_base_used=True
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"处理消息失败: {str(e)}")


@router.delete("/{conversation_name}/history", summary="清空对话历史")
async def clear_history(
    conversation_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    清空客服的对话历史
    
    注意：仅清空当前会话的历史，不影响知识库
    """
    try:
        # 验证客服存在
        conversation = conversation_service.get_conversation(db, conversation_name)
        
        # 获取智能体并清空历史
        agent_name = conversation.agent.name
        rag_agent = rag_manager.get_agent(agent_name)
        rag_agent.clear_history()
        
        return {
            "success": True,
            "message": "对话历史已清空"
        }
        
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"清空失败: {str(e)}")


@router.get("/{conversation_name}/info", summary="获取对话信息")
async def get_chat_info(
    conversation_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取对话相关信息
    
    包括：客服信息、关联的智能体、欢迎语等
    """
    try:
        conversation = conversation_service.get_conversation(db, conversation_name)
        return {
            "success": True,
            "data": {
                "conversation_name": conversation.name,
                "display_name": conversation.display_name,
                "avatar": conversation.avatar,
                "status": conversation.status,
                "welcome_message": conversation.welcome_message,
                "agent": {
                    "name": conversation.agent.name,
                    "display_name": conversation.agent.display_name,
                    "type": conversation.agent.agent_type
                },
                "message_count": conversation.message_count,
                "last_active": conversation.last_active_at.isoformat() if conversation.last_active_at else None
            }
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
