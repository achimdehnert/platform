"""
Variant Selection Utility - Phase 3B Session 5

Provides weighted random selection for A/B testing variants.
"""

import random
from typing import List, Optional
from apps.bfagent.models_handlers import ActionHandler


def select_variant(action_id: int, phase: str, order: int) -> Optional[ActionHandler]:
    """
    Select a handler variant based on traffic weights.
    
    Args:
        action_id: The action ID
        phase: The execution phase
        order: The order within phase
        
    Returns:
        Selected ActionHandler instance or None
        
    Example:
        # Variants for chapter_gen:
        # - Variant A (GPT-4): weight=80
        # - Variant B (Claude): weight=15
        # - Variant C (Gemini): weight=5
        # Total weight = 100
        # Random(0-100): 0-79=A, 80-94=B, 95-99=C
    """
    from apps.bfagent.models_handlers import ActionHandler
    
    # Get all active handlers for this action/phase/order
    handlers = ActionHandler.objects.filter(
        action_id=action_id,
        phase=phase,
        order=order,
        is_active=True
    ).order_by('variant')
    
    if not handlers.exists():
        return None
    
    # If only one handler, return it
    if handlers.count() == 1:
        return handlers.first()
    
    # Calculate total weight
    total_weight = sum(h.traffic_weight for h in handlers)
    
    if total_weight == 0:
        # All weights are 0, pick randomly
        return random.choice(list(handlers))
    
    # Weighted random selection
    rand = random.randint(0, total_weight - 1)
    current = 0
    
    for handler in handlers:
        current += handler.traffic_weight
        if rand < current:
            return handler
    
    # Fallback (shouldn't happen)
    return handlers.first()


def get_variant_distribution(action_id: int, phase: str, order: int) -> dict:
    """
    Get the traffic distribution for variants.
    
    Returns:
        {
            'variant_a': {'handler': <Handler>, 'weight': 80, 'percentage': 80.0},
            'variant_b': {'handler': <Handler>, 'weight': 15, 'percentage': 15.0},
            ...
        }
    """
    from apps.bfagent.models_handlers import ActionHandler
    
    handlers = ActionHandler.objects.filter(
        action_id=action_id,
        phase=phase,
        order=order,
        is_active=True
    ).select_related('handler')
    
    total_weight = sum(h.traffic_weight for h in handlers)
    
    distribution = {}
    for h in handlers:
        variant_key = h.variant or 'default'
        percentage = (h.traffic_weight / total_weight * 100) if total_weight > 0 else 0
        
        distribution[variant_key] = {
            'handler': h.handler,
            'weight': h.traffic_weight,
            'percentage': round(percentage, 1),
            'handler_id': h.handler.handler_id,
            'display_name': h.handler.display_name,
        }
    
    return distribution
