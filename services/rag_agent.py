"""
RAG Agent - 基于 Milvus 的智能问答代理
使用 LangChain v1.0+ Agent 框架实现
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
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.tools import StructuredTool
from services.milvus_service import get_milvus_store

load_dotenv()


class RAGAgent:
    """基于 Milvus 的 RAG Agent"""
    
    def __init__(self, agent_name: str, system_prompt: str):
        """
        初始化 RAG Agent
        
        Args:
            agent_name: 智能体名称
            system_prompt: 系统提示词（必填）
        
        Raises:
            ValueError: 如果 system_prompt 为空
        """
        if not system_prompt or not system_prompt.strip():
            raise ValueError("system_prompt 不能为空，必须提供有效的系统提示词")
        
        self.agent_name = agent_name
        self.system_prompt = system_prompt.strip()
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
    
    def _init_vector_store(self):
        """初始化向量存储"""
        self.vector_store = self.milvus_store.get_vector_store(self.agent_name)
        print(f"✅ 向量存储已就绪: {self.agent_name}")
    
    def _create_agent(self):
        """使用 LangChain v1.0+ Agent 框架创建 Agent"""
        # 1. 创建 LLM
        model = ChatOpenAI(
            temperature=0,
            max_tokens=1000,
            model=os.getenv("CHAT_MODEL", "gpt-3.5-turbo"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 2. 使用 @tool 装饰器定义工具（LangChain v1.0+ 标准方式）
        agent_name = self.agent_name  # 闭包捕获
        milvus_store = self.milvus_store
        
        @tool
        def knowledge_base_search(query: str) -> str:
            """搜索智能体的知识库获取相关文档内容。
            
            这个工具的功能是查找原始资料，用于回答用户提出的**所有事实性问题**。
            
            **[通用检索指南]**：如果用户的查询需要**精确事实、特定身份、或跨上下文的定义**，你应该尝试使用包含**多个角度或同义词**的关键词进行搜索，以提高全面召回率。
            
            你需要阅读工具返回的所有原始文档，并提取关键信息，用自然的语言组织成最终答案。
            
            Args:
                query: 搜索查询（用户问题或关键词，请确保查询词能最大限度地覆盖知识库中的相关信息）
                
            Returns:
                原始文档内容（需要你进一步处理和总结）
            """
            results = milvus_store.search_similar(agent_name, query, top_k=3)
            if not results:
                return "知识库中未找到相关内容"
            
            # 简洁返回，不加任何"文档片段"标签
            return "\n\n".join(r['content'] for r in results[:3])


        # 定义检索工具
        def retrieve_context(query: str) -> str:
            """从知识库检索相关内容"""
            # 使用 similarity_search_with_score 获取分数,提高确定性
            results = self.vector_store.similarity_search_with_score(query, k=3)
            
            # 按分数排序(分数越低越相似)
            results_sorted = sorted(results, key=lambda x: x[1])
            
            # 只使用前2个最相关的结果
            retrieved_docs = [doc for doc, score in results_sorted[:2]]
            
            serialized = "\n\n".join(
                f"Content: {doc.page_content}"
                for doc in retrieved_docs
            )
            return serialized
        
        retrieve_tool = StructuredTool.from_function(
            func=retrieve_context,
            name="retrieve_context",
            description="根据用户问题,从知识库中检索相关内容。",
        )
        
        tools = [retrieve_tool]
        
        #tools = [knowledge_base_search]
        
        # 3. 使用 create_agent（LangChain v1.0+ 官方推荐 API）
        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=self.system_prompt,
        )
        
        print(f"✅ LangChain v1.0+ Agent 创建成功 (create_agent): {self.agent_name} and system_prompt ({self.system_prompt})")
    
    def ask(self, question: str) -> str:
        """
        向 Agent 提问（使用 LangChain v1.0+ create_agent）
        
        Args:
            question: 用户问题
            
        Returns:
            str: Agent 回答
        """
        try:
            # 检查知识库是否为空
            stats = self.milvus_store.get_collection_stats(self.agent_name)
            if stats and stats.get("total_vectors", 0) == 0:
                empty_kb_msg = "您好！我是智能客服助手。目前我的知识库还是空的，请管理员先上传相关文档，我才能更好地为您服务。"
                return empty_kb_msg
            
            # 构建消息历史（LangGraph State 格式）
            messages = []
            # 添加历史消息（保留最近10轮）
            messages.extend(self.chat_history[-10:])
            # 添加当前用户问题
            messages.append({"role": "user", "content": question})
            
            # 使用 Agent 执行（LangGraph API）
            result = self.agent.invoke({"messages": messages})
            
            # 提取最后一条 AI 消息
            final_messages = result.get("messages", [])
            if final_messages:
                answer = final_messages[-1].content
            else:
                answer = "抱歉，我无法回答这个问题。"
            
            # 更新对话历史（添加时间戳）
            import time
            timestamp = int(time.time())  # Unix 时间戳（秒）
            
            self.chat_history.append(HumanMessage(
                content=question,
                additional_kwargs={"timestamp": timestamp}
            ))
            self.chat_history.append(AIMessage(
                content=answer,
                additional_kwargs={"timestamp": timestamp}
            ))
            
            return answer
            
        except Exception as e:
            print(f"❌ Agent 处理错误: {e}")
            import traceback
            traceback.print_exc()
            return "抱歉，处理您的问题时出现了错误。"
    
    async def ask_stream(self, question: str):
        """
        向 Agent 提问（流式响应，LangChain v1.0+ create_agent）
        
        Args:
            question: 用户问题
            
        Yields:
            str: 逐块返回的回答内容
        """
        try:
            # 检查知识库是否为空
            stats = self.milvus_store.get_collection_stats(self.agent_name)
            if stats and stats.get("total_vectors", 0) == 0:
                empty_kb_msg = "您好！我是智能客服助手。目前我的知识库还是空的，请管理员先上传相关文档，我才能更好地为您服务。"
                yield empty_kb_msg
                return
            
            # 构建消息历史
            messages = []
            messages.extend(self.chat_history[-10:])
            messages.append({"role": "user", "content": question})
            
            # Agent 流式响应（LangGraph stream API）
            full_response = ""
            last_content_length = 0
            
            async for chunk in self.agent.astream(
                {"messages": messages},
                stream_mode="values"  # 流式输出状态值
            ):
                # 获取最新消息
                latest_messages = chunk.get("messages", [])
                if latest_messages:
                    latest_message = latest_messages[-1]
                    
                    # 如果是 AI 消息，流式输出内容
                    if hasattr(latest_message, "content") and latest_message.content:
                        content = latest_message.content
                        # 只输出新增的内容（增量输出）
                        if len(content) > last_content_length:
                            new_content = content[last_content_length:]
                            last_content_length = len(content)
                            full_response = content
                            yield new_content
                    
                    # 如果是工具调用，打印日志
                    elif hasattr(latest_message, "tool_calls") and latest_message.tool_calls:
                        for tc in latest_message.tool_calls:
                            print(f"🔧 Agent 正在使用工具: {tc.get('name', 'unknown')}")
            
            # 更新对话历史（添加时间戳）
            if full_response:
                import time
                timestamp = int(time.time())  # Unix 时间戳（秒）
                
                self.chat_history.append(HumanMessage(
                    content=question,
                    additional_kwargs={"timestamp": timestamp}
                ))
                self.chat_history.append(AIMessage(
                    content=full_response,
                    additional_kwargs={"timestamp": timestamp}
                ))
            
        except Exception as e:
            print(f"❌ Agent 流式处理错误: {e}")
            import traceback
            traceback.print_exc()
            yield "抱歉，处理您的问题时出现了错误。"
    
    def add_document(self, file_path: str) -> dict:
        """
        添加文档到 Milvus
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 处理结果
        """
        # 提前生成 file_id 和 filename，确保失败时也能记录
        file_id = str(uuid.uuid4())
        filename = os.path.basename(file_path) if file_path else "unknown"
        
        try:
            # 验证文件存在性
            if not os.path.exists(file_path):
                # 即使文件不存在，也先创建元数据条目，这样可以记录失败状态
                self._save_initial_metadata(file_id, filename, 0, file_path)
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 获取文件信息
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            print(f"📄 处理文件: {filename}")
            
            # 1️⃣ 立即保存初始元数据（status=processing）
            self._save_initial_metadata(file_id, filename, file_size, file_path)
            
            # 加载文档
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
                docs = loader.load()
            elif file_path.endswith(('.txt', '.md')):
                # 尝试多种编码加载文本文件
                docs = None
                encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
                
                for encoding in encodings:
                    try:
                        loader = TextLoader(file_path, encoding=encoding)
                        docs = loader.load()
                        print(f"  使用 {encoding} 编码加载成功")
                        break
                    except Exception as e:
                        continue
                
                if docs is None:
                    raise ValueError(f"无法加载文件，尝试了所有编码: {encodings}")
            else:
                raise ValueError(f"不支持的文件类型: {filename}")
            
            print(f"  加载了 {len(docs)} 个文档页")
            
            # 分割文本
            # 注意：Embedding API 限制每个文本 < 512 tokens
            # 对于中文，1个汉字约等于2个tokens，所以 chunk_size 设为 400 字符比较安全
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=120,
                add_start_index=True,
                separators=["\n\n", "\n", "。", "！", "？", "；", "，", " "]
            )
            splits = text_splitter.split_documents(docs)
            print(f"  分割为 {len(splits)} 个文本块")
            
            # 过滤和截断过长的文本块（Embedding API 限制 < 512 tokens）
            # 对于中文，粗略估计 1个汉字 ≈ 2 tokens，所以限制在 250 字符以内
            filtered_splits = []
            for split in splits:
                content = split.page_content
                if len(content) > 250:
                    # 截断过长的文本
                    split.page_content = content[:250] + "..."
                filtered_splits.append(split)
            
            print(f"  过滤后保留 {len(filtered_splits)} 个文本块")
            
            # 添加元数据
            for split in filtered_splits:
                split.metadata.update({
                    'file_id': file_id,
                    'filename': filename,
                    'agent_name': self.agent_name
                })
            
            # 批量添加到 Milvus
            # 注意：Embedding API 批次大小限制为 32
            batch_size = 32
            total_added = 0
            failed_batches = []
            
            for i in range(0, len(filtered_splits), batch_size):
                batch = filtered_splits[i:i + batch_size]
                try:
                    self.vector_store.add_documents(batch)
                    total_added += len(batch)
                    print(f"  进度: {total_added}/{len(filtered_splits)}")
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
            
            print(f"✅ 成功添加 {total_added}/{len(filtered_splits)} 个向量")
            if failed_batches:
                print(f"⚠️ 失败 {len(failed_batches)} 个批次")
            
            # 2️⃣ 更新状态为完成（ready）
            self._update_file_status(
                file_id=file_id,
                status='ready',
                processing_progress=100,
                chunks_count=total_added
            )
            
            # 删除源文件
            try:
                os.remove(file_path)
                print(f"🗑️ 源文件已删除")
            except Exception as e:
                print(f"⚠️ 删除源文件失败: {e}")
            
            return {
                'file_id': file_id,
                'filename': filename,
                'chunks_count': total_added,
                'status': 'ready',  # ✅ 新增
                'processing_progress': 100  # ✅ 新增
            }
            
        except Exception as e:
            print(f"❌ 添加文档失败: {e}")
            # 3️⃣ 失败时更新状态
            try:
                self._update_file_status(
                    file_id=file_id,
                    status='failed',
                    processing_progress=0,
                    error_message=str(e)
                )
            except:
                pass  # 如果元数据更新失败，不影响异常抛出
            raise
    
    def remove_document(self, file_id: str):
        """
        从 Milvus 删除文档（同时删除向量数据和元数据）
        
        Args:
            file_id: 文件ID
        """
        try:
            # 1. 先删除 Milvus 向量数据（关键：确保级联删除）
            delete_success = self.milvus_store.delete_by_file_id(self.agent_name, file_id)
            
            if not delete_success:
                print(f"⚠️ 向量数据删除失败或不存在: {file_id}")
            
            # 2. 再更新元数据
            files_meta = self._load_files_meta()
            original_count = len(files_meta)
            files_meta = [f for f in files_meta if f['id'] != file_id]
            
            if len(files_meta) == original_count:
                print(f"⚠️ 元数据中未找到文件: {file_id}")
            
            self._save_files_meta(files_meta)
            
            print(f"✅ 文档已完全删除: {file_id} (向量: {'是' if delete_success else '否'}, 元数据: {'是' if len(files_meta) < original_count else '否'})")
        except Exception as e:
            print(f"❌ 删除文档失败: {e}")
            import traceback
            traceback.print_exc()
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
    
    def _save_initial_metadata(self, file_id: str, filename: str, file_size: int, file_path: str):
        """保存初始文件元数据（status=processing）"""
        files_meta = self._load_files_meta()
        files_meta.append({
            'id': file_id,
            'filename': filename,
            'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file_size': file_size,
            'chunks_count': 0,
            'file_type': file_path.split('.')[-1],
            'status': 'processing',  # ✅ 初始状态
            'error_message': None,  # ✅ 新增
            'processing_progress': 0,  # ✅ 新增
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # ✅ 新增
        })
        self._save_files_meta(files_meta)
        print(f"📝 初始元数据已保存: {filename} (status=processing)")
    
    def _update_file_status(self, file_id: str, status: str, processing_progress: int,
                           chunks_count: int = None, error_message: str = None):
        """更新文件处理状态"""
        files_meta = self._load_files_meta()
        
        for file in files_meta:
            if file['id'] == file_id:
                file['status'] = status
                file['processing_progress'] = processing_progress
                file['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if chunks_count is not None:
                    file['chunks_count'] = chunks_count
                if error_message:
                    file['error_message'] = error_message
                
                self._save_files_meta(files_meta)
                print(f"📝 状态已更新: {file['filename']} -> {status} ({processing_progress}%)")
                return
        
        print(f"⚠️ 未找到文件元数据: {file_id}")
