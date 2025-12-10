# LLM Council Backend Dockerfile
# Multi-stage build for smaller final image

FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Production stage
FROM python:3.11-slim

# Install runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash council

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY backend/ ./backend/
COPY pyproject.toml ./

# Set ownership
RUN chown -R council:council /app

# Create data directory with proper permissions
RUN mkdir -p /app/data/conversations && chown -R council:council /app/data

USER council

# Add virtual environment to path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default port
ENV PORT=8001

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run with uvicorn, graceful shutdown supported
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
