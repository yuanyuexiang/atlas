# API UUID 迁移指南

> **重要更新（2025-11-28）**：所有实体的 CRUD 接口已统一改为使用 UUID 作为路径参数，不再支持 name 查询。

## 📋 变更概述

为了提高 API 的 RESTful 规范性和安全性，我们将所有实体的增删改查接口统一改为使用 UUID 作为路径参数。

### 变更原则

- ✅ **统一使用 UUID**：所有路径参数改为实体的 `id` 字段（UUID）
- ❌ **不再支持 name**：路径参数不再接受 `name` 字段
- ✅ **保持响应格式**：响应数据结构保持不变
- ✅ **新增 id 字段**：所有响应中同时包含 `id` 和 `name` 字段

---

## 🔄 接口变更清单

### 1. Agent（智能体）接口

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `GET /agents/{agent_name}` | `GET /agents/{agent_id}` | 获取详情，使用 UUID |
| `PUT /agents/{agent_name}` | `PUT /agents/{agent_id}` | 更新，使用 UUID |
| `DELETE /agents/{agent_name}` | `DELETE /agents/{agent_id}` | 删除，使用 UUID |
| `POST /agents/{agent_name}/activate` | `POST /agents/{agent_id}/activate` | 激活，使用 UUID |
| `POST /agents/{agent_name}/deactivate` | `POST /agents/{agent_id}/deactivate` | 停用，使用 UUID |

### 2. Knowledge Base（知识库）接口

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `POST /knowledge-base/{agent_name}/documents` | `POST /knowledge-base/{agent_id}/documents` | 上传文档，使用 agent UUID |
| `GET /knowledge-base/{agent_name}/documents` | `GET /knowledge-base/{agent_id}/documents` | 文档列表，使用 agent UUID |
| `DELETE /knowledge-base/{agent_name}/documents/{file_id}` | `DELETE /knowledge-base/{agent_id}/documents/{file_id}` | 删除文档，agent 和 file 都用 UUID |
| `GET /knowledge-base/{agent_name}/stats` | `GET /knowledge-base/{agent_id}/stats` | 统计信息，使用 agent UUID |
| `DELETE /knowledge-base/{agent_name}/clear` | `DELETE /knowledge-base/{agent_id}/clear` | 清空知识库，使用 agent UUID |
| `POST /knowledge-base/{agent_name}/rebuild` | `POST /knowledge-base/{agent_id}/rebuild` | 重建索引，使用 agent UUID |

### 3. Conversation（客服）接口

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `GET /conversations/{conversation_name}` | `GET /conversations/{conversation_id}` | 获取详情，使用 UUID |
| `PUT /conversations/{conversation_name}` | `PUT /conversations/{conversation_id}` | 更新，使用 UUID |
| `DELETE /conversations/{conversation_name}` | `DELETE /conversations/{conversation_id}` | 删除，使用 UUID |
| `POST /conversations/{conversation_name}/switch-agent` | `POST /conversations/{conversation_id}/switch-agent` | 切换智能体，使用 UUID |
| `GET /conversations/{conversation_name}/agent-history` | `GET /conversations/{conversation_id}/agent-history` | 切换历史，使用 UUID |
| `POST /conversations/{conversation_name}/online` | `POST /conversations/{conversation_id}/online` | 上线，使用 UUID |
| `POST /conversations/{conversation_name}/offline` | `POST /conversations/{conversation_id}/offline` | 下线，使用 UUID |

### 4. Chat（对话）接口

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `POST /chat/{conversation_name}/message` | `POST /chat/{conversation_id}/message` | 发送消息，使用 conversation UUID |
| `POST /chat/{conversation_name}/message/stream` | `POST /chat/{conversation_id}/message/stream` | 流式消息，使用 conversation UUID |
| `DELETE /chat/{conversation_name}/history` | `DELETE /chat/{conversation_id}/history` | 清空历史，使用 conversation UUID |
| `GET /chat/{conversation_name}/info` | `GET /chat/{conversation_id}/info` | 对话信息，使用 conversation UUID |

---

## 💡 前端适配指南

### 步骤 1：获取列表时保存 ID

之前可能只保存了 `name`，现在需要同时保存 `id`：

```javascript
// ❌ 旧代码：只保存 name
const agents = await fetchAgents();
const agentName = agents[0].name;  // "customer-service"

// ✅ 新代码：保存 id
const agents = await fetchAgents();
const agentId = agents[0].id;  // "9fea81da-5854-48f4-9d4f-ca0134f113cf"
const agentName = agents[0].name;  // "customer-service" (仅用于显示)
```

### 步骤 2：更新 API 调用

将所有使用 `name` 的 API 调用改为使用 `id`：

```javascript
// ❌ 旧代码
await fetch(`/api/agents/${agentName}`)
await fetch(`/api/knowledge-base/${agentName}/documents`)
await fetch(`/api/conversations/${conversationName}/message`)

// ✅ 新代码
await fetch(`/api/agents/${agentId}`)
await fetch(`/api/knowledge-base/${agentId}/documents`)
await fetch(`/api/conversations/${conversationId}/message`)
```

### 步骤 3：检查所有 CRUD 操作

重点检查以下场景：

1. **详情页面**：通过 URL 参数获取实体详情
2. **编辑操作**：更新实体信息
3. **删除操作**：删除实体
4. **关联操作**：上传文档、发送消息等

### 步骤 4：更新路由配置

如果使用前端路由，更新路由参数：

```javascript
// ❌ 旧路由
{
  path: '/agents/:agentName',
  component: AgentDetail
}

// ✅ 新路由
{
  path: '/agents/:agentId',
  component: AgentDetail
}
```

---

## 📝 代码示例

### 完整的 Agent 管理示例

```javascript
class AgentManager {
  constructor(baseURL, token) {
    this.baseURL = baseURL;
    this.token = token;
  }

  // 获取列表
  async listAgents() {
    const response = await fetch(`${this.baseURL}/agents`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return await response.json();  // 返回数组，每项包含 id 和 name
  }

  // 获取详情（使用 UUID）
  async getAgent(agentId) {
    const response = await fetch(`${this.baseURL}/agents/${agentId}`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return await response.json();
  }

  // 更新（使用 UUID）
  async updateAgent(agentId, data) {
    const response = await fetch(`${this.baseURL}/agents/${agentId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    return await response.json();
  }

  // 删除（使用 UUID）
  async deleteAgent(agentId) {
    const response = await fetch(`${this.baseURL}/agents/${agentId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return await response.json();
  }

  // 上传文档（agent 使用 UUID，file 使用 UUID）
  async uploadDocument(agentId, file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `${this.baseURL}/knowledge-base/${agentId}/documents`,
      {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.token}` },
        body: formData
      }
    );
    return await response.json();
  }

  // 删除文档（agent 和 file 都使用 UUID）
  async deleteDocument(agentId, fileId) {
    const response = await fetch(
      `${this.baseURL}/knowledge-base/${agentId}/documents/${fileId}`,
      {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );
    return await response.json();
  }
}

// 使用示例
const manager = new AgentManager('https://atlas.matrix-net.tech/atlas/api', token);

// 1. 获取列表
const agents = await manager.listAgents();
console.log(agents[0].id);    // "9fea81da-5854-48f4-9d4f-ca0134f113cf"
console.log(agents[0].name);  // "customer-service"

// 2. 获取详情（使用 ID）
const agent = await manager.getAgent(agents[0].id);

// 3. 更新（使用 ID）
await manager.updateAgent(agents[0].id, {
  display_name: '新名称'
});

// 4. 删除（使用 ID）
await manager.deleteAgent(agents[0].id);
```

### Vue 3 组合式 API 示例

```vue
<script setup>
import { ref, onMounted } from 'vue'

const agents = ref([])
const selectedAgentId = ref(null)
const selectedAgent = ref(null)

// 获取列表
onMounted(async () => {
  const response = await fetch('/api/agents', {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  agents.value = await response.json()
})

// 查看详情（使用 ID）
async function viewAgent(agentId) {
  selectedAgentId.value = agentId
  const response = await fetch(`/api/agents/${agentId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  selectedAgent.value = await response.json()
}

// 删除（使用 ID）
async function deleteAgent(agentId) {
  await fetch(`/api/agents/${agentId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  })
  // 重新加载列表
  agents.value = agents.value.filter(a => a.id !== agentId)
}
</script>

<template>
  <div>
    <!-- 列表：显示 name，操作使用 id -->
    <div v-for="agent in agents" :key="agent.id">
      <span>{{ agent.name }}</span>
      <button @click="viewAgent(agent.id)">查看</button>
      <button @click="deleteAgent(agent.id)">删除</button>
    </div>

    <!-- 详情：使用 id 获取的数据 -->
    <div v-if="selectedAgent">
      <h2>{{ selectedAgent.display_name }}</h2>
      <p>ID: {{ selectedAgent.id }}</p>
      <p>Name: {{ selectedAgent.name }}</p>
    </div>
  </div>
</template>
```

---

## ⚠️ 常见问题

### Q1: 为什么要改成 UUID？

**A**: RESTful API 最佳实践：
- UUID 是唯一的主键，避免 name 重命名导致的问题
- URL 中使用 ID 更符合 REST 规范
- 提高安全性，不暴露实体的可读名称

### Q2: name 字段还能用吗？

**A**: 
- ✅ **响应中仍然包含** `name` 字段，用于显示
- ❌ **路径参数不再接受** `name`，只接受 `id` (UUID)
- ✅ **创建时仍需提供** `name`，但用于标识而非查询

### Q3: 如何获取实体的 UUID？

**A**: 
1. **从列表接口**：返回的数组中每个对象都包含 `id` 字段
2. **从创建接口**：创建成功后返回完整对象（包含 `id`）
3. **从详情接口**：返回对象中包含 `id` 字段

### Q4: 旧的 URL 还能用吗？

**A**: 
- ❌ 不能！使用 name 的旧 URL 会返回 404
- ✅ 必须更新为使用 UUID 的新 URL
- ⚠️ 建议清理前端缓存和本地存储

### Q5: 文档删除为什么传两个 UUID？

**A**: 
```
DELETE /knowledge-base/{agent_id}/documents/{file_id}
                         ^^^^^^^^              ^^^^^^^
                         智能体 UUID           文件 UUID
```
两个都是 UUID，分别标识智能体和文件。

---

## 🔧 调试技巧

### 1. 检查 API 响应

```javascript
// 确认响应中包含 id 字段
const agents = await fetchAgents();
console.log(agents[0]);
// 输出：{ id: "uuid", name: "customer-service", ... }
```

### 2. 检查请求 URL

```javascript
// 确认 URL 中使用的是 UUID
console.log(`/api/agents/${agentId}`);
// 应该是：/api/agents/9fea81da-5854-48f4-9d4f-ca0134f113cf
// 而不是：/api/agents/customer-service
```

### 3. 检查错误信息

```javascript
// 404 错误通常意味着使用了 name 而不是 UUID
fetch(`/api/agents/customer-service`)  // ❌ 404
fetch(`/api/agents/${agentId}`)        // ✅ 200
```

---

## 📊 影响范围总结

- ✅ **Agent 接口**：6 个路径变更
- ✅ **Knowledge Base 接口**：6 个路径变更
- ✅ **Conversation 接口**：8 个路径变更
- ✅ **Chat 接口**：4 个路径变更
- **总计**：24 个 API 接口需要前端适配

---

## ✅ 检查清单

前端开发完成以下检查后，可确认迁移完成：

- [ ] 所有列表页面保存实体的 `id` 字段
- [ ] 所有详情页面使用 `id` 获取数据
- [ ] 所有更新操作使用 `id`
- [ ] 所有删除操作使用 `id`
- [ ] 所有关联操作（上传文档、发送消息）使用 `id`
- [ ] 前端路由参数从 `name` 改为 `id`
- [ ] 清理浏览器缓存和 localStorage
- [ ] 测试所有 CRUD 操作正常工作

---

**文档版本**: v1.0.0  
**更新日期**: 2025-11-28  
**适用后端版本**: v0.3.0+
