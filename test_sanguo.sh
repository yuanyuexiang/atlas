#!/bin/bash

# 测试三国助手API - 完整流程测试

BASE_URL="http://localhost:8003/atlas/api"

echo "========== 0. 获取认证Token =========="
TOKEN=$(curl -s -X POST ${BASE_URL}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "❌ 获取Token失败"
    exit 1
fi

echo "✅ Token获取成功: ${TOKEN:0:30}..."
echo ""

echo "========== 1. 创建三国助手 =========="
AGENT_RESPONSE=$(curl -s -X POST ${BASE_URL}/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "name":"sanguo_full_test",
    "display_name":"三国历史助手",
    "agent_type":"general",
    "system_prompt":"你是一个精通三国历史的AI助手,你的知识库包含三国演义相关内容。请基于知识库内容回答问题。",
    "description":"专门回答三国历史问题"
  }')

AGENT_ID=$(echo $AGENT_RESPONSE | jq -r '.id')

if [ -z "$AGENT_ID" ] || [ "$AGENT_ID" = "null" ]; then
    echo "❌ 创建失败，返回: $AGENT_RESPONSE"
    exit 1
fi

echo "✅ 创建成功，Agent ID: ${AGENT_ID}"
echo "Agent详情:"
echo $AGENT_RESPONSE | jq '.'
echo ""

echo "========== 2. 上传三国演义.pdf =========="
UPLOAD_RESPONSE=$(curl -s -X POST ${BASE_URL}/knowledge-base/${AGENT_ID}/documents \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@/Users/yuanyuexiang/Desktop/workspace/atlas/三国演义.pdf")

echo "$UPLOAD_RESPONSE" | jq '.'
echo ""

echo "========== 3. 等待文档处理 (15秒) =========="
for i in {1..15}; do
    echo -n "."
    sleep 1
done
echo ""
echo ""

echo "========== 4. 查询文档列表 =========="
curl -s -X GET ${BASE_URL}/knowledge-base/${AGENT_ID}/documents \
  -H "Authorization: Bearer ${TOKEN}" | jq '.'
echo ""

echo "========== 5. 查询知识库统计 =========="
curl -s -X GET ${BASE_URL}/knowledge-base/${AGENT_ID}/statistics \
  -H "Authorization: Bearer ${TOKEN}" | jq '.'
echo ""

echo "========== 6. 测试对话 - 问三国问题 =========="
curl -s -X POST ${BASE_URL}/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{
    \"agent_name\": \"sanguo_full_test\",
    \"message\": \"刘备、关羽、张飞三人的关系是什么？他们在哪里结拜的？\",
    \"conversation_id\": \"test-conv-$(date +%s)\"
  }" | jq '.'
echo ""

echo "========== 测试完成 =========="
echo ""
echo "Agent ID: ${AGENT_ID}"
echo "Agent Name: sanguo_full_test"
