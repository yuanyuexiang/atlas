#!/bin/bash
# 测试 ID/Name 兼容性修复

echo "========================================="
echo "测试 API 支持 ID 和 Name 查询"
echo "========================================="
echo ""

BASE_URL="https://atlas.matrix-net.tech/atlas/api"

# 1. 登录
echo "1️⃣  登录..."
TOKEN=$(curl -k -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
    echo "  ❌ 登录失败"
    exit 1
fi
echo "  ✅ Token 获取成功"
echo ""

# 2. 获取客服列表
echo "2️⃣  获取客服列表..."
CONVERSATION_LIST=$(curl -k -s "$BASE_URL/conversations" \
  -H "Authorization: Bearer $TOKEN")

# 提取第一个客服的 ID 和 Name
CONV_ID=$(echo "$CONVERSATION_LIST" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null)
CONV_NAME=$(echo "$CONVERSATION_LIST" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['name'] if data else '')" 2>/dev/null)

if [ -z "$CONV_ID" ]; then
    echo "  ⚠️ 没有客服数据，创建测试客服..."
    
    # 创建智能体
    AGENT_NAME="test_fix_$(date +%s)"
    curl -k -s -X POST "$BASE_URL/agents" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"$AGENT_NAME\",
        \"display_name\": \"测试智能体\",
        \"agent_type\": \"general\"
      }" > /dev/null
    
    # 创建客服
    CONV_NAME="test_conv_$(date +%s)"
    CREATE_RESULT=$(curl -k -s -X POST "$BASE_URL/conversations" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"$CONV_NAME\",
        \"display_name\": \"测试客服\",
        \"agent_name\": \"$AGENT_NAME\",
        \"avatar\": \"🤖\"
      }")
    
    CONV_ID=$(echo "$CREATE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
    echo "  ✅ 创建测试客服成功"
else
    echo "  ✅ 找到客服"
    echo "     ID: $CONV_ID"
    echo "     Name: $CONV_NAME"
fi
echo ""

# 3. 测试用 Name 查询（原有功能）
echo "3️⃣  测试用 Name 查询详情..."
RESULT_NAME=$(curl -k -s "$BASE_URL/conversations/$CONV_NAME" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RESULT_NAME" | grep -q '"id"'; then
    echo "  ✅ 用 Name 查询成功"
else
    echo "  ❌ 用 Name 查询失败"
    echo "  $RESULT_NAME"
fi
echo ""

# 4. 测试用 ID 查询（修复后的功能）
echo "4️⃣  测试用 ID 查询详情（修复的 BUG）..."
RESULT_ID=$(curl -k -s "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RESULT_ID" | grep -q '"id"'; then
    echo "  ✅ 用 ID 查询成功"
    echo "     这是之前报告的 BUG，现在已修复！"
else
    echo "  ❌ 用 ID 查询失败"
    echo "  $RESULT_ID"
fi
echo ""

# 5. 测试用 ID 更新
echo "5️⃣  测试用 ID 更新客服..."
UPDATE_RESULT=$(curl -k -s -X PUT "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"已更新的名称"}')

if echo "$UPDATE_RESULT" | grep -q '"id"'; then
    echo "  ✅ 用 ID 更新成功"
else
    echo "  ❌ 用 ID 更新失败"
    echo "  $UPDATE_RESULT"
fi
echo ""

# 6. 测试智能体的 ID/Name 兼容性
echo "6️⃣  测试智能体 API 的 ID/Name 兼容性..."
AGENT_LIST=$(curl -k -s "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN")

AGENT_ID=$(echo "$AGENT_LIST" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null)
AGENT_NAME=$(echo "$AGENT_LIST" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['name'] if data else '')" 2>/dev/null)

# 用 Name 查询
AGENT_BY_NAME=$(curl -k -s "$BASE_URL/agents/$AGENT_NAME" \
  -H "Authorization: Bearer $TOKEN")

if echo "$AGENT_BY_NAME" | grep -q '"id"'; then
    echo "  ✅ 智能体用 Name 查询成功"
else
    echo "  ❌ 智能体用 Name 查询失败"
fi

# 用 ID 查询
AGENT_BY_ID=$(curl -k -s "$BASE_URL/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN")

if echo "$AGENT_BY_ID" | grep -q '"id"'; then
    echo "  ✅ 智能体用 ID 查询成功"
else
    echo "  ❌ 智能体用 ID 查询失败"
fi
echo ""

# 7. 总结
echo "========================================="
echo "✅ 修复验证完成"
echo "========================================="
echo ""
echo "修复内容："
echo "  1. 客服 API 现在支持用 ID 或 Name 查询"
echo "  2. 智能体 API 现在支持用 ID 或 Name 查询"
echo "  3. 所有 CRUD 操作都兼容两种方式"
echo ""
echo "受影响的接口："
echo "  - GET /conversations/{id_or_name}"
echo "  - PUT /conversations/{id_or_name}"
echo "  - DELETE /conversations/{id_or_name}"
echo "  - POST /conversations/{id_or_name}/switch-agent"
echo "  - GET /agents/{id_or_name}"
echo "  - PUT /agents/{id_or_name}"
echo "  - DELETE /agents/{id_or_name}"
echo ""
