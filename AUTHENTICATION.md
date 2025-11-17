# API 认证使用指南

## 🔐 认证概述

Echo 智能客服系统现已启用 **JWT（JSON Web Token）认证保护**，所有主要 API 端点都需要有效的身份验证令牌才能访问。

## 📋 认证状态

### 受保护的端点（需要认证）
- ✅ `/api/agents/*` - 智能体管理
- ✅ `/api/conversations/*` - 客服管理  
- ✅ `/api/knowledge-base/*` - 知识库管理
- ✅ `/api/chat/*` - 对话接口
- ✅ `/api/users/*` - 用户管理（**仅管理员**）

### 公开端点（无需认证）
- 🌐 `/health` - 健康检查
- 🌐 `/api/auth/register` - 用户注册
- 🌐 `/api/auth/login` - 用户登录
- 📖 `/docs` - API 文档（Swagger UI）

## 🚀 快速开始

### 1. 用户注册

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "email": "user@example.com",
    "password": "mypassword123",
    "full_name": "我的名字"
  }'
```

**响应示例**：
```json
{
  "username": "myuser",
  "email": "user@example.com",
  "full_name": "我的名字",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-11-17T08:00:00"
}
```

### 2. 用户登录（获取 Token）

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "password": "mypassword123"
  }'
```

**响应示例**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

⏱️ **Token 有效期**：30 分钟（1800 秒）

### 3. 使用 Token 访问受保护的 API

**重要**：在请求头中添加 `Authorization: Bearer <token>`

```bash
# 保存 Token 到变量
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 访问智能体列表
curl "http://localhost:8000/api/agents" \
  -H "Authorization: Bearer $TOKEN"

# 创建智能体
curl -X POST "http://localhost:8000/api/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-agent",
    "display_name": "我的智能体",
    "agent_type": "general"
  }'
```

### 4. 刷新 Token

```bash
curl -X POST "http://localhost:8000/api/auth/refresh" \
  -H "Authorization: Bearer $TOKEN"
```

## 👤 默认账户

系统已预置一个管理员账户：

```
用户名: admin
密码: admin123
```

⚠️ **重要**：首次使用后请立即修改默认密码！

## 🔑 修改密码

```bash
curl -X PUT "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "new_secure_password_123"
  }'
```

## 👥 用户权限

### 普通用户
- ✅ 查看和管理智能体
- ✅ 查看和管理客服
- ✅ 上传和管理知识库
- ✅ 发送对话消息
- ✅ 查看和更新自己的资料
- ❌ **无法**访问用户管理端点

### 管理员用户
- ✅ 拥有普通用户的所有权限
- ✅ 查看所有用户列表
- ✅ 创建新用户
- ✅ 更新用户信息
- ✅ 删除用户
- ✅ 升级用户为管理员

## 🛠️ 管理员操作示例

### 查看所有用户

```bash
curl "http://localhost:8000/api/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 创建新用户

```bash
curl -X POST "http://localhost:8000/api/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "new@example.com",
    "password": "password123",
    "is_superuser": false
  }'
```

### 升级用户为管理员

```bash
curl -X PUT "http://localhost:8000/api/users/{user_id}" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_superuser": true
  }'
```

## 🧪 测试认证功能

运行提供的测试脚本：

```bash
# 测试认证功能
./test_auth.sh

# 测试受保护的 API
./test_protected_apis.sh
```

## ⚠️ 错误处理

### 401 Unauthorized
**原因**：Token 无效、已过期或格式错误

**解决**：重新登录获取新 Token

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
**原因1**：未提供 Token

**解决**：在请求头添加 `Authorization: Bearer <token>`

```json
{
  "detail": "Not authenticated"
}
```

**原因2**：权限不足（普通用户访问管理员端点）

**解决**：使用管理员账户或联系管理员升级权限

```json
{
  "detail": "需要管理员权限"
}
```

## 🔒 安全建议

1. **生产环境**：修改 `.env` 文件中的 `JWT_SECRET_KEY`
   ```bash
   # 生成强随机密钥
   openssl rand -hex 32
   ```

2. **密码强度**：使用至少 8 位包含字母数字的密码

3. **定期更换**：定期修改管理员密码

4. **Token 管理**：
   - 不要在客户端存储明文 Token
   - Token 过期后立即重新登录
   - 退出登录时清除 Token

5. **HTTPS**：生产环境必须使用 HTTPS

## 📚 更多信息

- **API 文档**：访问 http://localhost:8000/docs 查看交互式 API 文档
- **健康检查**：访问 http://localhost:8000/health 检查系统状态

## 🆘 常见问题

**Q: Token 多久过期？**  
A: 默认 30 分钟。可在 `.env` 中修改 `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`

**Q: 忘记密码怎么办？**  
A: 目前需要联系管理员。密码重置功能正在开发中。

**Q: 可以同时使用多个 Token 吗？**  
A: 可以。每次登录都会生成新的独立 Token。

**Q: 如何撤销 Token？**  
A: 当前 Token 无法主动撤销，等待过期即可。Token 黑名单功能正在开发中。

---

**版本**: 0.2.0  
**更新时间**: 2025-11-17
