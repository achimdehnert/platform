#!/usr/bin/env python
"""Create orchestrator.py for Multi-Hub Framework"""
import os
from pathlib import Path

# Target file path
target_dir = Path('apps/bfagent/services')
target_file = target_dir / 'orchestrator.py'

# Ensure directory exists
target_dir.mkdir(parents=True, exist_ok=True)

# File content
content = '''"""
Multi-Hub Framework - Workflow Orchestrator
Central coordination between different domain hubs

Phase 3 of Multi-Hub Framework Integration:
- Orchestrates workflows across multiple domains
- Manages hub-specific execution
- Coordinates dependencies between workflow steps
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import logging

from django.db import transaction
from django.apps import apps

if TYPE_CHECKING:
    from apps.bfagent.models_domains import DomainArt, DomainType, DomainPhase
    from apps.bfagent.models import WorkflowPhase, AgentAction

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    phase_name: str
    hub_name: str
    action: str
    order: int
    is_required: bool
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowContext:
    """Context shared across workflow execution"""
    domain_art: str
    domain_type: str
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    completed_steps: List[str] = field(default_factory=list)


class WorkflowOrchestrator:
    """
    Central coordination engine for Multi-Hub Framework
    Manages cross-hub workflows and dependencies
    """
    
    def __init__(self):
        """Initialize orchestrator with registered hubs"""
        self.hubs: Dict[str, 'BaseHub'] = {}
        self._hub_mapping = {
            'book_creation': 'books',
            'expertise_management': 'experts',
            'customer_support': 'support',
            'content_formatting': 'formats',
            'research_management': 'research',
        }
        self._load_hubs()
    
    def _load_hubs(self):
        """Load and register available hubs"""
        # Register hubs (initially empty, can be extended)
        from .hubs import (
            BooksHub,
            ExpertsHub,
            SupportHub,
            FormatsHub,
            ResearchHub
        )
        
        self.hubs = {
            'books': BooksHub(),
            'experts': ExpertsHub(),
            'support': SupportHub(),
            'formats': FormatsHub(),
            'research': ResearchHub(),
        }
        logger.info(f"Loaded {len(self.hubs)} workflow hubs")
    
    def build_workflow(
        self, 
        domain_art: str, 
        domain_type: str,
        project_config: Optional[Dict[str, Any]] = None
    ) -> List[WorkflowStep]:
        """
        Build workflow from database configuration
        
        Args:
            domain_art: Domain art name (e.g., 'book_creation')
            domain_type: Domain type name (e.g., 'fiction')
            project_config: Optional project-specific configuration
            
        Returns:
            List of workflow steps in execution order
        """
        from apps.bfagent.models_domains import DomainArt, DomainType, DomainPhase
        
        try:
            # Get domain and type
            domain = DomainArt.objects.get(name=domain_art, is_active=True)
            dtype = DomainType.objects.get(
                domain_art=domain,
                name=domain_type,
                is_active=True
            )
            
            # Get phases for this domain type
            domain_phases = DomainPhase.objects.filter(
                domain_type=dtype,
                is_active=True
            ).select_related('workflow_phase').order_by('sort_order')
            
            # Build workflow steps
            steps = []
            hub_name = self._hub_mapping.get(domain_art, 'books')
            
            for domain_phase in domain_phases:
                phase = domain_phase.workflow_phase
                
                step = WorkflowStep(
                    phase_name=phase.name,
                    hub_name=hub_name,
                    action=f"execute_{phase.name.lower().replace(' ', '_')}",
                    order=domain_phase.sort_order,
                    is_required=domain_phase.is_required,
                    config=domain_phase.config or {},
                    dependencies=[]
                )
                steps.append(step)
            
            logger.info(
                f"Built workflow for {domain_art}/{domain_type}: "
                f"{len(steps)} steps"
            )
            return steps
            
        except Exception as e:
            logger.error(f"Error building workflow: {e}")
            raise
    
    def execute_workflow(
        self,
        context: WorkflowContext,
        steps: Optional[List[WorkflowStep]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow with the given context
        
        Args:
            context: Workflow execution context
            steps: Optional pre-built workflow steps, otherwise builds from DB
            
        Returns:
            Workflow execution results
        """
        if steps is None:
            steps = self.build_workflow(
                context.domain_art,
                context.domain_type
            )
        
        results = {
            'status': 'success',
            'completed_steps': [],
            'failed_steps': [],
            'skipped_steps': [],
            'context': context,
        }
        
        try:
            with transaction.atomic():
                for step in steps:
                    # Check dependencies
                    if not self._check_dependencies(step, context):
                        if step.is_required:
                            raise Exception(
                                f"Required step '{step.phase_name}' failed "
                                f"dependency check"
                            )
                        results['skipped_steps'].append(step.phase_name)
                        logger.warning(
                            f"Skipped optional step: {step.phase_name}"
                        )
                        continue
                    
                    # Execute step
                    step_result = self._execute_step(step, context)
                    
                    if step_result.get('success'):
                        step.status = WorkflowStatus.COMPLETED
                        step.result = step_result
                        context.completed_steps.append(step.phase_name)
                        results['completed_steps'].append(step.phase_name)
                        
                        # Update context with step results
                        if 'context_updates' in step_result:
                            context.data.update(step_result['context_updates'])
                    else:
                        step.status = WorkflowStatus.FAILED
                        if step.is_required:
                            raise Exception(
                                f"Required step '{step.phase_name}' failed: "
                                f"{step_result.get('error')}"
                            )
                        results['failed_steps'].append({
                            'step': step.phase_name,
                            'error': step_result.get('error')
                        })
                
                logger.info(
                    f"Workflow completed: {len(results['completed_steps'])} "
                    f"steps successful"
                )
                
        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            logger.error(f"Workflow execution failed: {e}")
        
        return results
    
    def _execute_step(
        self, 
        step: WorkflowStep, 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step
        
        Args:
            step: The workflow step to execute
            context: Workflow context
            
        Returns:
            Step execution result
        """
        hub = self.hubs.get(step.hub_name)
        if not hub:
            return {
                'success': False,
                'error': f"Hub '{step.hub_name}' not found"
            }
        
        try:
            step.status = WorkflowStatus.IN_PROGRESS
            result = hub.execute_action(step, context)
            return result
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _check_dependencies(
        self, 
        step: WorkflowStep, 
        context: WorkflowContext
    ) -> bool:
        """Check if step dependencies are satisfied"""
        for dep in step.dependencies:
            if dep not in context.completed_steps:
                return False
        return True
    
    def get_workflow_status(
        self, 
        domain_art: str, 
        domain_type: str,
        project_id: int
    ) -> Dict[str, Any]:
        """
        Get current workflow status for a project
        
        Args:
            domain_art: Domain art name
            domain_type: Domain type name
            project_id: Project ID
            
        Returns:
            Workflow status information
        """
        # TODO: Implement workflow status tracking
        # This would query a WorkflowExecution model or similar
        return {
            'domain_art': domain_art,
            'domain_type': domain_type,
            'project_id': project_id,
            'status': 'not_implemented',
        }


class BaseHub:
    """Base class for all domain hubs"""
    
    def __init__(self, domain_art: str):
        """
        Initialize hub
        
        Args:
            domain_art: Domain art identifier
        """
        self.domain_art = domain_art
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def execute_action(
        self, 
        step: WorkflowStep, 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """
        Execute an action within this hub
        
        Args:
            step: Workflow step to execute
            context: Current execution context
            
        Returns:
            Action execution results
        """
        action_method = getattr(self, step.action, None)
        
        if not action_method:
            self.logger.warning(
                f"Action '{step.action}' not implemented in {self.__class__.__name__}"
            )
            return {
                'success': True,
                'message': f"Action '{step.action}' not implemented (stub)",
                'context_updates': {}
            }
        
        try:
            result = action_method(step, context)
            self.logger.info(f"Executed {step.action} successfully")
            return result
        except Exception as e:
            self.logger.error(f"Action {step.action} failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_input(
        self, 
        step: WorkflowStep, 
        context: WorkflowContext
    ) -> bool:
        """Validate input for a step"""
        # Override in subclasses for specific validation
        return True


# Global orchestrator instance
_orchestrator: Optional[WorkflowOrchestrator] = None


def get_orchestrator() -> WorkflowOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator()
    return _orchestrator
'''

# Write file
print(f'📝 Creating {target_file}...')
with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'✅ Created: {target_file}')
print(f'📊 Size: {os.path.getsize(target_file)} bytes')
print('\n🚀 Next: Create hub implementations (hubs.py)')