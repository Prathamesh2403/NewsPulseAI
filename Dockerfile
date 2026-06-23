FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create ChromaDB data directories for both dev and production paths
# Dev / Railway: /app/data/vector_db
# Render persistent disk: /opt/render/project/src/data/vector_db
RUN mkdir -p /app/data/vector_db
RUN mkdir -p /opt/render/project/src/data/vector_db

# Expose API port
EXPOSE 8000

# Default command (overridden per service in Railway)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
