"""Run inside backend: docker compose exec backend python tests/foundation_smoke.py."""

import json
import os
from urllib.request import urlopen

import psycopg
from psycopg.errors import InsufficientPrivilege, ReadOnlySqlTransaction

for url in ("http://backend:8000/api/v1/health", "http://frontend:3000/api/health"):
    with urlopen(url, timeout=15) as response:
        assert json.load(response)["status"] == "ok"
    print("PASS: HTTP health and service DNS")

with psycopg.connect(connect_timeout=5) as conn:
    assert conn.execute("SELECT '[1,2,3]'::vector").fetchone()
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone() == ("a7c1f6d9e240",)
print("PASS: pgvector and migration revision")

password = os.environ["DEMO_READER_PASSWORD"]
with psycopg.connect(
    host="demo-postgres",
    dbname="insightmesh_demo",
    user="demo_reader",
    password=password,
    connect_timeout=5,
    autocommit=True,
) as conn:
    assert conn.execute("SELECT count(*) FROM public.foundation_probe").fetchone() == (1,)
    assert conn.execute("SELECT count(*) FROM public.orders").fetchone() == (8,)
    for read_only in (True, False):
        # Even disabling the convenience read-only setting must not grant writes.
        conn.execute(f"SET default_transaction_read_only = {'on' if read_only else 'off'}")
        try:
            with conn.transaction():
                conn.execute("UPDATE public.foundation_probe SET label = label WHERE id = 1")
                raise AssertionError("Reader unexpectedly has write permission")
        except (InsufficientPrivilege, ReadOnlySqlTransaction):
            pass
print("PASS: demo SELECT allowed; writes rejected with and without read-only default")
