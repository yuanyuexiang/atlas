# 根路径 (ROOT_PATH) 配置说明

## 📖 概述

Atlas 应用配置了 **ROOT_PATH = "/atlas"**，这意味着应用部署在 `/atlas` 子路径下。

## 🌐 访问地址说明

### 生产环境
- **基础路径**: `https://atlas.matrix-net.tech/atlas`
- **API 端点**: `https://atlas.matrix-net.tech/atlas/api/*`
- **Swagger 文档**: `https://atlas.matrix-net.tech/atlas/docs`
- **ReDoc 文档**: `https://atlas.matrix-net.tech/atlas/redoc`
- **健康检查**: `https://atlas.matrix-net.tech/atlas/health`

### 本地开发
- **基础路径**: `http://localhost:8000/atlas`
- **API 端点**: `http://localhost:8000/atlas/api/*`
- **Swagger 文档**: `http://localhost:8000/atlas/docs`
- **ReDoc 文档**: `http://localhost:8000/atlas/redoc`
- **健康检查**: `http://localhost:8000/atlas/health`

## 🎯 为什么使用 ROOT_PATH？

### 优势
1. **反向代理友好**: 支持 Nginx、Traefik 等反向代理
2. **多应用部署**: 同一域名下可部署多个应用
   ```
   atlas.matrix-net.tech/atlas    → Atlas 后端
   atlas.matrix-net.tech/frontend → 前端应用
   atlas.matrix-net.tech/admin    → 管理后台
   ```
3. **路径隔离**: 避免与其他服务路径冲突
4. **OpenAPI 文档自适应**: Swagger/ReDoc 自动识别根路径

## 🔧 配置说明

### 后端配置
```python
# core/config.py
ROOT_PATH: str = "/atlas"  # 应用部署在 /atlas 路径下

# app.py
app = FastAPI(
    root_path=settings.ROOT_PATH  # 设置根路径
)
```

### Nginx 反向代理配置示例
```nginx
server {
    listen 80;
    server_name atlas.matrix-net.tech;

    # 代理 /atlas 路径到后端
    location /atlas/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 对于 SSE 流式响应
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }
}
```

## 📝 API 调用示例

### 用户登录
```bash
# 生产环境
curl -X POST "https://atlas.matrix-net.tech/atlas/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# 本地开发
curl -X POST "http://localhost:8000/atlas/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

### 获取智能体列表
```bash
# 生产环境
curl "https://atlas.matrix-net.tech/atlas/api/agents" \
  -H "Authorization: Bearer $TOKEN"

# 本地开发
curl "http://localhost:8000/atlas/api/agents" \
  -H "Authorization: Bearer $TOKEN"
```

## 🚀 前端集成

### axios 配置
```javascript
// 根据环境自动切换
const BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://atlas.matrix-net.tech/atlas/api'
  : 'http://localhost:8000/atlas/api';

const axiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

// 添加 token
axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### fetch 配置
```javascript
const BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://atlas.matrix-net.tech/atlas'
  : 'http://localhost:8000/atlas';

// 登录
const response = await fetch(`${BASE_URL}/api/auth/login`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ username, password })
});

// 获取数据
const response = await fetch(`${BASE_URL}/api/agents`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## ⚠️ 注意事项

1. **所有 API 请求都必须包含 `/atlas` 前缀**
   - ✅ 正确: `/atlas/api/agents`
   - ❌ 错误: `/api/agents`

2. **本地开发也需要使用 `/atlas` 前缀**
   - 保持开发和生产环境一致
   - 避免部署后出现路径问题

3. **WebSocket/SSE 连接**
   ```javascript
   // 流式对话
   const eventSource = new EventSource(
     `${BASE_URL}/api/chat/conversation-name/message/stream?message=你好`,
     {
       headers: {
         'Authorization': `Bearer ${token}`
       }
     }
   );
   ```

4. **文件上传**
   ```javascript
   const formData = new FormData();
   formData.append('file', file);
   
   await fetch(`${BASE_URL}/api/knowledge-base/agent-name/documents`, {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${token}`
     },
     body: formData
   });
   ```

## 🔄 如果需要修改根路径

如果需要修改根路径（不推荐，除非有特殊需求）：

1. 修改 `core/config.py`:
   ```python
   ROOT_PATH: str = "/new-path"  # 或 "" 表示根路径
   ```

2. 更新 Nginx 配置

3. 更新前端 API 基础路径

4. 更新所有文档中的示例

## 📚 相关文档

- [前端开发指南](FRONTEND_GUIDE.md) - 详细的 API 接口文档
- [部署指南](DEPLOYMENT.md) - Docker 和 Nginx 部署配置
- [使用指南](USAGE.md) - 完整的使用示例
- [认证说明](AUTHENTICATION.md) - JWT 认证流程
