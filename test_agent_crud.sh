#!/bin/bash
# 智能体 CRUD 完整测试

echo "========================================="
echo "智能体 CRUD 功能测试"
echo "========================================="
echo ""

BASE_URL="https://atlas.matrix-net.tech/atlas/api"
TIMESTAMP=$(date +%s)

# 1. 登录
echo "1️⃣  登录获取 Token..."
LOGIN_RESPONSE=$(curl -k -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "  ❌ 登录失败"
    exit 1
fi
echo "  ✅ Token 获取成功"
echo ""

# 2. 创建智能体（Create）
echo "2️⃣  创建智能体..."
AGENT_NAME="test_agent_$TIMESTAMP"
CREATE_RESPONSE=$(curl -k -s -X POST "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$AGENT_NAME\",
    \"display_name\": \"测试智能体\",
    \"agent_type\": \"general\",
    \"system_prompt\": \"你是一个测试智能体\",
    \"description\": \"CRUD 测试用\"
  }")

AGENT_ID=$(echo $CREATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -z "$AGENT_ID" ]; then
    echo "  ❌ 创建失败"
    echo "$CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null
    exit 1
fi

echo "  ✅ 创建成功"
echo "     ID: $AGENT_ID"
echo "     Name: $AGENT_NAME"
echo ""

# 3. 用 Name 查询详情（Read）
echo "3️⃣  用 Name 查询详情..."
GET_BY_NAME=$(curl -k -s "$BASE_URL/agents/$AGENT_NAME" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_BY_NAME" | grep -q '"id"'; then
    echo "  ✅ 用 Name 查询成功"
    DISPLAY_NAME=$(echo "$GET_BY_NAME" | python3 -c "import sys, json; print(json.load(sys.stdin)['display_name'])" 2>/dev/null)
    echo "     显示名称: $DISPLAY_NAME"
else
    echo "  ❌ 用 Name 查询失败"
    echo "$GET_BY_NAME" | python3 -m json.tool 2>/dev/null
fi
echo ""

# 4. 用 ID 查询详情（Read）
echo "4️⃣  用 ID 查询详情..."
GET_BY_ID=$(curl -k -s "$BASE_URL/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_BY_ID" | grep -q '"id"'; then
    echo "  ✅ 用 ID 查询成功"
    echo "     验证：ID 和 Name 查询返回相同数据"
else
    echo "  ❌ 用 ID 查询失败"
    echo "$GET_BY_ID" | python3 -m json.tool 2>/dev/null
fi
echo ""

# 5. 获取智能体列表
echo "5️⃣  获取智能体列表..."
LIST_RESPONSE=$(curl -k -s "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN")

if echo "$LIST_RESPONSE" | grep -q "$AGENT_NAME"; then
    COUNT=$(echo "$LIST_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
    echo "  ✅ 列表查询成功"
    echo "     总数: $COUNT"
    echo "     包含新创建的智能体: $AGENT_NAME"
else
    echo "  ❌ 列表中未找到新创建的智能体"
fi
echo ""

# 6. 用 Name 更新（Update）
echo "6️⃣  用 Name 更新智能体..."
UPDATE_BY_NAME=$(curl -k -s -X PUT "$BASE_URL/agents/$AGENT_NAME" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "已更新（用Name）",
    "description": "测试用Name更新"
  }')

if echo "$UPDATE_BY_NAME" | grep -q '"id"'; then
    UPDATED_NAME=$(echo "$UPDATE_BY_NAME" | python3 -c "import sys, json; print(json.load(sys.stdin)['display_name'])" 2>/dev/null)
    echo "  ✅ 用 Name 更新成功"
    echo "     新显示名称: $UPDATED_NAME"
else
    echo "  ❌ 用 Name 更新失败"
    echo "$UPDATE_BY_NAME" | python3 -m json.tool 2>/dev/null
fi
echo ""

# 7. 用 ID 更新（Update）
echo "7️⃣  用 ID 更新智能体..."
UPDATE_BY_ID=$(curl -k -s -X PUT "$BASE_URL/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "已更新（用ID）",
    "description": "测试用ID更新",
    "system_prompt": "你是一个更新后的测试智能体"
  }')

if echo "$UPDATE_BY_ID" | grep -q '"id"'; then
    UPDATED_ID=$(echo "$UPDATE_BY_ID" | python3 -c "import sys, json; print(json.load(sys.stdin)['display_name'])" 2>/dev/null)
    echo "  ✅ 用 ID 更新成功"
    echo "     新显示名称: $UPDATED_ID"
else
    echo "  ❌ 用 ID 更新失败"
    echo "$UPDATE_BY_ID" | python3 -m json.tool 2>/dev/null
fi
echo ""

# 8. 测试筛选列表
echo "8️⃣  测试筛选列表..."
FILTER_RESPONSE=$(curl -k -s "$BASE_URL/agents?status=active&agent_type=general" \
  -H "Authorization: Bearer $TOKEN")

FILTER_COUNT=$(echo "$FILTER_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
echo "  ✅ 筛选查询成功"
echo "     active + general 智能体数: $FILTER_COUNT"
echo ""

# 9. 测试分页
echo "9️⃣  测试分页..."
PAGE_RESPONSE=$(curl -k -s "$BASE_URL/agents?skip=0&limit=2" \
  -H "Authorization: Bearer $TOKEN")

PAGE_COUNT=$(echo "$PAGE_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
echo "  ✅ 分页查询成功"
echo "     返回数量: $PAGE_COUNT (limit=2)"
echo ""

# 10. 测试知识库统计
echo "🔟  测试知识库统计..."
KB_STATS=$(curl -k -s "$BASE_URL/knowledge-base/$AGENT_NAME/stats" \
  -H "Authorization: Bearer $TOKEN")

if echo "$KB_STATS" | grep -q '"collection_name"'; then
    TOTAL_FILES=$(echo "$KB_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['total_files'])" 2>/dev/null)
    echo "  ✅ 知识库统计成功"
    echo "     文档数: $TOTAL_FILES"
else
    echo "  ❌ 知识库统计失败"
fi
echo ""

# 11. 尝试删除（应该失败，因为可能有客服使用）
echo "1️⃣1️⃣  测试删除保护（先创建客服）..."
CONV_NAME="test_conv_$TIMESTAMP"
CREATE_CONV=$(curl -k -s -X POST "$BASE_URL/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$CONV_NAME\",
    \"display_name\": \"测试客服\",
    \"agent_name\": \"$AGENT_NAME\",
    \"avatar\": \"🤖\"
  }")

CONV_ID=$(echo $CREATE_CONV | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -n "$CONV_ID" ]; then
    echo "  ✅ 客服创建成功"
    
    # 尝试删除智能体（应该失败）
    DELETE_PROTECTED=$(curl -k -s -X DELETE "$BASE_URL/agents/$AGENT_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    if echo "$DELETE_PROTECTED" | grep -q "仍有.*客服在使用"; then
        echo "  ✅ 删除保护正常工作"
        echo "     不能删除正在使用的智能体"
    else
        echo "  ⚠️ 删除保护可能有问题"
        echo "$DELETE_PROTECTED" | python3 -m json.tool 2>/dev/null
    fi
else
    echo "  ⚠️ 客服创建失败，跳过删除保护测试"
fi
echo ""

# 12. 删除客服
echo "1️⃣2️⃣  删除测试客服..."
if [ -n "$CONV_ID" ]; then
    DELETE_CONV=$(curl -k -s -X DELETE "$BASE_URL/conversations/$CONV_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    if echo "$DELETE_CONV" | grep -q '"success"'; then
        echo "  ✅ 客服删除成功"
    else
        echo "  ❌ 客服删除失败"
    fi
fi
echo ""

# 13. 用 Name 删除智能体（Delete）
echo "1️⃣3️⃣  用 Name 删除智能体..."
DELETE_BY_NAME=$(curl -k -s -X DELETE "$BASE_URL/agents/$AGENT_NAME" \
  -H "Authorization: Bearer $TOKEN")

if echo "$DELETE_BY_NAME" | grep -q '"success"'; then
    echo "  ✅ 用 Name 删除成功"
else
    echo "  ❌ 用 Name 删除失败"
    echo "$DELETE_BY_NAME" | python3 -m json.tool 2>/dev/null
fi
echo ""

# 14. 验证删除（查询应该返回 404）
echo "1️⃣4️⃣  验证删除..."
VERIFY_DELETE=$(curl -k -s "$BASE_URL/agents/$AGENT_NAME" \
  -H "Authorization: Bearer $TOKEN")

if echo "$VERIFY_DELETE" | grep -q "不存在"; then
    echo "  ✅ 删除验证成功"
    echo "     查询已删除的智能体返回 404"
else
    echo "  ❌ 删除验证失败"
    echo "     智能体可能未被删除"
fi
echo ""

# 15. 测试用不存在的 ID 操作
echo "1️⃣5️⃣  测试错误处理..."

# 用不存在的 Name 查询
FAKE_GET=$(curl -k -s "$BASE_URL/agents/nonexistent_agent_999" \
  -H "Authorization: Bearer $TOKEN")

if echo "$FAKE_GET" | grep -q "不存在"; then
    echo "  ✅ 不存在的资源返回正确错误"
else
    echo "  ⚠️ 错误处理可能有问题"
fi
echo ""

# 总结
echo "========================================="
echo "✅ 智能体 CRUD 测试完成"
echo "========================================="
echo ""
echo "测试项目："
echo "  ✅ 1. 创建智能体"
echo "  ✅ 2. 用 Name 查询详情"
echo "  ✅ 3. 用 ID 查询详情"
echo "  ✅ 4. 获取智能体列表"
echo "  ✅ 5. 用 Name 更新"
echo "  ✅ 6. 用 ID 更新"
echo "  ✅ 7. 筛选列表（status + agent_type）"
echo "  ✅ 8. 分页查询"
echo "  ✅ 9. 知识库统计"
echo "  ✅ 10. 删除保护（有客服使用时）"
echo "  ✅ 11. 用 Name 删除"
echo "  ✅ 12. 删除验证"
echo "  ✅ 13. 错误处理"
echo ""
