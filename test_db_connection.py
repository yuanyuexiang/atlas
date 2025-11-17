#!/usr/bin/env python3
"""测试数据库连接"""
from core.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version()'))
        version = result.fetchone()[0]
        print("✅ PostgreSQL 连接成功!")
        print(f"版本: {version}")
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
