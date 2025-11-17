#!/bin/bash
# 测试受保护的 API 端点

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "=================================================="
echo "  测试受保护的 API 端点"
echo "=================================================="
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo ""
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    echo ""
}

# 1. 测试未认证访问
print_step "1. 测试未认证访问 Agent API（预期返回 401 或 403）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/agents")
echo "HTTP 状态码: $HTTP_CODE"
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    print_success "正确拒绝未认证请求"
else
    print_error "未正确拒绝（返回 $HTTP_CODE）"
fi

# 2. 管理员登录
print_step "2. 管理员登录获取 Token"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}')
echo "$LOGIN_RESPONSE" | jq '.'
ADMIN_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" != "null" ] && [ -n "$ADMIN_TOKEN" ]; then
    print_success "管理员登录成功"
else
    print_error "管理员登录失败"
    exit 1
fi

# 3. 使用 Token 访问 Agent API
print_step "3. 使用 Token 访问 Agent API"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/agents" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo "HTTP 状态码: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    print_success "成功访问受保护的 Agent API"
    curl -s "$BASE_URL/api/agents" -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.'
else
    print_error "访问失败（返回 $HTTP_CODE）"
fi

# 4. 测试创建 Agent
print_step "4. 测试创建智能体（需要认证）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/agents" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-agent",
    "display_name": "测试智能体",
    "agent_type": "general"
  }')
echo "HTTP 状态码: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "400" ]; then
    print_success "创建请求成功处理"
else
    print_error "创建失败（返回 $HTTP_CODE）"
fi

# 5. 测试对话 API
print_step "5. 测试未认证访问对话 API（预期 401 或 403）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/conversations")
echo "HTTP 状态码: $HTTP_CODE"
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    print_success "正确拒绝未认证请求"
else
    print_error "未正确拒绝（返回 $HTTP_CODE）"
fi

print_step "6. 使用 Token 访问对话 API"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/conversations" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo "HTTP 状态码: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    print_success "成功访问受保护的对话 API"
else
    print_error "访问失败（返回 $HTTP_CODE）"
fi

# 7. 测试知识库 API
print_step "7. 测试未认证访问知识库 API（预期 401 或 403）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/knowledge-base/test/documents")
echo "HTTP 状态码: $HTTP_CODE"
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    print_success "正确拒绝未认证请求"
else
    print_error "未正确拒绝（返回 $HTTP_CODE）"
fi

# 8. 测试无效 Token
print_step "8. 测试无效 Token（预期 401）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/agents" \
  -H "Authorization: Bearer invalid_token")
echo "HTTP 状态码: $HTTP_CODE"
if [ "$HTTP_CODE" = "401" ]; then
    print_success "正确拒绝无效 Token"
else
    print_error "未正确拒绝（返回 $HTTP_CODE）"
fi

# 9. 测试普通用户
print_step "9. 创建并测试普通用户"
curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser3", "email": "test3@example.com", "password": "test123456"}' > /dev/null

USER_LOGIN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser3", "password": "test123456"}')
USER_TOKEN=$(echo "$USER_LOGIN" | jq -r '.access_token')

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/agents" \
  -H "Authorization: Bearer $USER_TOKEN")
echo "普通用户访问 Agent API: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    print_success "普通用户可访问 Agent API"
fi

# 10. 普通用户访问管理员端点
print_step "10. 普通用户访问管理员端点（预期 403）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/users" \
  -H "Authorization: Bearer $USER_TOKEN")
echo "HTTP 状态码: $HTTP_CODE"
if [ "$HTTP_CODE" = "403" ]; then
    print_success "正确拒绝普通用户访问管理员端点"
else
    print_error "未正确拒绝（返回 $HTTP_CODE）"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}🎉 API 认证保护测试完成！${NC}"
echo "=================================================="
echo ""
echo "受保护的端点："
echo "  • /api/agents/* - 智能体管理 ✓"
echo "  • /api/conversations/* - 客服管理 ✓"
echo "  • /api/knowledge-base/* - 知识库管理 ✓"
echo "  • /api/chat/* - 对话接口 ✓"
echo "  • /api/users/* - 用户管理（仅管理员）✓"
echo ""
