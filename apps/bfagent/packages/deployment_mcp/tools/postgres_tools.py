"""PostgreSQL Database Tools for MCP."""

from typing import Any

from ..clients.postgres_client import PostgresClient
from ..clients.ssh_client import SSHClient
from ..settings import settings


def _get_postgres_client(host: str | None = None) -> tuple[SSHClient, PostgresClient]:
    """Get SSH and PostgreSQL clients."""
    ssh = SSHClient(host=host or settings.ssh_host)
    pg = PostgresClient(ssh)
    return ssh, pg


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================


async def db_list(host: str | None = None) -> dict[str, Any]:
    """List all databases."""
    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()
        databases = await pg.list_databases()

        # Get sizes
        for db in databases:
            db.size = await pg.get_database_size(db.name)

        return {
            "success": True,
            "count": len(databases),
            "databases": [
                {
                    "name": d.name,
                    "owner": d.owner,
                    "size": d.size,
                    "encoding": d.encoding,
                }
                for d in databases
            ],
        }
    finally:
        await ssh.disconnect()


async def db_status(host: str | None = None) -> dict[str, Any]:
    """Get PostgreSQL server status."""
    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()
        status = await pg.get_status()
        return {
            "success": True,
            "status": status,
        }
    finally:
        await ssh.disconnect()


async def db_create(
    db_name: str,
    host: str | None = None,
    owner: str | None = None,
    encoding: str = "UTF8",
) -> dict[str, Any]:
    """Create a new database."""
    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()

        if await pg.database_exists(db_name):
            return {"success": False, "error": f"Database '{db_name}' already exists"}

        success = await pg.create_database(db_name, owner, encoding)
        return {
            "success": success,
            "message": f"Database '{db_name}' created" if success else "Creation failed",
        }
    finally:
        await ssh.disconnect()


async def db_drop(
    db_name: str,
    host: str | None = None,
    force: bool = False,
    confirm: bool = False,
) -> dict[str, Any]:
    """Drop a database."""
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to drop database.",
            "would_drop": db_name,
        }

    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()

        if not await pg.database_exists(db_name):
            return {"success": False, "error": f"Database '{db_name}' does not exist"}

        success = await pg.drop_database(db_name, force)
        return {
            "success": success,
            "message": f"Database '{db_name}' dropped" if success else "Drop failed",
        }
    finally:
        await ssh.disconnect()


async def db_query(
    db_name: str,
    sql: str,
    host: str | None = None,
) -> dict[str, Any]:
    """Execute SQL query."""
    # Safety: block dangerous queries without confirmation
    sql_upper = sql.upper().strip()
    dangerous = ["DROP", "DELETE", "TRUNCATE", "ALTER"]

    for keyword in dangerous:
        if sql_upper.startswith(keyword):
            return {
                "success": False,
                "error": f"Dangerous query blocked. Use specific tools for {keyword} operations.",
            }

    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()
        output, exit_code = await pg.execute_query(db_name, sql)
        return {
            "success": exit_code == 0,
            "output": output,
            "exit_code": exit_code,
        }
    finally:
        await ssh.disconnect()


# =============================================================================
# BACKUP OPERATIONS
# =============================================================================


async def db_backup(
    db_name: str,
    host: str | None = None,
    backup_path: str | None = None,
    format_type: str = "custom",
) -> dict[str, Any]:
    """Create database backup."""
    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()

        if not await pg.database_exists(db_name):
            return {"success": False, "error": f"Database '{db_name}' does not exist"}

        backup = await pg.backup_database(db_name, backup_path, format_type)
        return {
            "success": True,
            "backup": {
                "filename": backup.filename,
                "database": backup.database,
                "size": backup.size,
                "created": backup.created.isoformat(),
            },
            "message": f"Backup created: {backup.filename}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await ssh.disconnect()


async def db_backup_list(
    host: str | None = None,
    backup_path: str | None = None,
) -> dict[str, Any]:
    """List available backups."""
    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()
        backups = await pg.list_backups(backup_path)
        return {
            "success": True,
            "count": len(backups),
            "backups": [
                {
                    "filename": b.filename,
                    "database": b.database,
                    "size": b.size,
                }
                for b in backups
            ],
        }
    finally:
        await ssh.disconnect()


async def db_restore(
    db_name: str,
    backup_file: str,
    host: str | None = None,
    create_db: bool = True,
    confirm: bool = False,
) -> dict[str, Any]:
    """Restore database from backup."""
    if settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set confirm=True to restore database.",
            "would_restore": {
                "database": db_name,
                "from_file": backup_file,
            },
        }

    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()
        success = await pg.restore_database(db_name, backup_file, create_db)
        return {
            "success": success,
            "message": f"Database '{db_name}' restored from {backup_file}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await ssh.disconnect()


# =============================================================================
# MIGRATION OPERATIONS
# =============================================================================


async def db_migrate(
    project_path: str,
    host: str | None = None,
    command: str = "alembic upgrade head",
) -> dict[str, Any]:
    """Run database migrations."""
    ssh, pg = _get_postgres_client(host)
    try:
        await ssh.connect()
        output, exit_code = await pg.run_migrations(project_path, command)
        return {
            "success": exit_code == 0,
            "output": output,
            "exit_code": exit_code,
        }
    finally:
        await ssh.disconnect()
