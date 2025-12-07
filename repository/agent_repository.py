"""
智能体仓储层 - 纯 CRUD 操作
职责：数据库的增删改查，不包含业务逻辑
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from domain.entities import Agent, AgentStatus, AgentType, Document, DocumentStatus


class AgentRepository:
    """智能体仓储（Repository 模式）"""
    
    @staticmethod
    def create(db: Session, agent: Agent) -> Agent:
        """创建智能体"""
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent
    
    @staticmethod
    def get_by_id(db: Session, agent_id: str) -> Optional[Agent]:
        """根据 ID 获取智能体"""
        return db.query(Agent).filter(Agent.id == agent_id).first()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Agent]:
        """根据名称获取智能体"""
        return db.query(Agent).filter(Agent.name == name).first()
    
    @staticmethod
    def list_all(
        db: Session,
        status: Optional[AgentStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """获取智能体列表"""
        query = db.query(Agent)
        
        if status:
            query = query.filter(Agent.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, agent: Agent, update_data: dict) -> Agent:
        """更新智能体"""
        for field, value in update_data.items():
            if hasattr(agent, field):
                setattr(agent, field, value)
        
        agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(agent)
        return agent
    
    @staticmethod
    def delete(db: Session, agent: Agent) -> bool:
        """删除智能体"""
        db.delete(agent)
        db.commit()
        return True
    
    @staticmethod
    def exists_by_name(db: Session, name: str) -> bool:
        """检查名称是否存在"""
        return db.query(Agent).filter(Agent.name == name).first() is not None


class DocumentRepository:
    """文档仓储"""
    
    @staticmethod
    def create(db: Session, document: Document) -> Document:
        """创建文档记录"""
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    def get_by_id(db: Session, doc_id: str) -> Optional[Document]:
        """根据 ID 获取文档"""
        return db.query(Document).filter(Document.id == doc_id).first()
    
    @staticmethod
    def list_by_agent(db: Session, agent_id: str) -> List[Document]:
        """获取智能体的所有文档"""
        return db.query(Document).filter(Document.agent_id == agent_id).all()
    
    @staticmethod
    def update_status(
        db: Session,
        doc_id: str,
        status: DocumentStatus,
        chunks_count: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[Document]:
        """更新文档状态"""
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return None
        
        doc.status = status
        doc.processing_progress = 100 if status == DocumentStatus.READY else 0
        
        if chunks_count is not None:
            doc.chunks_count = chunks_count
        
        if error_message:
            doc.error_message = error_message
        
        if status == DocumentStatus.READY:
            doc.processed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(doc)
        return doc
    
    @staticmethod
    def delete(db: Session, doc_id: str) -> bool:
        """删除文档"""
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return False
        
        db.delete(doc)
        db.commit()
        return True
    
    @staticmethod
    def delete_by_agent(db: Session, agent_id: str) -> int:
        """删除智能体的所有文档"""
        count = db.query(Document).filter(Document.agent_id == agent_id).delete()
        db.commit()
        return count
