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
COPY pyproject.toml uv.lock ./
COPY . .

# Install dependencies using uv (use pip install for better compatibility)
RUN uv sync --frozen

# Create necessary directories
RUN mkdir -p metadata_store uploads

# Expose port
EXPOSE 8000

# Run the application using uv
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
