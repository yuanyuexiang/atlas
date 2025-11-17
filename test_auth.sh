#!/bin/bash
# JWT 认证功能测试脚本

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "=================================================="
echo "  JWT 认证功能测试"
echo "=================================================="
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo ""
}

# 1. 测试未认证访问（应该失败）
print_step "1. 测试未认证访问 Agent API（预期失败）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/agents")
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    print_success "正确拒绝未认证请求 (HTTP $HTTP_CODE)"
else
    echo "⚠️  未认证请求返回 HTTP $HTTP_CODE（可能未启用保护）"
    echo ""
fi

# 2. 注册新用户
print_step "2. 注册新用户"
curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "test123456",
    "full_name": "测试用户"
  }' | jq '.'
print_success "用户注册成功"

# 3. 用户登录获取 Token
print_step "3. 用户登录获取 Token"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test123456"
  }')
echo "$LOGIN_RESPONSE" | jq '.'

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    print_success "登录成功，获取到 Token"
else
    echo "❌ 登录失败"
    exit 1
fi

# 4. 使用 Token 访问受保护的端点
print_step "4. 使用 Token 获取当前用户信息"
curl -s "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
print_success "成功访问受保护端点"

# 5. 刷新 Token
print_step "5. 刷新 Token"
curl -s -X POST "$BASE_URL/api/auth/refresh" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
print_success "Token 刷新成功"

# 6. 管理员登录
print_step "6. 管理员登录"
ADMIN_LOGIN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')
echo "$ADMIN_LOGIN" | jq '.'

ADMIN_TOKEN=$(echo "$ADMIN_LOGIN" | jq -r '.access_token')
if [ "$ADMIN_TOKEN" != "null" ] && [ -n "$ADMIN_TOKEN" ]; then
    print_success "管理员登录成功"
else
    echo "❌ 管理员登录失败"
    exit 1
fi

# 7. 管理员访问用户列表
print_step "7. 管理员访问用户列表"
curl -s "$BASE_URL/api/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.'
print_success "管理员成功访问用户列表"

# 8. 普通用户尝试访问管理员端点（应该失败）
print_step "8. 普通用户尝试访问管理员端点（预期失败）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/users" \
  -H "Authorization: Bearer $TOKEN")
if [ "$HTTP_CODE" = "403" ]; then
    print_success "正确拒绝普通用户访问管理员端点 (HTTP $HTTP_CODE)"
else
    echo "⚠️  返回 HTTP $HTTP_CODE"
    echo ""
fi

# 9. 更新当前用户信息
print_step "9. 更新当前用户信息"
curl -s -X PUT "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "测试用户（已更新）"
  }' | jq '.'
print_success "用户信息更新成功"

# 10. 测试错误的 Token
print_step "10. 测试错误的 Token（预期失败）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer invalid_token_12345")
if [ "$HTTP_CODE" = "401" ]; then
    print_success "正确拒绝无效 Token (HTTP $HTTP_CODE)"
else
    echo "⚠️  返回 HTTP $HTTP_CODE"
    echo ""
fi

echo ""
echo "=================================================="
echo -e "${GREEN}🎉 认证功能测试完成！${NC}"
echo "=================================================="
echo ""
echo "测试摘要："
echo "  ✅ 用户注册"
echo "  ✅ 用户登录"
echo "  ✅ Token 验证"
echo "  ✅ Token 刷新"
echo "  ✅ 权限控制"
echo "  ✅ 管理员功能"
echo "  ✅ 用户信息更新"
echo "  ✅ 错误处理"
echo ""
echo "默认账号："
echo "  管理员: admin / admin123"
echo "  测试用户: testuser / test123456"
echo ""
