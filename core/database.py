"""
SQLite 数据库配置
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:p0stgr3s@117.72.204.201:5432/atlas"
)

# PostgreSQL 连接池配置
engine_kwargs = {
    "echo": False,  # 生产环境关闭 SQL 日志
}

if "postgresql" in DATABASE_URL:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,  # 连接前测试有效性
        "pool_recycle": 3600,  # 1小时回收连接
    })
elif "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库表"""
    from models.entities import Base
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表已初始化")


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
