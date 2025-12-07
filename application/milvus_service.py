"""
Milvus 向量存储服务
管理向量数据库的连接、Collection 创建、检索等操作
"""
from pymilvus import connections, Collection, utility, CollectionSchema, FieldSchema, DataType
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings
from typing import List, Optional, Dict
import os
from config.milvus import milvus_settings


class MilvusVectorStore:
    """Milvus 向量存储管理"""
    
    def __init__(self):
        self.connection_alias = "default"
        self.embeddings = None
        self._connect()
        self._init_embeddings()
    
    def _connect(self):
        """连接 Milvus 服务器"""
        try:
            # 检查是否已连接
            try:
                connections.disconnect(alias=self.connection_alias)
            except:
                pass
            
            # 建立新连接
            conn_params = {
                "alias": self.connection_alias,
                "host": milvus_settings.host,
                "port": str(milvus_settings.port),
            }
            
            if milvus_settings.user:
                conn_params["user"] = milvus_settings.user
            if milvus_settings.password:
                conn_params["password"] = milvus_settings.password
            
            connections.connect(**conn_params)
            print(f"✅ 已连接到 Milvus: {milvus_settings.host}:{milvus_settings.port}")
        except Exception as e:
            print(f"❌ Milvus 连接失败: {e}")
            raise
    
    def _init_embeddings(self):
        """初始化 Embedding 模型"""
        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        base_url = os.getenv("OPENAI_BASE_URL", "")
        api_key = os.getenv("OPENAI_API_KEY", "")
        chunk_size = 10
        
        print(f"🔧 初始化 Embedding 模型: {embedding_model}")
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            api_key=api_key,
            base_url=base_url,
            check_embedding_ctx_length=False,  # 禁用 token 长度检查
            chunk_size=chunk_size,  # 关键：限制批处理大小
            max_retries=3,
            timeout=30.0
        )
        print(f"✅ Embedding 模型已初始化: {embedding_model}")
    
    def get_collection_name(self, agent_name: str) -> str:
        """生成 Collection 名称（符合 Milvus 命名规则）"""
        # Milvus Collection 名称：字母、数字、下划线，长度 1-255
        safe_name = agent_name.replace("-", "_").replace(" ", "_")
        return f"agent_{safe_name}"
    
    def collection_exists(self, agent_name: str) -> bool:
        """检查 Collection 是否存在"""
        collection_name = self.get_collection_name(agent_name)
        try:
            return utility.has_collection(collection_name, using=self.connection_alias)
        except Exception as e:
            print(f"⚠️ 检查 Collection 失败: {e}")
            return False
    
    def create_vector_store(self, agent_name: str) -> Milvus:
        """为智能体创建向量存储"""
        collection_name = self.get_collection_name(agent_name)
        
        print(f"🔨 创建向量存储: {collection_name}")
        
        # 构建连接参数 - 使用已建立的连接
        connection_args = {
            "alias": self.connection_alias,  # 使用已建立的连接
        }
        
        # LangChain Milvus 会自动创建 Collection
        vector_store = Milvus(
            embedding_function=self.embeddings,
            collection_name=collection_name,
            connection_args=connection_args,
            index_params={
                "metric_type": milvus_settings.metric_type,
                "index_type": milvus_settings.index_type,
                "params": {"nlist": milvus_settings.nlist}
            },
            drop_old=False  # 不删除旧数据
        )
        
        print(f"✅ 向量存储已创建: {collection_name}")
        return vector_store
    
    def get_vector_store(self, agent_name: str) -> Milvus:
        """获取现有的向量存储（不存在则创建）"""
        collection_name = self.get_collection_name(agent_name)
        
        # 构建连接参数 - 确保使用现有连接
        connection_args = {
            "alias": self.connection_alias,  # 使用已建立的连接
        }
        
        vector_store = Milvus(
            embedding_function=self.embeddings,
            collection_name=collection_name,
            connection_args=connection_args,
            index_params={
                "metric_type": milvus_settings.metric_type,
                "index_type": milvus_settings.index_type,
                "params": {"nlist": milvus_settings.nlist}
            },
            drop_old=False
        )
        
        return vector_store
    
    def delete_collection(self, agent_name: str) -> bool:
        """删除 Collection"""
        collection_name = self.get_collection_name(agent_name)
        try:
            if self.collection_exists(agent_name):
                utility.drop_collection(collection_name, using=self.connection_alias)
                print(f"✅ 已删除 Collection: {collection_name}")
                return True
            return False
        except Exception as e:
            print(f"❌ 删除 Collection 失败: {e}")
            return False
    
    def delete_by_file_id(self, agent_name: str, file_id: str) -> bool:
        """根据 file_id 删除向量"""
        collection_name = self.get_collection_name(agent_name)
        
        if not self.collection_exists(agent_name):
            print(f"⚠️ Collection 不存在: {collection_name}")
            return False
        
        try:
            collection = Collection(collection_name, using=self.connection_alias)
            collection.load()
            
            # 使用表达式删除：file_id == "xxx"
            expr = f'file_id == "{file_id}"'
            result = collection.delete(expr)
            collection.flush()
            
            print(f"✅ 已删除文件向量: {file_id}, 删除数量: {result.delete_count}")
            return True
        except Exception as e:
            print(f"❌ 删除向量失败: {e}")
            return False
    
    def get_collection_stats(self, agent_name: str) -> Dict:
        """获取 Collection 统计信息"""
        collection_name = self.get_collection_name(agent_name)
        
        if not self.collection_exists(agent_name):
            return {
                "collection_name": collection_name,
                "total_vectors": 0,
                "exists": False
            }
        
        try:
            collection = Collection(collection_name, using=self.connection_alias)
            # 刷新数据以确保统计准确
            collection.flush()
            collection.load()
            
            stats = {
                "collection_name": collection_name,
                "total_vectors": collection.num_entities,
                "exists": True
            }
            
            return stats
        except Exception as e:
            print(f"⚠️ 获取统计信息失败: {e}")
            return {
                "collection_name": collection_name,
                "total_vectors": 0,
                "exists": False,
                "error": str(e)
            }
    
    def search_similar(
        self, 
        agent_name: str, 
        query: str, 
        top_k: int = 3
    ) -> List[Dict]:
        """相似度搜索"""
        try:
            vector_store = self.get_vector_store(agent_name)
            results = vector_store.similarity_search_with_score(query, k=top_k)
            
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                }
                for doc, score in results
            ]
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return []


# 全局单例
_milvus_store: Optional[MilvusVectorStore] = None


def get_milvus_store() -> MilvusVectorStore:
    """获取 Milvus 存储单例"""
    global _milvus_store
    if _milvus_store is None:
        _milvus_store = MilvusVectorStore()
    return _milvus_store


# 测试连接
if __name__ == "__main__":
    store = get_milvus_store()
    print("✅ Milvus 服务测试成功")
