"""
认证相关 API 路由
包括登录、注册、Token 刷新等
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.database import get_db
from config.auth import auth_settings
from api.schemas.auth import Token, UserLogin, UserCreate, UserResponse, UserUpdate
from application.auth_service import authenticate_user, create_access_token, get_current_user, get_current_superuser
from application.user_service import UserService
from domain.auth import User

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册
    
    - **username**: 用户名（3-50字符，只能包含字母、数字、下划线、连字符）
    - **email**: 邮箱
    - **password**: 密码（6-50字符）
    - **full_name**: 全名（可选）
    """
    try:
        user = UserService.create_user(db, user_create)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
    
    返回 JWT Access Token
    """
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 创建 Token
    access_token_expires = timedelta(minutes=auth_settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": auth_settings.access_token_expire_minutes * 60
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息
    
    需要认证
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    
    需要认证
    """
    updated_user = UserService.update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return updated_user


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    刷新 Token
    
    需要认证，返回新的 Access Token
    """
    access_token_expires = timedelta(minutes=auth_settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user.username, "user_id": current_user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": auth_settings.access_token_expire_minutes * 60
    }


@router.get("/debug/jwt-config")
async def debug_jwt_config():
    """
    调试端点：显示当前 JWT 配置（仅用于排查问题）
    生产环境应该移除此端点
    """
    import hashlib
    secret_hash = hashlib.md5(auth_settings.secret_key.encode()).hexdigest()
    
    return {
        "algorithm": auth_settings.algorithm,
        "access_token_expire_minutes": auth_settings.access_token_expire_minutes,
        "secret_key_md5": secret_hash,  # 只显示 hash，不暴露真实密钥
        "secret_key_length": len(auth_settings.secret_key),
        "message": "请对比本地和云上此值是否一致"
    }
