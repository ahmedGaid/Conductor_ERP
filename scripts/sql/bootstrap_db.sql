-- One-time database bootstrap. Run as the postgres superuser.
-- Creates the application role and database used by DATABASE_URL.
-- Safe to re-run.

DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'erp') THEN
      CREATE ROLE erp LOGIN PASSWORD 'erp';
   END IF;
END
$$;

SELECT 'CREATE DATABASE erp OWNER erp'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'erp')\gexec

GRANT ALL PRIVILEGES ON DATABASE erp TO erp;
