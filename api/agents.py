"""
智能体管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from schemas.schemas import AgentCreate, AgentUpdate, AgentResponse
from domain.auth import User
from application.agent_service import get_agent_service
from application.auth_service import get_current_active_user
from core.database import get_db

router = APIRouter(prefix="/agents", tags=["智能体管理"])
agent_service = get_agent_service()


@router.post("", response_model=AgentResponse, summary="创建智能体")
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    创建新的智能体（AI 能力单元）
    
    - **name**: 智能体唯一标识（字母、数字、下划线、短横线）
    - **display_name**: 显示名称（中文友好）
    - **agent_type**: 类型（general/legal/medical/financial/custom）
    - **system_prompt**: 系统提示词（可选，为空则使用默认）
    """
    try:
        result = agent_service.create_agent(db, agent_data)
        print(f"🔍 [DEBUG] create_agent 返回类型: {type(result)}")
        print(f"🔍 [DEBUG] create_agent 返回值: {result}")
        return result
    except ValueError as e:
        print(f"❌ [ERROR] ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ [ERROR] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("", summary="获取智能体列表")
async def list_agents(
    status: Optional[str] = Query(None, description="筛选状态：active/inactive/training/error"),
    agent_type: Optional[str] = Query(None, description="筛选类型：general/legal/medical/financial/custom"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取智能体列表（支持筛选和分页）
    
    返回每个智能体的详细信息，包括知识库统计和使用该智能体的客服列表
    """
    try:
        return agent_service.list_agents(db, status, agent_type, skip, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{agent_id}", response_model=AgentResponse, summary="获取智能体详情")
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定智能体的详细信息
    
    包括：配置、知识库统计、使用该智能体的客服列表
    参数：agent_id (UUID)
    """
    try:
        return agent_service.get_agent(db, agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.put("/{agent_id}", response_model=AgentResponse, summary="更新智能体")
async def update_agent(
    agent_id: str,
    update_data: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    更新智能体配置
    
    可更新：显示名称、系统提示词、状态、描述
    参数：agent_id (UUID)
    """
    try:
        return agent_service.update_agent(db, agent_id, update_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{agent_id}", summary="删除智能体")
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除智能体（同时删除知识库）
    
    注意：如果有客服正在使用该智能体，无法删除
    参数：agent_id (UUID)
    """
    try:
        return agent_service.delete_agent(db, agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/{agent_id}/activate", summary="激活智能体")
async def activate_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """激活智能体，参数：agent_id (UUID)"""
    try:
        update_data = AgentUpdate(status="active")
        return agent_service.update_agent(db, agent_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/deactivate", summary="停用智能体")
async def deactivate_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """停用智能体，参数：agent_id (UUID)"""
    try:
        update_data = AgentUpdate(status="inactive")
        return agent_service.update_agent(db, agent_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
