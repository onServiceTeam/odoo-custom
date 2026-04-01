-- PostgreSQL hardening for Odoo database
-- This runs on first initialization only

-- Enforce scram-sha-256 password encryption
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Connection security
ALTER SYSTEM SET ssl = 'off';  -- Internal Docker network, SSL handled by nginx

-- Logging for audit
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_statement = 'ddl';

-- Performance tuning for Odoo
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET max_connections = '100';
ALTER SYSTEM SET checkpoint_completion_target = '0.9';
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET random_page_cost = '1.1';
ALTER SYSTEM SET effective_io_concurrency = '200';

SELECT pg_reload_conf();
