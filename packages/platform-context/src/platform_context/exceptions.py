"""
Exception hierarchy for the platform.

All platform exceptions inherit from PlatformError.
"""


class PlatformError(Exception):
    """Base class for all platform errors."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT ERRORS
# ═══════════════════════════════════════════════════════════════════════════════

class TenantError(PlatformError):
    """Base for tenant-related errors."""
    pass


class TenantNotFoundError(TenantError):
    """Tenant does not exist."""

    def __init__(self, tenant_id):
        super().__init__(f"Tenant not found: {tenant_id}")
        self.tenant_id = tenant_id


class TenantSlugExistsError(TenantError):
    """Tenant slug already exists."""

    def __init__(self, slug):
        super().__init__(f"Tenant slug already exists: {slug}")
        self.slug = slug


class TenantSuspendedError(TenantError):
    """Tenant is suspended."""

    def __init__(self, tenant_id):
        super().__init__(f"Tenant is suspended: {tenant_id}")
        self.tenant_id = tenant_id


class TenantDeletedError(TenantError):
    """Tenant is deleted."""

    def __init__(self, tenant_id):
        super().__init__(f"Tenant is deleted: {tenant_id}")
        self.tenant_id = tenant_id


class TenantInactiveError(TenantError):
    """Tenant is not active (suspended or deleted)."""

    def __init__(self, tenant_id, status):
        super().__init__(f"Tenant {tenant_id} is {status}")
        self.tenant_id = tenant_id
        self.status = status


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBERSHIP ERRORS
# ═══════════════════════════════════════════════════════════════════════════════

class MembershipError(PlatformError):
    """Base for membership-related errors."""
    pass


class MembershipNotFoundError(MembershipError):
    """Membership does not exist."""

    def __init__(self, membership_id=None, tenant_id=None, user_id=None):
        if membership_id:
            msg = f"Membership not found: {membership_id}"
        else:
            msg = f"No membership for user {user_id} in tenant {tenant_id}"
        super().__init__(msg)
        self.membership_id = membership_id
        self.tenant_id = tenant_id
        self.user_id = user_id


class MembershipExistsError(MembershipError):
    """User is already a member of the tenant."""

    def __init__(self, tenant_id, user_id):
        super().__init__(f"User {user_id} is already member of tenant {tenant_id}")
        self.tenant_id = tenant_id
        self.user_id = user_id


class InvitationExpiredError(MembershipError):
    """Invitation has expired."""

    def __init__(self, membership_id):
        super().__init__(f"Invitation has expired: {membership_id}")
        self.membership_id = membership_id


class InvitationNotPendingError(MembershipError):
    """Invitation is not in pending state."""

    def __init__(self, membership_id, status):
        super().__init__(f"Invitation {membership_id} is {status}, not pending")
        self.membership_id = membership_id
        self.status = status


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION ERRORS
# ═══════════════════════════════════════════════════════════════════════════════

class PermissionError(PlatformError):
    """Base for permission-related errors."""
    pass


class PermissionDeniedError(PermissionError):
    """User does not have required permission."""

    def __init__(self, permission: str, message: str = None):
        super().__init__(message or f"Permission denied: {permission}")
        self.permission = permission


class PermissionNotFoundError(PermissionError):
    """Permission code does not exist."""

    def __init__(self, permission_code):
        super().__init__(f"Permission not found: {permission_code}")
        self.permission_code = permission_code


class RoleNotFoundError(PermissionError):
    """Role does not exist."""

    def __init__(self, role):
        super().__init__(f"Role not found: {role}")
        self.role = role


# ═══════════════════════════════════════════════════════════════════════════════
# USER ERRORS
# ═══════════════════════════════════════════════════════════════════════════════

class UserError(PlatformError):
    """Base for user-related errors."""
    pass


class UserNotFoundError(UserError):
    """User does not exist."""

    def __init__(self, user_id):
        super().__init__(f"User not found: {user_id}")
        self.user_id = user_id
