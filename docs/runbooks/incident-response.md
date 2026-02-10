# Runbook: Incident Response

**Last Updated**: 2026-02-10
**Owner**: Platform Team

## Severity Levels

| Level | Description | Response Time | Examples |
|-------|------------|---------------|----------|
| P1 | Service down, all customers affected | 15 minutes | API returning 500s, DB down |
| P2 | Degraded, major feature broken | 30 minutes | One channel not working, high latency |
| P3 | Minor issue, workaround available | 4 hours | Dashboard not loading, non-critical errors |
| P4 | Cosmetic or informational | Next business day | Log noise, minor UI issues |

## Diagnostic Checklist

### 1. Check Service Health

```bash
# API health
curl -s http://localhost:8000/health | jq .

# Pod status
kubectl -n fte-crm get pods
kubectl -n fte-crm describe pod <pod-name>  # if CrashLoopBackOff
```

### 2. Check Logs

```bash
# API logs (last 5 minutes)
kubectl -n fte-crm logs -l app=fte-api --since=5m --tail=100

# Worker logs
kubectl -n fte-crm logs -l app=fte-worker --since=5m --tail=100

# Look for ERROR level entries
kubectl -n fte-crm logs -l app=fte-api --since=5m | grep ERROR
```

### 3. Check Database

```bash
# Connection test
kubectl -n fte-crm exec -it deploy/fte-api -- python -c "
import asyncio
from production.database.queries import create_pool, health_check
async def check():
    await create_pool()
    result = await health_check()
    print(f'DB healthy: {result}')
asyncio.run(check())
"

# Active connections
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "SELECT count(*) FROM pg_stat_activity;"
```

### 4. Check Kafka

```bash
# Consumer group lag
kubectl -n fte-crm exec -it kafka-0 -- kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group fte-workers \
    --describe

# Topic message count
kubectl -n fte-crm exec -it kafka-0 -- kafka-run-class.sh kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 \
    --topic fte.tickets.incoming
```

### 5. Check Resources

```bash
# Node resources
kubectl top nodes

# Pod resources
kubectl -n fte-crm top pods

# HPA status
kubectl -n fte-crm get hpa
```

## Common Issues & Fixes

### API Returning 500 Errors
1. Check logs for stack traces
2. Check DB connectivity
3. Check environment variables (ConfigMap)
4. If recent deployment, rollback (see [rollback.md](./rollback.md))

### Kafka Consumer Lag Growing
1. Check worker pods are running
2. Check worker logs for errors
3. Scale workers: `kubectl -n fte-crm scale deployment/fte-worker --replicas=6`
4. Check if DLQ topic has messages (indicates processing failures)

### Database Connection Exhausted
1. Check `pg_stat_activity` for idle connections
2. Restart API pods: `kubectl -n fte-crm rollout restart deployment/fte-api`
3. Increase pool size if persistent

### OOMKilled Pods
1. Check `kubectl describe pod <pod>` for OOMKilled
2. Increase memory limits in deployment YAML
3. Apply and restart

## Communication Template

```
INCIDENT: [P1/P2/P3/P4] - [Brief Description]
STATUS: [Investigating/Identified/Resolved]
IMPACT: [Number of affected customers/channels]
STARTED: [Time UTC]
ETA: [Expected resolution time]
NEXT UPDATE: [Time of next update]
```

## Post-Mortem Template

After P1/P2 incidents, create a post-mortem within 48 hours:

1. **Timeline**: Chronological events
2. **Root Cause**: What caused the issue
3. **Impact**: Customers affected, duration
4. **Resolution**: How it was fixed
5. **Action Items**: Preventive measures with owners and due dates
