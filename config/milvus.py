"""
Milvus 向量数据库配置
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class MilvusSettings(BaseSettings):
    """Milvus 配置"""
    host: str = "117.72.204.201"
    port: int = 19530
    user: Optional[str] = None
    password: Optional[str] = None
    db_name: str = "default"
    
    # Collection 配置
    index_type: str = "IVF_FLAT"
    metric_type: str = "L2"
    nlist: int = 128
    
    class Config:
        env_prefix = "MILVUS_"
        case_sensitive = False
        env_file = ".env"
        extra = "ignore"  # 忽略额外字段


def get_milvus_settings() -> MilvusSettings:
    """获取 Milvus 配置"""
    from config.settings import settings
    return MilvusSettings(
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
        user=os.getenv("MILVUS_USER"),
        password=os.getenv("MILVUS_PASSWORD"),
        db_name=os.getenv("MILVUS_DB_NAME", "default")
    )


milvus_settings = get_milvus_settings()
