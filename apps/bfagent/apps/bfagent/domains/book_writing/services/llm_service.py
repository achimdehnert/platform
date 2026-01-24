"""
LLM Service for Book Writing
Handles API calls to OpenAI/Anthropic for content generation

UPDATED: Now uses LLMAgent as primary backend with automatic:
- Model routing (fast/balanced/best)
- Response caching
- Cost tracking
- Fallback chain
Falls back to direct API calls if gateway unavailable.
"""
import logging
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Import LLMAgent for centralized LLM access
try:
    from apps.bfagent.services.llm_agent import LLMAgent, ModelPreference, get_llm_agent
    LLMAGENT_AVAILABLE = True
except ImportError:
    LLMAGENT_AVAILABLE = False
    logger.warning("LLMAgent not available, using direct API calls")


class LLMService:
    """
    Service for LLM API calls
    Supports OpenAI and can be extended for other providers
    """
    
    def __init__(self, provider: str = "openai", model: str = None):
        """
        Initialize LLM Service
        
        Args:
            provider: 'openai' or 'anthropic'
            model: Model name (default: gpt-4 for OpenAI)
        """
        self.provider = provider
        self.model = model or self._get_default_model()
        self.api_key = self._get_api_key()
        self.client = self._initialize_client()
    
    def _get_default_model(self) -> str:
        """Get default model based on provider"""
        defaults = {
            'openai': 'gpt-4',
            'anthropic': 'claude-3-opus-20240229'
        }
        return defaults.get(self.provider, 'gpt-4')
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from Django settings"""
        if self.provider == 'openai':
            return getattr(settings, 'OPENAI_API_KEY', None)
        elif self.provider == 'anthropic':
            return getattr(settings, 'ANTHROPIC_API_KEY', None)
        return None
    
    def _initialize_client(self):
        """Initialize API client"""
        if not self.api_key:
            logger.warning(f"No API key found for {self.provider}")
            return None
        
        try:
            if self.provider == 'openai':
                import openai
                return openai.OpenAI(api_key=self.api_key)
            elif self.provider == 'anthropic':
                import anthropic
                return anthropic.Anthropic(api_key=self.api_key)
        except ImportError as e:
            logger.error(f"Failed to import {self.provider} library: {e}")
            return None
    
    def generate_chapter_content(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stream: bool = False,
        quality: str = "balanced",
        system_prompt: str = None,
        use_cache: bool = True,
    ) -> Dict[str, any]:
        """
        Generate chapter content using LLM
        
        Now uses LLMAgent as primary backend with automatic routing,
        caching, and fallback. Falls back to direct API if gateway unavailable.
        
        Args:
            prompt: The prompt to send to LLM
            max_tokens: Maximum tokens to generate
            temperature: Creativity level (0-1)
            stream: Whether to stream response
            quality: "fast", "balanced", or "best" (for LLMAgent routing)
            system_prompt: Optional system prompt override
            use_cache: Whether to cache responses (default True)
            
        Returns:
            Dict with 'success', 'content', 'usage', 'error'
        """
        # Try LLMAgent first (provides routing, caching, cost tracking)
        if LLMAGENT_AVAILABLE and not stream:
            result = self._generate_via_agent(
                prompt, max_tokens, temperature, quality, system_prompt, use_cache
            )
            if result['success']:
                return result
            # If agent failed but we have direct API configured, try fallback
            logger.info(f"LLMAgent failed ({result.get('error')}), trying direct API")
        
        # Fallback to direct API calls
        if not self.client:
            return {
                'success': False,
                'error': 'LLM client not initialized. Check API key.',
                'content': None,
                'usage': None
            }
        
        try:
            if self.provider == 'openai':
                return self._generate_openai(prompt, max_tokens, temperature, stream)
            elif self.provider == 'anthropic':
                return self._generate_anthropic(prompt, max_tokens, temperature)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported provider: {self.provider}',
                    'content': None,
                    'usage': None
                }
        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'content': None,
                'usage': None
            }
    
    def _generate_via_agent(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        quality: str,
        system_prompt: str,
        use_cache: bool,
    ) -> Dict[str, any]:
        """Generate using LLMAgent (centralized routing & caching)"""
        try:
            agent = get_llm_agent()
            
            # Check if gateway is available
            if not agent.health_check():
                return {
                    'success': False,
                    'error': 'LLM Gateway not available',
                    'content': None,
                    'usage': None
                }
            
            # Default system prompt for writing tasks
            if not system_prompt:
                system_prompt = (
                    "You are a professional fiction writer specializing in creative storytelling. "
                    "Generate high-quality, engaging content based on the provided context."
                )
            
            # Create preferences for routing
            preferences = ModelPreference(
                quality=quality,
                preferred_provider=self.provider if self.provider else None
            )
            
            # Call LLMAgent
            response = agent.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                preferences=preferences,
                temperature=temperature,
                max_tokens=max_tokens,
                use_cache=use_cache,
            )
            
            if response.success:
                logger.info(
                    f"LLMAgent success: model={response.model_used}, "
                    f"cached={response.cached}, latency={response.latency_ms:.0f}ms"
                )
            
            return {
                'success': response.success,
                'content': response.content,
                'usage': response.usage,
                'error': response.error,
                'model_used': response.model_used,
                'cost_estimate': response.cost_estimate,
                'cached': response.cached,
                'latency_ms': response.latency_ms,
            }
            
        except Exception as e:
            logger.error(f"LLMAgent error: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'LLMAgent error: {str(e)}',
                'content': None,
                'usage': None
            }
    
    def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stream: bool
    ) -> Dict[str, any]:
        """Generate using OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional fiction writer specializing in creative storytelling. Generate high-quality, engaging chapter content based on the provided context and outline."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream
        )
        
        if stream:
            # Handle streaming (for future implementation)
            return {'success': True, 'stream': response}
        else:
            content = response.choices[0].message.content
            usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            return {
                'success': True,
                'content': content,
                'usage': usage,
                'error': None
            }
    
    def _generate_anthropic(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, any]:
        """Generate using Anthropic API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        content = response.content[0].text
        usage = {
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'total_tokens': response.usage.input_tokens + response.usage.output_tokens
        }
        
        return {
            'success': True,
            'content': content,
            'usage': usage,
            'error': None
        }
    
    def estimate_tokens(self, text: str) -> int:
        """
        Rough estimate of tokens in text
        Rule of thumb: ~4 characters per token for English
        """
        return len(text) // 4
    
    def calculate_cost(self, usage: Dict[str, int]) -> float:
        """
        Calculate cost based on usage
        Prices as of 2024 (update as needed)
        """
        costs = {
            'openai': {
                'gpt-4': {'input': 0.03 / 1000, 'output': 0.06 / 1000},
                'gpt-4-turbo': {'input': 0.01 / 1000, 'output': 0.03 / 1000},
                'gpt-3.5-turbo': {'input': 0.0005 / 1000, 'output': 0.0015 / 1000},
            },
            'anthropic': {
                'claude-3-opus-20240229': {'input': 0.015 / 1000, 'output': 0.075 / 1000},
                'claude-3-sonnet-20240229': {'input': 0.003 / 1000, 'output': 0.015 / 1000},
            }
        }
        
        if self.provider not in costs or self.model not in costs[self.provider]:
            return 0.0
        
        model_cost = costs[self.provider][self.model]
        prompt_cost = usage.get('prompt_tokens', usage.get('input_tokens', 0)) * model_cost['input']
        completion_cost = usage.get('completion_tokens', usage.get('output_tokens', 0)) * model_cost['output']
        
        return prompt_cost + completion_cost
