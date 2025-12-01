"""
多智能体 RAG 管理器
管理多个 RAG Agent 实例
"""
import os
from typing import Optional, Dict, List
from services.rag_agent import RAGAgent
from services.milvus_service import get_milvus_store


class MultiRAGManager:
    """管理多个智能体的 RAG Agent"""
    
    def __init__(self):
        self.agents: Dict[str, RAGAgent] = {}
        self.milvus_store = get_milvus_store()
    
    def get_agent(self, agent_name: str, system_prompt: str = None) -> RAGAgent:
        """
        获取或创建指定智能体的 Agent
        
        Args:
            agent_name: 智能体名称
            system_prompt: 系统提示词（可选）
            
        Returns:
            RAGAgent 实例
        """
        if agent_name in self.agents:
            # 如果提供了新的 system_prompt，更新它
            if system_prompt and system_prompt != self.agents[agent_name].system_prompt:
                self.agents[agent_name].update_system_prompt(system_prompt)
            return self.agents[agent_name]
        
        # 创建新的 Agent
        agent = RAGAgent(agent_name=agent_name, system_prompt=system_prompt)
        self.agents[agent_name] = agent
        return agent
    
    def upload_file(self, agent_name: str, file_path: str) -> dict:
        """
        为指定智能体上传并向量化文件
        
        Args:
            agent_name: 智能体名称
            file_path: 文件路径
            
        Returns:
            dict: 处理结果
        """
        try:
            agent = self.get_agent(agent_name)
            result = agent.add_document(file_path)
            return {
                "success": True,
                "message": f"文件 {os.path.basename(file_path)} 上传成功",
                "data": result
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"上传失败: {str(e)}",
                "data": None
            }
    
    def delete_file(self, agent_name: str, file_id: str) -> dict:
        """
        删除指定智能体的文件
        
        Args:
            agent_name: 智能体名称
            file_id: 文件ID
            
        Returns:
            dict: 删除结果
        """
        try:
            agent = self.get_agent(agent_name)
            agent.remove_document(file_id)
            return {
                "success": True,
                "message": "文件删除成功"
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
            list: 文件元数据列表
        """
        try:
            # 直接读取元数据文件，避免创建 Agent 实例
            metadata_dir = os.getenv("METADATA_DIR", "metadata_store")
            meta_file = os.path.join(metadata_dir, f"{agent_name}.json")
            
            if os.path.exists(meta_file):
                import json
                with open(meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('files', [])
            return []
        except Exception as e:
            print(f"❌ 获取文件列表失败: {e}")
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
            if agent_name in self.agents:
                del self.agents[agent_name]
            
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
    
    def update_system_prompt(self, agent_name: str, new_prompt: str) -> dict:
        """
        更新指定智能体的系统提示词
        
        Args:
            agent_name: 智能体名称
            new_prompt: 新的系统提示词
            
        Returns:
            dict: 操作结果
        """
        try:
            agent = self.get_agent(agent_name)
            agent.update_system_prompt(new_prompt)
            return {
                "success": True,
                "message": "提示词更新成功"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"更新失败: {str(e)}"
            }


# 全局单例
_manager_instance: Optional[MultiRAGManager] = None


def get_rag_manager() -> MultiRAGManager:
    """获取 RAG 管理器单例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MultiRAGManager()
    return _manager_instance
