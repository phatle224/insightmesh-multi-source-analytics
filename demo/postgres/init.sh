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

CREATE TABLE IF NOT EXISTS public.customers (
  id integer PRIMARY KEY,
  customer_name text NOT NULL,
  region text NOT NULL,
  created_at date NOT NULL
);
CREATE TABLE IF NOT EXISTS public.categories (
  id integer PRIMARY KEY,
  category_name text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS public.products (
  id integer PRIMARY KEY,
  category_id integer NOT NULL REFERENCES public.categories(id),
  product_name text NOT NULL,
  unit_price numeric(12,2) NOT NULL CHECK (unit_price >= 0)
);
CREATE TABLE IF NOT EXISTS public.orders (
  id integer PRIMARY KEY,
  customer_id integer NOT NULL REFERENCES public.customers(id),
  ordered_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('completed', 'cancelled', 'pending', 'refunded'))
);
CREATE TABLE IF NOT EXISTS public.order_items (
  order_id integer NOT NULL REFERENCES public.orders(id),
  product_id integer NOT NULL REFERENCES public.products(id),
  quantity integer NOT NULL CHECK (quantity > 0),
  unit_price numeric(12,2) NOT NULL CHECK (unit_price >= 0),
  PRIMARY KEY (order_id, product_id)
);

INSERT INTO public.customers (id, customer_name, region, created_at) VALUES
  (1, 'Acme Retail', 'North', '2024-01-10'),
  (2, 'Bluebird Market', 'South', '2024-02-14'),
  (3, 'Cedar Goods', 'Central', '2024-03-22'),
  (4, 'Delta Outfitters', 'West', '2024-05-05'),
  (5, 'Evergreen Shop', 'East', '2024-06-18')
ON CONFLICT (id) DO NOTHING;
INSERT INTO public.categories (id, category_name) VALUES
  (1, 'Electronics'), (2, 'Home'), (3, 'Outdoors')
ON CONFLICT (id) DO NOTHING;
INSERT INTO public.products (id, category_id, product_name, unit_price) VALUES
  (1, 1, 'Wireless Keyboard', 79.00),
  (2, 1, 'USB-C Hub', 49.00),
  (3, 2, 'Desk Lamp', 65.00),
  (4, 2, 'Storage Basket', 28.00),
  (5, 3, 'Daypack', 95.00),
  (6, 3, 'Insulated Bottle', 32.00)
ON CONFLICT (id) DO NOTHING;
INSERT INTO public.orders (id, customer_id, ordered_at, status) VALUES
  (1001, 1, '2025-01-05 09:30:00+00', 'completed'),
  (1002, 2, '2025-01-08 14:10:00+00', 'completed'),
  (1003, 1, '2025-02-03 11:20:00+00', 'completed'),
  (1004, 3, '2025-02-12 16:45:00+00', 'cancelled'),
  (1005, 4, '2025-03-01 08:15:00+00', 'completed'),
  (1006, 5, '2025-03-16 13:05:00+00', 'refunded'),
  (1007, 2, '2025-04-02 10:00:00+00', 'pending'),
  (1008, 3, '2025-04-18 15:25:00+00', 'completed')
ON CONFLICT (id) DO NOTHING;
INSERT INTO public.order_items (order_id, product_id, quantity, unit_price) VALUES
  (1001, 1, 2, 79.00), (1001, 3, 1, 65.00),
  (1002, 2, 3, 49.00), (1002, 4, 2, 28.00),
  (1003, 5, 1, 95.00), (1003, 6, 2, 32.00),
  (1004, 3, 2, 65.00),
  (1005, 5, 2, 95.00), (1005, 1, 1, 79.00),
  (1006, 4, 4, 28.00),
  (1007, 2, 1, 49.00),
  (1008, 6, 3, 32.00), (1008, 3, 1, 65.00)
ON CONFLICT (order_id, product_id) DO NOTHING;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO demo_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO demo_reader;
SQL
