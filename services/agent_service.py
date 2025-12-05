"""
智能体管理服务
处理智能体的 CRUD 操作和 RAG Agent 实例管理
"""
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from models.entities import Agent, AgentStatus, AgentType
from models.schemas import AgentCreate, AgentUpdate, AgentResponse, KnowledgeBaseInfo
from services.rag_agent import RAGAgent
from services.document_processor import get_document_processor
from services.vector_store_manager import get_vector_store_manager


class AgentService:
    """智能体管理服务（统一管理数据库和 RAG 实例）"""
    
    def __init__(self):
        # RAG Agent 实例缓存
        self.rag_agents: Dict[str, RAGAgent] = {}
        # 依赖的服务
        self.doc_processor = get_document_processor()
        self.vector_manager = get_vector_store_manager()
    
    def get_rag_agent(self, db: Session, agent_name: str) -> RAGAgent:
        """
        获取或创建 RAG Agent 实例（自动从数据库读取配置）
        
        Args:
            db: 数据库会话
            agent_name: 智能体名称
            
        Returns:
            RAGAgent 实例
            
        Raises:
            ValueError: 如果 Agent 不存在
        """
        # 如果内存中已存在，直接返回
        if agent_name in self.rag_agents:
            return self.rag_agents[agent_name]
        
        # 从数据库读取配置
        db_agent = db.query(Agent).filter(Agent.name == agent_name).first()
        if not db_agent:
            raise ValueError(f"Agent 不存在: {agent_name}")
        
        # 创建 RAGAgent 实例（依赖注入）
        print(f"ℹ️ 创建新的 RAG Agent 实例: {agent_name}")
        rag_agent = RAGAgent(
            agent_name=agent_name,
            system_prompt=db_agent.system_prompt,
            vector_manager=self.vector_manager  # 依赖注入
        )
        self.rag_agents[agent_name] = rag_agent
        return rag_agent
    
    def create_agent(self, db: Session, agent_data: AgentCreate) -> AgentResponse:
        """创建智能体"""
        # 检查名称是否已存在
        existing = db.query(Agent).filter(Agent.name == agent_data.name).first()
        if existing:
            raise ValueError(f"智能体名称已存在: {agent_data.name}")
        
        # 生成默认系统提示词
        if not agent_data.system_prompt:
            agent_data.system_prompt = self._get_default_prompt(agent_data.agent_type)
        
        # 创建实体
        agent_id = str(uuid.uuid4())
        collection_name = f"agent_{agent_data.name}".replace("-", "_")
        
        agent = Agent(
            id=agent_id,
            name=agent_data.name,
            display_name=agent_data.display_name,
            agent_type=AgentType(agent_data.agent_type),
            status=AgentStatus.ACTIVE,
            system_prompt=agent_data.system_prompt,
            description=agent_data.description,
            milvus_collection=collection_name
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        # 初始化 RAG Agent（自动从数据库读取）
        self.get_rag_agent(db, agent_data.name)
        
        print(f"✅ 智能体已创建: {agent_data.name}")
        return self._to_response(db, agent)
    
    def get_agent(self, db: Session, agent_id: str) -> AgentResponse:
        """获取智能体详情 - 只支持 UUID"""
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            raise ValueError(f"智能体不存在: {agent_id}")
        return self._to_response(db, agent)
    
    def list_agents(
        self,
        db: Session,
        status: Optional[str] = None,
        agent_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list:
        """获取智能体列表（轻量级，不查询 Milvus 统计）"""
        query = db.query(Agent)
        
        if status:
            query = query.filter(Agent.status == AgentStatus(status))
        if agent_type:
            query = query.filter(Agent.agent_type == AgentType(agent_type))
        
        agents = query.offset(skip).limit(limit).all()
        
        # 使用轻量级响应，避免查询 Milvus
        return [self._to_light_response(db, agent) for agent in agents]
    
    def update_agent(
        self,
        db: Session,
        agent_id: str,
        update_data: AgentUpdate
    ) -> AgentResponse:
        """更新智能体 - 只支持 UUID"""
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            raise ValueError(f"智能体不存在: {agent_id}")
        
        # 更新字段
        for field, value in update_data.dict(exclude_unset=True).items():
            if field == "status":
                value = AgentStatus(value)
            setattr(agent, field, value)
        
        agent.updated_at = datetime.utcnow()
        
        # 如果更新了系统提示词，同步到 RAG Agent
        if update_data.system_prompt and agent.name in self.rag_agents:
            self.rag_agents[agent.name].update_system_prompt(update_data.system_prompt)
        
        db.commit()
        db.refresh(agent)
        
        print(f"✅ 智能体已更新: {agent.name}")
        return self._to_response(db, agent)
    
    def delete_agent(self, db: Session, agent_id: str) -> dict:
        """删除智能体 - 只支持 UUID"""
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            raise ValueError(f"智能体不存在: {agent_id}")
        
        # 检查是否有客服使用
        if agent.conversations:
            raise ValueError(f"无法删除：仍有 {len(agent.conversations)} 个客服在使用此智能体")
        
        # 删除知识库
        self.clear_knowledge_base(agent.name)
        
        # 删除数据库记录
        db.delete(agent)
        db.commit()
        
        print(f"✅ 智能体已删除: {agent.name}")
        return {"success": True, "message": f"智能体 {agent.name} 已删除"}
    
    # ==================== 知识库管理方法 ====================
    
    def upload_file(self, db: Session, agent_name: str, file_path: str) -> dict:
        """
        为指定智能体上传并向量化文件
        
        Args:
            db: 数据库会话
            agent_name: 智能体名称
            file_path: 文件路径
            
        Returns:
            dict: 处理结果
        """
        try:
            # 生成 file_id
            file_id = str(uuid.uuid4())
            filename = os.path.basename(file_path)
            
            # 1. 使用 DocumentProcessor 处理文档
            documents, stats = self.doc_processor.process_file(
                file_path=file_path,
                file_id=file_id,
                filename=filename,
                agent_name=agent_name
            )
            
            # 2. 使用 VectorStoreManager 添加到向量数据库
            result = self.vector_manager.add_documents(agent_name, documents)
            
            # 3. 删除源文件
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
            return {
                "success": False,
                "message": f"上传失败: {str(e)}",
                "data": None
            }
    
    def delete_file(self, db: Session, agent_name: str, file_id: str) -> dict:
        """
        删除指定智能体的文件
        
        Args:
            db: 数据库会话
            agent_name: 智能体名称
            file_id: 文件ID
            
        Returns:
            dict: 删除结果
        """
        try:
            # 直接使用 VectorStoreManager 删除向量数据
            success = self.vector_manager.delete_by_file_id(agent_name, file_id)
            if success:
                return {
                    "success": True,
                    "message": "文件删除成功"
                }
            else:
                return {
                    "success": False,
                    "message": "文件不存在或已删除"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }
    
    def list_files(self, agent_name: str) -> List[dict]:
        """
        列出指定智能体的所有文件
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            list: 文件元数据列表（暂时返回空列表，元数据应由数据库管理）
        """
        # TODO: 元数据应该存储在数据库中，而不是 JSON 文件
        # 这里暂时返回空列表，后续需要添加 Document 表
        return []
    
    def get_statistics(self, agent_name: str) -> dict:
        """
        获取指定智能体的知识库统计信息
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            dict: 统计信息
        """
        try:
            # 获取文件元数据
            files = self.list_files(agent_name)
            total_files = len(files)
            total_chunks = sum(f.get("chunks_count", 0) for f in files)
            total_size = sum(f.get("file_size", 0) for f in files)
            
            # 获取 Milvus 统计
            milvus_stats = self.milvus_store.get_collection_stats(agent_name)
            actual_vectors = milvus_stats.get("total_vectors", 0)
            
            # 数据一致性检查
            is_consistent = (total_files == 0 and actual_vectors == 0) or (total_files > 0 and actual_vectors > 0)
            
            result = {
                "agent_name": agent_name,
                "collection_name": milvus_stats.get("collection_name", ""),
                "total_files": total_files,
                "total_chunks": total_chunks,
                "total_vectors": actual_vectors,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "files": files,
                "is_consistent": is_consistent
            }
            
            # 如果数据不一致，添加警告信息
            if not is_consistent:
                result["warning"] = f"数据不一致：元数据显示 {total_files} 个文件，但向量库中有 {actual_vectors} 个向量"
                print(f"⚠️ 数据不一致检测 - {agent_name}: 文件={total_files}, 向量={actual_vectors}")
            
            return result
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {
                "agent_name": agent_name,
                "collection_name": "",
                "total_files": 0,
                "total_chunks": 0,
                "total_vectors": 0,
                "total_size_mb": 0,
                "files": []
            }
    
    def clear_knowledge_base(self, agent_name: str) -> dict:
        """
        清空指定智能体的知识库（包括向量数据和元数据）
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            dict: 操作结果
        """
        try:
            vector_deleted = False
            metadata_deleted = False
            
            # 1. 移除 agent 实例
            if agent_name in self.rag_agents:
                del self.rag_agents[agent_name]
            
            # 2. 删除 Milvus Collection（关键：确保向量数据被删除）
            vector_deleted = self.milvus_store.delete_collection(agent_name)
            
            # 3. 删除元数据文件
            metadata_dir = os.getenv("METADATA_DIR", "metadata_store")
            meta_file = os.path.join(metadata_dir, f"{agent_name}.json")
            if os.path.exists(meta_file):
                os.remove(meta_file)
                metadata_deleted = True
            
            print(f"✅ 知识库已清空: {agent_name} (向量: {'是' if vector_deleted else '否'}, 元数据: {'是' if metadata_deleted else '否'})")
            
            return {
                "success": True,
                "message": f"{agent_name} 的知识库已清空",
                "details": {
                    "vectors_deleted": vector_deleted,
                    "metadata_deleted": metadata_deleted
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"清空失败: {str(e)}"
            }
    
    # ==================== 内部辅助方法 ====================
    
    def _to_response(self, db: Session, agent: Agent) -> AgentResponse:
        """转换为完整响应模型（包含 Milvus 统计）"""
        # 获取知识库统计
        kb_stats = self.get_statistics(agent.name)
        
        # 获取使用该智能体的客服列表
        conversations_using = [c.name for c in agent.conversations]
        
        kb_info = KnowledgeBaseInfo(
            collection_name=kb_stats.get("collection_name", ""),
            total_files=kb_stats.get("total_files", 0),
            total_vectors=kb_stats.get("total_vectors", 0),
            total_size_mb=kb_stats.get("total_size_mb", 0.0),
            files=kb_stats.get("files", [])
        )
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            display_name=agent.display_name,
            agent_type=agent.agent_type.value,
            status=agent.status.value,
            system_prompt=agent.system_prompt,
            description=agent.description,
            knowledge_base=kb_info,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            conversations_using=conversations_using
        )
    
    def _to_light_response(self, db: Session, agent: Agent) -> AgentResponse:
        """转换为轻量级响应（只查询元数据，不查询 Milvus）"""
        # 只读取元数据文件，不查询 Milvus
        files = self.list_files(agent.name)
        total_files = len(files)
        total_chunks = sum(f.get("chunks_count", 0) for f in files)
        total_size = sum(f.get("file_size", 0) for f in files)
        
        # 获取使用该智能体的客服列表
        conversations_using = [c.name for c in agent.conversations]
        
        kb_info = KnowledgeBaseInfo(
            collection_name=f"agent_{agent.name}",
            total_files=total_files,
            total_vectors=total_chunks,  # 使用元数据中的 chunks_count
            total_size_mb=round(total_size / 1024 / 1024, 2),
            files=files
        )
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            display_name=agent.display_name,
            agent_type=agent.agent_type.value,
            status=agent.status.value,
            system_prompt=agent.system_prompt,
            description=agent.description,
            knowledge_base=kb_info,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            conversations_using=conversations_using
        )
    
    @staticmethod
    def _get_default_prompt(agent_type: str) -> str:
        """根据类型获取默认提示词"""
        prompts = {
            "general": "你是一个通用智能助手，可以回答各类问题。",
            "legal": "你是一位专业的法律顾问，精通民法、商法等领域。请基于知识库提供专业的法律建议。",
            "medical": "你是一位医疗健康助手，可以提供健康建议（仅供参考，不替代专业医疗诊断）。",
            "financial": "你是一位金融顾问，擅长投资理财和财务规划。请基于知识库提供专业建议。",
            "custom": "你是一个可定制的智能助手。"
        }
        return prompts.get(agent_type, prompts["general"])


# 全局单例
_agent_service_instance: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """获取 AgentService 单例"""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance
