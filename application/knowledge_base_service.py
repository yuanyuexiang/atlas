"""
知识库管理服务
职责：文档上传、删除、列表、统计（协调 DocumentProcessor 和 VectorStoreManager）
"""
import os
import uuid
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from domain.processors.document_processor import DocumentProcessor
from domain.processors.vector_store_manager import VectorStoreManager
from repository.agent_repository import DocumentRepository
from domain.entities import Document, DocumentStatus


class KnowledgeBaseService:
    """知识库管理服务"""
    
    def __init__(
        self,
        doc_processor: DocumentProcessor,
        vector_manager: VectorStoreManager
    ):
        """
        初始化服务
        
        Args:
            doc_processor: 文档处理器
            vector_manager: 向量存储管理器
        """
        self.doc_processor = doc_processor
        self.vector_manager = vector_manager
        self.doc_repo = DocumentRepository()
    
    def upload_file(
        self,
        db: Session,
        agent_id: str,
        agent_name: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        上传文档到知识库
        
        Args:
            db: 数据库会话
            agent_id: 智能体 ID
            agent_name: 智能体名称
            file_path: 文件路径
            
        Returns:
            dict: 上传结果
        """
        # 生成文件 ID
        file_id = str(uuid.uuid4())
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file_type = file_path.split('.')[-1] if '.' in file_path else 'unknown'
        
        # 1. 创建数据库记录（状态：processing）
        document = Document(
            id=file_id,
            agent_id=agent_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            status=DocumentStatus.PROCESSING,
            chunks_count=0,
            processing_progress=0
        )
        self.doc_repo.create(db, document)
        print(f"📝 文档记录已创建: {filename} (status=processing)")
        
        try:
            # 2. 使用 DocumentProcessor 处理文档
            documents, stats = self.doc_processor.process_file(
                file_path=file_path,
                file_id=file_id,
                filename=filename,
                agent_name=agent_name
            )
            
            # 3. 使用 VectorStoreManager 添加到向量数据库
            result = self.vector_manager.add_documents(agent_name, documents)
            
            # 4. 更新数据库状态为 ready
            self.doc_repo.update_status(
                db=db,
                doc_id=file_id,
                status=DocumentStatus.READY,
                chunks_count=result['added']
            )
            
            # 5. 删除源文件
            try:
                os.remove(file_path)
                print(f"🗑️ 源文件已删除")
            except Exception as e:
                print(f"⚠️ 删除源文件失败: {e}")
            
            return {
                "success": True,
                "message": f"文件 {filename} 上传成功",
                "data": {
                    'file_id': file_id,
                    'filename': filename,
                    'chunks_count': result['added'],
                    'status': 'ready',
                    'processing_progress': 100
                }
            }
            
        except Exception as e:
            # 更新数据库状态为 failed
            self.doc_repo.update_status(
                db=db,
                doc_id=file_id,
                status=DocumentStatus.FAILED,
                error_message=str(e)
            )
            
            return {
                "success": False,
                "message": f"上传失败: {str(e)}",
                "data": None
            }
    
    def delete_file(
        self,
        db: Session,
        agent_name: str,
        file_id: str
    ) -> Dict[str, Any]:
        """
        删除文档
        
        Args:
            db: 数据库会话
            agent_name: 智能体名称
            file_id: 文件 ID
            
        Returns:
            dict: 删除结果
        """
        try:
            # 1. 从向量数据库删除
            vector_success = self.vector_manager.delete_by_file_id(agent_name, file_id)
            
            # 2. 从数据库删除记录
            db_success = self.doc_repo.delete(db, file_id)
            
            if db_success:
                return {
                    "success": True,
                    "message": "文件删除成功"
                }
            else:
                return {
                    "success": False,
                    "message": "文件不存在"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }
    
    def list_files(self, db: Session, agent_id: str) -> List[Dict[str, Any]]:
        """
        获取智能体的文档列表
        
        Args:
            db: 数据库会话
            agent_id: 智能体 ID
            
        Returns:
            list: 文档列表
        """
        documents = self.doc_repo.list_by_agent(db, agent_id)
        
        return [
            {
                'id': doc.id,
                'filename': doc.filename,
                'file_size': doc.file_size,
                'file_type': doc.file_type,
                'status': doc.status.value,
                'chunks_count': doc.chunks_count,
                'processing_progress': doc.processing_progress,
                'error_message': doc.error_message,
                'uploaded_at': doc.uploaded_at.strftime('%Y-%m-%d %H:%M:%S') if doc.uploaded_at else None,
                'processed_at': doc.processed_at.strftime('%Y-%m-%d %H:%M:%S') if doc.processed_at else None
            }
            for doc in documents
        ]
    
    def get_statistics(self, agent_name: str) -> Dict[str, Any]:
        """
        获取知识库统计信息
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            dict: 统计信息
        """
        return self.vector_manager.get_statistics(agent_name)
    
    def clear_knowledge_base(
        self,
        db: Session,
        agent_id: str,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        清空知识库
        
        Args:
            db: 数据库会话
            agent_id: 智能体 ID
            agent_name: 智能体名称
            
        Returns:
            dict: 清空结果
        """
        try:
            # 1. 清空向量数据库
            vector_success = self.vector_manager.clear_collection(agent_name)
            
            # 2. 删除所有文档记录
            count = self.doc_repo.delete_by_agent(db, agent_id)
            
            if vector_success:
                return {
                    "success": True,
                    "message": f"知识库已清空，删除了 {count} 个文档记录"
                }
            else:
                return {
                    "success": False,
                    "message": "清空失败"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"清空失败: {str(e)}"
            }


# 全局单例
_kb_service = None


def get_kb_service() -> KnowledgeBaseService:
    """获取知识库服务单例"""
    global _kb_service
    if _kb_service is None:
        from domain.processors.document_processor import get_document_processor
        from domain.processors.vector_store_manager import get_vector_store_manager
        
        _kb_service = KnowledgeBaseService(
            doc_processor=get_document_processor(),
            vector_manager=get_vector_store_manager()
        )
    return _kb_service
