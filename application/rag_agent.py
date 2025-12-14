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
from langchain.agents import AgentExecutor
from langchain_core.tools import tool
from langchain_core.tools import StructuredTool
from domain.processors.vector_store_manager import VectorStoreManager

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
        self.executor = None
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
        # 1. 创建 LLM（两个实例：一个流式用于Agent，一个非流式用于工具）
        llm_streaming = ChatOpenAI(
            temperature=0,
            max_tokens=1000,
            model=os.getenv("CHAT_MODEL", "gpt-3.5-turbo"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            streaming=True  # 🔥 Agent 流式输出
        )
        
        llm_non_streaming = ChatOpenAI(
            temperature=0,
            max_tokens=1000,
            model=os.getenv("CHAT_MODEL", "gpt-3.5-turbo"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            streaming=False  # 工具内部调用，不使用流式
        )
        
        # 2. 使用 @tool 装饰器定义工具（LangChain v1.0+ 标准方式）
        agent_name = self.agent_name  # 闭包捕获
        vector_manager = self.vector_manager

        def rewrite_query(query: str) -> str:
            """改写用户问题为更适合检索的查询语句。
            
            将口语化问题转换为3条不同角度的关键词查询。
            
            Args:
                query: 原始用户问题
                
            Returns:
                改写后的3条检索查询（JSON数组格式）
            """
            print(f"\n🔧 [rewrite_query] 开始执行 - 原始问题: {query}")
            messages = [
                SystemMessage(content="你是查询改写专家，擅长将口语化问题转换为适合语义检索的关键词查询。"),
                HumanMessage(content=f"""请将用户问题改写成3条关键词丰富的检索query。
                
                要求：
                1. 每条query从不同角度表达相同的信息需求
                2. 使用同义词和相关术语扩展查询
                3. 返回JSON数组格式：["query1", "query2", "query3"]
                
                用户问题：{query}
                
                改写结果（JSON数组）：""")
            ]
            response = llm_non_streaming.invoke(messages)
            result = response.content.strip()
            print(f"✅ [rewrite_query] 执行完成 - 改写结果: {result}")
            return result
        
        def retrieve_context(queries: str) -> str:
            """从知识库检索与查询最相关的文档内容。
            
            使用多条改写后的查询进行检索，合并去重结果。
            
            Args:
                queries: 改写后的查询（JSON数组格式，如rewrite_query返回的结果）
                
            Returns:
                检索到的文档内容，包含相似度分数
            """
            print(f"\n🔧 [retrieve_context] 开始执行 - 收到查询: {queries}")
            import json
            
            # 解析查询列表
            try:
                query_list = json.loads(queries) if queries.startswith('[') else [queries]
            except:
                query_list = [queries]  # 如果解析失败，当作单个查询
            
            print(f"📋 [retrieve_context] 解析后的查询列表: {query_list}")
            
            # 使用多条查询检索，收集所有结果
            all_results = {}
            for query in query_list[:3]:  # 最多使用3条查询
                print(f"🔍 [retrieve_context] 正在检索: {query}")
                results = vector_manager.search_similar(agent_name, query, top_k=3)
                for result in results:
                    doc_id = result.get('metadata', {}).get('doc_id', result.get('content', '')[:50])
                    # 保留最高分数的结果（分数越高越相似）
                    if doc_id not in all_results or result.get('score', 0) > all_results[doc_id].get('score', 0):
                        all_results[doc_id] = result
            
            if not all_results:
                return "知识库中未找到相关内容"
            
            # 按相似度排序，取前3个
            sorted_results = sorted(all_results.values(), key=lambda x: x.get('score', 0), reverse=True)[:3]
            
            # 格式化返回结果
            formatted_results = []
            for i, result in enumerate(sorted_results, 1):
                score = result.get('score', 0)
                content = result.get('content', '')
                formatted_results.append(f"[文档{i}] (相似度: {score:.3f})\n{content}")
            
            result_text = "\n\n".join(formatted_results)
            print(f"✅ [retrieve_context] 执行完成 - 返回 {len(sorted_results)} 个文档")
            return result_text

        def verify_answer(content: str) -> str:
            """验证最终答案的准确性。
            
            检查答案是否有充分的文档证据支撑。
            注意：需要在生成答案时自己记录使用的文档内容。
            
            Args:
                content: 包含答案和文档的文本（格式：答案|||文档内容）
                
            Returns:
                验证结果：VERIFIED 或 UNVERIFIED + 问题说明
            """
            print(f"\n🔧 [verify_answer] 开始执行 - 收到内容长度: {len(content)} 字符")
            # 尝试分割答案和文档
            parts = content.split('|||')
            if len(parts) == 2:
                answer, context = parts[0].strip(), parts[1].strip()
            else:
                # 如果格式不对，直接返回无法验证
                return "VERIFIED（无文档上下文，跳过验证）"
            
            messages = [
                SystemMessage(content="你是事实核查专家，负责验证答案是否有充分的文档证据支撑。"),
                HumanMessage(content=f"""请检查答案是否有充分的文档证据支撑。
                
                【文档上下文】
                {context}
                
                【待验证的答案】
                {answer}
                
                【验证要求】
                1. 检查答案中的每个关键论点
                2. 确认是否都能在文档中找到依据
                3. 如果全部有证据支撑，返回：VERIFIED
                4. 如果有内容缺乏证据，返回：UNVERIFIED - [具体问题]
                
                验证结果：""")
            ]
            response = llm_non_streaming.invoke(messages)
            result = response.content.strip()
            print(f"✅ [verify_answer] 执行完成 - 验证结果: {result}")
            return result
        
        # 创建工具（清晰的描述和调用顺序）
        rewrite_query_tool = StructuredTool.from_function(
            func=rewrite_query,
            name="rewrite_query",
            description="【第1步-必须】改写用户问题为3条适合检索的关键词查询。返回JSON数组格式。必须最先调用此工具以提高检索召回率。"
        )
        
        retrieve_tool = StructuredTool.from_function(
            func=retrieve_context,
            name="retrieve_context",
            description="【第2步-必须】使用改写后的查询（JSON数组）从知识库检索文档。会自动合并多条查询的结果并去重。返回前3个最相关的文档片段及相似度分数。"
        )

        verify_answer_tool = StructuredTool.from_function(
            func=verify_answer,
            name="verify_answer",
            description="【第3步-可选】验证答案准确性。传入格式：'答案|||文档内容'。返回VERIFIED或UNVERIFIED+问题说明。仅用于重要事实验证。"
        )
        
        tools = [rewrite_query_tool, retrieve_tool, verify_answer_tool]
        
        # 增强系统提示词，指导 Agent 如何使用工具
        enhanced_system_prompt = f"""{self.system_prompt}
        
        【RAG工作流程 - 严格顺序执行】
        你必须按照以下步骤**顺序执行**，不可并行调用工具：
        
        1. **查询改写**（第1步-必须先执行）
           先调用 rewrite_query(用户问题)
           - 等待返回结果（JSON数组格式）
           - 例如：["关键词查询1", "关键词查询2", "关键词查询3"]
        
        2. **文档检索**（第2步-使用第1步的返回结果）
           使用第1步返回的JSON数组调用 retrieve_context(第1步的结果)
           - 必须等待rewrite_query完成后再调用
           - 传入的参数必须是rewrite_query的返回值
           - 返回前3个最相关文档及相似度分数
        
        3. **生成答案**（第3步-基于第2步的文档）
           基于retrieve_context返回的文档生成答案
           - 仅使用文档中的信息
           - 如果文档无关（相似度<0.5），告知"抱歉，知识库中暂无相关信息"
           - 自然引用，如"根据资料显示..."而非"文档1说..."
        
        4. **验证答案**（第4步-可选）
           如果涉及重要事实，调用 verify_answer("答案|||文档内容")
           - 检查答案是否有证据支撑
           - 如果UNVERIFIED，说明缺乏依据或需调整
        
        【关键规则】
        ⚠️ 禁止并行调用工具！必须等待前一个工具返回结果后再调用下一个
        ⚠️ retrieve_context的参数必须是rewrite_query的返回值，不可自己编造
        - 严格基于文档回答，不编造信息
        - 找不到内容就明确告知，不要臆测
        - 引用要自然流畅，避免生硬的标注"""
        
        # 3. 使用 create_agent（LangChain v1.0+ 官方推荐 API）
        agent = create_agent(
            model=llm_streaming,
            tools=tools,
            system_prompt=enhanced_system_prompt,
        )
        print(f"✅ LangChain v1.0+ Agent 创建成功 (create_agent): {self.agent_name}")

        # 4. 创建 AgentExecutor 封装执行逻辑
        self.executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=5  # 可根据需要调整
        )
        print(f"✅ AgentExecutor 已创建完成: {self.agent_name}")
    
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
            
            # 使用 AgentExecutor 执行
            result = self.executor.invoke({"input": "", "messages": messages})
            
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
            
            # AgentExecutor 流式响应（使用 astream_events 获取真正的 token 级流式输出）
            full_response = ""
            
            async for event in self.executor.astream_events(
                {"input": "", "messages": messages},
                version="v2"  # 使用 v2 版本获取更细粒度的事件
            ):
                kind = event.get("event")
                
                # 只处理 LLM 的流式 token 输出
                if kind == "on_chat_model_stream":
                    chunk_content = event.get("data", {}).get("chunk")
                    if chunk_content and hasattr(chunk_content, "content"):
                        token = chunk_content.content
                        if token:
                            full_response += token
                            yield token
                
                # 打印工具调用日志（不输出给用户）
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    print(f"🔧 Agent 正在使用工具: {tool_name}")
            
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

