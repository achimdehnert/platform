"""
LLM Auto-Router Service
========================

Intelligentes Routing von Tasks basierend auf Complexity-Level.
Nutzt das vorhandene `complexity` Feld aus TestRequirement.

Routing-Logik:
- LOW: Lokale LLMs (Ollama) - schnell, kostenlos
- MEDIUM: Lokale LLMs (Ollama/vLLM) - größere Modelle
- HIGH: Cloud APIs (OpenAI/Anthropic) oder Cascade - komplexe Tasks

Usage:
    from apps.bfagent.services.llm_router import LLMRouter
    
    router = LLMRouter()
    llm = router.get_llm_for_task(complexity='medium', task_type='coding')
    result = router.execute(prompt, complexity='low')
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Task complexity levels matching TestRequirement.complexity"""
    AUTO = 'auto'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class TaskType(Enum):
    """Types of tasks for routing decisions"""
    CODING = 'coding'
    WRITING = 'writing'
    ANALYSIS = 'analysis'
    TRANSLATION = 'translation'
    CHAT = 'chat'
    ILLUSTRATION = 'illustration'


@dataclass
class RoutingDecision:
    """Result of routing decision"""
    llm_id: int
    llm_name: str
    provider: str
    reason: str
    estimated_cost: float
    is_local: bool
    requires_cascade: bool


class LLMRouter:
    """
    Intelligent LLM router based on task complexity and type.
    
    Routing Strategy:
    - LOW complexity → Local LLMs (Ollama 8B models)
    - MEDIUM complexity → Local LLMs (Ollama 33B/70B models)
    - HIGH complexity → Cloud APIs or delegate to Cascade
    """
    
    # Routing rules: (complexity, task_type) → provider_preferences
    ROUTING_RULES = {
        # LOW complexity - use small, fast local models
        (ComplexityLevel.LOW, TaskType.CODING): ['ollama_small', 'ollama_coder', 'api_fast'],
        (ComplexityLevel.LOW, TaskType.WRITING): ['ollama_small', 'api_fast'],
        (ComplexityLevel.LOW, TaskType.ANALYSIS): ['ollama_small', 'api_fast'],
        (ComplexityLevel.LOW, TaskType.TRANSLATION): ['ollama_small', 'api_fast'],
        (ComplexityLevel.LOW, TaskType.CHAT): ['ollama_small', 'api_fast'],
        
        # MEDIUM complexity - use larger local models
        (ComplexityLevel.MEDIUM, TaskType.CODING): ['ollama_coder', 'ollama_large', 'api_standard'],
        (ComplexityLevel.MEDIUM, TaskType.WRITING): ['ollama_large', 'api_standard'],
        (ComplexityLevel.MEDIUM, TaskType.ANALYSIS): ['ollama_large', 'api_standard'],
        (ComplexityLevel.MEDIUM, TaskType.TRANSLATION): ['ollama_large', 'api_standard'],
        (ComplexityLevel.MEDIUM, TaskType.CHAT): ['ollama_large', 'api_standard'],
        
        # HIGH complexity - use best available, consider Cascade
        (ComplexityLevel.HIGH, TaskType.CODING): ['cascade', 'api_premium', 'ollama_large'],
        (ComplexityLevel.HIGH, TaskType.WRITING): ['api_premium', 'ollama_large'],
        (ComplexityLevel.HIGH, TaskType.ANALYSIS): ['cascade', 'api_premium'],
        (ComplexityLevel.HIGH, TaskType.TRANSLATION): ['api_premium', 'ollama_large'],
        (ComplexityLevel.HIGH, TaskType.CHAT): ['api_premium', 'ollama_large'],
    }
    
    # Provider categories mapped to LLM criteria
    PROVIDER_CRITERIA = {
        'ollama_small': {'provider': 'ollama', 'max_params': '8B', 'is_local': True},
        'ollama_coder': {'provider': 'ollama', 'name_contains': 'coder', 'is_local': True},
        'ollama_large': {'provider': 'ollama', 'min_params': '33B', 'is_local': True},
        'vllm': {'provider': 'vllm', 'is_local': True},
        'api_fast': {'provider__in': ['openai', 'groq'], 'model_tier': 'fast'},
        'api_standard': {'provider__in': ['openai', 'anthropic'], 'model_tier': 'standard'},
        'api_premium': {'provider__in': ['openai', 'anthropic'], 'model_tier': 'premium'},
        'cascade': {'requires_cascade': True},
    }
    
    def __init__(self):
        self._llm_cache = None
        self._cache_timestamp = None
    
    def _get_available_llms(self) -> List[Dict]:
        """Get all active LLMs from database"""
        try:
            from apps.bfagent.models import Llms
            
            llms = Llms.objects.filter(is_active=True).values(
                'id', 'name', 'provider', 'model_id', 'api_endpoint',
                'is_local', 'max_tokens', 'cost_per_1k_input', 'cost_per_1k_output'
            )
            return list(llms)
        except Exception as e:
            logger.error(f"Failed to get LLMs: {e}")
            return []
    
    def _match_llm_to_category(self, llm: Dict, category: str) -> bool:
        """Check if LLM matches a provider category"""
        criteria = self.PROVIDER_CRITERIA.get(category, {})
        
        if criteria.get('requires_cascade'):
            return False  # Cascade is handled separately
        
        # Check provider
        if 'provider' in criteria:
            if llm.get('provider', '').lower() != criteria['provider'].lower():
                return False
        
        if 'provider__in' in criteria:
            if llm.get('provider', '').lower() not in [p.lower() for p in criteria['provider__in']]:
                return False
        
        # Check is_local
        if 'is_local' in criteria:
            if llm.get('is_local') != criteria['is_local']:
                return False
        
        # Check name contains (for coder models)
        if 'name_contains' in criteria:
            if criteria['name_contains'].lower() not in llm.get('name', '').lower():
                return False
        
        return True
    
    def estimate_complexity(self, 
                           description: str, 
                           files_affected: int = 0,
                           acceptance_criteria_count: int = 0,
                           category: str = None) -> ComplexityLevel:
        """
        Auto-estimate complexity based on task characteristics.
        
        Args:
            description: Task description text
            files_affected: Number of files likely affected
            acceptance_criteria_count: Number of acceptance criteria
            category: Task category (bug_fix, feature, refactor, etc.)
        
        Returns:
            ComplexityLevel enum value
        """
        score = 0
        text = description.lower()
        
        # HIGH complexity keywords
        high_keywords = [
            'refactor', 'architektur', 'migration', 'security', 'performance',
            'multi-file', 'database schema', 'breaking change', 'api design',
            'authentication', 'authorization', 'caching', 'optimization'
        ]
        
        # MEDIUM complexity keywords
        medium_keywords = [
            'new view', 'model', 'api', 'handler', 'service', 'endpoint',
            'validation', 'form', 'serializer', 'test', 'integration'
        ]
        
        # LOW complexity keywords
        low_keywords = [
            'typo', 'text', 'config', 'template', 'css', 'label', 'string',
            'comment', 'documentation', 'readme', 'formatting', 'style'
        ]
        
        # Score based on keywords
        if any(kw in text for kw in high_keywords):
            score += 3
        if any(kw in text for kw in medium_keywords):
            score += 2
        if any(kw in text for kw in low_keywords):
            score -= 1
        
        # Score based on files affected
        if files_affected > 5:
            score += 3
        elif files_affected > 2:
            score += 1
        
        # Score based on acceptance criteria
        if acceptance_criteria_count > 5:
            score += 2
        elif acceptance_criteria_count > 2:
            score += 1
        
        # Score based on category
        if category in ['security', 'performance', 'refactor']:
            score += 2
        elif category in ['feature']:
            score += 1
        elif category in ['bug_fix'] and 'simple' not in text:
            score += 1
        
        # Determine complexity
        if score >= 5:
            return ComplexityLevel.HIGH
        elif score >= 2:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.LOW
    
    def get_routing_decision(self,
                            complexity: str = 'auto',
                            task_type: str = 'coding',
                            description: str = '',
                            llm_override_id: int = None) -> RoutingDecision:
        """
        Get routing decision for a task.
        
        Args:
            complexity: 'auto', 'low', 'medium', 'high'
            task_type: 'coding', 'writing', 'analysis', etc.
            description: Task description for auto-estimation
            llm_override_id: Optional specific LLM to use
        
        Returns:
            RoutingDecision with selected LLM info
        """
        # Handle override
        if llm_override_id:
            try:
                from apps.bfagent.models import Llms
                llm = Llms.objects.get(id=llm_override_id)
                return RoutingDecision(
                    llm_id=llm.id,
                    llm_name=llm.name,
                    provider=llm.provider,
                    reason="LLM override specified",
                    estimated_cost=0.0,
                    is_local=llm.is_local,
                    requires_cascade=False
                )
            except Exception:
                pass  # Fall through to normal routing
        
        # Determine complexity
        if complexity == 'auto':
            complexity_level = self.estimate_complexity(description)
        else:
            complexity_level = ComplexityLevel(complexity)
        
        # Get task type enum
        try:
            task_type_enum = TaskType(task_type.lower())
        except ValueError:
            task_type_enum = TaskType.CODING
        
        # Get routing preferences
        preferences = self.ROUTING_RULES.get(
            (complexity_level, task_type_enum),
            ['ollama_small', 'api_standard']  # Default fallback
        )
        
        # Check for Cascade requirement
        if 'cascade' in preferences and preferences.index('cascade') == 0:
            return RoutingDecision(
                llm_id=0,
                llm_name="Cascade (Claude/GPT-4)",
                provider="cascade",
                reason=f"HIGH complexity {task_type} task - requires Cascade",
                estimated_cost=0.0,
                is_local=False,
                requires_cascade=True
            )
        
        # Find matching LLM
        available_llms = self._get_available_llms()
        
        for category in preferences:
            if category == 'cascade':
                continue
            
            for llm in available_llms:
                if self._match_llm_to_category(llm, category):
                    return RoutingDecision(
                        llm_id=llm['id'],
                        llm_name=llm['name'],
                        provider=llm['provider'],
                        reason=f"{complexity_level.value.upper()} complexity → {category}",
                        estimated_cost=float(llm.get('cost_per_1k_input', 0) or 0),
                        is_local=llm.get('is_local', False),
                        requires_cascade=False
                    )
        
        # No match found - return cascade as fallback
        return RoutingDecision(
            llm_id=0,
            llm_name="Cascade (fallback)",
            provider="cascade",
            reason="No matching LLM found - falling back to Cascade",
            estimated_cost=0.0,
            is_local=False,
            requires_cascade=True
        )
    
    def execute(self,
               prompt: str,
               system_prompt: str = "",
               complexity: str = 'auto',
               task_type: str = 'coding',
               description: str = '',
               llm_override_id: int = None,
               max_tokens: int = 4096) -> Dict[str, Any]:
        """
        Execute a task with automatic LLM routing.
        
        Args:
            prompt: The prompt to execute
            system_prompt: Optional system prompt
            complexity: Complexity level or 'auto'
            task_type: Type of task
            description: Task description for auto-estimation
            llm_override_id: Optional LLM override
            max_tokens: Maximum tokens for response
        
        Returns:
            Dict with 'ok', 'text', 'routing', 'error' keys
        """
        # Get routing decision
        routing = self.get_routing_decision(
            complexity=complexity,
            task_type=task_type,
            description=description,
            llm_override_id=llm_override_id
        )
        
        # If requires Cascade, return decision for caller to handle
        if routing.requires_cascade:
            return {
                'ok': False,
                'text': None,
                'routing': routing.__dict__,
                'error': None,
                'requires_cascade': True,
                'message': f"Task requires Cascade: {routing.reason}"
            }
        
        # Execute with selected LLM
        try:
            from apps.bfagent.models import Llms
            from apps.bfagent.services.llm_client import generate_text, LlmRequest
            
            llm = Llms.objects.get(id=routing.llm_id)
            
            request = LlmRequest(
                provider=llm.provider,
                api_endpoint=llm.api_endpoint,
                api_key=llm.api_key or '',
                model=llm.model_id,
                system=system_prompt,
                prompt=prompt,
                max_tokens=max_tokens,
            )
            
            result = generate_text(request)
            
            return {
                'ok': result.get('ok', False),
                'text': result.get('text'),
                'routing': routing.__dict__,
                'error': result.get('error'),
                'requires_cascade': False,
                'latency_ms': result.get('latency_ms')
            }
            
        except Exception as e:
            logger.exception("LLM execution failed")
            return {
                'ok': False,
                'text': None,
                'routing': routing.__dict__,
                'error': str(e),
                'requires_cascade': False
            }


# Singleton instance
_router_instance = None

def get_router() -> LLMRouter:
    """Get singleton router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance
