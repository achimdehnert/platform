"""PostgreSQL Client for database operations via SSH."""

from datetime import datetime
from typing import Any

from ..models import Database, DatabaseBackup
from ..settings import settings
from .ssh_client import SSHClient


class PostgresClient:
    """Client for PostgreSQL operations via SSH."""

    def __init__(
        self,
        ssh_client: SSHClient,
        pg_user: str | None = None,
        pg_port: int | None = None,
    ):
        """Initialize PostgreSQL client."""
        self.ssh = ssh_client
        self.pg_user = pg_user or settings.postgres_default_user
        self.pg_port = pg_port or settings.postgres_default_port

    def _psql_cmd(self, sql: str, db: str = "postgres") -> str:
        """Build psql command."""
        escaped_sql = sql.replace('"', '\\"')
        return f'sudo -u {self.pg_user} psql -p {self.pg_port} -d {db} -c "{escaped_sql}"'

    def _psql_query(self, sql: str, db: str = "postgres") -> str:
        """Build psql query command with tuples only output."""
        escaped_sql = sql.replace('"', '\\"')
        return f'sudo -u {self.pg_user} psql -p {self.pg_port} -d {db} -t -A -c "{escaped_sql}"'

    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================

    async def list_databases(self) -> list[Database]:
        """List all databases."""
        sql = "SELECT datname, pg_catalog.pg_get_userbyid(datdba) as owner, pg_encoding_to_char(encoding) FROM pg_database WHERE datistemplate = false"

        stdout, _, exit_code = await self.ssh.run(self._psql_query(sql))

        if exit_code != 0:
            return []

        databases = []
        for line in stdout.strip().split("\n"):
            if not line or line.startswith("("):
                continue
            parts = line.split("|")
            if len(parts) >= 2:
                databases.append(
                    Database(
                        name=parts[0],
                        owner=parts[1],
                        encoding=parts[2] if len(parts) > 2 else "UTF8",
                    )
                )
        return databases

    async def get_database_size(self, db_name: str) -> str:
        """Get database size."""
        sql = f"SELECT pg_size_pretty(pg_database_size('{db_name}'))"
        stdout, _, exit_code = await self.ssh.run(self._psql_query(sql))

        if exit_code != 0:
            return "unknown"
        return stdout.strip()

    async def database_exists(self, db_name: str) -> bool:
        """Check if database exists."""
        sql = f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"
        stdout, _, exit_code = await self.ssh.run(self._psql_query(sql))
        return exit_code == 0 and stdout.strip() == "1"

    async def create_database(
        self,
        db_name: str,
        owner: str | None = None,
        encoding: str = "UTF8",
    ) -> bool:
        """Create a new database."""
        sql = f"CREATE DATABASE {db_name}"
        if owner:
            sql += f" OWNER {owner}"
        sql += f" ENCODING '{encoding}'"

        _, _, exit_code = await self.ssh.run(self._psql_cmd(sql))
        return exit_code == 0

    async def drop_database(self, db_name: str, force: bool = False) -> bool:
        """Drop a database."""
        if force:
            # Terminate active connections first
            terminate_sql = f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
            """
            await self.ssh.run(self._psql_cmd(terminate_sql))

        sql = f"DROP DATABASE IF EXISTS {db_name}"
        _, _, exit_code = await self.ssh.run(self._psql_cmd(sql))
        return exit_code == 0

    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================

    async def execute_query(self, db_name: str, sql: str) -> tuple[str, int]:
        """Execute SQL query."""
        stdout, stderr, exit_code = await self.ssh.run(
            self._psql_cmd(sql, db=db_name)
        )
        return stdout or stderr, exit_code

    async def execute_query_json(self, db_name: str, sql: str) -> list[dict[str, Any]]:
        """Execute query and return JSON-like results."""
        # Get column names first
        stdout, _, exit_code = await self.ssh.run(self._psql_query(sql, db=db_name))

        if exit_code != 0:
            return []

        # Parse results (simple parsing)
        results = []
        for line in stdout.strip().split("\n"):
            if line and not line.startswith("("):
                results.append({"row": line})
        return results

    # =========================================================================
    # BACKUP OPERATIONS
    # =========================================================================

    async def backup_database(
        self,
        db_name: str,
        backup_path: str | None = None,
        format_type: str = "custom",  # custom, plain, tar
    ) -> DatabaseBackup:
        """Create database backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = {"custom": "dump", "plain": "sql", "tar": "tar"}[format_type]
        filename = f"{db_name}_{timestamp}.{ext}"
        full_path = f"{backup_path or '/var/backups/postgres'}/{filename}"

        # Ensure backup directory exists
        await self.ssh.run(f"mkdir -p {backup_path or '/var/backups/postgres'}")

        # Run pg_dump
        cmd = f"sudo -u {self.pg_user} pg_dump -p {self.pg_port} -F{format_type[0]} -f {full_path} {db_name}"
        _, stderr, exit_code = await self.ssh.run(cmd, timeout=600)

        if exit_code != 0:
            raise RuntimeError(f"Backup failed: {stderr}")

        # Get file size
        size_out, _, _ = await self.ssh.run(f"stat -c %s {full_path}")
        size = int(size_out.strip()) if size_out.strip().isdigit() else 0

        return DatabaseBackup(
            filename=filename,
            database=db_name,
            size=size,
            created=datetime.now(),
        )

    async def list_backups(self, backup_path: str | None = None) -> list[DatabaseBackup]:
        """List available backups."""
        path = backup_path or "/var/backups/postgres"
        stdout, _, exit_code = await self.ssh.run(
            f"ls -la {path}/*.dump {path}/*.sql {path}/*.tar 2>/dev/null | awk '{{print $5,$9}}'"
        )

        if exit_code != 0:
            return []

        backups = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                filename = parts[1].split("/")[-1]
                db_name = filename.split("_")[0] if "_" in filename else "unknown"
                backups.append(
                    DatabaseBackup(
                        filename=filename,
                        database=db_name,
                        size=int(parts[0]) if parts[0].isdigit() else 0,
                        created=datetime.now(),  # Would need stat for actual time
                    )
                )
        return backups

    async def restore_database(
        self,
        db_name: str,
        backup_file: str,
        create_db: bool = True,
    ) -> bool:
        """Restore database from backup."""
        # Determine backup format
        if backup_file.endswith(".dump"):
            restore_cmd = f"pg_restore -p {self.pg_port}"
            if create_db:
                restore_cmd += " -C"
            restore_cmd += f" -d postgres {backup_file}"
        else:
            if create_db:
                await self.create_database(db_name)
            restore_cmd = f"psql -p {self.pg_port} -d {db_name} -f {backup_file}"

        cmd = f"sudo -u {self.pg_user} {restore_cmd}"
        _, stderr, exit_code = await self.ssh.run(cmd, timeout=600)

        if exit_code != 0:
            raise RuntimeError(f"Restore failed: {stderr}")
        return True

    # =========================================================================
    # MIGRATION OPERATIONS
    # =========================================================================

    async def run_migrations(
        self,
        project_path: str,
        command: str = "alembic upgrade head",
    ) -> tuple[str, int]:
        """Run database migrations."""
        cmd = f"cd {project_path} && {command}"
        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=300)
        return stdout or stderr, exit_code

    # =========================================================================
    # STATUS OPERATIONS
    # =========================================================================

    async def get_status(self) -> dict[str, Any]:
        """Get PostgreSQL server status."""
        # Check if running
        _, _, running = await self.ssh.run("systemctl is-active postgresql")

        # Get version
        version_out, _, _ = await self.ssh.run(self._psql_query("SELECT version()"))

        # Get connection count
        conn_out, _, _ = await self.ssh.run(
            self._psql_query("SELECT count(*) FROM pg_stat_activity")
        )

        # Get uptime
        uptime_out, _, _ = await self.ssh.run(
            self._psql_query("SELECT now() - pg_postmaster_start_time()")
        )

        return {
            "running": running == 0,
            "version": version_out.strip() if version_out else "unknown",
            "connections": int(conn_out.strip()) if conn_out.strip().isdigit() else 0,
            "uptime": uptime_out.strip() if uptime_out else "unknown",
        }
