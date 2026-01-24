"""
LLM Processing Handler - Calls actual LLM APIs for content generation

This handler integrates with various LLM providers (OpenAI, Anthropic, etc.)
and provides flexible LLM selection, token tracking, and cost calculation.
"""

import time
from typing import Dict, Any
from decimal import Decimal
import structlog

from apps.bfagent.models import Llms
from ..base.processing import BaseProcessingHandler
from ..exceptions import ProcessingHandlerException, LLMException
from ..decorators import with_logging, with_performance_monitoring, retry_on_failure
from ..schemas import LLMProcessorConfig

logger = structlog.get_logger()


class LLMProcessingHandler(BaseProcessingHandler):
    """
    Processing Handler that calls LLM APIs for content generation
    
    Configuration:
        llm_id (int, optional): ID of LLM to use from Llms table
        llm_name (str, optional): Name of LLM (e.g., "gpt-4-turbo")
        fallback_llm_id (int, optional): Fallback LLM if primary fails
        temperature (float): Creativity level (0.0-1.0), default 0.7
        max_tokens (int): Maximum response tokens, default 4000
        top_p (float): Nucleus sampling parameter, default 1.0
        frequency_penalty (float): Repetition penalty, default 0.0
        presence_penalty (float): Topic diversity penalty, default 0.0
        stream (bool): Enable streaming responses, default False
        
    Example Config:
        {
            "llm_id": 1,
            "temperature": 0.8,
            "max_tokens": 8000,
            "fallback_llm_id": 2
        }
    """
    
    handler_type = "processing"
    handler_name = "llm_processor"
    
    def validate_config(self) -> None:
        """Validate LLM selection configuration using Pydantic"""
        try:
            LLMProcessorConfig(**self.config)
        except Exception as e:
            raise ProcessingHandlerException(
                message="Invalid configuration for LLMProcessingHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    def _get_llm(self) -> Llms:
        """
        Get LLM instance from configuration
        
        Returns:
            Llms: The LLM model instance to use
            
        Raises:
            ValueError: If LLM not found or inactive
        """
        llm_id = self.config.get("llm_id")
        llm_name = self.config.get("llm_name")
        
        try:
            if llm_id:
                llm = Llms.objects.get(id=llm_id, is_active=True)
            else:
                llm = Llms.objects.get(llm_name=llm_name, is_active=True)
                
            return llm
            
        except Llms.DoesNotExist:
            # Try fallback if configured
            fallback_id = self.config.get("fallback_llm_id")
            if fallback_id:
                try:
                    return Llms.objects.get(id=fallback_id, is_active=True)
                except Llms.DoesNotExist:
                    pass
            
            raise ValueError(
                f"LLM not found or inactive: "
                f"llm_id={llm_id}, llm_name={llm_name}"
            )
    
    def _call_llm_api(
        self,
        llm: Llms,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call the LLM API based on provider
        
        Args:
            llm: The LLM instance to use
            prompt: The prompt text
            temperature: Creativity level
            max_tokens: Maximum response tokens
            **kwargs: Additional provider-specific parameters
            
        Returns:
            dict: Response with content, tokens, and metadata
        """
        provider = llm.provider.lower()
        
        if provider == "openai":
            return self._call_openai(llm, prompt, temperature, max_tokens, **kwargs)
        elif provider == "anthropic":
            return self._call_anthropic(llm, prompt, temperature, max_tokens, **kwargs)
        elif provider == "google":
            return self._call_google(llm, prompt, temperature, max_tokens, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def _call_openai(
        self,
        llm: Llms,
        prompt: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call OpenAI API
        
        Returns:
            dict: {
                "content": str,
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int,
                "model": str
            }
        """
        try:
            import openai
            
            client = openai.OpenAI(
                api_key=llm.api_key,
                base_url=llm.api_endpoint if llm.api_endpoint else None
            )
            
            response = client.chat.completions.create(
                model=llm.llm_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=kwargs.get("top_p", 1.0),
                frequency_penalty=kwargs.get("frequency_penalty", 0.0),
                presence_penalty=kwargs.get("presence_penalty", 0.0)
            )
            
            return {
                "content": response.choices[0].message.content,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    def _call_anthropic(
        self,
        llm: Llms,
        prompt: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call Anthropic (Claude) API
        
        Returns:
            dict: Response with content and token usage
        """
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=llm.api_key)
            
            response = client.messages.create(
                model=llm.llm_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return {
                "content": response.content[0].text,
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "model": response.model,
                "finish_reason": response.stop_reason
            }
            
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")
    
    def _call_google(
        self,
        llm: Llms,
        prompt: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call Google (Gemini) API
        
        Returns:
            dict: Response with content and token usage
        """
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=llm.api_key)
            model = genai.GenerativeModel(llm.llm_name)
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "top_p": kwargs.get("top_p", 1.0)
                }
            )
            
            return {
                "content": response.text,
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
                "model": llm.llm_name,
                "finish_reason": "stop"
            }
            
        except Exception as e:
            raise RuntimeError(f"Google API error: {str(e)}")
    
    def _calculate_cost(self, llm: Llms, total_tokens: int) -> Decimal:
        """
        Calculate generation cost based on token usage
        
        Args:
            llm: The LLM instance
            total_tokens: Total tokens used
            
        Returns:
            Decimal: Cost in USD
        """
        cost_per_token = llm.cost_per_1k_tokens / 1000
        return Decimal(str(total_tokens * cost_per_token))
    
    @with_logging
    @with_performance_monitoring
    @retry_on_failure(max_attempts=3, delay=1.0)
    def process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data by calling configured LLM
        
        Args:
            data: Input data (must contain prompt or rendered_template)
            context: Execution context
            
        Returns:
            dict: {
                "generated_content": str,
                "llm_used": Llms instance,
                "llm_name": str,
                "llm_id": int,
                "prompt_tokens": int,
                "completion_tokens": int,
                "tokens_used": int,
                "generation_cost": Decimal,
                "execution_time_ms": int,
                "model_version": str
            }
        """
        # Get LLM instance
        llm = self._get_llm()
        
        # Get prompt from data
        prompt = data.get("rendered_template") or data.get("prompt")
        if not prompt:
            raise ValueError("No prompt found in data (expected 'rendered_template' or 'prompt')")
        
        # Extract config parameters
        temperature = self.config.get("temperature", 0.7)
        max_tokens = self.config.get("max_tokens", 4000)
        
        # Call LLM API with timing
        start_time = time.time()
        
        try:
            response = self._call_llm_api(
                llm=llm,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=self.config.get("top_p", 1.0),
                frequency_penalty=self.config.get("frequency_penalty", 0.0),
                presence_penalty=self.config.get("presence_penalty", 0.0)
            )
        except Exception as e:
            # Try fallback if configured
            fallback_id = self.config.get("fallback_llm_id")
            if fallback_id:
                try:
                    llm = Llms.objects.get(id=fallback_id, is_active=True)
                    response = self._call_llm_api(
                        llm=llm,
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                except Exception:
                    raise e
            else:
                raise e
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Calculate cost
        cost = self._calculate_cost(llm, response["total_tokens"])
        
        return {
            "generated_content": response["content"],
            "llm_used": llm,
            "llm_name": llm.llm_name,
            "llm_id": llm.id,
            "prompt_tokens": response["prompt_tokens"],
            "completion_tokens": response["completion_tokens"],
            "tokens_used": response["total_tokens"],
            "generation_cost": cost,
            "execution_time_ms": execution_time_ms,
            "model_version": response["model"],
            "finish_reason": response.get("finish_reason", "unknown")
        }
