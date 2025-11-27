#!/bin/bash

BASE_URL="http://localhost:8000/atlas/api"

# 获取 token
echo "🔑 登录获取 Token..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "✅ Token: ${TOKEN:0:50}..."
echo ""

# 创建测试文件
echo "📝 创建测试文档..."
cat > /tmp/knowledge_test.txt << 'EOF'
# 产品知识库

## 产品A
产品A是一款智能客服系统，具有以下特点：
- 支持多语言对话
- 基于RAG技术的知识库问答
- 7x24小时在线服务

价格：每月999元

## 产品B  
产品B是企业级数据分析平台：
- 实时数据处理
- 可视化报表生成
- AI智能预测

价格：每月1999元
EOF

echo "✅ 测试文档已创建"
echo ""

# 上传文档
echo "📤 上传文档到智能体 test_agent_1763997087284..."
UPLOAD_RESULT=$(curl -s -X POST "$BASE_URL/knowledge-base/test_agent_1763997087284/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/knowledge_test.txt")

echo "$UPLOAD_RESULT" | python3 -m json.tool
echo ""

# 等待向量化完成
echo "⏳ 等待向量化..."
sleep 2
echo ""

# 查看知识库统计
echo "📊 查看知识库统计..."
curl -s "$BASE_URL/agents/test_agent_1763997087284" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys, json; kb = json.load(sys.stdin)['knowledge_base']; print(f'Collection: {kb[\"collection_name\"]}'); print(f'文件数: {kb[\"total_files\"]}'); print(f'向量数: {kb[\"total_vectors\"]}'); print(f'文件列表:'); [print(f\"  - {f['filename']} ({f['chunks_count']} chunks)\") for f in kb['files']]"
echo ""

# 查看文件列表
echo "📚 查看文档列表..."
curl -s "$BASE_URL/knowledge-base/test_agent_1763997087284/documents" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "✅ 测试完成！"
