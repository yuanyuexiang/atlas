"""
向量存储管理服务 - 负责向量数据的增删改查
职责：向量数据库操作、批量处理、错误重试
"""
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore


class VectorStoreManager:
    """向量存储管理服务"""
    
    def __init__(self, milvus_store, batch_size: int = 32):
        """
        初始化向量存储管理器
        
        Args:
            milvus_store: Milvus 服务实例
            batch_size: 批处理大小（默认 32，适配大多数 Embedding API 限制）
        """
        self.milvus_store = milvus_store
        self.batch_size = batch_size
    
    def get_vector_store(self, agent_name: str) -> VectorStore:
        """
        获取指定智能体的向量存储
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            VectorStore: 向量存储实例
        """
        return self.milvus_store.get_vector_store(agent_name)
    
    def add_documents(
        self,
        agent_name: str,
        documents: List[Document]
    ) -> Dict[str, Any]:
        """
        批量添加文档到向量数据库
        
        Args:
            agent_name: 智能体名称
            documents: 文档列表
            
        Returns:
            dict: 处理结果 {success: bool, added: int, failed: int, errors: List}
            
        Raises:
            Exception: 所有批次都失败时抛出异常
        """
        vector_store = self.get_vector_store(agent_name)
        
        total_added = 0
        failed_batches = []
        
        # 批量处理
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            try:
                vector_store.add_documents(batch)
                total_added += len(batch)
                print(f"  进度: {total_added}/{len(documents)}")
            except Exception as e:
                error_msg = str(e)
                print(f"  ⚠️ 批次 {batch_num} 失败: {error_msg}")
                failed_batches.append({
                    'batch': batch_num,
                    'error': error_msg
                })
        
        # 检查是否完全失败
        if total_added == 0:
            error_details = "\n".join([
                f"批次{err['batch']}: {err['error']}" 
                for err in failed_batches
            ])
            raise Exception(
                f"向量化失败：所有文本块都未能添加到向量数据库。\n"
                f"可能原因：\n"
                f"1. Embedding API 配置错误或 API Key 无效\n"
                f"2. 网络连接问题\n"
                f"3. 向量数据库连接异常\n"
                f"详细错误：\n{error_details}"
            )
        
        # 返回处理结果
        result = {
            'success': True,
            'added': total_added,
            'failed': len(failed_batches),
            'errors': failed_batches
        }
        
        print(f"✅ 成功添加 {total_added}/{len(documents)} 个向量")
        if failed_batches:
            print(f"⚠️ 失败 {len(failed_batches)} 个批次")
        
        return result
    
    def delete_by_file_id(self, agent_name: str, file_id: str) -> bool:
        """
        根据文件 ID 删除向量数据
        
        Args:
            agent_name: 智能体名称
            file_id: 文件 ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            success = self.milvus_service.delete_by_file_id(agent_name, file_id)
            if success:
                print(f"✅ 向量数据已删除: {file_id}")
            else:
                print(f"⚠️ 向量数据删除失败或不存在: {file_id}")
            return success
        except Exception as e:
            print(f"❌ 删除向量数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def search_similar(
        self,
        agent_name: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档
        
        Args:
            agent_name: 智能体名称
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            List[dict]: 搜索结果列表
        """
        return self.milvus_store.search_similar(agent_name, query, top_k)
    
    def get_statistics(self, agent_name: str) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            dict: 统计信息
        """
        return self.milvus_store.get_collection_stats(agent_name)
    
    def clear_collection(self, agent_name: str) -> bool:
        """
        清空集合中的所有向量
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            bool: 是否成功
        """
        try:
            # 通过删除并重建集合来清空
            self.milvus_store.delete_collection(agent_name)
            # 重新初始化向量存储
            self.get_vector_store(agent_name)
            print(f"✅ 集合已清空: {agent_name}")
            return True
        except Exception as e:
            print(f"❌ 清空集合失败: {e}")
            import traceback
            traceback.print_exc()
            return False


# 全局单例
_vector_store_manager = None


def get_vector_store_manager() -> VectorStoreManager:
    """获取向量存储管理器单例"""
    global _vector_store_manager
    if _vector_store_manager is None:
        from application.milvus_service import get_milvus_store
        _vector_store_manager = VectorStoreManager(get_milvus_store())
    return _vector_store_manager
