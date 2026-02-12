"""
Audit event logging for compliance.

DEPRECATED: Use platform_context.audit instead.
This module re-exports from platform-context for backward compatibility.
"""

import warnings

from platform_context.audit import emit_audit_event  # noqa: F401

warnings.warn(
    "bfagent_core.audit is deprecated, use platform_context.audit instead",
    DeprecationWarning,
    stacklevel=2,
)
