"""
Domain Registry - Zentrale Verwaltung aller BF Agent Domains
"""

from typing import Dict, List, Optional
import logging
from .feature_types import DomainInfo, DomainCategory

logger = logging.getLogger(__name__)


class DomainRegistry:
    """
    Central registry for all BF Agent domains
    Manages domain information, dependencies, and lifecycle
    """
    
    def __init__(self):
        self.domains: Dict[str, DomainInfo] = {}
        self._initialize_domains()
    
    def _initialize_domains(self):
        """Initialize all known domains"""
        
        # CORE DOMAIN
        self.register_domain(DomainInfo(
            id="core",
            name="Core",
            description="Core functionality and shared utilities",
            category=DomainCategory.CORE,
            version="1.0.0",
            is_active=True,
            base_path="apps/core",
            dependencies=[],
            metadata={"is_system": True}
        ))
        
        # BFAGENT DOMAIN (Main Application)
        self.register_domain(DomainInfo(
            id="bfagent",
            name="BF Agent",
            description="Main BF Agent application and orchestration",
            category=DomainCategory.CORE,
            version="1.0.0",
            is_active=True,
            base_path="apps/bfagent",
            dependencies=["core"],
            metadata={"is_main": True}
        ))
        
        # PRESENTATION STUDIO DOMAIN
        self.register_domain(DomainInfo(
            id="presentation_studio",
            name="Presentation Studio",
            description="PPTX creation, enhancement, and research capabilities",
            category=DomainCategory.PRESENTATION,
            version="2.0.0",
            is_active=True,
            base_path="apps/presentation_studio",
            dependencies=["core", "bfagent"],
            metadata={
                "features": ["pptx_enhancement", "research_agent", "slide_management"],
                "handlers_count": 8
            }
        ))
        
        # GENAGENT DOMAIN
        self.register_domain(DomainInfo(
            id="genagent",
            name="GenAgent",
            description="Generative AI agent capabilities",
            category=DomainCategory.AI,
            version="1.0.0",
            is_active=True,
            base_path="apps/genagent",
            dependencies=["core", "bfagent"],
            metadata={
                "ai_models": ["gpt-4", "claude"],
                "capabilities": ["text_generation", "analysis", "summarization"]
            }
        ))
        
        # MEDTRANS DOMAIN
        self.register_domain(DomainInfo(
            id="medtrans",
            name="MedTrans",
            description="Medical translation and terminology management",
            category=DomainCategory.MEDICAL,
            version="1.0.0",
            is_active=True,
            base_path="apps/medtrans",
            dependencies=["core", "bfagent", "genagent"],
            metadata={
                "languages": ["de", "en", "fr"],
                "specializations": ["medical", "pharmaceutical"]
            }
        ))
        
        # HUB DOMAIN
        self.register_domain(DomainInfo(
            id="hub",
            name="Hub",
            description="Central hub for integrations and workflows",
            category=DomainCategory.INTEGRATION,
            version="1.0.0",
            is_active=True,
            base_path="apps/hub",
            dependencies=["core", "bfagent"],
            metadata={
                "integrations": ["external_apis", "webhooks", "data_sync"]
            }
        ))
        
        # CONTROL CENTER DOMAIN
        self.register_domain(DomainInfo(
            id="control_center",
            name="Control Center",
            description="Administrative control and monitoring",
            category=DomainCategory.ADMIN,
            version="1.0.0",
            is_active=True,
            base_path="apps/control_center",
            dependencies=["core", "bfagent"],
            metadata={
                "capabilities": ["monitoring", "tool_registry", "health_checks"]
            }
        ))
        
        logger.info(f"Initialized {len(self.domains)} domains")
    
    def register_domain(self, domain: DomainInfo):
        """Register a domain"""
        self.domains[domain.id] = domain
        logger.debug(f"Registered domain: {domain.name}")
    
    def get_domain(self, domain_id: str) -> Optional[DomainInfo]:
        """Get domain by ID"""
        return self.domains.get(domain_id)
    
    def get_active_domains(self) -> List[DomainInfo]:
        """Get all active domains"""
        return [d for d in self.domains.values() if d.is_active]
    
    def get_domains_by_category(self, category: DomainCategory) -> List[DomainInfo]:
        """Get domains by category"""
        return [d for d in self.domains.values() if d.category == category]
    
    def get_domain_dependencies(self, domain_id: str) -> List[DomainInfo]:
        """Get all dependencies for a domain"""
        domain = self.get_domain(domain_id)
        if not domain:
            return []
        
        dependencies = []
        for dep_id in domain.dependencies:
            dep_domain = self.get_domain(dep_id)
            if dep_domain:
                dependencies.append(dep_domain)
        return dependencies
    
    def get_dependent_domains(self, domain_id: str) -> List[DomainInfo]:
        """Get all domains that depend on this domain"""
        dependents = []
        for domain in self.domains.values():
            if domain_id in domain.dependencies:
                dependents.append(domain)
        return dependents
    
    def validate_dependencies(self) -> List[str]:
        """Validate all domain dependencies"""
        errors = []
        
        for domain in self.domains.values():
            for dep_id in domain.dependencies:
                if dep_id not in self.domains:
                    errors.append(
                        f"Domain '{domain.id}' depends on unknown domain '{dep_id}'"
                    )
        
        return errors
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get dependency graph for all domains"""
        graph = {}
        for domain_id, domain in self.domains.items():
            graph[domain_id] = domain.dependencies.copy()
        return graph
    
    def generate_domain_report(self) -> Dict:
        """Generate comprehensive domain report"""
        return {
            "total_domains": len(self.domains),
            "active_domains": len(self.get_active_domains()),
            "categories": {
                "core": len(self.get_domains_by_category(DomainCategory.CORE)),
                "ai": len(self.get_domains_by_category(DomainCategory.AI)),
                "medical": len(self.get_domains_by_category(DomainCategory.MEDICAL)),
                "presentation": len(self.get_domains_by_category(DomainCategory.PRESENTATION)),
                "content": len(self.get_domains_by_category(DomainCategory.CONTENT)),
                "admin": len(self.get_domains_by_category(DomainCategory.ADMIN)),
                "integration": len(self.get_domains_by_category(DomainCategory.INTEGRATION))
            },
            "dependency_errors": self.validate_dependencies(),
            "dependency_graph": self.get_dependency_graph()
        }


# Global registry instance
_registry = None


def get_domain_registry() -> DomainRegistry:
    """Get global domain registry instance"""
    global _registry
    if _registry is None:
        _registry = DomainRegistry()
    return _registry
