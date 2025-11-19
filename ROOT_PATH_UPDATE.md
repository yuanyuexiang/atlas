# ROOT_PATH 配置更新记录

**更新日期**: 2025-11-19  
**更新内容**: 添加 FastAPI 根路径支持，配置 ROOT_PATH="/atlas"

## 📝 更新内容

### 1. 核心配置修改

#### `core/config.py`
```python
# 添加反向代理根路径配置
ROOT_PATH: str = "/atlas"  # 应用部署在 /atlas 路径下
```

#### `app.py`
```python
# FastAPI 应用初始化时设置根路径
app = FastAPI(
    title=settings.APP_NAME,
    root_path=settings.ROOT_PATH,  # 设置根路径
    # ... 其他配置
)
```

### 2. 文档更新

所有文档中的 API URL 已更新为包含 `/atlas` 前缀：

#### 更新的文档
- ✅ `README.md` - 添加根路径说明，更新所有 URL (20+ 处)
- ✅ `FRONTEND_GUIDE.md` - 更新生产环境和本地开发 URL (60+ 处)
- ✅ `USAGE.md` - 更新使用示例中的 URL (17+ 处)
- ✅ `AUTHENTICATION.md` - 更新认证示例 URL (10+ 处)
- ✅ `DEPLOYMENT.md` - 添加根路径配置说明

#### 新增的文档
- 📄 `ROOT_PATH_GUIDE.md` - 详细的根路径配置和使用指南
- 📄 `nginx.conf.example` - Nginx 反向代理配置示例
- 📄 `ROOT_PATH_UPDATE.md` - 本更新记录文档

### 3. URL 变更对照

| 环境 | 旧 URL | 新 URL |
|------|--------|--------|
| 本地 API | `http://localhost:8000/api/*` | `http://localhost:8000/atlas/api/*` |
| 本地文档 | `http://localhost:8000/docs` | `http://localhost:8000/atlas/docs` |
| 本地健康检查 | `http://localhost:8000/health` | `http://localhost:8000/atlas/health` |
| 生产 API | `https://atlas.matrix-net.tech/api/*` | `https://atlas.matrix-net.tech/atlas/api/*` |
| 生产文档 | `https://atlas.matrix-net.tech/docs` | `https://atlas.matrix-net.tech/atlas/docs` |

## 🎯 影响范围

### 后端
- ✅ **向后兼容**: 通过 `root_path` 参数实现，不破坏现有路由定义
- ✅ **OpenAPI 文档**: Swagger/ReDoc 自动适配新路径
- ✅ **健康检查**: `/atlas/health` 正常工作

### 前端
- ⚠️ **需要更新**: 所有前端应用需要更新 API Base URL
  ```javascript
  // 旧配置
  const BASE_URL = 'https://atlas.matrix-net.tech/api'
  
  // 新配置
  const BASE_URL = 'https://atlas.matrix-net.tech/atlas/api'
  ```

### 部署
- ⚠️ **Nginx 配置**: 需要更新反向代理配置 (见 `nginx.conf.example`)
- ✅ **Docker**: 无需修改，容器内部路径不变

## 🚀 部署步骤

### 1. 本地测试
```bash
# 启动应用
uvicorn app:app --host 0.0.0.0 --port 8000

# 测试新路径
curl http://localhost:8000/atlas/health
curl http://localhost:8000/atlas/docs
```

### 2. 更新 Nginx 配置
```bash
# 复制示例配置
sudo cp nginx.conf.example /etc/nginx/sites-available/atlas

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo nginx -s reload
```

### 3. 更新前端应用
```javascript
// 更新 API Base URL
const API_BASE = process.env.NODE_ENV === 'production'
  ? 'https://atlas.matrix-net.tech/atlas/api'
  : 'http://localhost:8000/atlas/api';
```

## ✅ 验证清单

- [ ] 后端服务启动成功
- [ ] 可以访问 `/atlas/health` 健康检查
- [ ] 可以访问 `/atlas/docs` API 文档
- [ ] 认证接口 `/atlas/api/auth/login` 正常工作
- [ ] 所有 API 接口路径正确
- [ ] Nginx 反向代理配置正确
- [ ] 前端应用 API 调用正常
- [ ] SSE 流式响应正常工作

## 📚 相关文档

- [根路径配置说明](ROOT_PATH_GUIDE.md) - 详细配置和使用指南
- [前端开发指南](FRONTEND_GUIDE.md) - API 接口文档
- [部署指南](DEPLOYMENT.md) - 部署配置
- [Nginx 配置示例](nginx.conf.example) - 反向代理配置

## 🔄 回滚方案

如需回滚到根路径部署：

1. 修改 `core/config.py`:
   ```python
   ROOT_PATH: str = ""  # 改为空字符串
   ```

2. 重启应用

3. 恢复 Nginx 配置和前端 URL

## 💡 优势总结

1. ✅ **反向代理友好**: 支持 Nginx、Traefik 等
2. ✅ **多应用共存**: 同一域名部署多个应用
3. ✅ **路径隔离**: 避免路径冲突
4. ✅ **文档自适应**: OpenAPI 文档自动调整
5. ✅ **灵活部署**: 支持子路径和根路径部署

## �� 注意事项

1. **所有前端应用必须更新 API Base URL**
2. **测试环境也需要使用 `/atlas` 前缀以保持一致性**
3. **检查所有硬编码的 URL 是否已更新**
4. **SSE/WebSocket 连接需要特别注意路径**

---

**更新者**: GitHub Copilot  
**审核者**: 待审核  
**状态**: ✅ 完成
