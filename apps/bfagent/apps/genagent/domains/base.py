"""
Domain Template System - Base Classes for Universal Workflows

Enables definition of any domain (forensic reports, scientific papers,
medical diagnostics, etc.) through reusable templates.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Callable
from enum import Enum
from datetime import datetime


class ExecutionMode(Enum):
    """Execution modes for actions"""
    SEQUENTIAL = "sequential"  # One after another
    PARALLEL = "parallel"      # Simultaneously (where possible)
    CONDITIONAL = "conditional"  # Based on conditions


class ValidationLevel(Enum):
    """Validation levels"""
    NONE = "none"
    BASIC = "basic"      # Only data types
    STRICT = "strict"    # Full business logic validation
    CUSTOM = "custom"    # Domain-specific rules


@dataclass
class ActionTemplate:
    """
    Template for a single action in a workflow
    
    An action is an atomic work unit (e.g., "analyze photo",
    "research literature", "make diagnosis")
    """
    
    # Identification
    name: str
    handler_class: str  # Full Python path, e.g. 'apps.genagent.handlers.demo_handlers.EchoHandler'
    description: str = ""
    
    # Workflow position
    order: int = 0
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Execution parameters
    timeout_seconds: int = 300
    retry_count: int = 0
    continue_on_error: bool = False
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Names of other actions
    required_fields: List[str] = field(default_factory=list)  # Required context fields
    
    # Optional: Execution conditions
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    # Metadata
    estimated_duration_seconds: int = 60
    tags: List[str] = field(default_factory=list)
    
    def validate_config(self) -> bool:
        """Validates the action configuration"""
        if not self.name:
            raise ValueError("Action name cannot be empty")
        
        if not self.handler_class:
            raise ValueError(f"Action '{self.name}' has no handler_class defined")
        
        if self.timeout_seconds <= 0:
            raise ValueError(f"Action '{self.name}' timeout must be positive")
        
        return True
    
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """
        Checks if action should be executed
        
        Args:
            context: Current workflow context
            
        Returns:
            True if action should be executed
        """
        # 1. Check required fields
        for field_name in self.required_fields:
            if field_name not in context:
                return False
        
        # 2. Check custom condition
        if self.condition and not self.condition(context):
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes to dictionary for DB storage"""
        return {
            'name': self.name,
            'handler_class': self.handler_class,
            'description': self.description,
            'order': self.order,
            'config': self.config,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'continue_on_error': self.continue_on_error,
            'dependencies': self.dependencies,
            'required_fields': self.required_fields,
            'tags': self.tags,
        }


@dataclass
class PhaseTemplate:
    """
    Template for a workflow phase
    
    A phase groups related actions (e.g., "Data Collection",
    "Analysis", "Documentation")
    """
    
    # Identification
    name: str
    description: str = ""
    
    # Workflow position
    order: int = 0
    
    # Visual representation
    color: str = "#3B82F6"
    icon: str = ""
    
    # Actions in this phase
    actions: List[ActionTemplate] = field(default_factory=list)
    
    # Execution mode
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    
    # Flags
    required: bool = True  # Can phase be skipped?
    parallel_execution: bool = False  # Execute actions in parallel?
    
    # Validation
    validation_level: ValidationLevel = ValidationLevel.BASIC
    
    # Metadata
    estimated_duration_seconds: int = 0  # Calculated from actions
    
    def __post_init__(self):
        """Calculates metadata after initialization"""
        if not self.estimated_duration_seconds:
            self.estimated_duration_seconds = sum(
                action.estimated_duration_seconds for action in self.actions
            )
    
    def add_action(self, action: ActionTemplate) -> None:
        """Adds an action to this phase"""
        action.order = len(self.actions)
        self.actions.append(action)
        self.estimated_duration_seconds += action.estimated_duration_seconds
    
    def get_action(self, name: str) -> Optional[ActionTemplate]:
        """Finds action by name"""
        for action in self.actions:
            if action.name == name:
                return action
        return None
    
    def validate(self) -> bool:
        """Validates the phase configuration"""
        if not self.name:
            raise ValueError("Phase name cannot be empty")
        
        if not self.actions:
            raise ValueError(f"Phase '{self.name}' has no actions defined")
        
        # Validate all actions
        for action in self.actions:
            action.validate_config()
        
        # Check dependencies
        action_names = {action.name for action in self.actions}
        for action in self.actions:
            for dep in action.dependencies:
                if dep not in action_names:
                    raise ValueError(
                        f"Action '{action.name}' depends on '{dep}' "
                        f"which is not in phase '{self.name}'"
                    )
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'order': self.order,
            'color': self.color,
            'icon': self.icon,
            'actions': [action.to_dict() for action in self.actions],
            'execution_mode': self.execution_mode.value,
            'required': self.required,
            'parallel_execution': self.parallel_execution,
        }


@dataclass
class DomainTemplate:
    """
    Complete template for a domain
    
    Defines all phases, actions and configurations for a
    complete workflow (e.g., forensic report, dissertation)
    """
    
    # ==================== IDENTIFICATION ====================
    
    domain_id: str  # Unique identifier, e.g. 'explosion', 'thesis'
    display_name: str  # Display name, e.g. 'Forensic Report'
    description: str = ""
    
    # ==================== VISUAL REPRESENTATION ====================
    
    icon: str = "📄"  # Emoji or icon name
    color: str = "#3B82F6"  # Primary color for UI
    
    # ==================== WORKFLOW STRUCTURE ====================
    
    phases: List[PhaseTemplate] = field(default_factory=list)
    
    # ==================== HANDLER MAPPING ====================
    
    handlers: Dict[str, Type] = field(default_factory=dict)  # handler_class -> Handler class
    
    # ==================== CONFIGURATION ====================
    
    default_config: Dict[str, Any] = field(default_factory=dict)  # Default settings
    required_fields: List[str] = field(default_factory=list)  # Required fields to start
    optional_fields: List[str] = field(default_factory=list)  # Optional fields
    
    # ==================== OUTPUT ====================
    
    output_format: str = "pdf"  # 'pdf', 'docx', 'html', 'json'
    output_template: Optional[str] = None  # Path to template file
    
    # ==================== VALIDATION ====================
    
    validation_rules: Dict[str, Callable] = field(default_factory=dict)  # field_name -> validator
    validation_level: ValidationLevel = ValidationLevel.BASIC
    
    # ==================== METADATA ====================
    
    version: str = "1.0"
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    tags: List[str] = field(default_factory=list)  # e.g. ['forensic', 'technical', 'expert-report']
    category: str = "general"  # e.g. 'expert_reports', 'academic', 'creative'
    
    # ==================== CAPABILITIES ====================
    
    supports_async: bool = False  # Supports asynchronous execution?
    supports_resume: bool = True  # Can workflow be resumed?
    supports_branches: bool = False  # Supports conditional branches?
    
    # ==================== ESTIMATIONS ====================
    
    estimated_total_duration_seconds: int = 0  # Calculated
    estimated_cost: float = 0.0  # Optional: Estimated costs (e.g. API calls)
    
    def __post_init__(self):
        """Calculates metadata after initialization"""
        if not self.estimated_total_duration_seconds:
            self.estimated_total_duration_seconds = sum(
                phase.estimated_duration_seconds for phase in self.phases
            )
    
    # ==================== PHASE MANAGEMENT ====================
    
    def add_phase(self, phase: PhaseTemplate) -> None:
        """Adds a phase"""
        phase.order = len(self.phases)
        self.phases.append(phase)
        self.estimated_total_duration_seconds += phase.estimated_duration_seconds
    
    def get_phase(self, name: str) -> Optional[PhaseTemplate]:
        """Finds phase by name"""
        for phase in self.phases:
            if phase.name == name:
                return phase
        return None
    
    def get_phase_by_order(self, order: int) -> Optional[PhaseTemplate]:
        """Finds phase by order"""
        for phase in self.phases:
            if phase.order == order:
                return phase
        return None
    
    # ==================== ACTION MANAGEMENT ====================
    
    def get_all_actions(self) -> List[ActionTemplate]:
        """Returns all actions from all phases"""
        actions = []
        for phase in self.phases:
            actions.extend(phase.actions)
        return actions
    
    def get_action(self, name: str) -> Optional[ActionTemplate]:
        """Finds action by name across all phases"""
        for phase in self.phases:
            action = phase.get_action(name)
            if action:
                return action
        return None
    
    # ==================== VALIDATION ====================
    
    def validate(self) -> bool:
        """
        Complete validation of the template
        
        Checks:
        - Domain configuration
        - All phases
        - All actions
        - Handler availability
        - Dependencies
        """
        # 1. Basic validation
        if not self.domain_id:
            raise ValueError("domain_id cannot be empty")
        
        if not self.display_name:
            raise ValueError("display_name cannot be empty")
        
        if not self.phases:
            raise ValueError(f"Domain '{self.domain_id}' has no phases defined")
        
        # 2. Validate all phases
        for phase in self.phases:
            phase.validate()
        
        # 3. Check handler availability (optional - handlers might be registered later)
        # We'll make this lenient for now
        
        return True
    
    def validate_required_fields(self, context: Dict[str, Any]) -> List[str]:
        """
        Validates if all required fields are present in context
        
        Returns:
            List of missing fields (empty = all ok)
        """
        missing = []
        for field_name in self.required_fields:
            if field_name not in context:
                missing.append(field_name)
        
        # Validate with custom validators
        for field_name, validator in self.validation_rules.items():
            if field_name in context:
                try:
                    if not validator(context[field_name]):
                        missing.append(f"{field_name} (validation failed)")
                except Exception as e:
                    missing.append(f"{field_name} (validation error: {e})")
        
        return missing
    
    # ==================== SERIALIZATION ====================
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes template to dictionary for DB/JSON"""
        return {
            'domain_id': self.domain_id,
            'display_name': self.display_name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'phases': [phase.to_dict() for phase in self.phases],
            'default_config': self.default_config,
            'required_fields': self.required_fields,
            'optional_fields': self.optional_fields,
            'output_format': self.output_format,
            'validation_level': self.validation_level.value,
            'version': self.version,
            'author': self.author,
            'tags': self.tags,
            'category': self.category,
            'supports_async': self.supports_async,
            'supports_resume': self.supports_resume,
            'supports_branches': self.supports_branches,
            'estimated_total_duration_seconds': self.estimated_total_duration_seconds,
            'estimated_cost': self.estimated_cost,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainTemplate':
        """Creates template from dictionary"""
        # Reconstruct phases
        phases = [
            PhaseTemplate(
                name=p['name'],
                description=p['description'],
                order=p['order'],
                color=p['color'],
                icon=p.get('icon', ''),
                actions=[
                    ActionTemplate(
                        name=a['name'],
                        handler_class=a['handler_class'],
                        description=a['description'],
                        order=a['order'],
                        config=a['config'],
                        timeout_seconds=a['timeout_seconds'],
                        retry_count=a['retry_count'],
                        continue_on_error=a['continue_on_error'],
                        dependencies=a.get('dependencies', []),
                        required_fields=a.get('required_fields', []),
                        tags=a.get('tags', []),
                    )
                    for a in p['actions']
                ],
                execution_mode=ExecutionMode(p['execution_mode']),
                required=p['required'],
                parallel_execution=p['parallel_execution'],
            )
            for p in data['phases']
        ]
        
        return cls(
            domain_id=data['domain_id'],
            display_name=data['display_name'],
            description=data['description'],
            icon=data['icon'],
            color=data['color'],
            phases=phases,
            default_config=data['default_config'],
            required_fields=data['required_fields'],
            optional_fields=data.get('optional_fields', []),
            output_format=data['output_format'],
            validation_level=ValidationLevel(data['validation_level']),
            version=data['version'],
            author=data.get('author', ''),
            tags=data['tags'],
            category=data['category'],
            supports_async=data['supports_async'],
            supports_resume=data['supports_resume'],
            supports_branches=data['supports_branches'],
        )
    
    # ==================== UTILITY METHODS ====================
    
    def estimate_workflow_duration(self, context: Dict[str, Any] = None) -> int:
        """
        Estimates workflow duration based on context
        
        Can consider conditional actions
        """
        total = 0
        
        for phase in self.phases:
            if not phase.required:
                continue  # Don't count optional phases
            
            for action in phase.actions:
                # Check if action would be executed
                if context and not action.should_execute(context):
                    continue
                
                total += action.estimated_duration_seconds
        
        return total
    
    def get_statistics(self) -> Dict[str, Any]:
        """Returns statistics about the template"""
        all_actions = self.get_all_actions()
        
        return {
            'domain_id': self.domain_id,
            'total_phases': len(self.phases),
            'total_actions': len(all_actions),
            'required_phases': sum(1 for p in self.phases if p.required),
            'optional_phases': sum(1 for p in self.phases if not p.required),
            'actions_with_dependencies': sum(1 for a in all_actions if a.dependencies),
            'conditional_actions': sum(1 for a in all_actions if a.condition),
            'estimated_duration_hours': self.estimated_total_duration_seconds / 3600,
            'parallel_capable_phases': sum(1 for p in self.phases if p.parallel_execution),
            'tags': self.tags,
            'category': self.category,
        }
    
    def __repr__(self) -> str:
        return (
            f"DomainTemplate(id='{self.domain_id}', "
            f"name='{self.display_name}', "
            f"phases={len(self.phases)}, "
            f"actions={len(self.get_all_actions())})"
        )


# ==================== HELPER FUNCTIONS ====================

def create_simple_action(
    name: str,
    handler_class: str,
    description: str = "",
    config: Dict[str, Any] = None,
    timeout: int = 300
) -> ActionTemplate:
    """Helper function to quickly create an action"""
    return ActionTemplate(
        name=name,
        handler_class=handler_class,
        description=description,
        config=config or {},
        timeout_seconds=timeout
    )


def create_simple_phase(
    name: str,
    actions: List[ActionTemplate],
    description: str = "",
    color: str = "#3B82F6"
) -> PhaseTemplate:
    """Helper function to quickly create a phase"""
    return PhaseTemplate(
        name=name,
        description=description,
        color=color,
        actions=actions
    )
