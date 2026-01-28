"""
PromptFramework Facade
======================

High-level, easy-to-use API for the entire Prompt Framework.

Provides a singleton instance with lazy initialization and
configuration from environment/settings.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from bfagent_llm.engine import SecureTemplateEngine, RenderedPrompt
from bfagent_llm.service import (
    ResilientPromptService,
    ExecutionResult,
    TierConfig,
)
from bfagent_llm.adapters import (
    GatewayLLMAdapter,
    OpenAILLMAdapter,
    FallbackLLMAdapter,
)

logger = logging.getLogger(__name__)


class PromptFramework:
    """
    High-level facade for the Prompt Framework.
    
    Provides easy access to template rendering and LLM execution
    with sensible defaults and automatic configuration.
    
    Usage:
        # Get singleton instance
        framework = PromptFramework.get_instance()
        
        # Execute a prompt
        result = await framework.execute(
            system_prompt="You are a helpful assistant.",
            user_prompt="Explain {{ topic }} in simple terms.",
            context={"topic": "quantum computing"},
            tier="standard",
        )
        print(result.response.content)
    """
    
    _instance: Optional[PromptFramework] = None
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        gateway_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        tiers: Optional[Dict[str, TierConfig]] = None,
    ):
        """
        Initialize PromptFramework.
        
        Args:
            llm_client: Custom LLM client (optional)
            gateway_url: LLM Gateway URL (default: from env)
            openai_api_key: OpenAI API key (default: from env)
            anthropic_api_key: Anthropic API key (default: from env)
            tiers: Custom tier configurations (optional)
        """
        self._engine: Optional[SecureTemplateEngine] = None
        self._service: Optional[ResilientPromptService] = None
        
        # Configuration
        self.gateway_url = gateway_url or os.getenv(
            "LLM_GATEWAY_URL", "http://localhost:8100"
        )
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.tiers = tiers
        self._custom_client = llm_client
    
    @classmethod
    def get_instance(cls) -> PromptFramework:
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance. Useful for testing."""
        cls._instance = None
    
    @property
    def engine(self) -> SecureTemplateEngine:
        """Get or create template engine."""
        if self._engine is None:
            self._engine = SecureTemplateEngine()
        return self._engine
    
    @property
    def service(self) -> ResilientPromptService:
        """Get or create prompt service."""
        if self._service is None:
            client = self._custom_client or self._create_default_client()
            self._service = ResilientPromptService(
                llm_client=client,
                tiers=self.tiers,
            )
        return self._service
    
    def _create_default_client(self) -> Any:
        """Create default LLM client with fallback chain."""
        adapters = []
        
        # Try gateway first
        try:
            gateway = GatewayLLMAdapter(base_url=self.gateway_url)
            adapters.append(gateway)
            logger.info(f"Gateway adapter configured: {self.gateway_url}")
        except Exception as e:
            logger.warning(f"Failed to create gateway adapter: {e}")
        
        # Add OpenAI as fallback
        if self.openai_api_key:
            try:
                openai = OpenAILLMAdapter(api_key=self.openai_api_key)
                adapters.append(openai)
                logger.info("OpenAI adapter configured as fallback")
            except Exception as e:
                logger.warning(f"Failed to create OpenAI adapter: {e}")
        
        if not adapters:
            raise RuntimeError(
                "No LLM adapters available. Set LLM_GATEWAY_URL or OPENAI_API_KEY."
            )
        
        if len(adapters) == 1:
            return adapters[0]
        
        return FallbackLLMAdapter(adapters)
    
    def render(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
        output_format: str = "",
        default_values: Optional[Dict[str, Any]] = None,
    ) -> RenderedPrompt:
        """
        Render prompts with context.
        
        Args:
            system_prompt: System prompt template
            user_prompt: User prompt template
            context: Variables for rendering
            output_format: Optional output format instructions
            default_values: Default values for missing context keys
            
        Returns:
            RenderedPrompt with all rendered parts
        """
        return self.engine.render(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=context,
            output_format=output_format,
            default_values=default_values,
        )
    
    def render_string(
        self,
        template: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Render a single template string.
        
        Args:
            template: Template string
            context: Variables for rendering
            
        Returns:
            Rendered string
        """
        return self.engine.render_string(template, context)
    
    async def execute(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        tier: str = "standard",
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Render and execute prompt.
        
        Args:
            system_prompt: System prompt template
            user_prompt: User prompt template
            context: Variables for rendering (optional)
            tier: LLM tier (default: standard)
            model: Override model (optional)
            max_tokens: Override max tokens (optional)
            temperature: Override temperature (optional)
            
        Returns:
            ExecutionResult with response or error
        """
        # Render templates if context provided
        if context:
            rendered_system = self.engine.render_string(system_prompt, context)
            rendered_user = self.engine.render_string(user_prompt, context)
        else:
            rendered_system = system_prompt
            rendered_user = user_prompt
        
        # Execute via service
        return await self.service.execute(
            system_prompt=rendered_system,
            user_prompt=rendered_user,
            tier=tier,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
    def execute_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        tier: str = "standard",
        **kwargs,
    ) -> ExecutionResult:
        """
        Synchronous version of execute.
        
        For use in non-async contexts.
        """
        import asyncio
        return asyncio.run(
            self.execute(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context=context,
                tier=tier,
                **kwargs,
            )
        )
    
    def validate_template(self, template: str) -> Dict[str, Any]:
        """
        Validate a template for security and syntax.
        
        Args:
            template: Template string to validate
            
        Returns:
            Dict with valid, errors, and warnings
        """
        result = self.engine.validate_template(template)
        return {
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers."""
        return self.service.get_circuit_status()
    
    def reset_circuit(self, tier_code: str) -> None:
        """Reset circuit breaker for a tier."""
        self.service.reset_circuit(tier_code)
