"""
Database utilities for multi-tenancy.

Provides Postgres RLS (Row Level Security) session variable management.
"""

from uuid import UUID


def set_db_tenant(tenant_id: UUID | None) -> None:
    """
    Set Postgres session variable for RLS policies.
    
    This sets `app.current_tenant` which RLS policies use:
    
        CREATE POLICY tenant_isolation ON my_table
        USING (tenant_id = current_setting('app.current_tenant')::uuid);
    
    Args:
        tenant_id: The tenant UUID, or None to clear access
    
    Note:
        - Call this in middleware after resolving tenant
        - Uses SET LOCAL so it's transaction-scoped
        - Empty string = no tenant access (safe default when RLS enabled)
    """
    # Import here to avoid Django dependency at module level
    from django.db import connection
    
    value = "" if tenant_id is None else str(tenant_id)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant', %s, true)", [value])


def get_db_tenant() -> UUID | None:
    """
    Get the current tenant from Postgres session variable.
    
    Returns:
        The tenant UUID if set, None otherwise
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.current_tenant', true)")
        result = cursor.fetchone()
        if result and result[0]:
            try:
                return UUID(result[0])
            except ValueError:
                return None
        return None
