"""
CAD-Hub Django Models
ADR-009 compliant: Database-driven, normalized, FK integers
Naming: {app}_{entity} for tables, snake_case for columns
"""

from cad_services.django.models.cadhub import (
    CADModel,
    Door,
    ElementProperty,
    Floor,
    Project,
    PropertyDefinition,
    Room,
    Slab,
    Unit,
    UsageCategory,
    Wall,
    Window,
)
from cad_services.django.models.core import (
    Membership,
    Permission,
    Plan,
    Role,
    RolePermission,
    Tenant,
    User,
)
from cad_services.django.models.fire_safety import (
    EscapeParamsRef,
    EscapeRoute,
    FireCompartment,
    FireRatedElement,
    FireRatingRef,
)


__all__ = [
    # Core
    "Plan",
    "Tenant",
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "Membership",
    # CAD-Hub
    "Unit",
    "UsageCategory",
    "PropertyDefinition",
    "Project",
    "CADModel",
    "Floor",
    "Room",
    "Window",
    "Door",
    "Wall",
    "Slab",
    "ElementProperty",
    # Fire Safety
    "FireRatingRef",
    "EscapeParamsRef",
    "FireCompartment",
    "FireRatedElement",
    "EscapeRoute",
]
