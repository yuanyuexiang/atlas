"""
FastAPI 主应用
Echo 智能客服后端系统
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import settings
from core.database import init_db
from api import agents, conversations, knowledge_base, chat, auth, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("🚀 正在启动 Echo 智能客服后端系统...")
    init_db()
    print("✅ 数据库已初始化")
    
    # 测试 Milvus 连接
    try:
        from services.milvus_service import get_milvus_store
        milvus_store = get_milvus_store()
        print("✅ Milvus 连接成功")
    except Exception as e:
        print(f"⚠️ Milvus 连接失败: {e}")
    
    yield
    
    # 关闭时清理
    print("👋 正在关闭系统...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="""
    ## Echo 智能客服后端系统
    
    基于 FastAPI + Milvus + LangChain 构建的智能客服 API
    
    ### 核心功能
    
    - 🤖 **智能体管理**: 创建和管理多个 AI 智能体
    - 💬 **客服管理**: 客服与智能体解耦，支持动态切换
    - 📚 **知识库管理**: 上传文档，自动向量化存储到 Milvus
    - 💭 **智能对话**: 基于知识库的智能问答
    
    ### 架构特点
    
    - **前后端分离**: RESTful API 设计
    - **客服-智能体解耦**: 多客服可共享一个智能体
    - **知识库隔离**: 每个智能体独立的向量数据库
    - **动态切换**: 支持客服切换不同智能体（白班/夜班）
    
    ### 技术栈
    
    - FastAPI: Web 框架
    - Milvus: 向量数据库
    - LangChain: RAG 框架
    - SQLite: 关系数据库
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(agents.router, prefix=settings.API_PREFIX)
app.include_router(conversations.router, prefix=settings.API_PREFIX)
app.include_router(knowledge_base.router, prefix=settings.API_PREFIX)
app.include_router(chat.router, prefix=settings.API_PREFIX)


@app.get("/", tags=["系统"])
async def root():
    """根路径 - 系统信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    try:
        # 检查 Milvus 连接
        from services.milvus_service import get_milvus_store
        milvus_store = get_milvus_store()
        
        return {
            "status": "healthy",
            "milvus": "connected",
            "version": settings.VERSION
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "milvus": "disconnected",
            "error": str(e)
        }


@app.get(f"{settings.API_PREFIX}/info", tags=["系统"])
async def api_info():
    """API 信息"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "api_prefix": settings.API_PREFIX,
        "endpoints": {
            "auth": f"{settings.API_PREFIX}/auth",
            "users": f"{settings.API_PREFIX}/users",
            "agents": f"{settings.API_PREFIX}/agents",
            "conversations": f"{settings.API_PREFIX}/conversations",
            "knowledge_base": f"{settings.API_PREFIX}/knowledge-base",
            "chat": f"{settings.API_PREFIX}/chat"
        },
        "features": {
            "authentication": "JWT",
            "vector_db": "Milvus",
            "rag_framework": "LangChain",
            "web_framework": "FastAPI"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
