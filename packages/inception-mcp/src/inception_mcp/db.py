"""
Database Connection Module
==========================

PostgreSQL connection handling for the Inception MCP Server.
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import psycopg
from psycopg.rows import dict_row


def get_connection_string() -> str:
    """Get database connection string from environment."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/platform"
    )


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """Get async database connection."""
    conn = await psycopg.AsyncConnection.connect(
        get_connection_string(),
        row_factory=dict_row,
    )
    try:
        yield conn
    finally:
        await conn.close()


async def execute_query(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute a query and return results."""
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


async def execute_one(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    """Execute a query and return single result."""
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchone()


async def execute_write(sql: str, params: tuple | None = None) -> int:
    """Execute an INSERT/UPDATE/DELETE and return affected rows."""
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            await conn.commit()
            return cur.rowcount


async def execute_insert_returning(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    """Execute INSERT with RETURNING and return the result."""
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            await conn.commit()
            return await cur.fetchone()
