# 后端接口变更说明

## ✅ 无需前端修改的变更

以下修复**不影响接口契约**，前端无需修改：

### 1. 列表接口返回格式 ✅
**变更**: 从分页对象改为直接返回数组
- **之前**: `{total: 10, agents: [...]}`
- **现在**: `[...]`
- **前端影响**: 如果前端之前已经能处理数组格式，无需修改
- **兼容性**: ✅ 向下兼容（更简单）

### 2. 文件上传功能 ✅
**变更**: 修复了向量化失败问题
- **接口路径**: `POST /knowledge-base/{agent_name}/documents`
- **请求参数**: 无变化，仍然是 `multipart/form-data`，字段名 `file`
- **响应格式**: 无变化
```json
{
  "file_id": "uuid",
  "filename": "文件名.txt",
  "chunks_count": 1,
  "upload_time": ""
}
```
- **前端影响**: ✅ 无需修改

### 3. 空知识库友好提示 ✅
**变更**: 优化了空知识库时的响应内容
- **接口路径**: `POST /chat/{conversation_name}/message`
- **请求/响应格式**: 无变化
- **响应内容变化**: 
  - 之前: `"抱歉，处理您的问题时出现了错误。"`
  - 现在: `"您好！我是智能客服助手。目前我的知识库还是空的，请管理员先上传相关文档，我才能更好地为您服务。"`
- **前端影响**: ✅ 无需修改（只是文本内容更友好）

### 4. 健康检查端点 ✅
**变更**: 端点一直存在
- **接口路径**: `GET /atlas/health`
- **前端影响**: ✅ 无需修改

---

## ⚠️ 需要前端确认的变更

### 1. 客服更新接口新增可选字段

**接口**: `PUT /conversations/{conversation_name}`

**新增字段**:
```typescript
{
  display_name?: string;
  avatar?: string;
  agent_name?: string;  // 🆕 新增：支持更新关联的智能体
  status?: string;
  welcome_message?: string;
  description?: string;
}
```

**说明**:
- 新增 `agent_name` 字段用于更新客服关联的智能体
- 如果不传此字段，保留原有关联
- 支持传入智能体的 `name` 或 `id` (UUID)

**前端是否需要修改**:
- ✅ 如果前端需要支持"更换客服关联的智能体"功能，需要添加此字段
- ✅ 如果前端只修改其他字段（display_name等），无需修改（向后兼容）

**示例**:
```javascript
// 只修改显示名称（无需修改）
PUT /conversations/conv-001
{
  "display_name": "新的客服名称"
}

// 同时更换智能体（如需要此功能）
PUT /conversations/conv-001
{
  "display_name": "新的客服名称",
  "agent_name": "agent-002"  // 🆕
}
```

---

## 📋 完整接口对照表

### 智能体管理
| 接口 | 方法 | 变更 | 前端影响 |
|------|------|------|----------|
| `/agents` | GET | ✅ 返回数组而非对象 | 无需修改 |
| `/agents` | POST | 无变化 | 无需修改 |
| `/agents/{id}` | GET | 无变化 | 无需修改 |
| `/agents/{id}` | PUT | 无变化 | 无需修改 |
| `/agents/{id}` | DELETE | 无变化 | 无需修改 |

### 客服管理
| 接口 | 方法 | 变更 | 前端影响 |
|------|------|------|----------|
| `/conversations` | GET | ✅ 返回数组而非对象 | 无需修改 |
| `/conversations` | POST | 无变化 | 无需修改 |
| `/conversations/{id}` | GET | 无变化 | 无需修改 |
| `/conversations/{id}` | PUT | ⚠️ 新增 `agent_name` 字段 | 可选修改 |
| `/conversations/{id}` | DELETE | 无变化 | 无需修改 |

### 知识库管理
| 接口 | 方法 | 变更 | 前端影响 |
|------|------|------|----------|
| `/knowledge-base/{agent}/documents` | POST | ✅ 修复向量化 | 无需修改 |
| `/knowledge-base/{agent}/documents` | GET | 无变化 | 无需修改 |
| `/knowledge-base/{agent}/stats` | GET | ✅ 统计更准确 | 无需修改 |

### 对话接口
| 接口 | 方法 | 变更 | 前端影响 |
|------|------|------|----------|
| `/chat/{conv}/message` | POST | ✅ 优化空KB提示 | 无需修改 |
| `/chat/{conv}/message/stream` | POST | ✅ 优化空KB提示 | 无需修改 |

---

## 🎯 前端修改建议

### 必须修改 ❌
**无**

### 建议修改 ⚠️
1. **客服编辑页面** - 如果需要支持更换智能体功能：
   ```typescript
   // 添加智能体选择器
   interface ConversationUpdateForm {
     display_name?: string;
     agent_name?: string;  // 新增
     // ... 其他字段
   }
   ```

2. **列表接口处理** - 如果之前处理了分页对象：
   ```typescript
   // 之前（如果是这样）
   const { agents, total } = response.data;
   
   // 现在
   const agents = response.data;  // 直接是数组
   ```

### 无需修改 ✅
- 文件上传功能
- 对话接口
- 其他所有 CRUD 接口

---

## 📞 联系方式

如有疑问，请检查：
1. 在线 API 文档: `https://atlas.matrix-net.tech/atlas/docs`
2. OpenAPI Schema: `https://atlas.matrix-net.tech/atlas/openapi.json`
