#!/bin/bash
# Echo 智能客服后端 API 测试脚本

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
AGENT_NAME="demo_agent"
CONV_NAME="demo_conversation"

echo "=================================================="
echo "  Echo 智能客服后端 API 测试"
echo "=================================================="
echo ""

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo ""
}

# 1. 健康检查
print_step "1. 健康检查"
curl -s "$BASE_URL/health" | jq '.'
print_success "服务器运行正常"

# 2. 创建智能体
print_step "2. 创建智能体: $AGENT_NAME"
curl -s -X POST "$BASE_URL/api/agents" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$AGENT_NAME\",
    \"display_name\": \"演示客服\",
    \"agent_type\": \"general\",
    \"system_prompt\": \"你是一个专业友好的客服助手，请用简洁明了的语言回答用户问题。\",
    \"milvus_collection\": \"${AGENT_NAME}_kb\"
  }" | jq '.'
print_success "智能体创建成功"

# 3. 准备并上传测试文档
print_step "3. 上传知识库文档"
cat > /tmp/demo_knowledge.txt << 'EOF'
产品服务说明

我们是一家提供智能客服解决方案的公司，主要服务包括：

1. 智能问答系统
   - 基于大语言模型的智能对话
   - 支持多轮对话和上下文理解
   - 知识库动态管理和更新

2. RAG 检索增强
   - 向量数据库存储（Milvus）
   - 语义检索和相似度匹配
   - 实时知识库更新

3. 多智能体管理
   - 灵活的智能体配置
   - 对话会话动态切换
   - 智能体性能监控

联系方式：
- 客服热线: 400-800-8888
- 技术支持: support@example.com
- 工作时间: 周一至周日 9:00-22:00
- 官网: https://www.example.com

常见问题：
Q: 系统支持哪些文件格式？
A: 支持 PDF、TXT、Markdown 格式的文档上传。

Q: 如何更新知识库？
A: 通过 API 上传新文档即可自动更新向量数据库。

Q: 是否支持多语言？
A: 目前主要支持中文，未来会扩展更多语言。
EOF

curl -s -X POST "$BASE_URL/api/knowledge-base/$AGENT_NAME/documents" \
  -F "file=@/tmp/demo_knowledge.txt" | jq '.'
print_success "文档上传成功"

# 4. 查看知识库统计
print_step "4. 查看知识库统计"
curl -s "$BASE_URL/api/knowledge-base/$AGENT_NAME/stats" | jq '.data'
print_success "知识库查询成功"

# 5. 创建对话
print_step "5. 创建对话: $CONV_NAME"
curl -s -X POST "$BASE_URL/api/conversations" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$CONV_NAME\",
    \"display_name\": \"演示对话001\",
    \"agent_name\": \"$AGENT_NAME\",
    \"welcome_message\": \"您好！我是智能客服助手，很高兴为您服务。请问有什么可以帮助您的？\"
  }" | jq '.'
print_success "对话创建成功"

# 6. 测试问答
print_step "6. 测试问答 - 问题 1: 你们提供什么服务？"
curl -s -X POST "$BASE_URL/api/chat/$CONV_NAME/message" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "你们提供什么服务？"
  }' | jq '.'
print_success "回答完成"

sleep 1

print_step "7. 测试问答 - 问题 2: 联系方式是什么？"
curl -s -X POST "$BASE_URL/api/chat/$CONV_NAME/message" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "联系方式是什么？"
  }' | jq '.'
print_success "回答完成"

sleep 1

print_step "8. 测试问答 - 问题 3: 支持哪些文件格式？"
curl -s -X POST "$BASE_URL/api/chat/$CONV_NAME/message" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "支持哪些文件格式？"
  }' | jq '.'
print_success "回答完成"

# 9. 查看所有资源
print_step "9. 查看系统资源"
echo "【智能体列表】"
curl -s "$BASE_URL/api/agents" | jq '.agents[] | {name, display_name, status, knowledge_base}'
echo ""
echo "【对话列表】"
curl -s "$BASE_URL/api/conversations" | jq '.conversations[] | {name, display_name, agent: .agent.name, message_count}'
print_success "资源查询完成"

# 10. 总结
echo ""
echo "=================================================="
echo -e "${GREEN}🎉 测试全部完成！${NC}"
echo "=================================================="
echo ""
echo "API 文档: $BASE_URL/docs"
echo "健康检查: $BASE_URL/health"
echo ""
echo "创建的资源："
echo "  - 智能体: $AGENT_NAME"
echo "  - 对话: $CONV_NAME"
echo "  - 知识库文档: 1 个"
echo ""
echo "清理资源（可选）："
echo "  curl -X DELETE $BASE_URL/api/agents/$AGENT_NAME"
echo "  curl -X DELETE $BASE_URL/api/conversations/$CONV_NAME"
echo ""
