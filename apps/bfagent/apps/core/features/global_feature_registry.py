"""
Global Feature Registry - Domain-übergreifendes Feature-Management
Zentrale Registry für alle Features über alle Domains hinweg
"""

from typing import Dict, List, Optional, Set
import logging
from .feature_types import (
    Feature,
    FeatureCapability,
    HandlerInfo,
    FeatureStatus,
    FeaturePriority,
    DomainFeatureReport
)
from .domain_registry import get_domain_registry

logger = logging.getLogger(__name__)


class GlobalFeatureRegistry:
    """
    Global registry for all features across all domains
    
    Features:
    - Multi-domain feature support
    - Cross-domain handler sharing
    - Domain-specific configuration
    - Comprehensive reporting
    - Feature discovery across domains
    """
    
    def __init__(self):
        self.features: Dict[str, Feature] = {}
        self.handlers: Dict[str, HandlerInfo] = {}
        self.domain_registry = get_domain_registry()
        self._initialize_features()
    
    def _initialize_features(self):
        """Initialize features from all domains"""
        self._init_presentation_studio_features()
        self._init_genagent_features()
        self._init_medtrans_features()
        self._init_core_features()
        logger.info(f"Initialized {len(self.features)} features across {len(self.domain_registry.domains)} domains")
    
    def _init_presentation_studio_features(self):
        """Initialize Presentation Studio features"""
        
        # Content Enhancement Feature
        self.register_feature(Feature(
            id="pptx_content_enhancement",
            name="Content Enhancement",
            description="Enhance presentation content with AI",
            category="content",
            status=FeatureStatus.ACTIVE,
            priority=FeaturePriority.HIGH,
            primary_domain="presentation_studio",
            supported_domains={"presentation_studio"},
            version="2.0.0",
            handlers=[
                HandlerInfo(
                    name="enhance_content",
                    class_name="EnhanceContentHandler",
                    module_path="apps.presentation_studio.handlers.enhance_content_handler",
                    version="2.0.0",
                    domains={"presentation_studio"}
                )
            ]
        ))
        
        # Research Agent Feature (Could be cross-domain!)
        self.register_feature(Feature(
            id="research_agent",
            name="Research Agent",
            description="AI-powered research and content generation",
            category="ai",
            status=FeatureStatus.ACTIVE,
            priority=FeaturePriority.HIGH,
            primary_domain="presentation_studio",
            supported_domains={"presentation_studio", "genagent"},  # Cross-domain!
            version="1.0.0",
            handlers=[
                HandlerInfo(
                    name="research_agent",
                    class_name="ResearchAgentHandler",
                    module_path="apps.presentation_studio.handlers.research_agent_handler",
                    version="1.0.0",
                    domains={"presentation_studio", "genagent"}  # Shared handler!
                )
            ],
            metadata={"cross_domain": True}
        ))
        
        # Slide Deletion Feature
        self.register_feature(Feature(
            id="slide_deletion",
            name="Slide Deletion",
            description="Delete individual or multiple slides",
            category="core",
            status=FeatureStatus.ACTIVE,
            priority=FeaturePriority.HIGH,
            primary_domain="presentation_studio",
            supported_domains={"presentation_studio"},
            version="1.0.0",
            handlers=[
                HandlerInfo(
                    name="slide_deletion",
                    class_name="SlideDeletionHandler",
                    module_path="apps.presentation_studio.handlers.slide_deletion_handler",
                    version="1.0.0",
                    domains={"presentation_studio"},
                    is_base_handler_v2=True
                )
            ]
        ))
        
        # Validation Feature (Cross-domain!)
        self.register_feature(Feature(
            id="validation",
            name="Content Validation",
            description="Validate files and content across domains",
            category="quality",
            status=FeatureStatus.ACTIVE,
            priority=FeaturePriority.HIGH,
            primary_domain="core",
            supported_domains={"presentation_studio", "medtrans", "genagent"},  # Multi-domain!
            version="1.0.0",
            handlers=[
                HandlerInfo(
                    name="validation",
                    class_name="ValidationHandler",
                    module_path="apps.presentation_studio.handlers.validation_handler",
                    version="1.0.0",
                    domains={"presentation_studio", "medtrans", "genagent"},
                    is_base_handler_v2=True
                )
            ],
            domain_specific_config={
                "presentation_studio": {
                    "validate_pptx": True,
                    "check_slides": True,
                    "max_file_size_mb": 100
                },
                "medtrans": {
                    "validate_terminology": True,
                    "check_medical_accuracy": True
                },
                "genagent": {
                    "validate_ai_output": True,
                    "check_content_quality": True
                }
            },
            metadata={"cross_domain": True, "reusable": True}
        ))
        
        # Text Formatting Feature (Highly reusable!)
        self.register_feature(Feature(
            id="text_formatting",
            name="Text Formatting",
            description="Advanced text formatting capabilities",
            category="formatting",
            status=FeatureStatus.ACTIVE,
            priority=FeaturePriority.MEDIUM,
            primary_domain="core",
            supported_domains={"presentation_studio", "medtrans", "genagent", "hub"},
            version="1.0.0",
            handlers=[
                HandlerInfo(
                    name="text_formatting",
                    class_name="TextFormattingHandler",
                    module_path="apps.presentation_studio.handlers.text_formatting_handler",
                    version="1.0.0",
                    domains={"presentation_studio", "medtrans", "genagent", "hub"},
                    is_base_handler_v2=True
                )
            ],
            metadata={"cross_domain": True, "highly_reusable": True}
        ))
    
    def _init_genagent_features(self):
        """Initialize GenAgent features"""
        
        # AI Text Generation
        self.register_feature(Feature(
            id="ai_text_generation",
            name="AI Text Generation",
            description="Generate text using AI models",
            category="ai",
            status=FeatureStatus.ACTIVE,
            priority=FeaturePriority.HIGH,
            primary_domain="genagent",
            supported_domains={"genagent", "presentation_studio", "medtrans"},
            version="1.0.0",
            metadata={"ai_models": ["gpt-4", "claude"], "cross_domain": True}
        ))
    
    def _init_medtrans_features(self):
        """Initialize MedTrans features"""
        
        # Medical Translation
        self.register_feature(Feature(
            id="medical_translation",
            name="Medical Translation",
            description="Translate medical content with terminology validation",
            category="translation",
            status=FeatureStatus.ACTIVE,
            priority=FeaturePriority.HIGH,
            primary_domain="medtrans",
            supported_domains={"medtrans"},
            version="1.0.0",
            metadata={"languages": ["de", "en", "fr"]}
        ))
    
    def _init_core_features(self):
        """Initialize Core features (shared across all domains)"""
        
        # Authentication & Authorization
        self.register_feature(Feature(
            id="auth_system",
            name="Authentication System",
            description="User authentication and authorization",
            category="security",
            status=FeatureStatus.ACTIVE,
            priority=FeaturePriority.CRITICAL,
            primary_domain="core",
            supported_domains={"core", "bfagent", "presentation_studio", "genagent", "medtrans", "hub", "control_center"},
            version="1.0.0",
            metadata={"cross_domain": True, "critical": True}
        ))
    
    def register_feature(self, feature: Feature):
        """Register a feature"""
        self.features[feature.id] = feature
        for handler in feature.handlers:
            self.handlers[handler.name] = handler
        logger.debug(f"Registered feature: {feature.name} (Primary: {feature.primary_domain})")
    
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get feature by ID"""
        return self.features.get(feature_id)
    
    def get_features_by_domain(self, domain_id: str) -> List[Feature]:
        """Get all features available for a specific domain"""
        return [
            f for f in self.features.values()
            if f.is_available_for_domain(domain_id)
        ]
    
    def get_features_by_status(self, status: FeatureStatus) -> List[Feature]:
        """Get features by status"""
        return [f for f in self.features.values() if f.status == status]
    
    def get_cross_domain_features(self) -> List[Feature]:
        """Get features that span multiple domains"""
        return [
            f for f in self.features.values()
            if len(f.supported_domains) > 1 or f.metadata.get("cross_domain")
        ]
    
    def get_shared_handlers(self) -> List[HandlerInfo]:
        """Get handlers that are used across multiple domains"""
        return [
            h for h in self.handlers.values()
            if len(h.domains) > 1
        ]
    
    def get_domain_report(self, domain_id: str) -> Optional[DomainFeatureReport]:
        """Generate report for a specific domain"""
        domain = self.domain_registry.get_domain(domain_id)
        if not domain:
            return None
        
        domain_features = self.get_features_by_domain(domain_id)
        
        active = len([f for f in domain_features if f.status == FeatureStatus.ACTIVE])
        planned = len([f for f in domain_features if f.status == FeatureStatus.PLANNED])
        deprecated = len([f for f in domain_features if f.status == FeatureStatus.DEPRECATED])
        
        # Count handlers
        domain_handlers = set()
        for feature in domain_features:
            for handler in feature.handlers:
                if domain_id in handler.domains:
                    domain_handlers.add(handler.name)
        
        v2_handlers = sum(
            1 for h_name in domain_handlers
            if self.handlers.get(h_name) and self.handlers[h_name].is_base_handler_v2
        )
        
        # Count cross-domain features
        cross_domain = len([
            f for f in domain_features
            if len(f.supported_domains) > 1
        ])
        
        # Categories
        categories = {}
        for feature in domain_features:
            categories[feature.category] = categories.get(feature.category, 0) + 1
        
        # Priority breakdown
        priority_breakdown = {}
        for feature in domain_features:
            priority_breakdown[feature.priority.value] = priority_breakdown.get(feature.priority.value, 0) + 1
        
        return DomainFeatureReport(
            domain_id=domain_id,
            domain_name=domain.name,
            total_features=len(domain_features),
            active_features=active,
            planned_features=planned,
            deprecated_features=deprecated,
            total_handlers=len(domain_handlers),
            base_handler_v2_count=v2_handlers,
            legacy_handler_count=len(domain_handlers) - v2_handlers,
            test_coverage=0.0,  # TODO: Calculate from test framework
            categories=categories,
            priority_breakdown=priority_breakdown,
            cross_domain_features=cross_domain,
            metadata=domain.metadata
        )
    
    def generate_global_report(self) -> Dict:
        """Generate comprehensive report across all domains"""
        all_active = self.get_features_by_status(FeatureStatus.ACTIVE)
        all_planned = self.get_features_by_status(FeatureStatus.PLANNED)
        cross_domain = self.get_cross_domain_features()
        shared_handlers = self.get_shared_handlers()
        
        # Generate per-domain reports
        domain_reports = {}
        for domain_id in self.domain_registry.domains.keys():
            report = self.get_domain_report(domain_id)
            if report:
                domain_reports[domain_id] = {
                    "total_features": report.total_features,
                    "active_features": report.active_features,
                    "cross_domain_features": report.cross_domain_features,
                    "base_handler_v2_count": report.base_handler_v2_count,
                    "legacy_handler_count": report.legacy_handler_count
                }
        
        # Calculate migration progress
        total_handlers = len(self.handlers)
        v2_handlers = sum(1 for h in self.handlers.values() if h.is_base_handler_v2)
        migration_progress = (v2_handlers / total_handlers * 100) if total_handlers > 0 else 0
        
        return {
            "total_features": len(self.features),
            "active_features": len(all_active),
            "planned_features": len(all_planned),
            "cross_domain_features": len(cross_domain),
            "total_handlers": total_handlers,
            "shared_handlers": len(shared_handlers),
            "base_handler_v2_count": v2_handlers,
            "legacy_handler_count": total_handlers - v2_handlers,
            "migration_progress": f"{migration_progress:.1f}%",
            "domain_count": len(self.domain_registry.domains),
            "domain_reports": domain_reports,
            "reusability_score": len(shared_handlers) / total_handlers if total_handlers > 0 else 0
        }


# Global registry instance
_registry = None


def get_global_feature_registry() -> GlobalFeatureRegistry:
    """Get global feature registry instance"""
    global _registry
    if _registry is None:
        _registry = GlobalFeatureRegistry()
    return _registry
