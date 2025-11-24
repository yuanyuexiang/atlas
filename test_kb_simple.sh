#!/bin/bash
# 简化的知识库测试

BASE_URL="https://atlas.matrix-net.tech/atlas/api"

# 1. 登录
echo "登录..."
TOKEN=$(curl -k -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:20}..."

# 2. 测试现有智能体
echo ""
echo "获取智能体列表..."
AGENTS=$(curl -k -s -X GET "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN")

echo "$AGENTS" | python3 -m json.tool 2>/dev/null | head -30

# 3. 获取第一个智能体名称
FIRST_AGENT=$(echo "$AGENTS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['name'] if data else '')" 2>/dev/null)

if [ -n "$FIRST_AGENT" ]; then
    echo ""
    echo "测试智能体: $FIRST_AGENT"
    
    # 4. 获取知识库统计
    echo "获取知识库统计..."
    curl -k -s -X GET "$BASE_URL/knowledge-base/$FIRST_AGENT/stats" \
      -H "Authorization: Bearer $TOKEN" | python3 -m json.tool 2>/dev/null
      
    # 5. 测试上传小文件
    echo ""
    echo "创建测试文件..."
    TEST_FILE="/tmp/kb_test.txt"
    echo "这是一个知识库测试文档。产品名称是Echo智能客服系统。" > $TEST_FILE
    
    echo "上传测试文件..."
    UPLOAD_RESULT=$(curl -k -s -X POST "$BASE_URL/knowledge-base/$FIRST_AGENT/documents" \
      -H "Authorization: Bearer $TOKEN" \
      -F "file=@$TEST_FILE")
      
    echo "$UPLOAD_RESULT" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESULT"
    
    rm -f $TEST_FILE
else
    echo "❌ 没有找到智能体"
fi
