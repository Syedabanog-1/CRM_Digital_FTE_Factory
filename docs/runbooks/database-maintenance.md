# Runbook: Database Maintenance

**Last Updated**: 2026-02-10
**Owner**: Platform Team
**Database**: PostgreSQL 16+ with pgvector

## Backup

### Full Backup

```bash
# From Kubernetes
kubectl -n fte-crm exec -it postgres-0 -- pg_dump -U fte -d fte_crm -F c -f /tmp/backup.dump
kubectl -n fte-crm cp postgres-0:/tmp/backup.dump ./backups/fte_crm_$(date +%Y%m%d).dump

# From docker-compose (local)
docker exec production-postgres-1 pg_dump -U fte -d fte_crm -F c -f /tmp/backup.dump
docker cp production-postgres-1:/tmp/backup.dump ./backups/fte_crm_$(date +%Y%m%d).dump
```

### Restore from Backup

```bash
# Restore (WARNING: destructive - drops and recreates)
kubectl -n fte-crm cp ./backups/fte_crm_20260210.dump postgres-0:/tmp/restore.dump
kubectl -n fte-crm exec -it postgres-0 -- pg_restore -U fte -d fte_crm --clean --if-exists /tmp/restore.dump
```

## Vacuum & Analyze

Run weekly or after large data changes:

```bash
# Full vacuum and analyze (locks tables briefly)
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "VACUUM ANALYZE;"

# Vacuum specific high-churn tables
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "
VACUUM ANALYZE messages;
VACUUM ANALYZE tickets;
VACUUM ANALYZE agent_metrics;
"
```

## Reindex

Run monthly or if query performance degrades:

```bash
# Reindex all indexes
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "REINDEX DATABASE fte_crm;"

# Reindex specific table
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "REINDEX TABLE messages;"

# Rebuild pgvector index specifically
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "REINDEX INDEX idx_knowledge_base_embedding;"
```

## Check Table Sizes

```bash
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::text)) AS total_size,
    pg_size_pretty(pg_relation_size(tablename::text)) AS data_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::text) DESC;
"
```

## Connection Pool Monitoring

```bash
# Active connections
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "
SELECT
    state,
    count(*) as count
FROM pg_stat_activity
WHERE datname = 'fte_crm'
GROUP BY state;
"

# Connection limit
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "SHOW max_connections;"
```

## pgvector Index Management

```bash
# Check vector index stats
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::text)) as index_size
FROM pg_indexes
WHERE tablename = 'knowledge_base';
"

# Rebuild vector index (if search quality degrades after many inserts)
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "
DROP INDEX IF EXISTS idx_knowledge_base_embedding;
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
"
```

## Schema Migrations

```bash
# Apply new migration
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm < production/database/migrations/NNN_description.sql

# Check migration was applied
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "\dt"
```

## Emergency: Connection Storm

If all connections are exhausted:

```bash
# Kill idle connections
kubectl -n fte-crm exec -it postgres-0 -- psql -U fte -d fte_crm -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND pid <> pg_backend_pid()
AND datname = 'fte_crm';
"

# Then restart API pods to reset connection pools
kubectl -n fte-crm rollout restart deployment/fte-api
kubectl -n fte-crm rollout restart deployment/fte-worker
```
