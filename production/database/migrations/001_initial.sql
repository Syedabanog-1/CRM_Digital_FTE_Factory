-- Migration 001: Initial schema
-- Stage 2 Specialization - CRM Digital FTE Factory
-- Apply: psql -d fte_crm -f 001_initial.sql
-- Rollback: See DROP statements at bottom

BEGIN;

-- Load the full schema
\i ../schema.sql

COMMIT;

-- ROLLBACK (run manually if needed):
-- BEGIN;
-- DROP TABLE IF EXISTS agent_metrics CASCADE;
-- DROP TABLE IF EXISTS channel_configs CASCADE;
-- DROP TABLE IF EXISTS knowledge_base CASCADE;
-- DROP TABLE IF EXISTS tickets CASCADE;
-- DROP TABLE IF EXISTS messages CASCADE;
-- DROP TABLE IF EXISTS conversations CASCADE;
-- DROP TABLE IF EXISTS customer_identifiers CASCADE;
-- DROP TABLE IF EXISTS customers CASCADE;
-- DROP EXTENSION IF EXISTS vector;
-- DROP EXTENSION IF EXISTS "uuid-ossp";
-- COMMIT;
