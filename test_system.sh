#!/bin/bash
# 快速测试脚本 - 验证数据库迁移和应用功能

set -e

echo "🧪 开始测试 Atlas 应用..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
PASSED=0
FAILED=0

# 测试函数
test_passed() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED++))
}

test_failed() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED++))
}

test_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 1. 测试数据库连接
echo "📊 测试 PostgreSQL 连接..."
if uv run python test_db_connection.py 2>&1 | grep -q "连接成功"; then
    test_passed "PostgreSQL 连接正常"
else
    test_failed "PostgreSQL 连接失败"
fi
echo ""

# 2. 测试配置加载
echo "⚙️  测试配置加载..."
CONFIG_OUTPUT=$(uv run python -c "from core.config import settings; print(f'{settings.DATABASE_URL}|{settings.MILVUS_HOST}:{settings.MILVUS_PORT}')" 2>&1)
if echo "$CONFIG_OUTPUT" | grep -q "postgresql"; then
    test_passed "PostgreSQL 配置正确"
else
    test_failed "PostgreSQL 配置错误"
fi

if echo "$CONFIG_OUTPUT" | grep -q "117.72.204.201:19530"; then
    test_passed "Milvus 配置正确"
else
    test_failed "Milvus 配置错误"
fi
echo ""

# 3. 测试数据库初始化
echo "🗄️  测试数据库初始化..."
if uv run python create_admin.py 2>&1 | grep -q "管理员"; then
    test_passed "数据库初始化成功"
else
    test_failed "数据库初始化失败"
fi
echo ""

# 4. 启动应用（后台）
echo "🚀 启动应用服务..."
uv run python app.py > /tmp/atlas_test.log 2>&1 &
APP_PID=$!
test_info "应用 PID: $APP_PID"
sleep 8  # 等待启动

# 5. 测试健康检查
echo "💓 测试健康检查..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    test_passed "健康检查通过"
else
    test_failed "健康检查失败"
fi
echo ""

# 6. 测试登录认证
echo "🔐 测试登录认证..."
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')

if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
    test_passed "登录认证成功"
    TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
else
    test_failed "登录认证失败"
    TOKEN=""
fi
echo ""

# 7. 测试受保护的 API
if [ -n "$TOKEN" ]; then
    echo "🛡️  测试受保护的 API..."
    
    # 测试获取智能体列表
    if curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/agents | grep -q "\[\]"; then
        test_passed "智能体 API 正常"
    else
        test_failed "智能体 API 异常"
    fi
    
    # 测试获取客服列表
    if curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/conversations | grep -q "\[\]"; then
        test_passed "客服 API 正常"
    else
        test_failed "客服 API 异常"
    fi
    echo ""
else
    test_info "跳过受保护 API 测试（未获取到 Token）"
fi

# 8. 测试 Milvus 连接
echo "🔍 测试 Milvus 连接..."
if tail -20 /tmp/atlas_test.log | grep -q "Milvus 连接成功"; then
    test_passed "Milvus 连接正常"
else
    test_failed "Milvus 连接失败"
fi
echo ""

# 停止应用
echo "🛑 停止测试服务..."
kill $APP_PID 2>/dev/null || true
sleep 2
test_info "应用已停止"
echo ""

# 测试总结
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 测试总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo -e "总计: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！系统运行正常。${NC}"
    exit 0
else
    echo -e "${RED}⚠️  部分测试失败，请检查日志: /tmp/atlas_test.log${NC}"
    exit 1
fi
