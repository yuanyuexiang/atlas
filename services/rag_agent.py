"""
RAG Agent - 基于 Milvus 的智能问答代理
"""
import os
import json
import uuid
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from services.milvus_service import get_milvus_store

load_dotenv()


class RAGAgent:
    """基于 Milvus 的 RAG Agent"""
    
    def __init__(self, agent_name: str, system_prompt: str = None):
        """
        初始化 RAG Agent
        
        Args:
            agent_name: 智能体名称
            system_prompt: 系统提示词
        """
        self.agent_name = agent_name
        self.system_prompt = system_prompt or self._get_default_prompt()
        self.milvus_store = get_milvus_store()
        self.vector_store = None
        self.agent = None
        self.chat_history = []
        
        # 元数据路径
        self.metadata_dir = os.getenv("METADATA_DIR", "metadata_store")
        os.makedirs(self.metadata_dir, exist_ok=True)
        self.files_meta_path = os.path.join(self.metadata_dir, f"{agent_name}.json")
        
        # 初始化
        self._init_vector_store()
        self._create_agent()
    
    def _get_default_prompt(self) -> str:
        """获取默认系统提示词"""
        return (
            "你是一个智能助手，可以基于知识库回答用户的问题。\n"
            "重要规则:\n"
            "1. 使用检索到的知识库内容回答问题，准确引用相关信息\n"
            "2. 如果知识库中没有相关内容，诚实告知用户\n"
            "3. 使用清晰易懂的语言组织答案\n"
            "4. 对于相同的问题，始终给出一致的答案"
        )
    
    def _init_vector_store(self):
        """初始化向量存储"""
        self.vector_store = self.milvus_store.get_vector_store(self.agent_name)
        print(f"✅ 向量存储已就绪: {self.agent_name}")
    
    def _create_agent(self):
        """创建简化的 LLM（不使用 Agent 框架）"""
        # 创建 LLM
        self.llm = ChatOpenAI(
            temperature=0,
            max_tokens=1000,
            model=os.getenv("CHAT_MODEL", "gpt-3.5-turbo"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        print(f"✅ LLM 创建成功: {self.agent_name}")
    
    def ask(self, question: str) -> str:
        """
        向 Agent 提问
        
        Args:
            question: 用户问题
            
        Returns:
            str: Agent 回答
        """
        try:
            self.chat_history.append(HumanMessage(content=question))
            
            # 从知识库检索
            context = self._retrieve_for_agent(question)
            
            # 检查知识库是否为空
            if context == "未找到相关内容":
                # 检查知识库是否真的为空
                stats = self.milvus_store.get_collection_stats(self.agent_name)
                if stats and stats.get("total_vectors", 0) == 0:
                    # 知识库为空，返回友好提示
                    empty_kb_msg = "您好！我是智能客服助手。目前我的知识库还是空的，请管理员先上传相关文档，我才能更好地为您服务。"
                    self.chat_history.append(AIMessage(content=empty_kb_msg))
                    return empty_kb_msg
            
            # 构建 Prompt
            prompt_text = f"{self.system_prompt}\n\n知识库内容：\n{context}\n\n用户问题：{question}\n\n请基于知识库内容回答用户问题。"
            
            # 调用 LLM
            response = self.llm.invoke(prompt_text)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            self.chat_history.append(AIMessage(content=answer))
            return answer
            
        except Exception as e:
            print(f"❌ 处理错误: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f"抱歉，处理您的问题时出现了错误。"
            self.chat_history.append(AIMessage(content=error_msg))
            return error_msg
    
    async def ask_stream(self, question: str):
        """
        向 Agent 提问（流式响应）
        
        Args:
            question: 用户问题
            
        Yields:
            str: 逐块返回的回答内容
        """
        try:
            self.chat_history.append(HumanMessage(content=question))
            
            # 从知识库检索
            context = self._retrieve_for_agent(question)
            
            # 检查知识库是否为空
            if context == "未找到相关内容":
                # 检查知识库是否真的为空
                stats = self.milvus_store.get_collection_stats(self.agent_name)
                if stats and stats.get("total_vectors", 0) == 0:
                    # 知识库为空，返回友好提示
                    empty_kb_msg = "您好！我是智能客服助手。目前我的知识库还是空的，请管理员先上传相关文档，我才能更好地为您服务。"
                    self.chat_history.append(AIMessage(content=empty_kb_msg))
                    yield empty_kb_msg
                    return
            
            # 构建 Prompt
            prompt_text = f"{self.system_prompt}\n\n知识库内容：\n{context}\n\n用户问题：{question}\n\n请基于知识库内容回答用户问题。"
            
            # 流式调用 LLM
            full_response = ""
            async for chunk in self.llm.astream(prompt_text):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    full_response += content
                    yield content
            
            # 保存完整回答到历史
            self.chat_history.append(AIMessage(content=full_response))
            
        except Exception as e:
            print(f"❌ 流式处理错误: {e}")
            import traceback
            traceback.print_exc()
            error_msg = "抱歉，处理您的问题时出现了错误。"
            self.chat_history.append(AIMessage(content=error_msg))
            yield error_msg
    
    def _retrieve_for_agent(self, query: str) -> str:
        """Agent 内部使用的检索方法"""
        results = self.milvus_store.search_similar(self.agent_name, query, top_k=2)
        if not results:
            return "未找到相关内容"
        return "\n\n".join(r["content"] for r in results[:2])
    
    def add_document(self, file_path: str) -> dict:
        """
        添加文档到 Milvus
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 处理结果
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_id = str(uuid.uuid4())
            
            print(f"📄 处理文件: {filename}")
            
            # 加载文档
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file_path.endswith(('.txt', '.md')):
                loader = TextLoader(file_path, encoding='utf-8')
            else:
                raise ValueError(f"不支持的文件类型: {filename}")
            
            docs = loader.load()
            print(f"  加载了 {len(docs)} 个文档页")
            
            # 分割文本
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=200,
                add_start_index=True
            )
            splits = text_splitter.split_documents(docs)
            print(f"  分割为 {len(splits)} 个文本块")
            
            # 添加元数据
            for split in splits:
                split.metadata.update({
                    'file_id': file_id,
                    'filename': filename,
                    'agent_name': self.agent_name
                })
            
            # 批量添加到 Milvus
            batch_size = 50
            total_added = 0
            failed_batches = []
            
            for i in range(0, len(splits), batch_size):
                batch = splits[i:i + batch_size]
                try:
                    self.vector_store.add_documents(batch)
                    total_added += len(batch)
                    print(f"  进度: {total_added}/{len(splits)}")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  ⚠️ 批次 {i//batch_size + 1} 失败: {error_msg}")
                    failed_batches.append((i//batch_size + 1, error_msg))
            
            # 检查是否有向量成功添加
            if total_added == 0:
                error_details = "\n".join([f"批次{batch}: {err}" for batch, err in failed_batches])
                raise Exception(
                    f"向量化失败：所有文本块都未能添加到向量数据库。\n"
                    f"可能原因：\n"
                    f"1. Embedding API 配置错误或 API Key 无效\n"
                    f"2. 网络连接问题\n"
                    f"3. 向量数据库连接异常\n"
                    f"详细错误：\n{error_details}"
                )
            
            print(f"✅ 成功添加 {total_added}/{len(splits)} 个向量")
            if failed_batches:
                print(f"⚠️ 失败 {len(failed_batches)} 个批次")
            
            # 保存元数据
            files_meta = self._load_files_meta()
            files_meta.append({
                'id': file_id,
                'filename': filename,
                'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'file_size': file_size,
                'chunks_count': total_added,
                'file_type': file_path.split('.')[-1]
            })
            self._save_files_meta(files_meta)
            
            # 删除源文件
            try:
                os.remove(file_path)
                print(f"🗑️ 源文件已删除")
            except Exception as e:
                print(f"⚠️ 删除源文件失败: {e}")
            
            return {
                'file_id': file_id,
                'filename': filename,
                'chunks_count': total_added
            }
            
        except Exception as e:
            print(f"❌ 添加文档失败: {e}")
            raise
    
    def remove_document(self, file_id: str):
        """
        从 Milvus 删除文档
        
        Args:
            file_id: 文件ID
        """
        try:
            # Milvus 删除需要通过表达式
            # 注意：LangChain Milvus 可能不支持直接删除，需要重建或手动操作
            print(f"⚠️ Milvus 删除功能受限，建议重建知识库")
            
            # 更新元数据
            files_meta = self._load_files_meta()
            files_meta = [f for f in files_meta if f['id'] != file_id]
            self._save_files_meta(files_meta)
            
            print(f"✅ 已从元数据删除: {file_id}")
        except Exception as e:
            print(f"❌ 删除文档失败: {e}")
            raise
    
    def get_files_meta(self) -> List[dict]:
        """获取文件元数据"""
        return self._load_files_meta()
    
    def _load_files_meta(self) -> List[dict]:
        """加载元数据"""
        if os.path.exists(self.files_meta_path):
            try:
                with open(self.files_meta_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('files', [])
            except:
                return []
        return []
    
    def _save_files_meta(self, files: List[dict]):
        """保存元数据"""
        with open(self.files_meta_path, 'w', encoding='utf-8') as f:
            json.dump({'files': files}, f, ensure_ascii=False, indent=2)
    
    def clear_history(self):
        """清除对话历史"""
        self.chat_history = []
        print("🗑️ 对话历史已清除")
    
    def update_system_prompt(self, new_prompt: str):
        """更新系统提示词"""
        self.system_prompt = new_prompt
        self._create_agent()
        print(f"✅ 系统提示词已更新: {self.agent_name}")
    
    def get_system_prompt(self) -> str:
        """获取当前系统提示词"""
        return self.system_prompt
