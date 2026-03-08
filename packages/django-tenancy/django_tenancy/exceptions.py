class TenantNotFound(Exception):
    """Raised when no tenant can be resolved for the current request."""


class TenantMisconfigured(Exception):
    """Raised when tenancy settings are invalid or incomplete."""
