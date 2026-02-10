# Runbook: Rollback

**Last Updated**: 2026-02-10
**Owner**: Platform Team
**Severity**: Emergency Change

## When to Rollback

- Health endpoint returning errors
- Error rate > 5% for more than 2 minutes
- Kafka consumer lag growing unboundedly
- Database connection errors
- Customer-reported issues correlated with deployment

## Steps

### 1. Rollback Deployments

```bash
# Rollback API to previous revision
kubectl -n fte-crm rollout undo deployment/fte-api

# Rollback Worker to previous revision
kubectl -n fte-crm rollout undo deployment/fte-worker

# Verify rollback
kubectl -n fte-crm rollout status deployment/fte-api --timeout=60s
kubectl -n fte-crm rollout status deployment/fte-worker --timeout=60s
```

### 2. Verify Previous Version Running

```bash
# Check current image
kubectl -n fte-crm get deployment fte-api -o jsonpath='{.spec.template.spec.containers[0].image}'

# Check pods are running
kubectl -n fte-crm get pods

# Health check
curl -s http://localhost:8000/health | jq .
```

### 3. Check System Recovery

```bash
# Monitor error rate (should drop within 1-2 minutes)
# Check Grafana dashboard or:
kubectl -n fte-crm logs -l app=fte-api --tail=20 --since=2m

# Verify Kafka consumer lag is decreasing
# Check Kafka consumer group status
```

### 4. Notify

- Post in #fte-incidents: "Rolled back deployment [commit-hash] due to [reason]"
- Create incident ticket if customer impact occurred
- Schedule post-mortem if P1/P2 severity

## Rollback to Specific Revision

```bash
# List revision history
kubectl -n fte-crm rollout history deployment/fte-api

# Rollback to specific revision
kubectl -n fte-crm rollout undo deployment/fte-api --to-revision=N
```

## Time Target

Rollback should be complete within **5 minutes** of decision to rollback.
