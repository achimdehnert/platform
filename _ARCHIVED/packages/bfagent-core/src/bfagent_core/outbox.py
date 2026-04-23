"""
Outbox pattern for reliable event publishing.

DEPRECATED: Use platform_context.outbox instead.
This module re-exports from platform-context for backward compatibility.
"""

import warnings

from platform_context.outbox import emit_outbox_event  # noqa: F401

warnings.warn(
    "bfagent_core.outbox is deprecated, use platform_context.outbox instead",
    DeprecationWarning,
    stacklevel=2,
)
