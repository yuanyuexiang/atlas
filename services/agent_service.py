"""
智能体管理服务
处理智能体的 CRUD 操作
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from models.entities import Agent, AgentStatus, AgentType
from models.schemas import AgentCreate, AgentUpdate, AgentResponse, KnowledgeBaseInfo
from services.multi_rag_manager import get_rag_manager


class AgentService:
    """智能体管理服务"""
    
    def __init__(self):
        self.rag_manager = get_rag_manager()
    
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
        
        # 初始化 RAG Agent
        self.rag_manager.get_agent(agent_data.name, agent_data.system_prompt)
        
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
        """获取智能体列表"""
        query = db.query(Agent)
        
        if status:
            query = query.filter(Agent.status == AgentStatus(status))
        if agent_type:
            query = query.filter(Agent.agent_type == AgentType(agent_type))
        
        agents = query.offset(skip).limit(limit).all()
        
        return [self._to_response(db, agent) for agent in agents]
    
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
        if update_data.system_prompt:
            self.rag_manager.update_system_prompt(agent.name, update_data.system_prompt)
        
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
        self.rag_manager.clear_knowledge_base(agent_name)
        
        # 删除数据库记录
        db.delete(agent)
        db.commit()
        
        print(f"✅ 智能体已删除: {agent_name}")
        return {"success": True, "message": f"智能体 {agent_name} 已删除"}
    
    def _to_response(self, db: Session, agent: Agent) -> AgentResponse:
        """转换为响应模型"""
        # 获取知识库统计
        kb_stats = self.rag_manager.get_statistics(agent.name)
        
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
