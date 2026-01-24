#!/usr/bin/env python
"""Create orchestrator-handler bridge integration"""
import os
from pathlib import Path

# Target file path
target_dir = Path('apps/bfagent/services')
target_file = target_dir / 'orchestrator_bridge.py'

# Ensure directory exists
target_dir.mkdir(parents=True, exist_ok=True)

# File content
content = '''"""
Multi-Hub Framework - Orchestrator-Handler Bridge
Integrates the Orchestrator with existing Handler Framework

This module connects:
- WorkflowOrchestrator (Multi-Hub Framework)
- Handler System (Input/Processing/Output)
- PhaseActionConfig (Workflow Phases)
- PromptTemplate (Template System)
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
import logging

from django.db import transaction

from .orchestrator import (
    WorkflowOrchestrator,
    WorkflowStep,
    WorkflowContext,
    WorkflowStatus,
    get_orchestrator,
)
from .handlers.registries import (
    InputHandlerRegistry,
    ProcessingHandlerRegistry,
    OutputHandlerRegistry,
)

if TYPE_CHECKING:
    from apps.bfagent.models import (
        PhaseActionConfig,
        PromptTemplate,
        AgentAction,
        WorkflowPhase,
    )

logger = logging.getLogger(__name__)


class HandlerExecutor:
    """
    Executes workflow steps using the Handler Framework
    Bridges Orchestrator and Handler systems
    """
    
    def __init__(self, context: WorkflowContext):
        """Initialize with workflow context"""
        self.context = context
        self.orchestrator = get_orchestrator()
    
    def execute_step_with_handlers(
        self,
        step: WorkflowStep,
        phase_actions: Optional[List['PhaseActionConfig']] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow step using configured handlers
        
        Args:
            step: Workflow step to execute
            phase_actions: PhaseActionConfig entries for this phase
            
        Returns:
            Execution result with handler outputs
        """
        from apps.bfagent.models import PhaseActionConfig, WorkflowPhase
        
        result = {
            'success': True,
            'step_name': step.phase_name,
            'actions_executed': [],
            'handler_results': {},
            'context_updates': {},
        }
        
        try:
            # Get phase from database
            phase = WorkflowPhase.objects.get(name=step.phase_name)
            
            # Get configured actions for this phase if not provided
            if phase_actions is None:
                phase_actions = PhaseActionConfig.objects.filter(
                    phase=phase,
                    action__is_active=True
                ).select_related('action').order_by('order')
            
            # Execute each action using handlers
            for phase_action in phase_actions:
                action = phase_action.action
                
                # Get action configuration
                action_config = action.config or {}
                
                # Execute action handlers
                action_result = self._execute_action_handlers(
                    action=action,
                    config=action_config,
                    is_required=phase_action.is_required
                )
                
                result['actions_executed'].append({
                    'action': action.name,
                    'display_name': action.display_name,
                    'success': action_result.get('success', False),
                    'required': phase_action.is_required,
                })
                
                # Collect handler results
                if 'handler_results' in action_result:
                    result['handler_results'][action.name] = action_result['handler_results']
                
                # Update context
                if 'context_updates' in action_result:
                    result['context_updates'].update(action_result['context_updates'])
                
                # Fail if required action failed
                if phase_action.is_required and not action_result.get('success'):
                    result['success'] = False
                    result['error'] = f"Required action '{action.display_name}' failed"
                    break
            
            logger.info(
                f"Executed step '{step.phase_name}' with {len(result['actions_executed'])} actions"
            )
            
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _execute_action_handlers(
        self,
        action: 'AgentAction',
        config: Dict[str, Any],
        is_required: bool
    ) -> Dict[str, Any]:
        """
        Execute a single action using its configured handlers
        
        Pipeline:
        1. INPUT: Collect data (Input Handlers)
        2. PROCESSING: Transform data (Processing Handlers + PromptTemplate)
        3. OUTPUT: Store results (Output Handlers)
        """
        result = {
            'success': True,
            'handler_results': {
                'input': {},
                'processing': {},
                'output': {},
            },
            'context_updates': {},
        }
        
        try:
            # === STAGE 1: INPUT ===
            input_data = self._execute_input_handlers(
                config.get('input_handlers', [])
            )
            result['handler_results']['input'] = input_data
            
            # === STAGE 2: PROCESSING ===
            processing_config = config.get('processing', {})
            processed_data = self._execute_processing_handlers(
                input_data=input_data,
                processing_config=processing_config
            )
            result['handler_results']['processing'] = processed_data
            
            # === STAGE 3: OUTPUT ===
            output_results = self._execute_output_handlers(
                processed_data=processed_data,
                output_handlers=config.get('output_handlers', [])
            )
            result['handler_results']['output'] = output_results
            
            # Update context with results
            result['context_updates'] = {
                f'{action.name}_output': output_results
            }
            
        except Exception as e:
            logger.error(f"Action handler execution failed: {e}")
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _execute_input_handlers(
        self,
        handler_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute input handlers to collect data"""
        collected_data = {}
        
        for handler_config in handler_configs:
            handler_name = handler_config.get('handler')
            handler_settings = handler_config.get('config', {})
            
            try:
                HandlerClass = InputHandlerRegistry.get(handler_name)
                if not HandlerClass:
                    logger.warning(f"Input handler '{handler_name}' not found")
                    continue
                
                handler = HandlerClass(config=handler_settings)
                data = handler.collect(self.context.data)
                collected_data[handler_name] = data
                
                logger.debug(f"Input handler '{handler_name}' collected data")
                
            except Exception as e:
                logger.error(f"Input handler '{handler_name}' failed: {e}")
                collected_data[handler_name] = {'error': str(e)}
        
        return collected_data
    
    def _execute_processing_handlers(
        self,
        input_data: Dict[str, Any],
        processing_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute processing handlers to transform data"""
        processed_results = {}
        
        # Check if using PromptTemplate
        if 'template_key' in processing_config:
            template_result = self._execute_with_template(
                input_data=input_data,
                template_key=processing_config['template_key'],
                variables=processing_config.get('variables', {})
            )
            processed_results['template'] = template_result
        
        # Execute additional processing handlers
        for handler_config in processing_config.get('handlers', []):
            handler_name = handler_config.get('handler')
            handler_settings = handler_config.get('config', {})
            
            try:
                HandlerClass = ProcessingHandlerRegistry.get(handler_name)
                if not HandlerClass:
                    logger.warning(f"Processing handler '{handler_name}' not found")
                    continue
                
                handler = HandlerClass(config=handler_settings)
                result = handler.process(input_data, self.context.data)
                processed_results[handler_name] = result
                
                logger.debug(f"Processing handler '{handler_name}' completed")
                
            except Exception as e:
                logger.error(f"Processing handler '{handler_name}' failed: {e}")
                processed_results[handler_name] = {'error': str(e)}
        
        return processed_results
    
    def _execute_with_template(
        self,
        input_data: Dict[str, Any],
        template_key: str,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute using PromptTemplate"""
        from apps.bfagent.models import PromptTemplate
        
        try:
            template = PromptTemplate.objects.get(template_key=template_key)
            
            # Merge input data with variables
            all_variables = {**input_data, **variables}
            
            # TODO: Execute template with LLM
            # This would use the PromptTemplate's system_prompt and user_prompt_template
            # For now, return stub
            
            return {
                'template': template.name,
                'template_key': template_key,
                'status': 'stub',
                'message': 'Template execution not yet implemented',
                'variables': list(all_variables.keys()),
            }
            
        except PromptTemplate.DoesNotExist:
            logger.error(f"PromptTemplate '{template_key}' not found")
            return {
                'error': f"Template '{template_key}' not found",
                'status': 'error',
            }
    
    def _execute_output_handlers(
        self,
        processed_data: Dict[str, Any],
        output_handlers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute output handlers to store results"""
        output_results = {}
        
        for handler_config in output_handlers:
            handler_name = handler_config.get('handler')
            handler_settings = handler_config.get('config', {})
            
            try:
                HandlerClass = OutputHandlerRegistry.get(handler_name)
                if not HandlerClass:
                    logger.warning(f"Output handler '{handler_name}' not found")
                    continue
                
                handler = HandlerClass(config=handler_settings)
                
                # Parse data
                parsed_data = handler.parse(processed_data)
                
                # Validate
                validation = handler.validate(parsed_data)
                
                if validation.get('valid'):
                    # Store results (in real implementation)
                    output_results[handler_name] = {
                        'status': 'success',
                        'parsed_count': len(parsed_data) if isinstance(parsed_data, list) else 1,
                        'validation': validation,
                    }
                    logger.debug(f"Output handler '{handler_name}' completed")
                else:
                    output_results[handler_name] = {
                        'status': 'validation_failed',
                        'errors': validation.get('errors', []),
                    }
                
            except Exception as e:
                logger.error(f"Output handler '{handler_name}' failed: {e}")
                output_results[handler_name] = {'error': str(e)}
        
        return output_results


class IntegratedOrchestrator(WorkflowOrchestrator):
    """
    Enhanced Orchestrator with Handler Framework integration
    Extends base WorkflowOrchestrator with handler execution
    """
    
    def execute_workflow_with_handlers(
        self,
        context: WorkflowContext,
        steps: Optional[List[WorkflowStep]] = None
    ) -> Dict[str, Any]:
        """
        Execute workflow using Handler Framework
        
        Args:
            context: Workflow context
            steps: Optional pre-built steps
            
        Returns:
            Workflow execution results with handler outputs
        """
        if steps is None:
            steps = self.build_workflow(
                context.domain_art,
                context.domain_type
            )
        
        executor = HandlerExecutor(context)
        results = {
            'status': 'success',
            'completed_steps': [],
            'failed_steps': [],
            'handler_results': {},
        }
        
        try:
            with transaction.atomic():
                for step in steps:
                    # Execute with handlers
                    step_result = executor.execute_step_with_handlers(step)
                    
                    if step_result.get('success'):
                        step.status = WorkflowStatus.COMPLETED
                        results['completed_steps'].append(step.phase_name)
                        results['handler_results'][step.phase_name] = step_result['handler_results']
                        
                        # Update context
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
                    f"Workflow completed: {len(results['completed_steps'])} steps"
                )
                
        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            logger.error(f"Workflow execution failed: {e}")
        
        return results


def get_integrated_orchestrator() -> IntegratedOrchestrator:
    """Get integrated orchestrator instance"""
    return IntegratedOrchestrator()
'''

# Write file
print(f'📝 Creating {target_file}...')
with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'✅ Created: {target_file}')
print(f'📊 Size: {os.path.getsize(target_file)} bytes')
print('\n✅ Orchestrator-Handler Bridge created!')
print('\n📦 Integration Features:')
print('   • HandlerExecutor - Executes steps with handlers')
print('   • IntegratedOrchestrator - Enhanced orchestrator')
print('   • INPUT/PROCESSING/OUTPUT pipeline')
print('   • PromptTemplate integration')
print('   • PhaseActionConfig support')