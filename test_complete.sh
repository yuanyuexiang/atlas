#!/bin/bash

set -e

BASE_URL="http://localhost:8003/atlas/api"
AGENT_ID="8f696bcf-391c-4bbf-8d96-b3f2ab774b19"

echo "=========================================="
echo "🧪 开始完整功能测试"
echo "=========================================="
echo ""

# 1. 登录获取 Token
echo "🔑 1. 获取认证 Token..."
TOKEN=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ 登录失败"
    exit 1
fi
echo "✅ Token 已获取: ${TOKEN:0:20}..."
echo ""

# 2. 查询 Agent 详情
echo "📋 2. 查询 Agent 详情..."
curl -s -X GET "${BASE_URL}/agents/${AGENT_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | jq '{
    id, name, display_name, agent_type, status,
    knowledge_base: .knowledge_base | {collection_name, total_files, total_vectors}
  }'
echo ""

# 3. 上传文档
echo "📤 3. 上传三国演义.pdf..."
UPLOAD_RESULT=$(curl -s -X POST "${BASE_URL}/knowledge-base/${AGENT_ID}/documents" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@/Users/yuanyuexiang/Desktop/workspace/atlas/三国演义.pdf")

echo "$UPLOAD_RESULT" | jq '.'
echo ""

# 4. 等待文档处理
echo "⏳ 4. 等待文档向量化处理 (15秒)..."
for i in {15..1}; do
    echo -ne "   剩余 $i 秒...\r"
    sleep 1
done
echo ""
echo ""

# 5. 查询文档列表
echo "📚 5. 查询文档列表..."
curl -s -X GET "${BASE_URL}/knowledge-base/${AGENT_ID}/documents" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.[] | {
    filename, file_size, status, chunks_count, created_at
  }'
echo ""

# 6. 查询知识库统计
echo "📊 6. 查询知识库统计..."
curl -s -X GET "${BASE_URL}/agents/${AGENT_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.knowledge_base'
echo ""

# 7. 测试对话功能
echo "💬 7. 测试 RAG 对话..."
CHAT_RESULT=$(curl -s -X POST "${BASE_URL}/agents/${AGENT_ID}/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "message": "刘备、关羽、张飞是什么关系？他们在哪里结拜的？",
    "conversation_id": "test-conv-001"
  }')

echo "$CHAT_RESULT" | jq '{
    conversation_id,
    response: .response[:200],
    sources: .sources | length
}'
echo ""

# 8. 再次对话(测试会话历史)
echo "💬 8. 测试会话历史..."
CHAT_RESULT2=$(curl -s -X POST "${BASE_URL}/agents/${AGENT_ID}/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "message": "他们三个人的武器分别是什么？",
    "conversation_id": "test-conv-001"
  }')

echo "$CHAT_RESULT2" | jq '{
    conversation_id,
    response: .response[:200]
}'
echo ""

echo "=========================================="
echo "✅ 测试完成！"
echo "=========================================="
echo ""
echo "📌 测试的 Agent:"
echo "   - ID: ${AGENT_ID}"
echo "   - 名称: sanguo_demo"
echo "   - 类型: 三国演义助手"
echo ""
