"""
全局配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """应用配置"""
    # 应用信息
    APP_NAME: str = "Echo 智能客服后端系统"
    VERSION: str = "0.2.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # API 配置
    API_PREFIX: str = "/api"
    
    # OpenAI 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-3.5-turbo")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # 文件配置
    UPLOAD_DIR: str = "uploads"
    METADATA_DIR: str = os.getenv("METADATA_DIR", "metadata_store")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".pdf", ".txt", ".md"]
    
    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:p0stgr3s@117.72.204.201:5432/atlas"
    )
    
    # Milvus 配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "117.72.204.201")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    
    # JWT 认证配置
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "your-secret-key-change-this-in-production"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    
    # CORS 配置
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
