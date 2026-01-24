"""
PostgreSQL Client
=================

Remote PostgreSQL management via SSH.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from deployment_mcp.clients.ssh import CommandResult, get_ssh_manager


@dataclass
class Database:
    """PostgreSQL database information."""

    name: str
    owner: str
    encoding: str
    size: str
    tablespace: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Database":
        """Create from query result row."""
        return cls(
            name=row.get("datname", ""),
            owner=row.get("owner", ""),
            encoding=row.get("encoding", ""),
            size=row.get("size", ""),
            tablespace=row.get("tablespace", "pg_default"),
        )


@dataclass
class DatabaseStats:
    """Database statistics."""

    name: str
    size: str
    connections: int
    max_connections: int
    active_queries: int
    idle_connections: int
    transactions_committed: int
    transactions_rolled_back: int
    blocks_read: int
    blocks_hit: int
    cache_hit_ratio: float


@dataclass
class TableInfo:
    """Table information."""

    schema: str
    name: str
    size: str
    row_estimate: int
    toast_size: str | None


@dataclass
class BackupResult:
    """Result of a backup operation."""

    success: bool
    database: str
    backup_path: str
    size: str | None
    duration_seconds: float
    error: str | None


class PostgresClient:
    """PostgreSQL client for remote database management via SSH."""

    def __init__(
        self,
        server_name: str,
        db_user: str = "postgres",
        db_host: str = "localhost",
        db_port: int = 5432,
    ) -> None:
        self.server_name = server_name
        self.db_user = db_user
        self.db_host = db_host
        self.db_port = db_port
        self._ssh = get_ssh_manager()

    def _psql_cmd(self, query: str, database: str = "postgres", tuples_only: bool = True) -> str:
        """Build psql command."""
        flags = "-t" if tuples_only else ""
        # Use -A for unaligned output, -F for field separator
        return (
            f'psql -h {self.db_host} -p {self.db_port} -U {self.db_user} '
            f'-d {database} {flags} -A -F "||" -c "{query}"'
        )

    def _psql_json_cmd(self, query: str, database: str = "postgres") -> str:
        """Build psql command with JSON output."""
        # Wrap query to return JSON
        json_query = f"SELECT json_agg(t) FROM ({query}) t"
        return (
            f'psql -h {self.db_host} -p {self.db_port} -U {self.db_user} '
            f'-d {database} -t -A -c "{json_query}"'
        )

    async def _run(self, cmd: str) -> CommandResult:
        """Run command on remote server."""
        return await self._ssh.run_command(self.server_name, cmd)

    async def _query(self, query: str, database: str = "postgres") -> list[dict[str, Any]]:
        """Execute query and return results as list of dicts."""
        cmd = self._psql_json_cmd(query, database)
        result = await self._run(cmd)

        if not result.success:
            raise RuntimeError(f"Query failed: {result.stderr}")

        output = result.stdout.strip()
        if not output or output == "null":
            return []

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return []

    async def list_databases(self) -> list[Database]:
        """List all databases."""
        query = """
            SELECT 
                d.datname,
                pg_catalog.pg_get_userbyid(d.datdba) as owner,
                pg_catalog.pg_encoding_to_char(d.encoding) as encoding,
                pg_catalog.pg_size_pretty(pg_catalog.pg_database_size(d.datname)) as size,
                t.spcname as tablespace
            FROM pg_catalog.pg_database d
            LEFT JOIN pg_catalog.pg_tablespace t ON d.dattablespace = t.oid
            WHERE d.datistemplate = false
            ORDER BY d.datname
        """
        rows = await self._query(query)
        return [Database.from_row(row) for row in rows]

    async def get_database_stats(self, database: str) -> DatabaseStats | None:
        """Get detailed statistics for a database."""
        # Get basic stats
        stats_query = f"""
            SELECT 
                pg_database.datname as name,
                pg_size_pretty(pg_database_size(pg_database.datname)) as size,
                (SELECT count(*) FROM pg_stat_activity WHERE datname = '{database}') as connections,
                (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections,
                (SELECT count(*) FROM pg_stat_activity WHERE datname = '{database}' AND state = 'active') as active_queries,
                (SELECT count(*) FROM pg_stat_activity WHERE datname = '{database}' AND state = 'idle') as idle_connections
            FROM pg_database
            WHERE datname = '{database}'
        """

        rows = await self._query(stats_query)
        if not rows:
            return None

        row = rows[0]

        # Get transaction stats
        tx_query = f"""
            SELECT 
                xact_commit as committed,
                xact_rollback as rolled_back,
                blks_read,
                blks_hit
            FROM pg_stat_database
            WHERE datname = '{database}'
        """
        tx_rows = await self._query(tx_query)
        tx = tx_rows[0] if tx_rows else {}

        # Calculate cache hit ratio
        blks_read = tx.get("blks_read", 0) or 0
        blks_hit = tx.get("blks_hit", 0) or 0
        total_blocks = blks_read + blks_hit
        cache_hit_ratio = (blks_hit / total_blocks * 100) if total_blocks > 0 else 0.0

        return DatabaseStats(
            name=row.get("name", database),
            size=row.get("size", "0 bytes"),
            connections=row.get("connections", 0) or 0,
            max_connections=row.get("max_connections", 100) or 100,
            active_queries=row.get("active_queries", 0) or 0,
            idle_connections=row.get("idle_connections", 0) or 0,
            transactions_committed=tx.get("committed", 0) or 0,
            transactions_rolled_back=tx.get("rolled_back", 0) or 0,
            blocks_read=blks_read,
            blocks_hit=blks_hit,
            cache_hit_ratio=round(cache_hit_ratio, 2),
        )

    async def get_tables(self, database: str, schema: str = "public") -> list[TableInfo]:
        """Get tables in a database."""
        query = f"""
            SELECT 
                schemaname as schema,
                tablename as name,
                pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size,
                n_live_tup as row_estimate,
                pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename) - 
                              pg_relation_size(schemaname || '.' || tablename)) as toast_size
            FROM pg_stat_user_tables
            WHERE schemaname = '{schema}'
            ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
        """
        rows = await self._query(query, database)
        return [
            TableInfo(
                schema=row.get("schema", schema),
                name=row.get("name", ""),
                size=row.get("size", "0 bytes"),
                row_estimate=row.get("row_estimate", 0) or 0,
                toast_size=row.get("toast_size"),
            )
            for row in rows
        ]

    async def get_active_queries(self, database: str | None = None) -> list[dict[str, Any]]:
        """Get currently running queries."""
        where_clause = f"AND datname = '{database}'" if database else ""
        query = f"""
            SELECT 
                pid,
                datname as database,
                usename as user,
                client_addr,
                state,
                EXTRACT(EPOCH FROM (now() - query_start))::int as duration_seconds,
                LEFT(query, 100) as query_preview
            FROM pg_stat_activity
            WHERE state != 'idle'
            AND pid != pg_backend_pid()
            {where_clause}
            ORDER BY query_start
        """
        return await self._query(query)

    async def check_connection(self) -> bool:
        """Check if PostgreSQL is accessible."""
        cmd = self._psql_cmd("SELECT 1", tuples_only=True)
        result = await self._run(cmd)
        return result.success and "1" in result.stdout

    async def get_version(self) -> str:
        """Get PostgreSQL version."""
        cmd = self._psql_cmd("SELECT version()", tuples_only=True)
        result = await self._run(cmd)
        if result.success:
            return result.stdout.strip()
        return "Unknown"

    async def backup_database(
        self,
        database: str,
        backup_dir: str = "/var/backups/postgresql",
        format: str = "custom",  # custom, plain, directory, tar
        compress: bool = True,
    ) -> BackupResult:
        """Create a database backup using pg_dump."""
        import time

        start_time = time.time()

        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = {"custom": "dump", "plain": "sql", "tar": "tar", "directory": ""}.get(
            format, "dump"
        )
        filename = f"{database}_{timestamp}.{extension}" if extension else f"{database}_{timestamp}"
        backup_path = f"{backup_dir}/{filename}"

        # Ensure backup directory exists
        mkdir_result = await self._run(f"mkdir -p {backup_dir}")
        if not mkdir_result.success:
            return BackupResult(
                success=False,
                database=database,
                backup_path=backup_path,
                size=None,
                duration_seconds=time.time() - start_time,
                error=f"Failed to create backup directory: {mkdir_result.stderr}",
            )

        # Build pg_dump command
        cmd = (
            f"pg_dump -h {self.db_host} -p {self.db_port} -U {self.db_user} "
            f"-F{format[0]} "  # c=custom, p=plain, d=directory, t=tar
        )
        if compress and format in ("custom", "directory"):
            cmd += "-Z 6 "  # compression level

        cmd += f"-f {backup_path} {database}"

        # Execute backup
        result = await self._run(cmd)
        duration = time.time() - start_time

        if not result.success:
            return BackupResult(
                success=False,
                database=database,
                backup_path=backup_path,
                size=None,
                duration_seconds=duration,
                error=result.stderr,
            )

        # Get backup size
        size_result = await self._run(f"du -h {backup_path} | cut -f1")
        size = size_result.stdout.strip() if size_result.success else None

        return BackupResult(
            success=True,
            database=database,
            backup_path=backup_path,
            size=size,
            duration_seconds=duration,
            error=None,
        )

    async def list_backups(self, backup_dir: str = "/var/backups/postgresql") -> list[dict[str, Any]]:
        """List existing backups."""
        cmd = f'ls -lh {backup_dir}/*.dump {backup_dir}/*.sql {backup_dir}/*.tar 2>/dev/null || true'
        result = await self._run(cmd)

        backups = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 9:
                backups.append({
                    "name": parts[-1].split("/")[-1],
                    "size": parts[4],
                    "date": f"{parts[5]} {parts[6]} {parts[7]}",
                    "path": parts[-1],
                })

        return backups
