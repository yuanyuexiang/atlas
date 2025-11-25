# 后端 API BUG 报告

## BUG 描述

**客服列表 API 和客服详情/更新 API 数据不一致**

列表接口返回了某些客服数据，但对这些客服进行详情查询或更新操作时返回 404 错误，提示"客服不存在"。

---

## 复现步骤

1. **调用列表接口**
   ```
   GET /conversations
   ```
   返回的数据中包含客服：
   ```json
   {
       "id": "71fa3861-fd46-4cfe-bb2e-deaaf2f317b7",
       "name": "test2",
       "display_name": "test2",
       "avatar": "🤖",
       "status": "online",
       "agent": {
           "id": "33e23e19-ec85-4d6b-960e-5a9ddbda4e8a",
           "name": "test2",
           "display_name": "test2",
           "agent_type": "general"
       },
       "welcome_message": "test2",
       "message_count": 0,
       "last_active_at": null,
       "created_at": "2025-11-21T08:48:18.865955"
   }
   ```

2. **尝试更新该客服**
   ```
   PUT /conversations/71fa3861-fd46-4cfe-bb2e-deaaf2f317b7
   Content-Type: application/json
   
   {
     "display_name": "新名称",
     "status": "online"
   }
   ```
   
3. **返回错误**
   ```
   Status: 404 Not Found
   
   {
     "detail": "客服不存在: 71fa3861-fd46-4cfe-bb2e-deaaf2f317b7"
   }
   ```

4. **再次调用列表接口**
   ```
   GET /conversations
   ```
   **依然返回这个客服**，数据未变化

---

## 实际表现

- ✅ `GET /conversations` - 返回该客服
- ❌ `GET /conversations/{id}` - 返回 404
- ❌ `PUT /conversations/{id}` - 返回 404  
- ❌ `DELETE /conversations/{id}` - 返回 404
- ❌ `POST /conversations/{id}/switch-agent` - 返回 404

---

## 影响范围

目前发现的受影响客服 ID：
- `71fa3861-fd46-4cfe-bb2e-deaaf2f317b7`

可能还有其他类似数据。

---

## 可能的原因

1. **数据库主从同步延迟**
   - 列表查询走的是从库，包含已删除的数据
   - 详情/更新查询走的是主库，数据已不存在

2. **软删除机制问题**
   - 列表接口未过滤软删除的数据
   - 详情/更新接口过滤了软删除的数据

3. **缓存不一致**
   - 列表接口有缓存，未及时更新
   - 详情/更新接口无缓存或缓存已失效

4. **数据库外键约束问题**
   - 关联的 agent 被删除，导致客服记录处于不一致状态

---

## 建议修复方案

### 方案 1：统一数据源（推荐）
确保列表接口和详情接口使用相同的数据源和查询逻辑，避免数据不一致。

### 方案 2：列表接口也过滤无效数据
在返回列表前，验证每条记录是否有效（关联的 agent 是否存在等）。

### 方案 3：数据库清理
定期清理数据库中的孤立记录和无效关联。

### 方案 4：接口容错
详情/更新接口在返回 404 时，同步检查并清理列表缓存。

---

## 临时前端处理

前端已实现临时解决方案：
- 当遇到 404 错误时，在前端内存中记录该客服 ID
- 在列表渲染时过滤掉这些无效 ID
- 避免用户看到"幽灵数据"

但这不是根本解决方案，**仍需后端修复数据一致性问题**。

---

## 测试建议

修复后请验证：
1. 列表接口返回的所有客服都能正常查询详情
2. 列表接口返回的所有客服都能正常更新
3. 删除客服后，列表接口不再返回该客服
4. 删除 agent 时，同步处理关联的客服（级联删除或更新）

---

## 联系人

前端开发者：[你的名字]
发现时间：2025-11-25
优先级：**高** - 影响核心 CRUD 功能

---

## 附录：完整 API 日志

### 1. 列表请求成功
```
GET https://atlas.matrix-net.tech/atlas/api/conversations
Status: 200 OK

返回 7 条记录，包含 ID "71fa3861-fd46-4cfe-bb2e-deaaf2f317b7"
```

### 2. 更新请求失败
```
PUT https://atlas.matrix-net.tech/atlas/api/conversations/71fa3861-fd46-4cfe-bb2e-deaaf2f317b7
Status: 404 Not Found

Response Body:
{
  "detail": "客服不存在: 71fa3861-fd46-4cfe-bb2e-deaaf2f317b7"
}
```

### 3. 再次列表请求
```
GET https://atlas.matrix-net.tech/atlas/api/conversations
Status: 200 OK

依然返回 7 条记录，包含相同的 ID
```
