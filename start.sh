#!/bin/bash
# Echo 智能客服后端启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=================================================="
echo "  Echo 智能客服后端系统"
echo -e "==================================================${NC}"
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ 虚拟环境不存在，请先运行: uv venv${NC}"
    exit 1
fi

# 检查 uvicorn
if [ ! -f ".venv/bin/uvicorn" ]; then
    echo -e "${YELLOW}⚠️  uvicorn 未安装，正在安装依赖...${NC}"
    uv pip install pymilvus langchain-milvus fastapi 'uvicorn[standard]' \
        sqlalchemy python-multipart python-dotenv pydantic pydantic-settings \
        langchain langchain-community langchain-openai langchain-text-splitters \
        beautifulsoup4 lxml pypdf
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env 文件不存在，请从 .env.example 复制并配置${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${BLUE}已创建 .env 文件，请编辑配置后重新运行${NC}"
        exit 1
    fi
fi

# 检查是否已有进程在运行
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  端口 8000 已被占用${NC}"
    echo "是否停止现有进程？(y/n)"
    read -r response
    if [ "$response" = "y" ]; then
        PID=$(lsof -Pi :8000 -sTCP:LISTEN -t)
        kill "$PID"
        echo -e "${GREEN}✅ 已停止进程 $PID${NC}"
        sleep 2
    else
        echo "使用其他端口启动..."
        PORT=8001
    fi
else
    PORT=8000
fi

# 启动服务器
echo ""
echo -e "${GREEN}🚀 正在启动服务器...${NC}"
echo -e "${BLUE}   主机: 0.0.0.0${NC}"
echo -e "${BLUE}   端口: $PORT${NC}"
echo -e "${BLUE}   模式: ${1:-production}${NC}"
echo ""

if [ "$1" = "dev" ] || [ "$1" = "--reload" ]; then
    # 开发模式（热重载）
    echo -e "${YELLOW}开发模式 (热重载已启用)${NC}"
    .venv/bin/uvicorn app:app --host 0.0.0.0 --port "$PORT" --reload
else
    # 生产模式
    echo -e "${GREEN}生产模式${NC}"
    echo ""
    echo -e "${BLUE}访问地址:${NC}"
    echo "  - API 文档: http://localhost:$PORT/docs"
    echo "  - ReDoc: http://localhost:$PORT/redoc"
    echo "  - 健康检查: http://localhost:$PORT/health"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
    echo ""
    .venv/bin/uvicorn app:app --host 0.0.0.0 --port "$PORT"
fi
