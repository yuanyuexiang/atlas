# ============================================
# Stage 1: Builder - 使用 uv 官方镜像构建
# ============================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

WORKDIR /app

# 安装编译依赖（PostgreSQL、C 编译器等）
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 仅复制依赖文件（利用 Docker 缓存）
COPY pyproject.toml uv.lock ./

# 安装 Python 依赖
RUN uv sync --frozen --no-dev

# 复制完整项目代码
COPY . .

# ============================================
# Stage 2: Runtime - 精简运行时镜像
# ============================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# 仅安装运行时依赖（无需 gcc）
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制 uv 二进制（官方镜像中 uv 在 /usr/local/bin）
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# 从 builder 复制虚拟环境和项目
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# 确保目录存在
RUN mkdir -p metadata_store uploads

# 设置生产环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBUG=false \
    PATH="/app/.venv/bin:$PATH"

# 暴露端口
EXPOSE 8000

# 使用 uv run 启动应用
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
