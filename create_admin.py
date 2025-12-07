#!/usr/bin/env python3
"""
创建默认管理员用户
"""
import sys
from sqlalchemy.orm import Session

from config.database import SessionLocal, init_db
from application.user_service import UserService
from domain.auth import User


def create_default_admin():
    """创建默认管理员"""
    init_db()
    
    db: Session = SessionLocal()
    try:
        # 检查是否已存在 admin 用户
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("⚠️  管理员用户已存在")
            print(f"   用户名: {existing_admin.username}")
            print(f"   邮箱: {existing_admin.email}")
            return
        
        # 创建默认管理员
        admin = UserService.create_superuser(
            db=db,
            username="admin",
            email="admin@example.com",
            password="admin123",  # 请在生产环境中修改
            full_name="系统管理员"
        )
        
        print("✅ 默认管理员创建成功！")
        print(f"   用户名: {admin.username}")
        print(f"   邮箱: {admin.email}")
        print(f"   密码: admin123")
        print("")
        print("⚠️  请立即修改默认密码！")
        
    except Exception as e:
        print(f"❌ 创建管理员失败: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_default_admin()
