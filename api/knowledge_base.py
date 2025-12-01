"""
知识库管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from models.schemas import DocumentUploadResponse, KnowledgeBaseStats
from models.auth import User
from models.entities import Agent
from services.multi_rag_manager import get_rag_manager
from services.agent_service import AgentService
from services.auth_service import get_current_active_user
from core.database import get_db
from core.config import settings
import os
import shutil
import uuid

router = APIRouter(prefix="/knowledge-base", tags=["知识库管理"])
rag_manager = get_rag_manager()
agent_service = AgentService()


@router.post("/{agent_id}/documents", response_model=DocumentUploadResponse, summary="上传文档")
async def upload_document(
    agent_id: str,
    file: UploadFile = File(..., description="支持 PDF、TXT、MD 格式"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    为智能体上传知识库文档并自动向量化
    
    参数：agent_id (UUID)
    
    流程：
    1. 保存临时文件
    2. 文档解析和文本切分
    3. 向量化并存入 Milvus
    4. 保存元数据
    """
    try:
        # 验证智能体存在并获取 name
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            raise HTTPException(404, "智能体不存在")
        
        # 验证文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"不支持的文件类型: {file_ext}")
        
        # 保存临时文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        # 使用短UUID避免文件名冲突，保持原始文件名
        file_id = str(uuid.uuid4())[:8]
        temp_path = os.path.join(upload_dir, f"{file_id}_{file.filename}")
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 验证文件大小
        file_size = os.path.getsize(temp_path)
        if file_size > settings.MAX_UPLOAD_SIZE:
            os.remove(temp_path)
            raise HTTPException(400, f"文件过大: {file_size / 1024 / 1024:.1f}MB > 10MB")
        
        # 上传到 Milvus（使用 agent.name）
        result = rag_manager.upload_file(agent.name, temp_path)
        
        if not result["success"]:
            raise HTTPException(500, result["message"])
        
        data = result["data"]
        return DocumentUploadResponse(
            file_id=data["file_id"],
            filename=data["filename"],
            chunks_count=data["chunks_count"],
            upload_time=data.get("upload_time", "")
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"上传失败: {str(e)}")


@router.get("/{agent_id}/documents", summary="获取文档列表")
async def list_documents(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取智能体的所有文档列表，参数：agent_id (UUID)"""
    try:
        # 轻量级验证：只检查智能体是否存在（不构建完整响应）
        from models.entities import Agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(404, f"智能体不存在: {agent_id}")
        
        # 直接读取文件列表（已优化，不创建 Agent 实例）
        files = rag_manager.list_files(agent.name)
        return {"success": True, "data": files}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


@router.delete("/{agent_id}/documents/{file_id}", summary="删除文档")
async def delete_document(
    agent_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除指定文档（级联删除向量数据和元数据）
    
    参数：
    - agent_id: 智能体 ID (UUID)
    - file_id: 文件 ID (UUID)
    
    注意：此操作会同时删除：
    1. Milvus 向量数据库中的向量记录
    2. 元数据文件中的文件记录
    """
    try:
        # 轻量级验证智能体存在（不构建完整响应）
        from models.entities import Agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            raise HTTPException(404, "智能体不存在")
        
        # 删除文件（包括向量数据和元数据）- 确保级联删除
        result = rag_manager.delete_file(agent.name, file_id)
        
        if not result.get("success"):
            raise HTTPException(500, result.get("message", "删除失败"))
        
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除失败: {str(e)}")


@router.get("/{agent_id}/stats", summary="获取知识库统计")
async def get_knowledge_base_stats(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取知识库统计信息
    
    参数：agent_id (UUID)
    包括：文档数、向量数、存储大小、文件列表
    """
    try:
        # 验证智能体存在并获取 name
        from models.entities import Agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(404, "智能体不存在")
        
        stats = rag_manager.get_statistics(agent.name)
        return {"success": True, "data": stats}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


@router.delete("/{agent_id}/clear", summary="清空知识库")
async def clear_knowledge_base(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    清空智能体的知识库
    
    参数：agent_id (UUID)
    警告：此操作不可逆，将删除所有文档和向量数据
    """
    try:
        # 验证智能体存在并获取 name
        from models.entities import Agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(404, "智能体不存在")
        
        result = rag_manager.clear_knowledge_base(agent.name)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"清空失败: {str(e)}")


@router.post("/{agent_id}/rebuild", summary="重建知识库索引")
async def rebuild_knowledge_base(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    重建知识库索引
    
    参数：agent_id (UUID)
    用于优化搜索性能或修复索引问题
    """
    try:
        # 验证智能体存在
        from models.entities import Agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(404, "智能体不存在")
        
        return {
            "success": True,
            "message": "索引重建功能待实现"
        }
    except Exception as e:
        raise HTTPException(500, f"重建失败: {str(e)}")


@router.post("/{agent_id}/fix-inconsistency", summary="修复数据不一致")
async def fix_data_inconsistency(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    修复知识库数据不一致问题
    
    参数：agent_id (UUID)
    
    场景：
    - 元数据显示 0 个文件，但向量库中还有数据
    - 向量数据和元数据记录不匹配
    
    处理：清空所有向量数据和元数据，恢复一致状态
    """
    try:
        # 验证智能体存在
        from models.entities import Agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(404, "智能体不存在")
        
        # 获取当前统计信息
        stats = rag_manager.get_statistics(agent.name)
        
        # 检查是否存在不一致
        if stats.get("is_consistent", True):
            return {
                "success": True,
                "message": "数据已一致，无需修复",
                "data": stats
            }
        
        # 执行修复：完全清空知识库
        result = rag_manager.clear_knowledge_base(agent.name)
        
        # 获取修复后的统计信息
        new_stats = rag_manager.get_statistics(agent.name)
        
        return {
            "success": True,
            "message": "数据不一致已修复，知识库已清空",
            "before": {
                "files": stats.get("total_files", 0),
                "vectors": stats.get("total_vectors", 0)
            },
            "after": {
                "files": new_stats.get("total_files", 0),
                "vectors": new_stats.get("total_vectors", 0)
            },
            "details": result.get("details", {})
        }
    except Exception as e:
        raise HTTPException(500, f"修复失败: {str(e)}")
        
        # TODO: 实现重建逻辑
        return {
            "success": True,
            "message": "重建功能开发中"
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"重建失败: {str(e)}")
