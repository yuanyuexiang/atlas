#!/bin/bash

BASE_URL="http://localhost:8000/atlas/api"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiIxYTViZTM1OS1mMzIwLTQ1ZTgtYThmZS1lZTIyNmI4ZGUyMGIiLCJleHAiOjE3NjQwOTIzNzV9.HDaHxUZvf6ZpDJmI-FTkpKQKWaPwGmDaXbWnMUNI01Y"

echo "=== 客服更新测试 - 智能体关联 ==="
echo ""

# 1. 创建测试智能体
echo "1️⃣ 创建测试智能体 agent-update-test"
AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "agent-update-test",
    "display_name": "更新测试智能体",
    "agent_type": "general",
    "model_name": "gpt-4o-mini",
    "description": "用于测试更新的智能体"
  }')
echo "$AGENT_RESPONSE" | python3 -m json.tool
AGENT_ID=$(echo "$AGENT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo ""

# 2. 创建另一个测试智能体
echo "2️⃣ 创建第二个测试智能体 agent-update-test2"
AGENT2_RESPONSE=$(curl -s -X POST "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "agent-update-test2",
    "display_name": "更新测试智能体2",
    "agent_type": "general",
    "model_name": "gpt-4o-mini",
    "description": "用于测试更新的第二个智能体"
  }')
echo "$AGENT2_RESPONSE" | python3 -m json.tool
AGENT2_ID=$(echo "$AGENT2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo ""

# 3. 创建客服并关联第一个智能体
echo "3️⃣ 创建客服 conv-update-test 并关联智能体1"
CONV_RESPONSE=$(curl -s -X POST "$BASE_URL/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"conv-update-test\",
    \"display_name\": \"更新测试客服\",
    \"agent_name\": \"agent-update-test\",
    \"description\": \"用于测试更新的客服\"
  }")
echo "$CONV_RESPONSE" | python3 -m json.tool
CONV_ID=$(echo "$CONV_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo ""

# 4. 查询客服详情，确认智能体关联
echo "4️⃣ 查询客服详情，确认智能体1关联"
curl -s -X GET "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 5. 更新客服 - 只修改 display_name，不传 agent_name
echo "5️⃣ 更新客服 - 只修改 display_name（不传 agent_name，应保留原有关联）"
curl -s -X PUT "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "更新后的客服名称"
  }' | python3 -m json.tool
echo ""

# 6. 再次查询，确认智能体关联是否还在
echo "6️⃣ 查询客服详情，确认智能体1关联是否保留"
curl -s -X GET "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 7. 更新客服 - 切换到智能体2
echo "7️⃣ 更新客服 - 切换到智能体2（使用 agent_name）"
curl -s -X PUT "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "agent-update-test2"
  }' | python3 -m json.tool
echo ""

# 8. 查询确认切换成功
echo "8️⃣ 查询客服详情，确认切换到智能体2"
curl -s -X GET "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 9. 更新客服 - 使用 UUID 切换回智能体1
echo "9️⃣ 更新客服 - 使用 UUID 切换回智能体1"
curl -s -X PUT "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"agent_name\": \"$AGENT_ID\"
  }" | python3 -m json.tool
echo ""

# 10. 查询确认
echo "🔟 查询客服详情，确认切换回智能体1"
curl -s -X GET "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# 清理测试数据
echo "🧹 清理测试数据"
curl -s -X DELETE "$BASE_URL/conversations/$CONV_ID" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
curl -s -X DELETE "$BASE_URL/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
curl -s -X DELETE "$BASE_URL/agents/$AGENT2_ID" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
echo "✅ 清理完成"
