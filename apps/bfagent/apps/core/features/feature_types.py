"""
Feature Types - Shared types for domain-übergreifendes Feature-Management
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from datetime import datetime


class FeatureStatus(Enum):
    """Feature availability status"""
    ACTIVE = "active"
    BETA = "beta"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    PLANNED = "planned"
    EXPERIMENTAL = "experimental"


class FeaturePriority(Enum):
    """Feature priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DomainCategory(Enum):
    """Domain categories"""
    CORE = "core"
    AI = "ai"
    MEDICAL = "medical"
    PRESENTATION = "presentation"
    CONTENT = "content"
    ADMIN = "admin"
    INTEGRATION = "integration"


@dataclass
class DomainInfo:
    """Information about a domain/app"""
    id: str
    name: str
    description: str
    category: DomainCategory
    version: str
    is_active: bool = True
    base_path: str = ""
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandlerInfo:
    """Information about a handler"""
    name: str
    class_name: str
    module_path: str
    version: str
    domains: Set[str] = field(default_factory=set)  # Multiple domains!
    is_base_handler_v2: bool = False
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureCapability:
    """Individual capability within a feature"""
    name: str
    description: str
    handler: HandlerInfo
    domains: Set[str] = field(default_factory=set)  # Can span multiple domains
    requires_auth: bool = True
    requires_permissions: List[str] = field(default_factory=list)
    input_schema: Optional[str] = None
    output_schema: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Feature:
    """Complete feature definition - domain-übergreifend"""
    id: str
    name: str
    description: str
    category: str
    status: FeatureStatus
    priority: FeaturePriority
    
    # Multi-Domain Support
    primary_domain: str  # Primary domain owning this feature
    supported_domains: Set[str] = field(default_factory=set)  # All domains supporting it
    domain_specific_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    capabilities: List[FeatureCapability] = field(default_factory=list)
    handlers: List[HandlerInfo] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_available_for_domain(self, domain_id: str) -> bool:
        """Check if feature is available for specific domain"""
        return domain_id in self.supported_domains or domain_id == self.primary_domain
    
    def get_domain_config(self, domain_id: str) -> Dict[str, Any]:
        """Get domain-specific configuration"""
        return self.domain_specific_config.get(domain_id, {})


@dataclass
class FeatureTest:
    """Test definition for a feature"""
    id: str
    feature_id: str
    name: str
    description: str
    test_type: str  # unit, integration, e2e
    domains: Set[str] = field(default_factory=set)  # Domains to test
    test_path: str = ""
    is_passing: Optional[bool] = None
    last_run: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainFeatureReport:
    """Report for features in a specific domain"""
    domain_id: str
    domain_name: str
    total_features: int
    active_features: int
    planned_features: int
    deprecated_features: int
    total_handlers: int
    base_handler_v2_count: int
    legacy_handler_count: int
    test_coverage: float
    categories: Dict[str, int]
    priority_breakdown: Dict[str, int]
    cross_domain_features: int  # Features shared with other domains
    metadata: Dict[str, Any] = field(default_factory=dict)
