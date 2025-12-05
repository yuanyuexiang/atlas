"""
RAG Agent - 基于 Milvus 的智能问答代理
使用 LangChain v1.0+ Agent 框架实现
职责：对话管理、Agent 创建、对话历史维护
"""
import os
from typing import Optional, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.tools import StructuredTool
from services.vector_store_manager import VectorStoreManager

load_dotenv()


class RAGAgent:
    """基于 Milvus 的 RAG Agent - 纯对话逻辑"""
    
    def __init__(
        self, 
        agent_name: str, 
        system_prompt: str,
        vector_manager: VectorStoreManager
    ):
        """
        初始化 RAG Agent
        
        Args:
            agent_name: 智能体名称
            system_prompt: 系统提示词（必填）
            vector_manager: 向量存储管理器（依赖注入）
        
        Raises:
            ValueError: 如果 system_prompt 为空
        """
        if not system_prompt or not system_prompt.strip():
            raise ValueError("system_prompt 不能为空，必须提供有效的系统提示词")
        
        self.agent_name = agent_name
        self.system_prompt = system_prompt.strip()
        self.vector_manager = vector_manager
        self.vector_store = None
        self.agent = None
        self.chat_history = []
        
        # 初始化
        self._init_vector_store()
        self._create_agent()
    
    def _init_vector_store(self):
        """初始化向量存储"""
        self.vector_store = self.vector_manager.get_vector_store(self.agent_name)
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
        vector_manager = self.vector_manager
        
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
            results = vector_manager.search_similar(agent_name, query, top_k=3)
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
            stats = self.vector_manager.get_statistics(self.agent_name)
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
            stats = self.vector_manager.get_statistics(self.agent_name)
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
    
    def clear_history(self):
        """清除对话历史"""
        self.chat_history = []
        print("🗑️ 对话历史已清除")
    
    def update_system_prompt(self, new_prompt: str):
        """更新系统提示词"""
        if not new_prompt or not new_prompt.strip():
            raise ValueError("system_prompt 不能为空")
        self.system_prompt = new_prompt.strip()
        self._create_agent()
        print(f"✅ 系统提示词已更新: {self.agent_name}")
    
    def get_system_prompt(self) -> str:
        """获取当前系统提示词"""
        return self.system_prompt

