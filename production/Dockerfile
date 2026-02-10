# Stage 2 Specialization - Multi-stage Python build
# Single image for both API and Worker (different CMD)
# Build context: repository root (not production/)

# Builder stage
FROM python:3.11-slim AS builder

WORKDIR /app
COPY production/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code (entire repo for proper package imports)
COPY production/ production/
COPY src/ src/
COPY context/ context/
COPY pyproject.toml .

# Expose API port
EXPOSE 8000

# Default: run the API server
# Override with: command: ["python", "-m", "production.workers"]
CMD ["uvicorn", "production.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
