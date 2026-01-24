"""
Domain-Aware Workflow Templates - Version 2.0
Backward-compatible with existing workflow_templates.py
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PipelineStage(Enum):
    """Pipeline stages"""
    INPUT = "input"
    PROCESSING = "processing"
    OUTPUT = "output"


@dataclass
class DomainMetadata:
    """Domain-specific metadata for visual builder"""
    domain_id: str
    display_name: str
    category: str
    icon: str = "📋"
    color: str = "#3b82f6"
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "domain_id": self.domain_id,
            "display_name": self.display_name,
            "category": self.category,
            "icon": self.icon,
            "color": self.color,
            "description": self.description
        }


@dataclass
class PhaseMetadata:
    """Phase-level metadata"""
    phase_id: str
    name: str
    order: int
    color: str
    pipeline_stage: PipelineStage
    icon: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "phase_id": self.phase_id,
            "name": self.name,
            "order": self.order,
            "color": self.color,
            "icon": self.icon,
            "description": self.description,
            "pipeline_stage": self.pipeline_stage.value
        }


@dataclass
class EnhancedWorkflowTemplate:
    """
    Enhanced WorkflowTemplate with Domain-Awareness
    Backward-compatible: Auto-generates metadata if not provided
    """
    
    # Original fields (compatible with WorkflowTemplate)
    template_id: str
    name: str
    description: str
    input_handlers: List[Dict] = field(default_factory=list)
    processing_handlers: List[Dict] = field(default_factory=list)
    output_handlers: List[Dict] = field(default_factory=list)
    required_variables: List[str] = field(default_factory=list)
    
    # NEW: Domain-aware fields
    category: str = "general"
    domain_metadata: Optional[DomainMetadata] = None
    phase_metadata: List[PhaseMetadata] = field(default_factory=list)
    
    def __post_init__(self):
        """Auto-generate metadata if not provided"""
        if self.domain_metadata is None:
            self.domain_metadata = self._auto_generate_domain_metadata()
        
        if not self.phase_metadata:
            self.phase_metadata = self._auto_generate_phase_metadata()
    
    def _auto_generate_domain_metadata(self) -> DomainMetadata:
        """Generate domain metadata from category"""
        domain_map = {
            "creative_writing": DomainMetadata(
                domain_id="creative_writing",
                display_name="Creative Writing",
                category="creative",
                icon="✍️",
                color="#8b5cf6",
                description="AI-powered creative writing workflows"
            ),
            "book_writing": DomainMetadata(
                domain_id="book_writing",
                display_name="Book Writing",
                category="creative",
                icon="📚",
                color="#8b5cf6",
                description="Complete book writing workflows"
            )
        }
        
        return domain_map.get(
            self.category,
            DomainMetadata(
                domain_id=self.category,
                display_name=self.name,
                category=self.category
            )
        )
    
    def _auto_generate_phase_metadata(self) -> List[PhaseMetadata]:
        """Auto-generate phases from handlers"""
        phases = []
        order = 0
        
        # Input phase
        if self.input_handlers:
            phases.append(PhaseMetadata(
                phase_id="input",
                name=self._get_phase_name("input"),
                order=order,
                color="#3b82f6",
                icon="📥",
                pipeline_stage=PipelineStage.INPUT,
                description="Input handlers for data collection"
            ))
            order += 1
        
        # Processing phase
        if self.processing_handlers:
            phases.append(PhaseMetadata(
                phase_id="processing",
                name=self._get_phase_name("processing"),
                order=order,
                color="#10b981",
                icon="⚙️",
                pipeline_stage=PipelineStage.PROCESSING,
                description="Processing handlers for generation"
            ))
            order += 1
        
        # Output phase
        if self.output_handlers:
            phases.append(PhaseMetadata(
                phase_id="output",
                name=self._get_phase_name("output"),
                order=order,
                color="#f59e0b",
                icon="📤",
                pipeline_stage=PipelineStage.OUTPUT,
                description="Output handlers for result storage"
            ))
        
        return phases
    
    def _get_phase_name(self, stage: str) -> str:
        """Domain-specific phase names"""
        if self.domain_metadata:
            domain_id = self.domain_metadata.domain_id
            
            phase_names = {
                "book_writing": {
                    "input": "Content Preparation",
                    "processing": "AI Generation",
                    "output": "Chapter Creation"
                },
                "creative_writing": {
                    "input": "Content Preparation",
                    "processing": "AI Generation",
                    "output": "Content Creation"
                }
            }
            
            if domain_id in phase_names:
                return phase_names[domain_id].get(stage, stage.title())
        
        # Fallback
        return {
            "input": "Data Collection",
            "processing": "Processing & Analysis",
            "output": "Output Generation"
        }.get(stage, stage.title())
    
    def to_domain_aware_dict(self) -> Dict:
        """Convert to domain-aware format for Visual Builder"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain_metadata.to_dict(),
            "phases": [
                {
                    **phase.to_dict(),
                    "handlers": self._get_handlers_for_phase(phase)
                }
                for phase in sorted(self.phase_metadata, key=lambda p: p.order)
            ],
            "variables": self.required_variables
        }
    
    def _get_handlers_for_phase(self, phase: PhaseMetadata) -> List[Dict]:
        """Get handlers for a specific phase"""
        stage = phase.pipeline_stage
        
        if stage == PipelineStage.INPUT:
            return self.input_handlers
        elif stage == PipelineStage.PROCESSING:
            return self.processing_handlers
        elif stage == PipelineStage.OUTPUT:
            return self.output_handlers
        
        return []
    
    def to_pipeline_config(self) -> Dict[str, Any]:
        """Backward-compatible: Original format"""
        return {
            "input": self.input_handlers,
            "processing": self.processing_handlers,
            "output": self.output_handlers[0] if self.output_handlers else {}
        }


# ============= ENHANCED TEMPLATES =============

# Chapter Generation (Enhanced)
CHAPTER_GENERATION_V2 = EnhancedWorkflowTemplate(
    template_id="chapter_gen",
    name="Chapter Generation",
    description="Generate complete chapter with AI assistance",
    category="book_writing",
    
    input_handlers=[
        {"handler": "project_fields", "config": {"fields": ["book_title", "genre"]}},
        {"handler": "chapter_data", "config": {"load_previous_chapters": True}}
    ],
    processing_handlers=[
        {"handler": "prompt_template_processor", "config": {"template_key": "chapter_outline"}},
        {"handler": "llm_processor", "config": {"temperature": 0.7, "max_tokens": 2000}}
    ],
    output_handlers=[
        {"handler": "chapter_creator", "config": {"auto_publish": False}}
    ],
    required_variables=["chapter_number", "chapter_title"],
    
    # Explicit domain metadata (optional)
    domain_metadata=DomainMetadata(
        domain_id="book_writing",
        display_name="Book Writing Workflow",
        category="creative",
        icon="📚",
        color="#8b5cf6",
        description="Complete book writing with AI assistance"
    ),
    
    phase_metadata=[
        PhaseMetadata(
            phase_id="preparation",
            name="Content Preparation",
            order=0,
            color="#3b82f6",
            icon="📋",
            pipeline_stage=PipelineStage.INPUT,
            description="Load project and chapter context"
        ),
        PhaseMetadata(
            phase_id="generation",
            name="AI Generation",
            order=1,
            color="#10b981",
            icon="🤖",
            pipeline_stage=PipelineStage.PROCESSING,
            description="Generate chapter content with AI"
        ),
        PhaseMetadata(
            phase_id="finalization",
            name="Chapter Creation",
            order=2,
            color="#f59e0b",
            icon="📝",
            pipeline_stage=PipelineStage.OUTPUT,
            description="Save chapter to database"
        )
    ]
)

# Character Development (Enhanced)
CHARACTER_DEVELOPMENT_V2 = EnhancedWorkflowTemplate(
    template_id="character_dev",
    name="Character Development",
    description="Generate detailed character profile",
    category="book_writing",
    
    processing_handlers=[
        {"handler": "prompt_template_processor", "config": {"template_key": "character_generation"}},
        {"handler": "llm_processor", "config": {"temperature": 0.8, "max_tokens": 3000}}
    ],
    required_variables=["character_name", "genre"]
)


# ============= REGISTRY =============

class EnhancedWorkflowRegistry:
    """Registry for domain-aware templates"""
    
    _templates: Dict[str, EnhancedWorkflowTemplate] = {}
    
    @classmethod
    def register(cls, template: EnhancedWorkflowTemplate):
        """Register a template"""
        cls._templates[template.template_id] = template
    
    @classmethod
    def get(cls, template_id: str) -> Optional[EnhancedWorkflowTemplate]:
        """Get template by ID"""
        return cls._templates.get(template_id)
    
    @classmethod
    def get_all(cls) -> List[EnhancedWorkflowTemplate]:
        """Get all templates"""
        return list(cls._templates.values())
    
    @classmethod
    def get_by_domain(cls, domain_id: str) -> List[EnhancedWorkflowTemplate]:
        """Get all templates for a domain"""
        return [
            t for t in cls._templates.values()
            if t.domain_metadata and t.domain_metadata.domain_id == domain_id
        ]
    
    @classmethod
    def get_domains(cls) -> Dict[str, Dict]:
        """Get all unique domains with template counts"""
        domains = {}
        
        for template in cls._templates.values():
            if template.domain_metadata:
                domain_id = template.domain_metadata.domain_id
                
                if domain_id not in domains:
                    domains[domain_id] = {
                        **template.domain_metadata.to_dict(),
                        "template_count": 0,
                        "templates": []
                    }
                
                domains[domain_id]["template_count"] += 1
                domains[domain_id]["templates"].append({
                    "template_id": template.template_id,
                    "name": template.name
                })
        
        return domains


# Plot Development Template
PLOT_DEVELOPMENT_V2 = EnhancedWorkflowTemplate(
    template_id="plot_dev",
    name="Plot Development",
    description="Create compelling plot structures and story arcs",
    category="book_writing",
    
    input_handlers=[
        {"handler": "project_fields", "config": {"fields": ["book_title", "genre", "target_audience"]}},
        {"handler": "character_data", "config": {"include_relationships": True}}
    ],
    processing_handlers=[
        {"handler": "prompt_template_processor", "config": {"template_key": "plot_structure"}},
        {"handler": "llm_processor", "config": {"temperature": 0.8, "max_tokens": 3000}},
        {"handler": "framework_generator", "config": {"framework_type": "three_act"}}
    ],
    output_handlers=[
        {"handler": "simple_text_field", "config": {"field_name": "plot_outline"}}
    ],
    required_variables=["project_id", "plot_type"],
    
    domain_metadata=DomainMetadata(
        domain_id="book_writing",
        display_name="Book Writing Workflow",
        category="creative",
        icon="📚",
        color="#8b5cf6",
        description="Complete book writing with AI assistance"
    ),
    
    phase_metadata=[
        PhaseMetadata(
            phase_id="story_setup",
            name="Story Setup",
            order=0,
            color="#3b82f6",
            icon="📖",
            pipeline_stage=PipelineStage.INPUT,
            description="Gather story elements and characters"
        ),
        PhaseMetadata(
            phase_id="plot_generation",
            name="Plot Generation",
            order=1,
            color="#10b981",
            icon="🎭",
            pipeline_stage=PipelineStage.PROCESSING,
            description="Generate plot structure with AI"
        ),
        PhaseMetadata(
            phase_id="output",
            name="Save Plot Outline",
            order=2,
            color="#f59e0b",
            icon="💾",
            pipeline_stage=PipelineStage.OUTPUT,
            description="Save generated plot structure"
        )
    ]
)

# World Building Template
WORLD_BUILDING_V2 = EnhancedWorkflowTemplate(
    template_id="world_building",
    name="World Building",
    description="Create rich, detailed fictional worlds",
    category="book_writing",
    
    input_handlers=[
        {"handler": "project_fields", "config": {"fields": ["book_title", "genre"]}},
        {"handler": "world_data", "config": {"include_existing": True}}
    ],
    processing_handlers=[
        {"handler": "prompt_template_processor", "config": {"template_key": "world_creation"}},
        {"handler": "llm_processor", "config": {"temperature": 0.9, "max_tokens": 4000}}
    ],
    output_handlers=[
        {"handler": "simple_text_field", "config": {"field_name": "world_description"}}
    ],
    required_variables=["project_id"],
    
    domain_metadata=DomainMetadata(
        domain_id="book_writing",
        display_name="Book Writing Workflow",
        category="creative",
        icon="📚",
        color="#8b5cf6",
        description="Complete book writing with AI assistance"
    ),
    
    phase_metadata=[
        PhaseMetadata(
            phase_id="world_context",
            name="World Context",
            order=0,
            color="#3b82f6",
            icon="🌍",
            pipeline_stage=PipelineStage.INPUT,
            description="Load existing world data"
        ),
        PhaseMetadata(
            phase_id="world_generation",
            name="World Generation",
            order=1,
            color="#10b981",
            icon="✨",
            pipeline_stage=PipelineStage.PROCESSING,
            description="AI-powered world creation"
        ),
        PhaseMetadata(
            phase_id="save_world",
            name="Save World",
            order=2,
            color="#f59e0b",
            icon="💾",
            pipeline_stage=PipelineStage.OUTPUT,
            description="Store world details"
        )
    ]
)

# Character Arc Template
CHARACTER_ARC_V2 = EnhancedWorkflowTemplate(
    template_id="character_arc",
    name="Character Arc Development",
    description="Develop character transformation arcs throughout the story",
    category="book_writing",
    
    input_handlers=[
        {"handler": "project_fields", "config": {"fields": ["book_title"]}},
        {"handler": "character_data", "config": {"load_full_profile": True}}
    ],
    processing_handlers=[
        {"handler": "prompt_template_processor", "config": {"template_key": "character_arc"}},
        {"handler": "llm_processor", "config": {"temperature": 0.75, "max_tokens": 2500}}
    ],
    output_handlers=[
        {"handler": "simple_text_field", "config": {"field_name": "character_arc"}}
    ],
    required_variables=["project_id", "character_id"],
    
    domain_metadata=DomainMetadata(
        domain_id="book_writing",
        display_name="Book Writing Workflow",
        category="creative",
        icon="📚",
        color="#8b5cf6",
        description="Complete book writing with AI assistance"
    ),
    
    phase_metadata=[
        PhaseMetadata(
            phase_id="character_analysis",
            name="Character Analysis",
            order=0,
            color="#3b82f6",
            icon="👤",
            pipeline_stage=PipelineStage.INPUT,
            description="Analyze character profile"
        ),
        PhaseMetadata(
            phase_id="arc_development",
            name="Arc Development",
            order=1,
            color="#10b981",
            icon="📈",
            pipeline_stage=PipelineStage.PROCESSING,
            description="Generate character transformation arc"
        ),
        PhaseMetadata(
            phase_id="save_arc",
            name="Save Arc",
            order=2,
            color="#f59e0b",
            icon="💾",
            pipeline_stage=PipelineStage.OUTPUT,
            description="Store character arc"
        )
    ]
)


# Register templates
EnhancedWorkflowRegistry.register(CHAPTER_GENERATION_V2)
EnhancedWorkflowRegistry.register(CHARACTER_DEVELOPMENT_V2)
EnhancedWorkflowRegistry.register(PLOT_DEVELOPMENT_V2)
EnhancedWorkflowRegistry.register(WORLD_BUILDING_V2)
EnhancedWorkflowRegistry.register(CHARACTER_ARC_V2)


# Backward-compatible exports
WORKFLOWS_V2 = {
    "chapter_gen": CHAPTER_GENERATION_V2,
    "character_dev": CHARACTER_DEVELOPMENT_V2,
    "plot_dev": PLOT_DEVELOPMENT_V2,
    "world_building": WORLD_BUILDING_V2,
    "character_arc": CHARACTER_ARC_V2
}
