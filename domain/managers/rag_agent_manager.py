"""
RAG Agent 实例管理器
职责：管理 RAGAgent 实例的生命周期（创建、缓存、销毁）
"""
from typing import Dict, Optional
from services.rag_agent import RAGAgent
from domain.processors.vector_store_manager import VectorStoreManager


class RAGAgentManager:
    """RAG Agent 实例管理器"""
    
    def __init__(self, vector_manager: VectorStoreManager):
        """
        初始化管理器
        
        Args:
            vector_manager: 向量存储管理器（依赖注入）
        """
        self.vector_manager = vector_manager
        self.rag_agents: Dict[str, RAGAgent] = {}
    
    def get_or_create(self, agent_name: str, system_prompt: str) -> RAGAgent:
        """
        获取或创建 RAG Agent 实例
        
        Args:
            agent_name: 智能体名称
            system_prompt: 系统提示词
            
        Returns:
            RAGAgent 实例
        """
        # 如果内存中已存在，直接返回
        if agent_name in self.rag_agents:
            return self.rag_agents[agent_name]
        
        # 创建新实例
        print(f"ℹ️ 创建新的 RAG Agent 实例: {agent_name}")
        rag_agent = RAGAgent(
            agent_name=agent_name,
            system_prompt=system_prompt,
            vector_manager=self.vector_manager
        )
        
        # 缓存
        self.rag_agents[agent_name] = rag_agent
        return rag_agent
    
    def get(self, agent_name: str) -> Optional[RAGAgent]:
        """
        获取已存在的 RAG Agent 实例（不创建）
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            RAGAgent 实例或 None
        """
        return self.rag_agents.get(agent_name)
    
    def remove(self, agent_name: str) -> bool:
        """
        从内存中移除 RAG Agent 实例
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            是否成功移除
        """
        if agent_name in self.rag_agents:
            del self.rag_agents[agent_name]
            print(f"🗑️ RAG Agent 实例已移除: {agent_name}")
            return True
        return False
    
    def reload(self, agent_name: str, system_prompt: str) -> RAGAgent:
        """
        重新加载 RAG Agent 实例（先移除再创建）
        
        Args:
            agent_name: 智能体名称
            system_prompt: 新的系统提示词
            
        Returns:
            新的 RAGAgent 实例
        """
        self.remove(agent_name)
        return self.get_or_create(agent_name, system_prompt)
    
    def update_system_prompt(self, agent_name: str, new_prompt: str) -> bool:
        """
        更新已存在实例的系统提示词
        
        Args:
            agent_name: 智能体名称
            new_prompt: 新的系统提示词
            
        Returns:
            是否成功
        """
        rag_agent = self.get(agent_name)
        if rag_agent:
            rag_agent.update_system_prompt(new_prompt)
            return True
        return False
    
    def clear_all(self):
        """清空所有实例"""
        self.rag_agents.clear()
        print("🗑️ 所有 RAG Agent 实例已清空")
    
    def get_stats(self) -> dict:
        """获取管理器统计信息"""
        return {
            "total_agents": len(self.rag_agents),
            "agent_names": list(self.rag_agents.keys())
        }


# 全局单例
_rag_agent_manager = None


def get_rag_agent_manager() -> RAGAgentManager:
    """获取 RAG Agent 管理器单例"""
    global _rag_agent_manager
    if _rag_agent_manager is None:
        from domain.processors.vector_store_manager import get_vector_store_manager
        _rag_agent_manager = RAGAgentManager(get_vector_store_manager())
    return _rag_agent_manager
