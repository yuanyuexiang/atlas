"""
用户管理服务
提供用户 CRUD 操作
"""
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid

from domain.auth import User
from schemas.auth_schemas import UserCreate, UserUpdate
from application.auth_service import get_password_hash


class UserService:
    """用户管理服务"""
    
    @staticmethod
    def create_user(db: Session, user_create: UserCreate) -> User:
        """创建用户"""
        # 检查用户名是否存在
        existing_user = db.query(User).filter(User.username == user_create.username).first()
        if existing_user:
            raise ValueError(f"用户名已存在: {user_create.username}")
        
        # 检查邮箱是否存在
        existing_email = db.query(User).filter(User.email == user_create.email).first()
        if existing_email:
            raise ValueError(f"邮箱已存在: {user_create.email}")
        
        # 创建用户
        user = User(
            id=str(uuid.uuid4()),
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=get_password_hash(user_create.password),
            is_active=True,
            is_superuser=False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """通过 ID 获取用户"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """获取用户列表"""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_user(db: Session, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """更新用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        
        # 如果更新密码，需要加密
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def delete_user(db: Session, user_id: str) -> bool:
        """删除用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        
        return True
    
    @staticmethod
    def create_superuser(db: Session, username: str, email: str, password: str, full_name: str = None) -> User:
        """创建超级用户"""
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
