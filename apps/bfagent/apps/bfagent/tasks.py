"""
Celery Tasks for BF Agent
Async long-running operations

Includes:
- Auto-illustration tasks
- Delegated LLM task execution (for complexity-based routing)
- Requirement auto-processing (when status → in_progress)
- n8n Webhook Integration
"""
from celery import shared_task
import structlog
import requests
from django.conf import settings

logger = structlog.get_logger(__name__)


def trigger_n8n_webhook(requirement, celery_task_id: str) -> dict:
    """
    Trigger n8n webhook when requirement processing starts.
    
    Args:
        requirement: TestRequirement instance
        celery_task_id: Current Celery task ID
        
    Returns:
        Dict with trigger result
    """
    n8n_base_url = getattr(settings, 'N8N_BASE_URL', None)
    n8n_webhook_url = getattr(settings, 'N8N_WEBHOOK_URL', None)
    
    if not n8n_base_url:
        logger.debug("n8n_not_configured")
        return {'triggered': False, 'reason': 'N8N_BASE_URL not configured'}
    
    # Construct webhook URL for requirement processing
    webhook_url = n8n_webhook_url or f"{n8n_base_url}/webhook/requirement-process"
    
    payload = {
        'event': 'requirement_started',
        'requirement': {
            'id': str(requirement.pk),
            'name': requirement.name,
            'description': requirement.description[:500] if requirement.description else '',
            'status': requirement.status,
            'category': requirement.category,
            'priority': requirement.priority,
        },
        'initiative': {
            'id': str(requirement.initiative.pk) if requirement.initiative else None,
            'title': requirement.initiative.title if requirement.initiative else None,
        },
        'celery_task_id': celery_task_id,
        'source': 'bfagent-celery',
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'X-BFAgent-Source': 'celery-task',
            },
            timeout=10
        )
        
        logger.info(
            "n8n_webhook_triggered",
            webhook_url=webhook_url,
            status_code=response.status_code,
            requirement_id=str(requirement.pk)
        )
        
        return {
            'triggered': True,
            'webhook_url': webhook_url,
            'status_code': response.status_code,
            'response': response.text[:200] if response.text else None
        }
        
    except requests.exceptions.Timeout:
        logger.warning("n8n_webhook_timeout", webhook_url=webhook_url)
        return {'triggered': False, 'reason': 'Webhook timeout'}
    except requests.exceptions.ConnectionError:
        logger.warning("n8n_webhook_connection_error", webhook_url=webhook_url)
        return {'triggered': False, 'reason': 'Connection error - n8n not reachable'}
    except Exception as e:
        logger.error("n8n_webhook_error", error=str(e))
        return {'triggered': False, 'reason': str(e)}


# =============================================================================
# REQUIREMENT AUTO-PROCESSING
# =============================================================================

@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_requirement_task(self, requirement_id: str):
    """
    Process a requirement that was moved to 'in_progress'.
    
    This task:
    1. Loads the requirement details
    2. Runs MCP analysis tools (analyze_requirement, check_workflow_rules)
    3. Generates enhanced Cascade context
    4. Optionally triggers n8n workflow
    5. Updates status when complete
    
    Args:
        requirement_id: UUID of the TestRequirement
        
    Returns:
        Dict with processing result
    """
    from apps.bfagent.models_testing import TestRequirement, RequirementFeedback
    from apps.bfagent.services.requirement_analyzer import (
        analyze_requirement, check_workflow_rules, generate_cascade_context, work_on_requirement
    )
    
    logger.info("requirement_task_started", requirement_id=requirement_id)
    
    try:
        requirement = TestRequirement.objects.select_related('initiative').get(pk=requirement_id)
        
        # Add feedback that processing started
        RequirementFeedback.objects.create(
            requirement=requirement,
            feedback_type='progress',
            content=f"🤖 **Auto-Worker gestartet**\n\nCelery Task: `{self.request.id}`\nRequirement wird analysiert...",
            is_from_cascade=True
        )
        
        # Log to initiative if exists
        if requirement.initiative:
            requirement.initiative.log_activity(
                action='task_started',
                details=f"Auto-Worker für '{requirement.name}' gestartet (Task: {self.request.id})",
                actor='celery'
            )
        
        # ===== RUN MCP ANALYSIS TOOLS =====
        
        # 1. Analyze requirement quality
        analysis = analyze_requirement(requirement)
        quality_score = analysis.get('quality_score', 0)
        feasibility = analysis.get('feasibility', 'unknown')
        
        analysis_summary = f"📊 **Requirement Analyse**\n\n"
        analysis_summary += f"**Quality Score:** {quality_score}/100\n"
        analysis_summary += f"**Feasibility:** {feasibility.upper()}\n"
        
        if analysis.get('issues'):
            analysis_summary += f"\n**Issues ({len(analysis['issues'])}):**\n"
            for issue in analysis['issues'][:3]:  # Max 3 issues
                analysis_summary += f"- ⚠️ {issue}\n"
        
        if analysis.get('suggestions'):
            analysis_summary += f"\n**Suggestions:**\n"
            for suggestion in analysis['suggestions'][:3]:  # Max 3 suggestions
                analysis_summary += f"- 💡 {suggestion}\n"
        
        RequirementFeedback.objects.create(
            requirement=requirement,
            feedback_type='comment',
            content=analysis_summary,
            is_from_cascade=True
        )
        
        # 2. Check workflow rules
        rules = check_workflow_rules(requirement)
        
        if rules.get('violations') or rules.get('warnings'):
            rules_summary = "🔍 **Workflow Check**\n\n"
            if rules.get('violations'):
                rules_summary += f"**❌ Violations ({len(rules['violations'])}):**\n"
                for v in rules['violations']:
                    rules_summary += f"- {v}\n"
            if rules.get('warnings'):
                rules_summary += f"\n**⚠️ Warnings ({len(rules['warnings'])}):**\n"
                for w in rules['warnings']:
                    rules_summary += f"- {w}\n"
            
            RequirementFeedback.objects.create(
                requirement=requirement,
                feedback_type='blocker' if rules.get('violations') else 'comment',
                content=rules_summary,
                is_from_cascade=True
            )
        
        # ===== CALL LLM TO ACTUALLY WORK ON THE REQUIREMENT =====
        RequirementFeedback.objects.create(
            requirement=requirement,
            feedback_type='progress',
            content=f"🤖 **LLM wird aufgerufen...**\n\nModel: wird ermittelt\nKategorie: {requirement.category}",
            is_from_cascade=True
        )
        
        llm_result = work_on_requirement(requirement, analysis)
        
        if llm_result.get('ok') and llm_result.get('response'):
            # LLM successfully worked on the requirement
            response_preview = llm_result['response'][:2000] if len(llm_result['response']) > 2000 else llm_result['response']
            RequirementFeedback.objects.create(
                requirement=requirement,
                feedback_type='solution',
                content=f"🧠 **LLM Lösung ({llm_result.get('model', 'unknown')})**\n\nTokens: {llm_result.get('tokens_input', 0)} → {llm_result.get('tokens_output', 0)}\nDauer: {llm_result.get('duration_ms', 0)}ms\n\n---\n\n{response_preview}",
                is_from_cascade=True
            )
        else:
            # LLM call failed
            RequirementFeedback.objects.create(
                requirement=requirement,
                feedback_type='blocker',
                content=f"❌ **LLM Fehler**\n\n{llm_result.get('error', 'Unbekannter Fehler')}\n\n*Hinweis: Prüfe LLM-Konfiguration in Settings oder Requirement.*",
                is_from_cascade=True
            )
        
        # Trigger n8n Webhook if configured (optional - not required for task completion)
        n8n_result = trigger_n8n_webhook(requirement, self.request.id)
        
        if n8n_result.get('triggered'):
            status_code = n8n_result.get('status_code', 'N/A')
            if status_code == 200:
                RequirementFeedback.objects.create(
                    requirement=requirement,
                    feedback_type='progress',
                    content=f"🔗 **n8n Workflow gestartet**\n\nWebhook: `{n8n_result.get('webhook_url', 'N/A')}`",
                    is_from_cascade=True
                )
            else:
                # n8n not available or workflow not active - just log, don't block
                RequirementFeedback.objects.create(
                    requirement=requirement,
                    feedback_type='comment',
                    content=f"ℹ️ **n8n Webhook optional**\n\nStatus: {status_code} (Workflow nicht aktiv oder nicht konfiguriert)",
                    is_from_cascade=True
                )
        
        # ===== TASK COMPLETION FEEDBACK =====
        RequirementFeedback.objects.create(
            requirement=requirement,
            feedback_type='solution',
            content=f"✅ **Celery Task abgeschlossen**\n\nTask: `{self.request.id}`\nRequirement bereit für Bearbeitung.\n\n**Nächster Schritt:** Kontext in Cascade einfügen und autonom arbeiten lassen.",
            is_from_cascade=True
        )
        
        # Log to initiative if exists
        if requirement.initiative:
            requirement.initiative.log_activity(
                action='task_completed',
                details=f"Auto-Worker für '{requirement.name}' abgeschlossen (Task: {self.request.id})",
                actor='celery'
            )
        
        logger.info("requirement_task_completed", requirement_id=requirement_id, n8n=n8n_result)
        
        return {
            'ok': True,
            'requirement_id': requirement_id,
            'requirement_name': requirement.name,
            'n8n_triggered': n8n_result.get('triggered', False),
            'message': 'Task verarbeitet'
        }
        
    except TestRequirement.DoesNotExist:
        logger.error("requirement_not_found", requirement_id=requirement_id)
        return {'ok': False, 'error': f'Requirement {requirement_id} nicht gefunden'}
    except Exception as e:
        logger.exception("requirement_task_failed", requirement_id=requirement_id, error=str(e))
        
        # Add error feedback
        try:
            requirement = TestRequirement.objects.get(pk=requirement_id)
            RequirementFeedback.objects.create(
                requirement=requirement,
                feedback_type='blocker',
                content=f"❌ **Auto-Worker Fehler**\n\n{str(e)}",
                is_from_cascade=True
            )
        except Exception:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {'ok': False, 'error': str(e)}


# =============================================================================
# DELEGATED TASK EXECUTION (Complexity-based LLM Routing)
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_delegated_task(self, task_id: str):
    """
    Execute a delegated task in the background.
    
    This task is called when a task is queued for background execution.
    Currently runs synchronously (Celery not active), but the structure
    is ready for async background processing.
    
    Args:
        task_id: UUID of the DelegatedTask to execute
        
    Returns:
        Dict with execution result
    """
    from apps.bfagent.services.task_executor import get_executor
    from apps.bfagent.models_tasks import DelegatedTask
    
    logger.info("delegated_task_started", task_id=task_id, celery_task_id=self.request.id)
    
    try:
        # Update task with celery ID
        try:
            task = DelegatedTask.objects.get(id=task_id)
            task.celery_task_id = self.request.id
            task.status = 'queued'
            task.save(update_fields=['celery_task_id', 'status'])
        except DelegatedTask.DoesNotExist:
            logger.error("delegated_task_not_found", task_id=task_id)
            return {'ok': False, 'error': f'Task {task_id} not found'}
        
        # Execute
        executor = get_executor()
        result = executor.execute_task(task_id)
        
        logger.info(
            "delegated_task_completed", 
            task_id=task_id, 
            success=result.get('ok'),
            llm_used=result.get('llm_used')
        )
        
        return result
        
    except Exception as e:
        logger.exception("delegated_task_failed", task_id=task_id, error=str(e))
        
        # Mark task as failed
        try:
            task = DelegatedTask.objects.get(id=task_id)
            task.mark_failed(str(e))
        except Exception:
            pass
        
        # Retry if possible
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {'ok': False, 'error': str(e)}


@shared_task(bind=True)
def batch_execute_delegated_tasks(self, task_ids: list):
    """
    Execute multiple delegated tasks in sequence.
    
    Useful for batch operations where multiple simple tasks
    need to be processed.
    
    Args:
        task_ids: List of DelegatedTask UUIDs
        
    Returns:
        Dict with batch results
    """
    logger.info("batch_execution_started", task_count=len(task_ids))
    
    results = []
    for task_id in task_ids:
        try:
            result = execute_delegated_task(task_id)
            results.append({
                'task_id': task_id,
                'ok': result.get('ok', False),
                'error': result.get('error')
            })
        except Exception as e:
            results.append({
                'task_id': task_id,
                'ok': False,
                'error': str(e)
            })
    
    success_count = sum(1 for r in results if r.get('ok'))
    logger.info(
        "batch_execution_completed", 
        total=len(task_ids), 
        success=success_count,
        failed=len(task_ids) - success_count
    )
    
    return {
        'total': len(task_ids),
        'success': success_count,
        'failed': len(task_ids) - success_count,
        'results': results
    }


# =============================================================================
# ILLUSTRATION TASKS
# =============================================================================


@shared_task(bind=True)
def auto_illustrate_chapter_task(self, chapter_id: int, user_id: int, max_illustrations: int = 3):
    """
    Async task for auto-illustrating a chapter
    
    Args:
        self: Celery task instance (for progress updates)
        chapter_id: Chapter ID to illustrate
        user_id: User ID (for permissions)
        max_illustrations: Maximum number of illustrations
        
    Returns:
        Dict with results
    """
    from apps.bfagent.handlers.chapter_illustration_handler import ChapterIllustrationHandler
    from apps.bfagent.models import Chapter
    import asyncio
    
    logger.info("task_started", task_id=self.request.id, chapter_id=chapter_id, user_id=user_id)
    
    try:
        # Update state
        self.update_state(state='ANALYZING', meta={'progress': 10, 'status': 'Analyzing chapter...'})
        
        # Get chapter
        try:
            chapter = Chapter.objects.get(pk=chapter_id, project__user_id=user_id)
        except Chapter.DoesNotExist:
            raise ValueError(f"Chapter {chapter_id} not found or access denied")
        
        # Initialize handler (use mock mode from env or settings)
        handler = ChapterIllustrationHandler(mock_mode=False)
        
        # Update state
        self.update_state(state='GENERATING_PROMPTS', meta={'progress': 30, 'status': 'Generating prompts...'})
        
        # Run auto-illustration (sync wrapper for async function)
        result = asyncio.run(handler.auto_illustrate_chapter(
            chapter_id=chapter.id,
            chapter_text=chapter.text or "",
            max_illustrations=max_illustrations,
            style_profile=None,  # TODO: Get from project settings
            provider='dalle3',
            quality='standard'
        ))
        
        # Update state
        self.update_state(state='GENERATING_IMAGES', meta={'progress': 60, 'status': f'Generating {result.total_positions_found} images...'})
        
        # Save results to database
        # TODO: Create GeneratedImage objects and link to chapter
        
        logger.info("task_completed", task_id=self.request.id, images_generated=result.images_generated, cost=result.total_cost_usd)
        
        return {
            'status': 'SUCCESS',
            'chapter_id': chapter_id,
            'images_generated': result.images_generated,
            'total_cost_usd': result.total_cost_usd,
            'duration_seconds': result.duration_seconds,
            'positions': [p.dict() for p in result.positions],
            'images': result.generated_images
        }
    
    except Exception as e:
        logger.error("task_failed", task_id=self.request.id, chapter_id=chapter_id, error=str(e))
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
