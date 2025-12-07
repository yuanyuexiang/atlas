"""
客服管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from api.schemas import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    AgentSwitchRequest, AgentSwitchResponse
)
from domain.auth import User
from application.conversation_service import ConversationService
from application.auth_service import get_current_active_user
from config.database import get_db

router = APIRouter(prefix="/conversations", tags=["客服管理"])
conversation_service = ConversationService()


@router.post("", response_model=ConversationResponse, summary="创建客服")
async def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    创建新的客服（会话界面）
    
    - **name**: 客服唯一标识
    - **display_name**: 显示名称
    - **agent_name**: 关联的智能体名称
    - **avatar**: 头像（emoji 或 URL）
    - **welcome_message**: 欢迎语（可选）
    """
    try:
        return conversation_service.create_conversation(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("", summary="获取客服列表")
async def list_conversations(
    status: Optional[str] = Query(None, description="筛选状态：online/offline/busy"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取客服列表（支持筛选和分页）"""
    try:
        return conversation_service.list_conversations(db, status, skip, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{conversation_id}", response_model=ConversationResponse, summary="获取客服详情")
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取指定客服的详细信息，参数：conversation_id (UUID)"""
    try:
        return conversation_service.get_conversation(db, conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.put("/{conversation_id}", response_model=ConversationResponse, summary="更新客服")
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新客服配置，参数：conversation_id (UUID)"""
    try:
        return conversation_service.update_conversation(db, conversation_id, update_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{conversation_id}", summary="删除客服")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除客服，参数：conversation_id (UUID)"""
    try:
        return conversation_service.delete_conversation(db, conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/{conversation_id}/switch-agent", response_model=AgentSwitchResponse, summary="切换智能体")
async def switch_agent(
    conversation_id: str,
    switch_data: AgentSwitchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    切换客服使用的智能体
    
    参数：conversation_id (UUID)
    可用于：
    - 白班/夜班智能体切换
    - 专家智能体切换
    - A/B 测试
    """
    try:
        return conversation_service.switch_agent(db, conversation_id, switch_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换失败: {str(e)}")


@router.get("/{conversation_id}/agent-history", summary="查看智能体切换历史")
async def get_agent_switch_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查看客服的智能体切换历史记录，参数：conversation_id (UUID)"""
    try:
        return conversation_service.get_switch_history(db, conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/{conversation_id}/online", summary="客服上线")
async def set_online(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """设置客服状态为在线，参数：conversation_id (UUID)"""
    try:
        update_data = ConversationUpdate(status="online")
        return conversation_service.update_conversation(db, conversation_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/offline", summary="客服下线")
async def set_offline(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """设置客服状态为离线，参数：conversation_id (UUID)"""
    try:
        update_data = ConversationUpdate(status="offline")
        return conversation_service.update_conversation(db, conversation_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
