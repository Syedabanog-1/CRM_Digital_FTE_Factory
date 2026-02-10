# Runbook: Scaling

**Last Updated**: 2026-02-10
**Owner**: Platform Team
**Severity**: Standard Change

## Current Configuration

| Component | Min Replicas | Max Replicas | CPU Request | Memory Request |
|-----------|-------------|-------------|-------------|----------------|
| API | 3 | 10 | 250m | 256Mi |
| Worker | 3 | 10 | 250m | 256Mi |

HPA targets: 70% CPU utilization (API), 70% CPU utilization (Worker).

## When to Scale

### Auto-Scaling (HPA)
The HPA automatically scales based on CPU utilization. No manual action needed unless:
- HPA is at max replicas and still overloaded
- Need to pre-scale for expected traffic spike

### Manual Scale-Up

```bash
# Check current state
kubectl -n fte-crm get hpa
kubectl -n fte-crm get pods

# Temporarily increase API replicas
kubectl -n fte-crm scale deployment/fte-api --replicas=8

# Temporarily increase Worker replicas
kubectl -n fte-crm scale deployment/fte-worker --replicas=8
```

### Manual Scale-Down

```bash
# Scale back to normal
kubectl -n fte-crm scale deployment/fte-api --replicas=3
kubectl -n fte-crm scale deployment/fte-worker --replicas=3
```

## Identifying Bottlenecks

### CPU Bound (API)
- Symptom: High p95 latency, HPA scaling up
- Action: Scale API replicas or increase CPU request

### Memory Bound
- Symptom: OOMKilled pods
- Action: Increase memory limits in deployment YAML

### Kafka Consumer Lag
- Symptom: Growing lag on `fte.tickets.incoming` topic
- Action: Scale Worker replicas

### Database Connection Pool
- Symptom: Connection timeout errors in logs
- Action: Increase `DB_MAX_POOL_SIZE` in ConfigMap, restart pods

## Updating HPA Limits

```bash
# Edit HPA max replicas
kubectl -n fte-crm patch hpa fte-api-hpa -p '{"spec":{"maxReplicas":15}}'
kubectl -n fte-crm patch hpa fte-worker-hpa -p '{"spec":{"maxReplicas":15}}'
```

## Updating Resource Limits

Edit `k8s/deployment-api.yaml` or `k8s/deployment-worker.yaml`:

```yaml
resources:
  requests:
    cpu: "500m"      # Increase from 250m
    memory: "512Mi"  # Increase from 256Mi
  limits:
    cpu: "1000m"
    memory: "1Gi"
```

Then apply: `kubectl apply -f k8s/deployment-api.yaml`
