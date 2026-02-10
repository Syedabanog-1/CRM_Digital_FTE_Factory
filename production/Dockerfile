# Stage 2 Specialization - Multi-stage Python build
# Single image for both API and Worker (different CMD)

# Builder stage
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Default: run the API server
# Override with: command: ["python", "-m", "workers"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
