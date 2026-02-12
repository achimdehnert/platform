"""
Exception hierarchy for bfagent-core.

DEPRECATED: Use platform_context.exceptions instead.
This module re-exports from platform-context for backward compatibility.
"""

import warnings

from platform_context.exceptions import (  # noqa: F401
    InvitationExpiredError,
    InvitationNotPendingError,
    MembershipError,
    MembershipExistsError,
    MembershipNotFoundError,
    PermissionDeniedError,
    PermissionError,
    PermissionNotFoundError,
    PlatformError,
    RoleNotFoundError,
    TenantDeletedError,
    TenantError,
    TenantInactiveError,
    TenantNotFoundError,
    TenantSlugExistsError,
    TenantSuspendedError,
    UserError,
    UserNotFoundError,
)

warnings.warn(
    "bfagent_core.exceptions is deprecated, "
    "use platform_context.exceptions instead",
    DeprecationWarning,
    stacklevel=2,
)
