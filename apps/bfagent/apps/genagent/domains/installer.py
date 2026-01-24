"""
Domain Template Installer

Converts Domain Templates into database workflows.
Connects the template system with the Phase/Action database models.
"""

import logging
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.utils import timezone

from .base import DomainTemplate, PhaseTemplate, ActionTemplate
from .registry import DomainRegistry

# Import Phase/Action Models from genagent
try:
    from apps.genagent.models import Phase, Action
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    Phase = None
    Action = None

logger = logging.getLogger(__name__)


class DomainInstaller:
    """
    Installs Domain Templates as database workflows
    
    Converts DomainTemplate → Phase/Action DB objects
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Args:
            dry_run: If True, no database changes
        """
        self.dry_run = dry_run
        self.stats = {
            'phases_created': 0,
            'actions_created': 0,
            'errors': []
        }
    
    def install_from_registry(
        self,
        domain_id: str,
        initial_context: Dict[str, Any] = None
    ) -> Optional[int]:
        """
        Installs a template from the registry
        
        Args:
            domain_id: ID of template to install
            initial_context: Initial context (e.g. story_id)
            
        Returns:
            First Phase ID or None on error
        """
        template = DomainRegistry.get(domain_id)
        return self.install_template(template, initial_context)
    
    def install_template(
        self,
        template: DomainTemplate,
        initial_context: Dict[str, Any] = None
    ) -> Optional[int]:
        """
        Installs a template as workflow in database
        
        Args:
            template: Template to install
            initial_context: Initial context (e.g. story_id)
            
        Returns:
            First Phase ID or None on error
        """
        if not MODELS_AVAILABLE:
            raise RuntimeError("Phase/Action models not available")
        
        # Validate template
        try:
            template.validate()
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            self.stats['errors'].append(str(e))
            return None
        
        # Validate required fields
        if initial_context:
            missing = template.validate_required_fields(initial_context)
            if missing:
                error = f"Missing required fields: {missing}"
                logger.error(error)
                self.stats['errors'].append(error)
                return None
        
        logger.info(f"Installing template '{template.domain_id}' as workflow...")
        
        if self.dry_run:
            logger.info("   (DRY RUN - no database changes)")
            self._dry_run_preview(template)
            return None
        
        try:
            with transaction.atomic():
                first_phase_id = None
                
                # Create phases
                for phase_template in template.phases:
                    phase = self._create_phase_from_template(phase_template)
                    
                    if first_phase_id is None:
                        first_phase_id = phase.id
                    
                    # Create actions for this phase
                    for action_template in phase_template.actions:
                        self._create_action_from_template(
                            action_template,
                            phase=phase
                        )
                
                logger.info(
                    f"Installation complete! "
                    f"Created {self.stats['phases_created']} phases, "
                    f"{self.stats['actions_created']} actions"
                )
                
                return first_phase_id
                
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            self.stats['errors'].append(str(e))
            raise
    
    def _create_phase_from_template(
        self,
        phase_template: PhaseTemplate
    ) -> 'Phase':
        """Creates a Phase from PhaseTemplate"""
        phase = Phase.objects.create(
            name=phase_template.name,
            description=phase_template.description,
            order=phase_template.order,
            color=phase_template.color,
            is_active=phase_template.required
        )
        
        self.stats['phases_created'] += 1
        logger.debug(f"  Created phase: {phase.name}")
        
        return phase
    
    def _create_action_from_template(
        self,
        action_template: ActionTemplate,
        phase: 'Phase'
    ) -> 'Action':
        """Creates an Action from ActionTemplate"""
        action = Action.objects.create(
            phase=phase,
            name=action_template.name,
            description=action_template.description,
            handler_class=action_template.handler_class,
            order=action_template.order,
            config=action_template.config,
            timeout_seconds=action_template.timeout_seconds,
            retry_count=action_template.retry_count,
            continue_on_error=action_template.continue_on_error
        )
        
        self.stats['actions_created'] += 1
        logger.debug(f"    Created action: {action.name}")
        
        return action
    
    def _dry_run_preview(self, template: DomainTemplate) -> None:
        """Prints preview of what would be created"""
        print("\n" + "="*60)
        print(f"DRY RUN PREVIEW: {template.display_name}")
        print("="*60)
        
        print(f"\nWould create:")
        print(f"   • Domain: {template.domain_id}")
        print(f"   • Phases: {len(template.phases)}")
        print(f"   • Actions: {len(template.get_all_actions())}")
        
        print(f"\nPhase Structure:")
        for phase in template.phases:
            print(f"\n   Phase {phase.order}: {phase.name}")
            print(f"      Color: {phase.color}")
            print(f"      Actions: {len(phase.actions)}")
            for action in phase.actions:
                print(f"         → {action.name}")
                print(f"            Handler: {action.handler_class}")
                print(f"            Config: {action.config}")
        
        print("\n" + "="*60 + "\n")
    
    def batch_install(
        self,
        domain_ids: List[str],
        initial_contexts: List[Dict[str, Any]] = None
    ) -> Dict[str, Optional[int]]:
        """
        Installs multiple templates at once
        
        Args:
            domain_ids: List of domain IDs to install
            initial_contexts: Optional list of contexts (same length as domain_ids)
            
        Returns:
            Dict of domain_id -> phase_id (or None on error)
        """
        if initial_contexts and len(initial_contexts) != len(domain_ids):
            raise ValueError("initial_contexts must match domain_ids length")
        
        results = {}
        
        for i, domain_id in enumerate(domain_ids):
            context = initial_contexts[i] if initial_contexts else None
            
            try:
                phase_id = self.install_from_registry(domain_id, context)
                results[domain_id] = phase_id
            except Exception as e:
                logger.error(f"Failed to install {domain_id}: {e}")
                results[domain_id] = None
        
        return results


# ==================== CONVENIENCE FUNCTIONS ====================

def install_domain(
    domain_id: str,
    context: Dict[str, Any] = None,
    dry_run: bool = False
) -> Optional[int]:
    """
    Convenience function to install a domain template
    
    Args:
        domain_id: ID of template in registry
        context: Initial context
        dry_run: If True, only preview
        
    Returns:
        First Phase ID or None
        
    Example:
        >>> phase_id = install_domain('book', {'story_id': 123})
        >>> print(f"Created workflow starting with phase {phase_id}")
    """
    installer = DomainInstaller(dry_run=dry_run)
    return installer.install_from_registry(domain_id, context)


def update_domain(
    phase_id: int,
    domain_id: str,
    preserve_logs: bool = True
) -> bool:
    """
    Updates an existing workflow with new template
    
    Args:
        phase_id: ID of first phase to update
        domain_id: Template to update from
        preserve_logs: Keep execution logs
        
    Returns:
        True if successful
    """
    # TODO: Implement update logic
    # This would:
    # 1. Find all phases/actions related to this workflow
    # 2. Compare with new template
    # 3. Update/create/delete as needed
    # 4. Preserve execution logs if requested
    
    logger.warning("update_domain not yet implemented")
    return False
