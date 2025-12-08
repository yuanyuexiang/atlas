"""
智能体管理服务 - Facade 模式
职责：协调 Repository、RAGAgentManager、KnowledgeBaseService
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from domain.entities import Agent, AgentStatus, AgentType
from api.schemas import AgentCreate, AgentUpdate, AgentResponse, KnowledgeBaseInfo
from repository.agent_repository import AgentRepository
from domain.managers.rag_agent_manager import RAGAgentManager, get_rag_agent_manager
from application.knowledge_base_service import KnowledgeBaseService, get_kb_service
from application.rag_agent import RAGAgent


class AgentService:
    """智能体管理服务（协调器 / Facade）"""
    
    def __init__(
        self,
        rag_manager: RAGAgentManager,
        kb_service: KnowledgeBaseService
    ):
        """
        初始化服务
        
        Args:
            rag_manager: RAG Agent 管理器
            kb_service: 知识库服务
        """
        self.agent_repo = AgentRepository()
        self.rag_manager = rag_manager
        self.kb_service = kb_service
    
    # ==================== RAG Agent 管理 ====================
    
    def get_rag_agent(self, db: Session, agent_name: str) -> RAGAgent:
        """
        获取或创建 RAG Agent 实例
        
        Args:
            db: 数据库会话
            agent_name: 智能体名称
            
        Returns:
            RAGAgent 实例
        """
        # 从数据库读取配置
        agent = self.agent_repo.get_by_name(db, agent_name)
        if not agent:
            raise ValueError(f"Agent 不存在: {agent_name}")
        
        # 通过 RAGAgentManager 获取或创建实例
        return self.rag_manager.get_or_create(agent_name, agent.system_prompt)
    
    # ==================== CRUD 操作 ====================
    
    def create_agent(self, db: Session, agent_data: AgentCreate) -> AgentResponse:
        """创建智能体"""
        # 检查名称是否已存在
        if self.agent_repo.exists_by_name(db, agent_data.name):
            raise ValueError(f"智能体名称已存在: {agent_data.name}")
        
        # 生成默认系统提示词
        if not agent_data.system_prompt:
            agent_data.system_prompt = self._get_default_prompt(agent_data.agent_type)
        
        # 创建实体
        agent = Agent(
            id=str(uuid.uuid4()),
            name=agent_data.name,
            display_name=agent_data.display_name,
            agent_type=AgentType(agent_data.agent_type),
            status=AgentStatus.ACTIVE,
            system_prompt=agent_data.system_prompt,
            description=agent_data.description,
            milvus_collection=f"agent_{agent_data.name}".replace("-", "_")
        )
        
        # 保存到数据库
        agent = self.agent_repo.create(db, agent)
        
        # 初始化 RAG Agent
        self.rag_manager.get_or_create(agent.name, agent.system_prompt)
        
        print(f"✅ 智能体已创建: {agent_data.name}")
        return self._to_response(db, agent)
    
    def get_agent(self, db: Session, agent_id: str) -> AgentResponse:
        """获取智能体详情"""
        agent = self.agent_repo.get_by_id(db, agent_id)
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
    ) -> List[AgentResponse]:
        """获取智能体列表"""
        import time
        start_time = time.time()
        
        status_enum = AgentStatus(status) if status else None
        agents = self.agent_repo.list_all(db, status_enum, skip, limit)
        
        print(f"⏱️ [list_agents] 数据库查询耗时: {time.time() - start_time:.3f}秒")
        
        # 如果指定了 agent_type，进行过滤
        if agent_type:
            agents = [a for a in agents if a.agent_type.value == agent_type]
        
        # 批量转换，使用轻量级响应（不查询向量统计）
        convert_start = time.time()
        result = [self._to_response_lite(db, agent) for agent in agents]
        print(f"⏱️ [list_agents] 转换响应耗时: {time.time() - convert_start:.3f}秒")
        print(f"⏱️ [list_agents] 总耗时: {time.time() - start_time:.3f}秒")
        
        return result
    
    def update_agent(
        self,
        db: Session,
        agent_id: str,
        update_data: AgentUpdate
    ) -> AgentResponse:
        """更新智能体"""
        agent = self.agent_repo.get_by_id(db, agent_id)
        if not agent:
            raise ValueError(f"智能体不存在: {agent_id}")
        
        # 准备更新数据
        update_dict = update_data.dict(exclude_unset=True)
        if "status" in update_dict:
            update_dict["status"] = AgentStatus(update_dict["status"])
        if "agent_type" in update_dict:
            update_dict["agent_type"] = AgentType(update_dict["agent_type"])
        
        # 更新数据库
        agent = self.agent_repo.update(db, agent, update_dict)
        
        # 如果更新了 system_prompt，重新加载 RAG Agent
        if "system_prompt" in update_dict:
            self.rag_manager.reload(agent.name, agent.system_prompt)
        
        print(f"✅ 智能体已更新: {agent.name}")
        return self._to_response(db, agent)
    
    def delete_agent(self, db: Session, agent_id: str) -> dict:
        """删除智能体"""
        agent = self.agent_repo.get_by_id(db, agent_id)
        if not agent:
            raise ValueError(f"智能体不存在: {agent_id}")
        
        # 检查是否有客服使用
        if agent.conversations:
            raise ValueError(f"无法删除：仍有 {len(agent.conversations)} 个客服在使用此智能体")
        
        # 清空知识库
        self.kb_service.clear_knowledge_base(db, agent.id, agent.name)
        
        # 移除 RAG Agent 实例
        self.rag_manager.remove(agent.name)
        
        # 删除数据库记录
        self.agent_repo.delete(db, agent)
        
        print(f"✅ 智能体已删除: {agent.name}")
        return {"success": True, "message": f"智能体 {agent.name} 已删除"}
    
    # ==================== 知识库管理（委托给 KnowledgeBaseService）====================
    
    def upload_file(self, db: Session, agent_name: str, file_path: str) -> dict:
        """上传文档"""
        agent = self.agent_repo.get_by_name(db, agent_name)
        if not agent:
            raise ValueError(f"Agent 不存在: {agent_name}")
        
        return self.kb_service.upload_file(db, agent.id, agent.name, file_path)
    
    def delete_file(self, db: Session, agent_name: str, file_id: str) -> dict:
        """删除文档"""
        return self.kb_service.delete_file(db, agent_name, file_id)
    
    def list_files(self, db: Session, agent_id: str) -> List[dict]:
        """列出文档"""
        return self.kb_service.list_files(db, agent_id)
    
    def get_statistics(self, agent_name: str) -> dict:
        """获取统计信息"""
        return self.kb_service.get_statistics(agent_name)
    
    def clear_knowledge_base(self, db: Session, agent_id: str, agent_name: str) -> dict:
        """清空知识库"""
        return self.kb_service.clear_knowledge_base(db, agent_id, agent_name)
    
    # ==================== 辅助方法 ====================
    
    def _get_default_prompt(self, agent_type: str) -> str:
        """获取默认系统提示词"""
        prompts = {
            "general": "你是一个友好且专业的AI助手，能够回答各种问题并提供帮助。",
            "legal": "你是一个专业的法律顾问AI助手，精通法律条文和案例分析。",
            "medical": "你是一个专业的医疗AI助手，能够提供医疗咨询和健康建议。",
            "financial": "你是一个专业的金融AI助手，精通投资理财和金融分析。",
            "custom": "你是一个定制化的AI助手。"
        }
        return prompts.get(agent_type, prompts["general"])
    
    def _to_response(self, db: Session, agent: Agent) -> AgentResponse:
        """转换为响应对象（完整版，包含向量统计）"""
        # 刷新实例以加载关系
        db.refresh(agent)
        
        # 构建知识库信息
        try:
            vector_count = self.kb_service.get_statistics(agent.name).get("total_vectors", 0)
        except Exception as e:
            print(f"⚠️ 获取向量统计失败: {e}")
            vector_count = 0
        
        kb_info = KnowledgeBaseInfo(
            collection_name=agent.milvus_collection or f"agent_{agent.name}",
            total_files=len(agent.documents) if agent.documents else 0,
            total_vectors=vector_count,
            total_size_mb=0.0,
            files=[]
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
            updated_at=agent.updated_at
        )
    
    def _to_response_lite(self, db: Session, agent: Agent) -> AgentResponse:
        """转换为响应对象（轻量级，不查询向量统计）
        
        用于列表查询，避免大量的 Milvus 统计调用
        使用文档数量作为向量数量的近似值（假设每个文档平均100个向量）
        """
        # 刷新实例以加载关系
        db.refresh(agent)
        
        # 优先使用数据库的文档记录
        file_count = len(agent.documents) if agent.documents else 0
        
        # 如果数据库中没有记录，但可能 Milvus 中有数据（历史遗留）
        # 则查询一次 Milvus 来确认
        if file_count == 0:
            try:
                stats = self.kb_service.get_statistics(agent.name)
                actual_vectors = stats.get("total_vectors", 0)
                if actual_vectors > 0:
                    # 有向量数据，估算文件数
                    file_count = max(1, actual_vectors // 100)  # 反推文件数
                    estimated_vectors = actual_vectors
                else:
                    estimated_vectors = 0
            except Exception as e:
                # 查询失败时，使用0
                estimated_vectors = 0
        else:
            # 有数据库记录时，使用估算值
            estimated_vectors = file_count * 100
        
        # 构建知识库信息
        kb_info = KnowledgeBaseInfo(
            collection_name=agent.milvus_collection or f"agent_{agent.name}",
            total_files=file_count,
            total_vectors=estimated_vectors,  # 使用估算值或实际值
            total_size_mb=0.0,
            files=[]
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
            updated_at=agent.updated_at
        )


# 全局单例
_agent_service = None


def get_agent_service() -> AgentService:
    """获取智能体服务单例"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService(
            rag_manager=get_rag_agent_manager(),
            kb_service=get_kb_service()
        )
    return _agent_service
