import argparse
import os
import sqlite3
from typing import Dict, List, Optional, Sequence, Set, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json


def _sqlite_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    return [r[0] for r in cur.fetchall()]


def _pg_table_column_types(cur, schema: str, table: str) -> Dict[str, str]:
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        """,
        (schema, table),
    )
    return {r[0]: r[1] for r in cur.fetchall()}


def _coerce_value_for_pg(value, pg_type: str):
    if value is None:
        return None

    # SQLite often stores booleans as 0/1 (ints)
    if pg_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(int(value))
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"1", "t", "true", "yes", "y"}:
                return True
            if v in {"0", "f", "false", "no", "n"}:
                return False
        return value

    # JSON fields: accept dict/list or parse JSON strings
    if pg_type in {"json", "jsonb"}:
        if isinstance(value, (dict, list)):
            return Json(value)
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return Json({})
            try:
                import json

                return Json(json.loads(s))
            except Exception:
                # Fallback: let Postgres try to cast text to json/jsonb
                return value
        return value

    return value


def _pg_tables(cur, schema: str) -> List[str]:
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """,
        (schema,),
    )
    return [r[0] for r in cur.fetchall()]


def _pg_fk_dependencies(cur, schema: str) -> Dict[str, Set[str]]:
    """Return mapping table -> set(referenced_tables) for FK constraints in given schema."""
    cur.execute(
        """
        SELECT
            tc.table_name AS table_name,
            ccu.table_name AS referenced_table_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = %s
        """,
        (schema,),
    )
    deps: Dict[str, Set[str]] = {}
    for table_name, ref_table in cur.fetchall():
        deps.setdefault(table_name, set()).add(ref_table)
    return deps


def _toposort_tables(tables: List[str], deps: Dict[str, Set[str]]) -> List[str]:
    """Kahn topological sort. Keeps original relative order as much as possible."""
    table_set = set(tables)
    in_deg: Dict[str, int] = {t: 0 for t in tables}
    adj: Dict[str, Set[str]] = {t: set() for t in tables}

    for t in tables:
        for ref in deps.get(t, set()):
            if ref in table_set and ref != t:
                in_deg[t] += 1
                adj.setdefault(ref, set()).add(t)

    queue = [t for t in tables if in_deg[t] == 0]
    out: List[str] = []

    while queue:
        n = queue.pop(0)
        out.append(n)
        for m in sorted(adj.get(n, set())):
            in_deg[m] -= 1
            if in_deg[m] == 0:
                queue.append(m)

    # If cycles exist, append remaining tables in original order
    remaining = [t for t in tables if t not in out]
    return out + remaining


def _sqlite_table_columns(conn: sqlite3.Connection, table: str) -> Tuple[List[str], Optional[str]]:
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    cols: List[str] = []
    pk_col: Optional[str] = None
    for _cid, name, _ctype, _notnull, _dflt, pk in cur.fetchall():
        cols.append(name)
        if pk == 1:
            pk_col = name
    return cols, pk_col


def _pg_table_columns(cur, schema: str, table: str) -> List[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table),
    )
    return [r[0] for r in cur.fetchall()]


def _pg_has_table(cur, schema: str, table: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name = %s
        """,
        (schema, table),
    )
    return cur.fetchone() is not None


def _copy_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    schema: str,
    table: str,
    truncate: bool,
    batch_size: int,
) -> None:
    sqlite_cols, sqlite_pk = _sqlite_table_columns(sqlite_conn, table)

    with pg_conn.cursor() as pg_cur:
        if not _pg_has_table(pg_cur, schema, table):
            print(f"⚠️  Skipping {table}: target table does not exist in Postgres")
            return

        pg_cols = _pg_table_columns(pg_cur, schema, table)
        pg_col_types = _pg_table_column_types(pg_cur, schema, table)

        common_cols = [c for c in sqlite_cols if c in pg_cols]
        if not common_cols:
            print(f"⚠️  Skipping {table}: no common columns")
            return

        pk_col = sqlite_pk if sqlite_pk in common_cols else None

        if truncate:
            pg_cur.execute(
                sql.SQL("TRUNCATE TABLE {}.{} RESTART IDENTITY CASCADE").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
            )
            pg_conn.commit()

        sqlite_cur = sqlite_conn.cursor()
        select_cols_sqlite = ", ".join([f'"{c}"' for c in common_cols])
        sqlite_cur.execute(f'SELECT {select_cols_sqlite} FROM "{table}"')

        placeholders = [sql.Placeholder() for _ in common_cols]
        cols_sql = sql.SQL(", ").join(map(sql.Identifier, common_cols))

        if pk_col:
            update_cols = [c for c in common_cols if c != pk_col]
            if update_cols:
                set_clause = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c))
                    for c in update_cols
                )
                insert_stmt = sql.SQL(
                    "INSERT INTO {}.{} ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {}"
                ).format(
                    sql.Identifier(schema),
                    sql.Identifier(table),
                    cols_sql,
                    sql.SQL(", ").join(placeholders),
                    sql.Identifier(pk_col),
                    set_clause,
                )
            else:
                insert_stmt = sql.SQL(
                    "INSERT INTO {}.{} ({}) VALUES ({}) ON CONFLICT ({}) DO NOTHING"
                ).format(
                    sql.Identifier(schema),
                    sql.Identifier(table),
                    cols_sql,
                    sql.SQL(", ").join(placeholders),
                    sql.Identifier(pk_col),
                )
        else:
            insert_stmt = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
                sql.Identifier(schema),
                sql.Identifier(table),
                cols_sql,
                sql.SQL(", ").join(placeholders),
            )

        total = 0
        batch: List[Sequence[object]] = []

        while True:
            rows = sqlite_cur.fetchmany(batch_size)
            if not rows:
                break
            batch.extend(rows)

            # Coerce SQLite values into Postgres-friendly types per column
            coerced_batch = []
            for row in batch:
                coerced_row = []
                for i, col in enumerate(common_cols):
                    coerced_row.append(_coerce_value_for_pg(row[i], pg_col_types.get(col, "")))
                coerced_batch.append(tuple(coerced_row))

            pg_cur.executemany(insert_stmt.as_string(pg_conn), coerced_batch)
            pg_conn.commit()
            total += len(batch)
            batch.clear()

        print(f"✅ {table}: copied {total} rows (columns={len(common_cols)} pk={pk_col or 'n/a'})")


def _connect_pg_from_env():
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    db = os.environ.get("POSTGRES_DB", "bfagent_dev")
    user = os.environ.get("POSTGRES_USER", "bfagent")
    password = os.environ.get("POSTGRES_PASSWORD", "bfagent_dev_2024")

    # Prevent UnicodeDecodeError from localized libpq error messages on Windows
    # (e.g., German "für Benutzer" contains byte 0xfc).
    os.environ.setdefault("PGCLIENTENCODING", "UTF8")
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("LC_ALL", "C.UTF-8")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=password,
        options="-c lc_messages=C -c client_encoding=UTF8",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Copy selected tables from a SQLite DB file into PostgreSQL (existing schema)."
    )
    parser.add_argument(
        "--sqlite",
        required=True,
        help="Path to sqlite file (e.g. C:/.../bfagent_backup_*.db)",
    )
    parser.add_argument(
        "--tables",
        default="domain_arts,navigation_sections,navigation_items",
        help="Comma-separated table list to copy (ignored when --all-tables is set)",
    )
    parser.add_argument(
        "--all-tables",
        action="store_true",
        help="Copy all tables that exist in BOTH SQLite and Postgres schema (safe intersection).",
    )
    parser.add_argument(
        "--skip-tables",
        default="django_migrations,sqlite_sequence,django_content_type,auth_permission,domain_types",
        help="Comma-separated table list to skip (used with --all-tables)",
    )
    parser.add_argument(
        "--schema",
        default="public",
        help="Target Postgres schema (default: public)",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE target tables before inserting (destructive)",
    )
    parser.add_argument(
        "--disable-fk-checks",
        action="store_true",
        help="Disable FK checks during import (Postgres session_replication_role=replica). Use only on fresh DB.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for inserts",
    )

    args = parser.parse_args()

    sqlite_path = args.sqlite
    tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    skip_tables = {t.strip() for t in args.skip_tables.split(",") if t.strip()}

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = None

    sqlite_table_set = set(_sqlite_tables(sqlite_conn))

    pg_conn = _connect_pg_from_env()
    try:
        print("SQLite -> Postgres table copy")
        print(f"- SQLite: {sqlite_path}")
        print(
            f"- Postgres: {os.environ.get('POSTGRES_HOST','localhost')}:{os.environ.get('POSTGRES_PORT','5432')} / {os.environ.get('POSTGRES_DB','bfagent_dev')}"
        )
        print(f"- Schema: {args.schema}")
        with pg_conn.cursor() as pg_cur:
            pg_table_set = set(_pg_tables(pg_cur, args.schema))
            deps = _pg_fk_dependencies(pg_cur, args.schema)

        if args.all_tables:
            tables = sorted((sqlite_table_set & pg_table_set) - skip_tables)

        ordered_tables = _toposort_tables(tables, deps)
        print(f"- Tables (ordered): {ordered_tables}")

        if args.disable_fk_checks:
            with pg_conn.cursor() as pg_cur:
                pg_cur.execute("SET session_replication_role = 'replica'")
            pg_conn.commit()

        failed_tables: List[str] = []
        try:
            for table in ordered_tables:
                if table not in sqlite_table_set:
                    print(f"⚠️  Skipping {table}: table not found in SQLite")
                    continue
                try:
                    _copy_table(
                        sqlite_conn=sqlite_conn,
                        pg_conn=pg_conn,
                        schema=args.schema,
                        table=table,
                        truncate=bool(args.truncate),
                        batch_size=int(args.batch_size),
                    )
                except Exception as e:
                    failed_tables.append(table)
                    try:
                        pg_conn.rollback()
                    except Exception:
                        pass
                    print(f"❌ {table}: {e}")
        finally:
            # Ensure we are not in an aborted transaction before resetting role
            try:
                pg_conn.rollback()
            except Exception:
                pass

            if args.disable_fk_checks:
                with pg_conn.cursor() as pg_cur:
                    pg_cur.execute("SET session_replication_role = 'origin'")
                pg_conn.commit()

        if failed_tables:
            print(f"⚠️ Import finished with failures ({len(failed_tables)}): {failed_tables}")

    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
