#!/bin/sh
set -eu

# No shell tracing: credentials must not enter the container logs.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=reader_password="$DEMO_READER_PASSWORD" <<'SQL'
SELECT 'CREATE ROLE demo_reader LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'demo_reader')\gexec
ALTER ROLE demo_reader PASSWORD :'reader_password';
ALTER ROLE demo_reader SET default_transaction_read_only = on;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE TEMPORARY ON DATABASE insightmesh_demo FROM PUBLIC;
GRANT CONNECT ON DATABASE insightmesh_demo TO demo_reader;
GRANT USAGE ON SCHEMA public TO demo_reader;
CREATE TABLE IF NOT EXISTS public.foundation_probe (
  id integer PRIMARY KEY,
  label text NOT NULL
);
INSERT INTO public.foundation_probe (id, label) VALUES (1, 'foundation-ready')
ON CONFLICT (id) DO NOTHING;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO demo_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO demo_reader;
SQL
