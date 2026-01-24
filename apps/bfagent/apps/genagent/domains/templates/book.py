"""
Book Writing Domain Template

Defines workflow for book writing process
"""

from apps.genagent.domains import (
    DomainTemplate,
    PhaseTemplate,
    ActionTemplate,
    ExecutionMode,
    ValidationLevel,
    DomainRegistry,
)

# Create Book Domain Template
BOOK_TEMPLATE = DomainTemplate(
    # ==================== IDENTIFICATION ====================
    domain_id="book",
    display_name="Book Writing",
    description="Complete workflow for AI-assisted book writing",
    
    # ==================== VISUAL ====================
    icon="BOOK",
    color="#3B82F6",
    
    # ==================== WORKFLOW ====================
    phases=[
        PhaseTemplate(
            name="Planning",
            description="Initial planning and setup phase",
            order=0,
            color="#8B5CF6",
            icon="TARGET",
            execution_mode=ExecutionMode.SEQUENTIAL,
            actions=[
                ActionTemplate(
                    name="Welcome Message",
                    handler_class="apps.genagent.handlers.demo_handlers.WelcomeHandler",
                    description="Welcomes user to book writing workflow",
                    order=0,
                    config={
                        "message": "Welcome to Book Writing Workflow"
                    },
                    estimated_duration_seconds=5
                ),
                ActionTemplate(
                    name="Validate Project Data",
                    handler_class="apps.genagent.handlers.demo_handlers.DataValidationHandler",
                    description="Validates required project information",
                    order=1,
                    config={
                        "required_fields": ["title", "genre", "target_audience"]
                    },
                    required_fields=["title", "genre", "target_audience"],
                    estimated_duration_seconds=10
                ),
            ]
        ),
        
        PhaseTemplate(
            name="Development",
            description="Core writing and development phase",
            order=1,
            color="#10B981",
            icon="PENCIL",
            execution_mode=ExecutionMode.SEQUENTIAL,
            actions=[
                ActionTemplate(
                    name="Process Title",
                    handler_class="apps.genagent.handlers.demo_handlers.DataTransformHandler",
                    description="Transforms and formats book title",
                    order=0,
                    config={
                        "source_field": "title",
                        "target_field": "formatted_title",
                        "transform": "capitalize"
                    },
                    estimated_duration_seconds=5
                ),
                ActionTemplate(
                    name="Log Progress",
                    handler_class="apps.genagent.handlers.demo_handlers.LogHandler",
                    description="Logs workflow progress",
                    order=1,
                    config={
                        "level": "info",
                        "message": "Processing book: {context}"
                    },
                    estimated_duration_seconds=2
                ),
            ]
        ),
        
        PhaseTemplate(
            name="Finalization",
            description="Final steps and completion",
            order=2,
            color="#F59E0B",
            icon="CHECK",
            execution_mode=ExecutionMode.SEQUENTIAL,
            actions=[
                ActionTemplate(
                    name="Final Validation",
                    handler_class="apps.genagent.handlers.demo_handlers.DataValidationHandler",
                    description="Final validation before completion",
                    order=0,
                    config={
                        "required_fields": ["title", "formatted_title"]
                    },
                    estimated_duration_seconds=5
                ),
            ]
        ),
    ],
    
    # ==================== CONFIGURATION ====================
    required_fields=["title", "genre", "target_audience"],
    optional_fields=["description", "author", "target_word_count"],
    default_config={
        "auto_save": True,
        "track_progress": True
    },
    
    # ==================== VALIDATION ====================
    validation_level=ValidationLevel.BASIC,
    
    # ==================== METADATA ====================
    version="1.0.0",
    author="GenAgent Team",
    tags=["creative", "writing", "books", "ai-assisted"],
    category="creative",
    
    # ==================== CAPABILITIES ====================
    supports_async=False,
    supports_resume=True,
    supports_branches=False,
)

# Auto-register on import
DomainRegistry.register(BOOK_TEMPLATE)
