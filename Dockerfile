# CRM Digital FTE Factory - Multi-stage Docker build
# Stage 1: Build React frontend
# Stage 2: Install Python dependencies
# Stage 3: Runtime (serves both API + frontend)
# Build context: repository root

# ---- Stage 1: Build React Frontend ----
FROM node:18-slim AS frontend-builder

WORKDIR /app/web-form
COPY web-form/package.json web-form/package-lock.json* ./
RUN npm ci --production=false 2>/dev/null || npm install
COPY web-form/ ./
RUN npm run build

# ---- Stage 2: Install Python Dependencies ----
FROM python:3.11-slim AS python-builder

WORKDIR /app
COPY production/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 3: Runtime ----
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=python-builder /install /usr/local

# Copy application code
COPY production/ production/
COPY src/ src/
COPY context/ context/
COPY pyproject.toml .

# Copy built React frontend
COPY --from=frontend-builder /app/web-form/build web-form/build/

# Render uses PORT env var (default 10000), local dev uses 8000
ENV PORT=10000
EXPOSE ${PORT}

# Use shell form so $PORT is expanded at runtime
CMD uvicorn production.api.main:app --host 0.0.0.0 --port $PORT
