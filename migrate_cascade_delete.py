"""
数据库迁移脚本 - 修复外键级联删除
修复问题：删除客服时报外键约束错误
"""

from sqlalchemy import create_engine, text
from core.config import settings

def migrate():
    """执行数据库迁移"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("开始数据库迁移...")
        
        try:
            # 1. 删除旧的外键约束
            print("1. 删除旧的外键约束...")
            conn.execute(text("""
                ALTER TABLE agent_switch_logs 
                DROP CONSTRAINT IF EXISTS agent_switch_logs_conversation_id_fkey;
            """))
            conn.commit()
            print("   ✅ 旧约束已删除")
            
            # 2. 添加新的外键约束（带级联删除）
            print("2. 添加新的外键约束（CASCADE）...")
            conn.execute(text("""
                ALTER TABLE agent_switch_logs 
                ADD CONSTRAINT agent_switch_logs_conversation_id_fkey 
                FOREIGN KEY (conversation_id) 
                REFERENCES conversations(id) 
                ON DELETE CASCADE;
            """))
            conn.commit()
            print("   ✅ 新约束已添加")
            
            print("\n✅ 数据库迁移完成！")
            print("\n修复内容：")
            print("  - agent_switch_logs.conversation_id 外键现在支持级联删除")
            print("  - 删除客服时会自动删除相关的切换日志")
            
        except Exception as e:
            print(f"\n❌ 迁移失败: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
