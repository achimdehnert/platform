"""Django template context processors.

DEPRECATED: Use platform_context.context_processors instead.
This module re-exports from platform-context for backward compatibility.
"""

import warnings

from platform_context.context_processors import (  # noqa: F401
    platform_context,
    tenant_context,
)

warnings.warn(
    "bfagent_core.context_processors is deprecated, "
    "use platform_context.context_processors instead",
    DeprecationWarning,
    stacklevel=2,
)
