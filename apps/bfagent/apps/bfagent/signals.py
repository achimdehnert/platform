"""
Django Signals for BF Agent
Auto-triggers for model changes

Includes:
- Auto-start Celery task when requirement → in_progress
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import structlog

logger = structlog.get_logger(__name__)

# Track previous status to detect changes
_requirement_previous_status = {}


@receiver(pre_save, sender='bfagent.TestRequirement')
def track_requirement_status_change(sender, instance, **kwargs):
    """Track status before save to detect changes."""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            _requirement_previous_status[str(instance.pk)] = old_instance.status
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender='bfagent.TestRequirement')
def auto_start_requirement_task(sender, instance, created, **kwargs):
    """
    Log when requirement status changes to 'in_progress'.
    
    NOTE: Celery task is now triggered explicitly in cascade_api.session_start()
    to avoid duplicate task runs and give better control.
    """
    # Skip if just created
    if created:
        return
    
    # Get previous status
    previous_status = _requirement_previous_status.pop(str(instance.pk), None)
    
    # Check if status changed TO in_progress - just log, don't trigger task
    if previous_status and previous_status != 'in_progress' and instance.status == 'in_progress':
        logger.info(
            "requirement_status_changed_to_in_progress",
            requirement_id=str(instance.pk),
            requirement_name=instance.name,
            previous_status=previous_status,
            note="Celery task is triggered explicitly in cascade_api, not here"
        )
