"""
对话 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from models.schemas import MessageRequest, MessageResponse
from models.auth import User
from services.conversation_service import ConversationService
from services.multi_rag_manager import get_rag_manager
from services.auth_service import get_current_active_user
from core.database import get_db
import json

router = APIRouter(prefix="/chat", tags=["对话"])
conversation_service = ConversationService()
rag_manager = get_rag_manager()


@router.post("/{conversation_id}/message", response_model=MessageResponse, summary="发送消息")
async def send_message(
    conversation_id: str,
    message: MessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    向客服发送消息并获取AI回复（同步方式，返回完整响应）
    
    参数：conversation_id (UUID)
    
    流程：
    1. 验证客服状态
    2. 获取客服关联的智能体
    3. 从智能体的知识库检索
    4. LLM 生成回复
    5. 更新活跃时间和消息计数
    """
    try:
        # 获取客服信息
        conversation = conversation_service.get_conversation(db, conversation_id)
        
        # 检查状态
        if conversation.status != "online":
            raise HTTPException(400, f"客服状态异常: {conversation.status}")
        
        # 获取智能体名称
        agent_name = conversation.agent.name
        
        # 获取 RAG Agent 并回答
        rag_agent = rag_manager.get_agent(agent_name)
        answer = rag_agent.ask(message.content)
        
        # 更新活跃时间
        conversation_service.update_activity(db, conversation_id)
        
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


@router.post("/{conversation_id}/message/stream", summary="发送消息（流式响应）")
async def send_message_stream(
    conversation_id: str,
    message: MessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    向客服发送消息并获取AI回复（流式响应，Server-Sent Events）
    
    参数：conversation_id (UUID)
    
    流式响应优势：
    - 逐字显示，用户体验更好（类似 ChatGPT）
    - 降低首字响应时间
    - 适合长文本生成
    
    响应格式：
    - Content-Type: text/event-stream
    - 每个数据块格式：data: {"content": "文本片段", "done": false}\n\n
    - 结束标记：data: {"content": "", "done": true}\n\n
    """
    try:
        # 获取客服信息
        conversation = conversation_service.get_conversation(db, conversation_id)
        
        # 检查状态
        if conversation.status != "online":
            raise HTTPException(400, f"客服状态异常: {conversation.status}")
        
        # 获取智能体名称
        agent_name = conversation.agent.name
        
        # 定义流式生成器
        async def generate():
            try:
                # 获取 RAG Agent
                rag_agent = rag_manager.get_agent(agent_name)
                
                # 发送开始标记
                yield f"data: {json.dumps({'content': '', 'done': False, 'agent_name': agent_name}, ensure_ascii=False)}\n\n"
                
                # 流式生成回答
                async for chunk in rag_agent.ask_stream(message.content):
                    if chunk:
                        data = {
                            "content": chunk,
                            "done": False,
                            "agent_name": agent_name
                        }
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                
                # 发送结束标记
                yield f"data: {json.dumps({'content': '', 'done': True, 'agent_name': agent_name}, ensure_ascii=False)}\n\n"
                
                # 更新活跃时间
                conversation_service.update_activity(db, conversation_id)
                
            except Exception as e:
                # 发送错误信息
                error_data = {
                    "content": f"抱歉，处理您的问题时出现了错误。",
                    "done": True,
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
            }
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"处理消息失败: {str(e)}")


@router.delete("/{conversation_id}/history", summary="清空对话历史")
async def clear_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    清空客服的对话历史
    
    参数：conversation_id (UUID)
    注意：仅清空当前会话的历史，不影响知识库
    """
    try:
        # 验证客服存在
        conversation = conversation_service.get_conversation(db, conversation_id)
        
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


@router.get("/{conversation_id}/info", summary="获取对话信息")
async def get_chat_info(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取对话相关信息
    
    参数：conversation_id (UUID)
    包括：客服信息、关联的智能体、欢迎语等
    """
    try:
        conversation = conversation_service.get_conversation(db, conversation_id)
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


@router.get("/{conversation_id}/messages", summary="获取聊天历史")
async def get_chat_history(
    conversation_id: str,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取对话历史记录（当前会话的消息列表）
    
    参数：
    - conversation_id (UUID): 客服 ID
    - page: 页码（从 1 开始）
    - page_size: 每页数量（默认 50，最大 100）
    
    注意：
    - 聊天历史存储在内存中，重启服务会清空
    - 返回当前会话的所有消息（用户消息 + AI 回复）
    - 按时间倒序返回（最新的在前）
    """
    try:
        # 验证客服存在
        conversation = conversation_service.get_conversation(db, conversation_id)
        
        # 获取智能体的聊天历史
        agent_name = conversation.agent.name
        rag_agent = rag_manager.get_agent(agent_name)
        
        # 获取历史记录
        chat_history = rag_agent.chat_history
        
        # 转换为消息格式
        messages = []
        for msg in chat_history:
            role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
            messages.append({
                "role": role,
                "content": msg.content,
                "timestamp": None  # 内存中没有时间戳
            })
        
        # 倒序（最新的在前）
        messages.reverse()
        
        # 分页
        total = len(messages)
        start = (page - 1) * page_size
        end = start + page_size
        page_messages = messages[start:end]
        
        return {
            "success": True,
            "data": {
                "messages": page_messages,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
        }
        
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")
