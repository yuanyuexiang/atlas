"""
知识库管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from models.schemas import DocumentUploadResponse, KnowledgeBaseStats
from models.auth import User
from services.multi_rag_manager import get_rag_manager
from services.agent_service import AgentService
from services.auth_service import get_current_active_user
from core.database import get_db
from core.config import settings
import os
import shutil

router = APIRouter(prefix="/knowledge-base", tags=["知识库管理"])
rag_manager = get_rag_manager()
agent_service = AgentService()


@router.post("/{agent_name}/documents", response_model=DocumentUploadResponse, summary="上传文档")
async def upload_document(
    agent_name: str,
    file: UploadFile = File(..., description="支持 PDF、TXT、MD 格式"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    为智能体上传知识库文档并自动向量化
    
    流程：
    1. 保存临时文件
    2. 文档解析和文本切分
    3. 向量化并存入 Milvus
    4. 保存元数据
    """
    try:
        # 验证智能体存在
        agent_service.get_agent(db, agent_name)
        
        # 验证文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"不支持的文件类型: {file_ext}")
        
        # 保存临时文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        temp_path = os.path.join(upload_dir, f"{agent_name}_{file.filename}")
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 验证文件大小
        file_size = os.path.getsize(temp_path)
        if file_size > settings.MAX_UPLOAD_SIZE:
            os.remove(temp_path)
            raise HTTPException(400, f"文件过大: {file_size / 1024 / 1024:.1f}MB > 10MB")
        
        # 上传到 Milvus
        result = rag_manager.upload_file(agent_name, temp_path)
        
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


@router.get("/{agent_name}/documents", summary="获取文档列表")
async def list_documents(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取智能体的所有文档列表"""
    try:
        # 验证智能体存在
        agent_service.get_agent(db, agent_name)
        
        files = rag_manager.list_files(agent_name)
        return {"success": True, "data": files}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


@router.delete("/{agent_name}/documents/{file_id}", summary="删除文档")
async def delete_document(
    agent_name: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除指定文档
    
    注意：Milvus 删除功能受限，建议使用重建知识库功能
    """
    try:
        # 验证智能体存在
        agent_service.get_agent(db, agent_name)
        
        result = rag_manager.delete_file(agent_name, file_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除失败: {str(e)}")


@router.get("/{agent_name}/stats", summary="获取知识库统计")
async def get_knowledge_base_stats(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取知识库统计信息
    
    包括：文档数、向量数、存储大小、文件列表
    """
    try:
        # 验证智能体存在
        agent_service.get_agent(db, agent_name)
        
        stats = rag_manager.get_statistics(agent_name)
        return {"success": True, "data": stats}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


@router.delete("/{agent_name}/clear", summary="清空知识库")
async def clear_knowledge_base(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    清空智能体的知识库
    
    警告：此操作不可逆，将删除所有文档和向量数据
    """
    try:
        # 验证智能体存在
        agent_service.get_agent(db, agent_name)
        
        result = rag_manager.clear_knowledge_base(agent_name)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"清空失败: {str(e)}")


@router.post("/{agent_name}/rebuild", summary="重建知识库索引")
async def rebuild_knowledge_base(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    重建知识库索引
    
    用于优化搜索性能或修复索引问题
    """
    try:
        # 验证智能体存在
        agent_service.get_agent(db, agent_name)
        
        # TODO: 实现重建逻辑
        return {
            "success": True,
            "message": "重建功能开发中"
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"重建失败: {str(e)}")
