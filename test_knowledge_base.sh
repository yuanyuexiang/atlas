#!/bin/bash
# 知识库管理功能测试脚本

echo "========================================="
echo "知识库管理功能测试"
echo "========================================="
echo ""

# 配置
BASE_URL="https://atlas.matrix-net.tech/atlas/api"
AGENT_NAME="test-kb-agent-$(date +%s)"

echo "📝 配置信息:"
echo "  Base URL: $BASE_URL"
echo "  测试智能体: $AGENT_NAME"
echo ""

# 1. 登录获取 token
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

# 2. 创建测试智能体
echo "2️⃣  创建测试智能体..."
CREATE_AGENT=$(curl -k -s -X POST "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$AGENT_NAME\",
    \"display_name\": \"知识库测试智能体\",
    \"agent_type\": \"general\",
    \"description\": \"用于测试知识库功能\"
  }")

AGENT_ID=$(echo $CREATE_AGENT | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -z "$AGENT_ID" ]; then
    echo "  ❌ 创建智能体失败"
    echo "  $CREATE_AGENT"
    exit 1
fi
echo "  ✅ 智能体创建成功: $AGENT_ID"
echo ""

# 3. 创建测试文件
echo "3️⃣  创建测试文档..."
TEST_FILE="/tmp/test_kb_doc.txt"
cat > $TEST_FILE << 'TESTDOC'
# 产品知识库测试文档

## 产品介绍
我们的产品是一个智能客服系统，基于 RAG 技术构建。

## 核心功能
1. 智能体管理 - 创建和管理多个 AI 智能体
2. 知识库管理 - 上传文档并自动向量化
3. 智能对话 - 基于知识库的问答

## 技术架构
- 后端: FastAPI + PostgreSQL + Milvus
- 前端: Vue 3 / React
- AI: OpenAI / OpenRouter

## 联系方式
Email: support@example.com
电话: 400-123-4567
TESTDOC

echo "  ✅ 测试文档创建成功: $TEST_FILE"
echo ""

# 4. 上传文档
echo "4️⃣  上传文档到知识库..."
UPLOAD_RESPONSE=$(curl -k -s -X POST "$BASE_URL/knowledge-base/$AGENT_NAME/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$TEST_FILE")

FILE_ID=$(echo $UPLOAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('file_id', ''))" 2>/dev/null)

if [ -z "$FILE_ID" ]; then
    echo "  ❌ 文档上传失败"
    echo "  $UPLOAD_RESPONSE"
else
    echo "  ✅ 文档上传成功"
    echo "  File ID: $FILE_ID"
    CHUNKS=$(echo $UPLOAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('chunks_count', 0))")
    echo "  Chunks: $CHUNKS"
fi
echo ""

# 5. 等待向量化处理
echo "5️⃣  等待向量化处理..."
sleep 3
echo "  ✅ 等待完成"
echo ""

# 6. 获取知识库统计
echo "6️⃣  获取知识库统计..."
STATS_RESPONSE=$(curl -k -s -X GET "$BASE_URL/knowledge-base/$AGENT_NAME/stats" \
  -H "Authorization: Bearer $TOKEN")

echo "$STATS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATS_RESPONSE"
echo ""

# 7. 获取文档列表
echo "7️⃣  获取文档列表..."
DOCS_RESPONSE=$(curl -k -s -X GET "$BASE_URL/knowledge-base/$AGENT_NAME/documents" \
  -H "Authorization: Bearer $TOKEN")

echo "$DOCS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DOCS_RESPONSE"
echo ""

# 8. 测试对话（使用知识库）
echo "8️⃣  测试基于知识库的对话..."

# 创建客服
CONV_NAME="test-conv-$(date +%s)"
CREATE_CONV=$(curl -k -s -X POST "$BASE_URL/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$CONV_NAME\",
    \"display_name\": \"测试客服\",
    \"agent_name\": \"$AGENT_NAME\",
    \"avatar\": \"🤖\"
  }")

echo "  创建测试客服..."

# 发送测试消息
CHAT_RESPONSE=$(curl -k -s -X POST "$BASE_URL/chat/$CONV_NAME/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"你们的产品有哪些核心功能？"}')

echo "  问题: 你们的产品有哪些核心功能？"
echo "  回答: $(echo $CHAT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('content', 'N/A'))" 2>/dev/null)"
echo ""

# 9. 测试删除文档
if [ -n "$FILE_ID" ]; then
    echo "9️⃣  测试删除文档..."
    DELETE_RESPONSE=$(curl -k -s -X DELETE "$BASE_URL/knowledge-base/$AGENT_NAME/documents/$FILE_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "$DELETE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "  ✅ 文档删除成功"
    echo ""
fi

# 10. 清理测试资源
echo "🧹 清理测试资源..."

# 删除客服
curl -k -s -X DELETE "$BASE_URL/conversations/$CONV_NAME" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# 删除智能体
curl -k -s -X DELETE "$BASE_URL/agents/$AGENT_NAME" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# 删除测试文件
rm -f $TEST_FILE

echo "  ✅ 清理完成"
echo ""

echo "========================================="
echo "✅ 知识库管理功能测试完成"
echo "========================================="
