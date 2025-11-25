# 删除客服 500 错误修复报告

## 问题描述
删除客服时返回 500 Internal Server Error

### 错误信息
```
psycopg2.errors.ForeignKeyViolation: 
update or delete on table "conversations" violates foreign key constraint 
"agent_switch_logs_conversation_id_fkey" on table "agent_switch_logs"

DETAIL: Key (id)=(ec748184-fa99-455e-ad45-13f924df7298) is still referenced 
from table "agent_switch_logs".
```

## 根本原因
外键约束问题：
- `agent_switch_logs` 表通过 `conversation_id` 引用 `conversations` 表
- 外键没有设置级联删除（`ON DELETE CASCADE`）
- 当客服有切换日志时，删除操作违反外键约束

## 修复方案

### 1. 修改数据库模型
**文件**: `models/entities.py`

```python
# 修复前
conversation_id = Column(String(36), ForeignKey("conversations.id"))

# 修复后
conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"))
```

### 2. 更新删除逻辑
**文件**: `services/conversation_service.py`

```python
def delete_conversation(self, db: Session, conversation_name: str) -> dict:
    """删除客服 - 支持 name 或 id"""
    from models.entities import AgentSwitchLog
    
    # ... 查询客服 ...
    
    # 删除关联的切换日志
    db.query(AgentSwitchLog).filter(
        AgentSwitchLog.conversation_id == conversation.id
    ).delete()
    
    # 删除客服
    db.delete(conversation)
    db.commit()
```

### 3. 执行数据库迁移
**文件**: `migrate_cascade_delete.py`

```bash
.venv/bin/python migrate_cascade_delete.py
```

迁移内容：
1. 删除旧的外键约束
2. 添加新的外键约束（带 `ON DELETE CASCADE`）

## 测试验证

### 测试用例 1：删除有切换日志的客服
```bash
# 删除之前报错的客服
curl -X DELETE https://atlas.matrix-net.tech/atlas/api/conversations/ec748184-fa99-455e-ad45-13f924df7298 \
  -H "Authorization: Bearer ${TOKEN}"

# 结果
{
  "success": true,
  "message": "客服 ec748184-fa99-455e-ad45-13f924df7298 已删除"
}
```

✅ 成功！

### 测试用例 2：用 Name 删除
```bash
curl -X DELETE https://atlas.matrix-net.tech/atlas/api/conversations/test2 \
  -H "Authorization: Bearer ${TOKEN}"
```

✅ 成功！

### 测试用例 3：验证日志也被删除
删除客服后，相关的 `agent_switch_logs` 记录会自动删除（级联删除）。

## 修复效果

### 修复前
```
DELETE /conversations/{id}
→ 500 Internal Server Error
→ ForeignKeyViolation
```

### 修复后
```
DELETE /conversations/{id}
→ 200 OK
→ 客服及关联日志全部删除
```

## 涉及的数据表

### conversations（客服表）
- 主表，存储客服信息

### agent_switch_logs（切换日志表）
- 子表，通过 `conversation_id` 关联客服
- **修复**：外键添加 `ON DELETE CASCADE`
- **效果**：删除客服时自动删除相关日志

## 影响范围
- ✅ `DELETE /conversations/{id_or_name}` - 现在可以正常删除
- ✅ 级联删除相关的切换日志
- ✅ 同时支持 ID 和 Name 删除

## 数据完整性
删除客服时会自动清理：
1. ✅ 客服记录本身
2. ✅ 相关的智能体切换日志
3. ⚠️ **不会**删除关联的智能体（智能体可被多个客服共享）

## 安全性考虑
- ✅ 外键约束确保数据一致性
- ✅ 级联删除避免孤立记录
- ✅ 保留智能体记录（避免误删除）

## 部署说明

### 步骤 1：执行数据库迁移
```bash
cd /path/to/atlas
.venv/bin/python migrate_cascade_delete.py
```

### 步骤 2：重启服务
```bash
docker-compose restart atlas
```

### 步骤 3：验证修复
```bash
# 测试删除功能
curl -X DELETE https://atlas.matrix-net.tech/atlas/api/conversations/{id} \
  -H "Authorization: Bearer ${TOKEN}"
```

## 后续建议

### 1. 检查其他外键
建议检查所有外键约束，确保合理设置级联删除：

```sql
-- 查询所有外键约束
SELECT 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';
```

### 2. 添加删除保护
对于重要资源，可以添加软删除或删除确认：

```python
# 软删除示例
conversation.is_deleted = True
conversation.deleted_at = datetime.utcnow()
```

### 3. 添加删除日志
记录删除操作，便于追踪和恢复：

```python
# 删除前记录日志
audit_log = AuditLog(
    action="delete",
    resource="conversation",
    resource_id=conversation.id,
    user_id=current_user.id
)
```

## 相关问题

### Q: 为什么不删除关联的智能体？
A: 智能体可以被多个客服共享，删除客服不应影响智能体。

### Q: 如果想恢复删除的客服怎么办？
A: 建议实现软删除机制，而不是物理删除。

### Q: 级联删除会影响性能吗？
A: 对于大量关联数据可能有影响，但切换日志通常数量不大，影响可忽略。

---

**修复时间**: 2025-11-26  
**修复状态**: ✅ 已完成  
**测试状态**: ✅ 已验证
