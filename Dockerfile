# ==============================================================================
# Sentinel AI — Unified Production Multi-Stage Dockerfile
# Optimized for Render Web Service (Free Tier) & Local Containerization
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build the React Production Frontend
# ------------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

# Install dependencies using package-lock.json for reproducible builds
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source code and build config
COPY frontend/ ./

# Compile React SPA (runs tsc -b && vite build)
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Unified Python + FastAPI Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner
WORKDIR /app

# Ensure Python output is unbuffered and clean
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install lightweight system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code, configuration, and data scaffolding
COPY . .

# Normalize line endings from Windows checkouts
RUN find /app -name "*.py" -print0 | xargs -0 dos2unix --quiet 2>/dev/null || true

# Copy compiled React production assets from the builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose default port (Render dynamically sets $PORT at runtime)
EXPOSE 8000

# Health check checking /api/health against the active port
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.getenv('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health')" || exit 1

# Start the unified FastAPI server listening on 0.0.0.0 and $PORT
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]