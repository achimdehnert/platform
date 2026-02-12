"""
Request context management using contextvars.

DEPRECATED: Use platform_context.context instead.
This module re-exports from platform-context for backward compatibility.
"""

import warnings

from platform_context.context import (  # noqa: F401
    RequestContext,
    clear_context,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
)

warnings.warn(
    "bfagent_core.context is deprecated, use platform_context.context instead",
    DeprecationWarning,
    stacklevel=2,
)
