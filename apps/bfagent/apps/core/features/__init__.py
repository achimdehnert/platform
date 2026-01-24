"""
Core Features Package - Domain-übergreifendes Feature-Management
Zentrale Feature-Registry für alle BF Agent Domains
"""

from .domain_registry import DomainRegistry, get_domain_registry
from .global_feature_registry import GlobalFeatureRegistry, get_global_feature_registry
from .feature_types import (
    Feature,
    FeatureCapability,
    HandlerInfo,
    FeatureStatus,
    FeaturePriority,
    DomainInfo
)

__all__ = [
    'DomainRegistry',
    'get_domain_registry',
    'GlobalFeatureRegistry',
    'get_global_feature_registry',
    'Feature',
    'FeatureCapability',
    'HandlerInfo',
    'FeatureStatus',
    'FeaturePriority',
    'DomainInfo'
]
