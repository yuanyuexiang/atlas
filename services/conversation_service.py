"""
客服管理服务
处理客服（会话界面）的 CRUD 操作和智能体切换
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from models.entities import Conversation, ConversationStatus, Agent, AgentSwitchLog
from models.schemas import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    AgentInfo, AgentSwitchRequest, AgentSwitchResponse
)


class ConversationService:
    """客服管理服务"""
    
    def create_conversation(self, db: Session, data: ConversationCreate) -> ConversationResponse:
        """创建客服"""
        # 检查名称是否已存在
        existing = db.query(Conversation).filter(Conversation.name == data.name).first()
        if existing:
            raise ValueError(f"客服名称已存在: {data.name}")
        
        # 检查智能体是否存在
        agent = db.query(Agent).filter(Agent.name == data.agent_name).first()
        if not agent:
            raise ValueError(f"智能体不存在: {data.agent_name}")
        
        # 创建客服
        conv_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conv_id,
            name=data.name,
            display_name=data.display_name,
            avatar=data.avatar,
            agent_id=agent.id,
            welcome_message=data.welcome_message or f"你好，我是{data.display_name}，有什么可以帮您？",
            description=data.description
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        print(f"✅ 客服已创建: {data.name} -> 智能体: {data.agent_name}")
        return self._to_response(conversation)
    
    def get_conversation(self, db: Session, conversation_name: str) -> ConversationResponse:
        """获取客服详情"""
        conversation = db.query(Conversation).filter(
            Conversation.name == conversation_name
        ).first()
        if not conversation:
            raise ValueError(f"客服不存在: {conversation_name}")
        return self._to_response(conversation)
    
    def list_conversations(
        self,
        db: Session,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> dict:
        """获取客服列表"""
        query = db.query(Conversation)
        
        if status:
            query = query.filter(Conversation.status == ConversationStatus(status))
        
        total = query.count()
        conversations = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "conversations": [self._to_response(c) for c in conversations]
        }
    
    def update_conversation(
        self,
        db: Session,
        conversation_name: str,
        update_data: ConversationUpdate
    ) -> ConversationResponse:
        """更新客服"""
        conversation = db.query(Conversation).filter(
            Conversation.name == conversation_name
        ).first()
        if not conversation:
            raise ValueError(f"客服不存在: {conversation_name}")
        
        # 更新字段
        for field, value in update_data.dict(exclude_unset=True).items():
            if field == "status":
                value = ConversationStatus(value)
            setattr(conversation, field, value)
        
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(conversation)
        
        print(f"✅ 客服已更新: {conversation_name}")
        return self._to_response(conversation)
    
    def delete_conversation(self, db: Session, conversation_name: str) -> dict:
        """删除客服"""
        conversation = db.query(Conversation).filter(
            Conversation.name == conversation_name
        ).first()
        if not conversation:
            raise ValueError(f"客服不存在: {conversation_name}")
        
        db.delete(conversation)
        db.commit()
        
        print(f"✅ 客服已删除: {conversation_name}")
        return {"success": True, "message": f"客服 {conversation_name} 已删除"}
    
    def switch_agent(
        self,
        db: Session,
        conversation_name: str,
        switch_data: AgentSwitchRequest
    ) -> AgentSwitchResponse:
        """切换客服使用的智能体"""
        # 获取客服
        conversation = db.query(Conversation).filter(
            Conversation.name == conversation_name
        ).first()
        if not conversation:
            raise ValueError(f"客服不存在: {conversation_name}")
        
        # 获取新智能体
        new_agent = db.query(Agent).filter(
            Agent.name == switch_data.new_agent_name
        ).first()
        if not new_agent:
            raise ValueError(f"智能体不存在: {switch_data.new_agent_name}")
        
        # 记录切换日志
        old_agent = conversation.agent
        log = AgentSwitchLog(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            old_agent_id=old_agent.id,
            new_agent_id=new_agent.id,
            switch_reason=switch_data.reason
        )
        db.add(log)
        
        # 更新关联
        conversation.agent_id = new_agent.id
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        
        print(f"✅ 客服 {conversation_name} 已切换智能体: {old_agent.name} -> {new_agent.name}")
        
        return AgentSwitchResponse(
            conversation_name=conversation_name,
            old_agent=old_agent.name,
            new_agent=new_agent.name,
            switched_at=datetime.utcnow()
        )
    
    def get_switch_history(self, db: Session, conversation_name: str) -> List[dict]:
        """获取智能体切换历史"""
        conversation = db.query(Conversation).filter(
            Conversation.name == conversation_name
        ).first()
        if not conversation:
            raise ValueError(f"客服不存在: {conversation_name}")
        
        logs = db.query(AgentSwitchLog).filter(
            AgentSwitchLog.conversation_id == conversation.id
        ).order_by(AgentSwitchLog.switched_at.desc()).all()
        
        return [
            {
                "old_agent_id": log.old_agent_id,
                "new_agent_id": log.new_agent_id,
                "reason": log.switch_reason,
                "switched_at": log.switched_at.isoformat()
            }
            for log in logs
        ]
    
    def update_activity(self, db: Session, conversation_name: str):
        """更新活跃时间和消息计数"""
        conversation = db.query(Conversation).filter(
            Conversation.name == conversation_name
        ).first()
        if conversation:
            conversation.last_active_at = datetime.utcnow()
            conversation.message_count += 1
            db.commit()
    
    def _to_response(self, conversation: Conversation) -> ConversationResponse:
        """转换为响应模型"""
        agent_info = AgentInfo(
            id=conversation.agent.id,
            name=conversation.agent.name,
            display_name=conversation.agent.display_name,
            agent_type=conversation.agent.agent_type.value
        )
        
        return ConversationResponse(
            id=conversation.id,
            name=conversation.name,
            display_name=conversation.display_name,
            avatar=conversation.avatar,
            status=conversation.status.value,
            agent=agent_info,
            welcome_message=conversation.welcome_message,
            message_count=conversation.message_count,
            last_active_at=conversation.last_active_at,
            created_at=conversation.created_at
        )
