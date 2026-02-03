"""
Domain events for tenant and permission lifecycle.

Events are emitted via the outbox pattern for reliability.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from bfagent_core.outbox import emit_outbox_event


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# BASE EVENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DomainEvent:
    """Base class for domain events."""
    
    event_type: str
    occurred_at: datetime = None
    
    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = _utc_now()
    
    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TenantCreatedEvent(DomainEvent):
    """Emitted when a tenant is created."""
    tenant_id: UUID = None
    slug: str = ""
    owner_id: UUID = None
    plan_code: str = ""
    event_type: str = "tenant.created"


@dataclass
class TenantActivatedEvent(DomainEvent):
    """Emitted when a tenant is activated (trial → active)."""
    tenant_id: UUID = None
    event_type: str = "tenant.activated"


@dataclass
class TenantSuspendedEvent(DomainEvent):
    """Emitted when a tenant is suspended."""
    tenant_id: UUID = None
    reason: str = ""
    event_type: str = "tenant.suspended"


@dataclass
class TenantDeletedEvent(DomainEvent):
    """Emitted when a tenant is soft-deleted."""
    tenant_id: UUID = None
    event_type: str = "tenant.deleted"


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBERSHIP EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MembershipInvitedEvent(DomainEvent):
    """Emitted when a user is invited to a tenant."""
    tenant_id: UUID = None
    membership_id: UUID = None
    user_id: UUID = None
    role: str = ""
    invited_by_id: UUID = None
    event_type: str = "membership.invited"


@dataclass
class MembershipAcceptedEvent(DomainEvent):
    """Emitted when an invitation is accepted."""
    tenant_id: UUID = None
    membership_id: UUID = None
    user_id: UUID = None
    event_type: str = "membership.accepted"


@dataclass
class MembershipRoleChangedEvent(DomainEvent):
    """Emitted when a member's role changes."""
    tenant_id: UUID = None
    membership_id: UUID = None
    user_id: UUID = None
    old_role: str = ""
    new_role: str = ""
    event_type: str = "membership.role_changed"


@dataclass
class MembershipRemovedEvent(DomainEvent):
    """Emitted when a member is removed."""
    tenant_id: UUID = None
    membership_id: UUID = None
    user_id: UUID = None
    event_type: str = "membership.removed"


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PermissionGrantedEvent(DomainEvent):
    """Emitted when a permission is granted."""
    tenant_id: UUID = None
    membership_id: UUID = None
    user_id: UUID = None
    permission_code: str = ""
    granted_by_id: UUID = None
    event_type: str = "permission.granted"


@dataclass
class PermissionRevokedEvent(DomainEvent):
    """Emitted when a permission is revoked."""
    tenant_id: UUID = None
    membership_id: UUID = None
    user_id: UUID = None
    permission_code: str = ""
    revoked_by_id: UUID = None
    event_type: str = "permission.revoked"


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT BUS
# ═══════════════════════════════════════════════════════════════════════════════

class EventBus:
    """
    Simple event bus using outbox pattern.
    
    Events are persisted to the outbox table within the same transaction,
    then published by a background worker.
    """
    
    def publish(self, event: DomainEvent, tenant_id: UUID = None) -> None:
        """Publish an event via the outbox."""
        if tenant_id is None and hasattr(event, "tenant_id"):
            tenant_id = event.tenant_id
        
        if tenant_id is None:
            from bfagent_core.context import get_context
            ctx = get_context()
            tenant_id = ctx.tenant_id
        
        if tenant_id is None:
            raise ValueError("tenant_id required for event publishing")
        
        emit_outbox_event(
            tenant_id=tenant_id,
            topic=event.event_type,
            payload=event.to_dict(),
        )


# Singleton
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    return _event_bus


def emit_event(event: DomainEvent, tenant_id: UUID = None) -> None:
    """Convenience function to emit an event."""
    _event_bus.publish(event, tenant_id)


__all__ = [
    # Base
    "DomainEvent",
    # Tenant Events
    "TenantCreatedEvent",
    "TenantActivatedEvent",
    "TenantSuspendedEvent",
    "TenantDeletedEvent",
    # Membership Events
    "MembershipInvitedEvent",
    "MembershipAcceptedEvent",
    "MembershipRoleChangedEvent",
    "MembershipRemovedEvent",
    # Permission Events
    "PermissionGrantedEvent",
    "PermissionRevokedEvent",
    # Bus
    "EventBus",
    "get_event_bus",
    "emit_event",
]
