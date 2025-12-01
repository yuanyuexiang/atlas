#!/bin/bash

# 数据一致性测试脚本
# 测试知识库数据不一致的检测和修复功能

BASE_URL="http://localhost:8000/atlas/api"
TOKEN=""

echo "========================================"
echo "知识库数据一致性测试"
echo "========================================"

# 1. 登录获取 Token
echo ""
echo "1. 登录获取 Token..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ 登录失败"
  echo $LOGIN_RESPONSE | jq
  exit 1
fi

echo "✅ 登录成功"

# 2. 获取智能体列表
echo ""
echo "2. 获取智能体列表..."
AGENTS=$(curl -s -X GET "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN")

echo $AGENTS | jq

# 选择第一个智能体
AGENT_ID=$(echo $AGENTS | jq -r '.[0].id')

if [ "$AGENT_ID" = "null" ] || [ -z "$AGENT_ID" ]; then
  echo "❌ 未找到智能体"
  exit 1
fi

echo "使用智能体: $AGENT_ID"

# 3. 获取知识库统计
echo ""
echo "3. 获取知识库统计..."
STATS=$(curl -s -X GET "$BASE_URL/knowledge-base/$AGENT_ID/stats" \
  -H "Authorization: Bearer $TOKEN")

echo $STATS | jq

# 4. 检查数据一致性
IS_CONSISTENT=$(echo $STATS | jq -r '.data.is_consistent')
TOTAL_FILES=$(echo $STATS | jq -r '.data.total_files')
TOTAL_VECTORS=$(echo $STATS | jq -r '.data.total_vectors')

echo ""
echo "数据一致性检查:"
echo "- 文件总数: $TOTAL_FILES"
echo "- 向量总数: $TOTAL_VECTORS"
echo "- 数据一致: $IS_CONSISTENT"

if [ "$IS_CONSISTENT" = "false" ]; then
  echo ""
  echo "⚠️ 检测到数据不一致！"
  WARNING=$(echo $STATS | jq -r '.data.warning')
  echo "警告: $WARNING"
  
  # 5. 执行修复
  echo ""
  echo "5. 执行数据一致性修复..."
  FIX_RESULT=$(curl -s -X POST "$BASE_URL/knowledge-base/$AGENT_ID/fix-inconsistency" \
    -H "Authorization: Bearer $TOKEN")
  
  echo $FIX_RESULT | jq
  
  # 6. 验证修复结果
  echo ""
  echo "6. 验证修复结果..."
  NEW_STATS=$(curl -s -X GET "$BASE_URL/knowledge-base/$AGENT_ID/stats" \
    -H "Authorization: Bearer $TOKEN")
  
  NEW_IS_CONSISTENT=$(echo $NEW_STATS | jq -r '.data.is_consistent')
  NEW_FILES=$(echo $NEW_STATS | jq -r '.data.total_files')
  NEW_VECTORS=$(echo $NEW_STATS | jq -r '.data.total_vectors')
  
  echo "修复后:"
  echo "- 文件总数: $NEW_FILES"
  echo "- 向量总数: $NEW_VECTORS"
  echo "- 数据一致: $NEW_IS_CONSISTENT"
  
  if [ "$NEW_IS_CONSISTENT" = "true" ]; then
    echo ""
    echo "✅ 数据一致性已恢复！"
  else
    echo ""
    echo "❌ 修复失败，数据仍不一致"
  fi
else
  echo ""
  echo "✅ 数据一致，无需修复"
fi

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"
