"""
Database Connection for FastAPI
ADR-009: PostgreSQL connection with async support
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg


DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER', 'bfagent')}:"
    f"{os.getenv('DB_PASSWORD', 'bfagent_dev_2024')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:"
    f"{os.getenv('DB_PORT', '5434')}/"
    f"{os.getenv('DB_NAME', 'cadhub')}"
)

pool: asyncpg.Pool | None = None


async def init_db():
    """Initialize database connection pool."""
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


async def close_db():
    """Close database connection pool."""
    global pool
    if pool:
        await pool.close()


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a database connection from the pool."""
    global pool
    if not pool:
        await init_db()
    async with pool.acquire() as conn:
        yield conn


async def fetch_all(query: str, *args) -> list[dict]:
    """Execute query and return all rows as dicts."""
    async with get_connection() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def fetch_one(query: str, *args) -> dict | None:
    """Execute query and return first row as dict."""
    async with get_connection() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def execute(query: str, *args) -> str:
    """Execute a query without returning results."""
    async with get_connection() as conn:
        return await conn.execute(query, *args)
