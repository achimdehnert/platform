"""
Feature Registry for PPTX Studio
Manages features, their handlers, and capabilities
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class FeatureStatus(Enum):
    """Feature availability status"""

    ACTIVE = "active"
    BETA = "beta"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    PLANNED = "planned"


class FeaturePriority(Enum):
    """Feature priority levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class HandlerInfo:
    """Information about a handler"""

    name: str
    class_name: str
    module_path: str
    version: str
    is_base_handler_v2: bool = False
    dependencies: List[str] = field(default_factory=list)


@dataclass
class FeatureCapability:
    """Individual capability within a feature"""

    name: str
    description: str
    handler: HandlerInfo
    requires_auth: bool = True
    requires_permissions: List[str] = field(default_factory=list)
    input_schema: Optional[str] = None
    output_schema: Optional[str] = None


@dataclass
class Feature:
    """Complete feature definition"""

    id: str
    name: str
    description: str
    category: str
    status: FeatureStatus
    priority: FeaturePriority
    capabilities: List[FeatureCapability] = field(default_factory=list)
    handlers: List[HandlerInfo] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeatureRegistry:
    """Central registry for all PPTX Studio features"""

    def __init__(self):
        self.features: Dict[str, Feature] = {}
        self.handlers: Dict[str, HandlerInfo] = {}
        self._initialize_features()

    def _initialize_features(self):
        """Initialize all features with their handlers"""

        # FEATURE: Content Enhancement
        self.register_feature(
            Feature(
                id="content_enhancement",
                name="Content Enhancement",
                description="Enhance presentation content with AI",
                category="core",
                status=FeatureStatus.ACTIVE,
                priority=FeaturePriority.HIGH,
                version="2.0.0",
                handlers=[
                    HandlerInfo(
                        name="enhance_content",
                        class_name="EnhanceContentHandler",
                        module_path="apps.presentation_studio.handlers.enhance_content_handler",
                        version="2.0.0",
                        is_base_handler_v2=False,
                    )
                ],
                capabilities=[
                    FeatureCapability(
                        name="add_slides",
                        description="Add enhanced slides to presentation",
                        handler=HandlerInfo(
                            name="enhance_content",
                            class_name="EnhanceContentHandler",
                            module_path="apps.presentation_studio.handlers.enhance_content_handler",
                            version="2.0.0",
                        ),
                        requires_permissions=["presentation_studio.enhance_presentation"],
                    )
                ],
            )
        )

        # FEATURE: Research Agent
        self.register_feature(
            Feature(
                id="research_agent",
                name="Research Agent",
                description="AI-powered research and content generation",
                category="ai",
                status=FeatureStatus.ACTIVE,
                priority=FeaturePriority.HIGH,
                version="1.0.0",
                handlers=[
                    HandlerInfo(
                        name="research_agent",
                        class_name="ResearchAgentHandler",
                        module_path="apps.presentation_studio.handlers.research_agent_handler",
                        version="1.0.0",
                        is_base_handler_v2=False,
                    )
                ],
                capabilities=[
                    FeatureCapability(
                        name="web_research",
                        description="Perform web research",
                        handler=HandlerInfo(
                            name="research_agent",
                            class_name="ResearchAgentHandler",
                            module_path="apps.presentation_studio.handlers.research_agent_handler",
                            version="1.0.0",
                        ),
                        requires_permissions=["presentation_studio.use_research_agent"],
                    ),
                    FeatureCapability(
                        name="generate_slides",
                        description="Generate slides from research",
                        handler=HandlerInfo(
                            name="research_agent",
                            class_name="ResearchAgentHandler",
                            module_path="apps.presentation_studio.handlers.research_agent_handler",
                            version="1.0.0",
                        ),
                        requires_permissions=["presentation_studio.generate_slides"],
                    ),
                ],
            )
        )

        # FEATURE: Text Formatting
        self.register_feature(
            Feature(
                id="text_formatting",
                name="Text Formatting",
                description="Advanced text formatting capabilities",
                category="formatting",
                status=FeatureStatus.ACTIVE,
                priority=FeaturePriority.MEDIUM,
                version="1.0.0",
                handlers=[
                    HandlerInfo(
                        name="text_formatting",
                        class_name="TextFormattingHandler",
                        module_path="apps.presentation_studio.handlers.text_formatting_handler",
                        version="1.0.0",
                        is_base_handler_v2=True,  # ✅ Uses BaseHandler v2!
                    )
                ],
            )
        )

        # FEATURE: Slide Extraction
        self.register_feature(
            Feature(
                id="slide_extraction",
                name="Slide Extraction",
                description="Extract and analyze slides from PPTX",
                category="core",
                status=FeatureStatus.ACTIVE,
                priority=FeaturePriority.HIGH,
                version="1.0.0",
                handlers=[
                    HandlerInfo(
                        name="slide_extractor",
                        class_name="SlideExtractor",
                        module_path="apps.presentation_studio.handlers.slide_extractor",
                        version="1.0.0",
                    )
                ],
            )
        )

        # FEATURE: Slide Editing
        self.register_feature(
            Feature(
                id="slide_editing",
                name="Slide Editing",
                description="Edit slide content and properties",
                category="core",
                status=FeatureStatus.ACTIVE,
                priority=FeaturePriority.HIGH,
                version="1.0.0",
                handlers=[
                    HandlerInfo(
                        name="slide_editor",
                        class_name="SlideEditor",
                        module_path="apps.presentation_studio.handlers.slide_editor",
                        version="1.0.0",
                    )
                ],
            )
        )

        # FEATURE: Layout Management
        self.register_feature(
            Feature(
                id="layout_management",
                name="Layout Management",
                description="Manage slide layouts and templates",
                category="design",
                status=FeatureStatus.ACTIVE,
                priority=FeaturePriority.MEDIUM,
                version="1.0.0",
                handlers=[
                    HandlerInfo(
                        name="slide_layout",
                        class_name="SlideLayoutHandler",
                        module_path="apps.presentation_studio.handlers.slide_layout_handler",
                        version="1.0.0",
                    )
                ],
            )
        )

        # FEATURE: PDF Content Extraction
        self.register_feature(
            Feature(
                id="pdf_extraction",
                name="PDF Content Extraction",
                description="Extract content from PDF documents",
                category="import",
                status=FeatureStatus.ACTIVE,
                priority=FeaturePriority.LOW,
                version="1.0.0",
                handlers=[
                    HandlerInfo(
                        name="pdf_content_extractor",
                        class_name="PDFContentExtractor",
                        module_path="from apps.core.services.extractors import PDFContentExtractor, SlideExtractor",
                        version="1.0.0",
                    )
                ],
            )
        )

        # PLANNED FEATURES (Need Implementation)

        # FEATURE: Slide Deletion (MISSING - HIGH PRIORITY)
        self.register_feature(
            Feature(
                id="slide_deletion",
                name="Slide Deletion",
                description="Delete individual or multiple slides",
                category="core",
                status=FeatureStatus.PLANNED,
                priority=FeaturePriority.HIGH,
                version="1.0.0",
                metadata={"needs_handler": True, "target_date": "2024-Q1"},
            )
        )

        # FEATURE: Slide Reordering (MISSING - MEDIUM PRIORITY)
        self.register_feature(
            Feature(
                id="slide_reordering",
                name="Slide Reordering",
                description="Change slide order in presentation",
                category="core",
                status=FeatureStatus.PLANNED,
                priority=FeaturePriority.MEDIUM,
                version="1.0.0",
                metadata={"needs_handler": True},
            )
        )

        # FEATURE: Template Management (MISSING - MEDIUM PRIORITY)
        self.register_feature(
            Feature(
                id="template_management",
                name="Template Management",
                description="Manage presentation templates",
                category="design",
                status=FeatureStatus.PLANNED,
                priority=FeaturePriority.MEDIUM,
                version="1.0.0",
                metadata={"needs_handler": True},
            )
        )

        # FEATURE: Validation (MISSING - HIGH PRIORITY)
        self.register_feature(
            Feature(
                id="validation",
                name="Presentation Validation",
                description="Validate PPTX files for errors",
                category="quality",
                status=FeatureStatus.PLANNED,
                priority=FeaturePriority.HIGH,
                version="1.0.0",
                metadata={"needs_handler": True},
            )
        )

        # FEATURE: Export (MISSING - MEDIUM PRIORITY)
        self.register_feature(
            Feature(
                id="export",
                name="Multi-format Export",
                description="Export to PDF, images, etc.",
                category="export",
                status=FeatureStatus.PLANNED,
                priority=FeaturePriority.MEDIUM,
                version="1.0.0",
                metadata={"needs_handler": True},
            )
        )

        logger.info(f"Initialized {len(self.features)} features")

    def register_feature(self, feature: Feature):
        """Register a feature"""
        self.features[feature.id] = feature
        for handler in feature.handlers:
            self.handlers[handler.name] = handler
        logger.debug(f"Registered feature: {feature.name}")

    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get feature by ID"""
        return self.features.get(feature_id)

    def get_active_features(self) -> List[Feature]:
        """Get all active features"""
        return [f for f in self.features.values() if f.status == FeatureStatus.ACTIVE]

    def get_planned_features(self) -> List[Feature]:
        """Get all planned features (need implementation)"""
        return [f for f in self.features.values() if f.status == FeatureStatus.PLANNED]

    def get_features_by_category(self, category: str) -> List[Feature]:
        """Get features by category"""
        return [f for f in self.features.values() if f.category == category]

    def get_features_by_priority(self, priority: FeaturePriority) -> List[Feature]:
        """Get features by priority"""
        return [f for f in self.features.values() if f.priority == priority]

    def is_feature_available(self, feature_id: str) -> bool:
        """Check if feature is available"""
        feature = self.get_feature(feature_id)
        return feature is not None and feature.status == FeatureStatus.ACTIVE

    def get_missing_handlers(self) -> List[str]:
        """Get list of features that need handlers"""
        missing = []
        for feature in self.features.values():
            if feature.status == FeatureStatus.PLANNED and feature.metadata.get("needs_handler"):
                missing.append(feature.id)
        return missing

    def generate_feature_report(self) -> Dict[str, Any]:
        """Generate comprehensive feature report"""
        total = len(self.features)
        active = len(self.get_active_features())
        planned = len(self.get_planned_features())
        missing_handlers = len(self.get_missing_handlers())

        v2_handlers = sum(1 for h in self.handlers.values() if h.is_base_handler_v2)
        legacy_handlers = len(self.handlers) - v2_handlers

        return {
            "total_features": total,
            "active_features": active,
            "planned_features": planned,
            "missing_handlers": missing_handlers,
            "handler_stats": {
                "total": len(self.handlers),
                "base_handler_v2": v2_handlers,
                "legacy": legacy_handlers,
                "migration_progress": (
                    f"{(v2_handlers / len(self.handlers) * 100):.1f}%" if self.handlers else "0%"
                ),
            },
            "categories": {
                "core": len(self.get_features_by_category("core")),
                "ai": len(self.get_features_by_category("ai")),
                "design": len(self.get_features_by_category("design")),
                "import": len(self.get_features_by_category("import")),
                "export": len(self.get_features_by_category("export")),
                "quality": len(self.get_features_by_category("quality")),
                "formatting": len(self.get_features_by_category("formatting")),
            },
            "priority_breakdown": {
                "critical": len(self.get_features_by_priority(FeaturePriority.CRITICAL)),
                "high": len(self.get_features_by_priority(FeaturePriority.HIGH)),
                "medium": len(self.get_features_by_priority(FeaturePriority.MEDIUM)),
                "low": len(self.get_features_by_priority(FeaturePriority.LOW)),
            },
        }


# Global registry instance
_registry = None


def get_feature_registry() -> FeatureRegistry:
    """Get global feature registry instance"""
    global _registry
    if _registry is None:
        _registry = FeatureRegistry()
    return _registry
