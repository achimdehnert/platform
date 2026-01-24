from datetime import datetime, timezone
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi import HTTPException
import psycopg2
from psycopg2.extras import Json

app = FastAPI(title="MCP Hub API", version="0.1.0")


def _pg_conn():
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    db = os.environ.get("POSTGRES_DB", "bfagent_dev")
    user = os.environ.get("POSTGRES_USER", "bfagent")
    password = os.environ.get("POSTGRES_PASSWORD", "bfagent_dev_2024")
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=password,
        options="-c lc_messages=C -c client_encoding=UTF8",
    )


def _ensure_tables() -> None:
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mcphub_dlm_report_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()
    finally:
        conn.close()


@app.get("/api/v1/health")
def health() -> dict:
    _ensure_tables()
    return {"status": "ok", "service": "mcphub-api", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/dlm/report/overview")
def dlm_report_overview() -> dict:
    _ensure_tables()
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload
                FROM mcphub_dlm_report_cache
                WHERE cache_key = %s
                """,
                ("overview",),
            )
            row = cur.fetchone()
        if not row:
            return {
                "kpis": {
                    "repositories": 0,
                    "documents": 0,
                    "current": 0,
                    "stale": 0,
                    "outdated": 0,
                },
                "repositories": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "version": "v1",
            }
        return row[0]
    finally:
        conn.close()


@app.post("/api/v1/dlm/report/overview")
def upsert_dlm_report_overview(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_tables()

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be an object")

    generated_at: Optional[str] = payload.get("generated_at")
    if not generated_at:
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload.setdefault("version", "v1")

    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO mcphub_dlm_report_cache (cache_key, payload, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (cache_key)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                """,
                ("overview", Json(payload)),
            )
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok"}
