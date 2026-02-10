# Runbook: Deployment

**Last Updated**: 2026-02-10
**Owner**: Platform Team
**Severity**: Standard Change

## Prerequisites

- kubectl configured with cluster access
- Docker registry credentials
- Latest code on `master` branch
- All CI tests passing (green)

## Steps

### 1. Build and Push Docker Image

```bash
# Build the production image
cd production/
docker build -t fte-crm-api:$(git rev-parse --short HEAD) .
docker tag fte-crm-api:$(git rev-parse --short HEAD) registry.example.com/fte-crm-api:$(git rev-parse --short HEAD)
docker tag fte-crm-api:$(git rev-parse --short HEAD) registry.example.com/fte-crm-api:latest

# Push to registry
docker push registry.example.com/fte-crm-api:$(git rev-parse --short HEAD)
docker push registry.example.com/fte-crm-api:latest
```

### 2. Update Deployment Manifests

```bash
# Update image tag in deployment YAML
# Edit k8s/deployment-api.yaml and k8s/deployment-worker.yaml
# Change image tag to the new commit hash
```

### 3. Apply to Cluster

```bash
# Apply namespace and configs first
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# Apply deployments
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/deployment-worker.yaml

# Verify rollout
kubectl -n fte-crm rollout status deployment/fte-api --timeout=120s
kubectl -n fte-crm rollout status deployment/fte-worker --timeout=120s
```

### 4. Smoke Test

```bash
# Check health endpoint
kubectl -n fte-crm port-forward svc/fte-api 8000:8000 &
curl -s http://localhost:8000/health | jq .

# Expected: {"status": "healthy", "database": "connected", ...}
```

### 5. Verify

```bash
# Check pod status
kubectl -n fte-crm get pods

# Check logs for errors
kubectl -n fte-crm logs -l app=fte-api --tail=50
kubectl -n fte-crm logs -l app=fte-worker --tail=50

# Check HPA
kubectl -n fte-crm get hpa
```

## Rollback

If issues are detected, see [rollback.md](./rollback.md).

## Post-Deployment

- Monitor Grafana dashboard for 15 minutes
- Check error rate stays below 1%
- Verify Kafka consumer lag is not increasing
- Notify team in Slack: #fte-deploys
