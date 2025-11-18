FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (including PostgreSQL dev libraries)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY . .

# Install dependencies using uv (use pip install for better compatibility)
RUN uv pip install --system -e .

# Create necessary directories
RUN mkdir -p metadata_store uploads

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBUG=false

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application using uv
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
