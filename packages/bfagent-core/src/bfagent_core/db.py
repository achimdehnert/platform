"""
Database utilities for multi-tenancy.

DEPRECATED: Use platform_context.db instead.
This module re-exports from platform-context for backward compatibility.
"""

import warnings

from platform_context.db import (  # noqa: F401
    get_db_tenant,
    set_db_tenant,
)

warnings.warn(
    "bfagent_core.db is deprecated, use platform_context.db instead",
    DeprecationWarning,
    stacklevel=2,
)
