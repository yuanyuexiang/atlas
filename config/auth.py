"""
JWT 认证配置
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class AuthSettings(BaseSettings):
    """JWT 认证配置"""
    # JWT 配置
    secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 密码加密配置
    pwd_schemes: list = ["bcrypt"]
    pwd_deprecated: str = "auto"
    
    class Config:
        env_prefix = "JWT_"
        case_sensitive = False
        env_file = ".env"
        extra = "ignore"


def get_auth_settings() -> AuthSettings:
    """获取认证配置"""
    return AuthSettings()


auth_settings = get_auth_settings()
