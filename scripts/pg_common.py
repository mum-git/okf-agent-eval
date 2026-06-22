#!/usr/bin/env python3
"""Shared PostgreSQL access for the OKF retrieval-layer experiment.

PostgreSQL is provided by the `pgserver` pip package (a self-contained Postgres
16 that runs from a user directory — no sudo, no system service). The server is
started lazily and reused across processes via pgserver's file locking, so every
script can just call `connect()` without worrying about lifecycle.

This module MUST run under the project venv that has pgserver + psycopg:
    .pgvenv/bin/python scripts/<script>.py ...

Environment:
    OKF_PG_DATA   data directory for the cluster (default: ~/.okf-pg/data)
    OKF_PG_DB     database name (default: okf_benchmark)
"""
from __future__ import annotations

import os
from pathlib import Path

import pgserver
import psycopg

DB_NAME = os.environ.get("OKF_PG_DB", "okf_benchmark")


def data_dir() -> Path:
    raw = os.environ.get("OKF_PG_DATA")
    path = Path(raw) if raw else Path.home() / ".okf-pg" / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_server() -> "pgserver.PostgresServer":
    """Ensure the bundled Postgres is running and return the server handle."""
    return pgserver.get_server(data_dir())


def ensure_database() -> None:
    """Create the okf_benchmark database if it does not exist."""
    srv = get_server()
    exists = srv.psql(
        f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'"
    ).strip()
    if "1" not in exists:
        srv.psql(f"CREATE DATABASE {DB_NAME}")


def conninfo() -> str:
    """libpq connection string targeting the okf_benchmark database."""
    return f"postgresql://postgres:@/{DB_NAME}?host={data_dir()}"


def connect() -> "psycopg.Connection":
    """Return a psycopg connection to the okf_benchmark database."""
    ensure_database()
    return psycopg.connect(conninfo())


if __name__ == "__main__":
    # Smoke test / used by setup script to confirm the cluster is reachable.
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            print(cur.fetchone()[0])
    print("conninfo:", conninfo())
