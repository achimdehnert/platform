"""
GenAgent Domain System

Universal domain template framework for defining reusable workflows
across different domains (books, forensics, thesis, etc.)
"""

from .base import (
    ActionTemplate,
    PhaseTemplate,
    DomainTemplate,
    ExecutionMode,
    ValidationLevel,
    create_simple_action,
    create_simple_phase,
)
from .registry import DomainRegistry, register_domain
from .installer import DomainInstaller, install_domain, update_domain

__all__ = [
    'ActionTemplate',
    'PhaseTemplate',
    'DomainTemplate',
    'ExecutionMode',
    'ValidationLevel',
    'create_simple_action',
    'create_simple_phase',
    'DomainRegistry',
    'register_domain',
    'DomainInstaller',
    'install_domain',
    'update_domain',
]
