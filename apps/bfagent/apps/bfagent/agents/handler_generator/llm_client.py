"""
Structured LLM Client for Handler Generation
Guarantees type-safe outputs using Function Calling and Pydantic
"""

from typing import Type, TypeVar, Optional
from pydantic import BaseModel
import json
from django.conf import settings


T = TypeVar('T', bound=BaseModel)


class StructuredLLMClient:
    """
    LLM client that guarantees structured outputs matching Pydantic models
    
    Supports:
    - Claude (Anthropic) with Function Calling
    - OpenAI with Function Calling
    - Fallback to JSON mode with validation
    """
    
    def __init__(self, provider: str = "anthropic"):
        """
        Initialize LLM client
        
        Args:
            provider: 'anthropic' or 'openai'
        """
        self.provider = provider
        self._init_client()
    
    def _init_client(self):
        """Initialize the appropriate LLM client"""
        if self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                api_key = settings.ANTHROPIC_API_KEY
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not set in Django settings or .env file")
                self.client = Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20241022"
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                api_key = settings.OPENAI_API_KEY
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set in Django settings or .env file")
                self.client = OpenAI(api_key=api_key)
                self.model = "gpt-4-turbo-preview"
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        max_tokens: int = 8000,
        temperature: float = 0.7
    ) -> T:
        """
        Generate structured output guaranteed to match Pydantic model
        
        Args:
            prompt: User prompt
            response_model: Pydantic model class
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Instance of response_model with validated data
            
        Raises:
            ValueError: If LLM doesn't return valid structured output
        """
        if self.provider == "anthropic":
            return self._generate_anthropic(
                prompt, response_model, system_prompt, max_tokens, temperature
            )
        elif self.provider == "openai":
            return self._generate_openai(
                prompt, response_model, system_prompt, max_tokens, temperature
            )
    
    def _generate_anthropic(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> T:
        """Generate using Anthropic Claude with Function Calling"""
        
        # Convert Pydantic model to tool definition
        schema = response_model.model_json_schema()
        
        tool = {
            "name": "generate_response",
            "description": f"Generate {response_model.__name__}",
            "input_schema": schema
        }
        
        # Build messages
        messages = [{"role": "user", "content": prompt}]
        
        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            tools=[tool],
            messages=messages
        )
        
        # Extract tool use
        tool_use = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use = block
                break
        
        if not tool_use:
            raise ValueError("LLM did not return structured output via tool use")
        
        # Validate and return
        try:
            return response_model.model_validate(tool_use.input)
        except Exception as e:
            raise ValueError(f"LLM output failed validation: {e}")
    
    def _generate_openai(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> T:
        """Generate using OpenAI with Function Calling"""
        
        # Convert Pydantic model to function definition
        schema = response_model.model_json_schema()
        
        function = {
            "name": "generate_response",
            "description": f"Generate {response_model.__name__}",
            "parameters": schema
        }
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            functions=[function],
            function_call={"name": "generate_response"},
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Extract function call
        message = response.choices[0].message
        if not message.function_call:
            raise ValueError("LLM did not return function call")
        
        # Parse and validate
        try:
            args = json.loads(message.function_call.arguments)
            return response_model.model_validate(args)
        except Exception as e:
            raise ValueError(f"LLM output failed validation: {e}")
    
    def generate_with_fallback(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        max_retries: int = 3
    ) -> T:
        """
        Generate with automatic retry on validation failure
        
        Args:
            prompt: User prompt
            response_model: Pydantic model
            system_prompt: Optional system prompt
            max_retries: Maximum retry attempts
            
        Returns:
            Validated response
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.generate_structured(
                    prompt=prompt,
                    response_model=response_model,
                    system_prompt=system_prompt
                )
            except Exception as e:
                last_error = e
                
                if attempt < max_retries - 1:
                    # Enhance prompt with error info
                    prompt += f"\n\nPrevious attempt failed with: {str(e)}\nPlease fix and try again."
        
        raise ValueError(f"Failed after {max_retries} attempts. Last error: {last_error}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def generate_structured_response(
    prompt: str,
    response_model: Type[T],
    provider: str = "anthropic",
    system_prompt: Optional[str] = None
) -> T:
    """
    Convenience function for one-off structured generation
    
    Example:
        from pydantic import BaseModel
        
        class UserInfo(BaseModel):
            name: str
            age: int
        
        result = generate_structured_response(
            prompt="Extract user info: John is 30 years old",
            response_model=UserInfo
        )
        print(result.name)  # "John"
        print(result.age)   # 30
    """
    client = StructuredLLMClient(provider=provider)
    return client.generate_structured(
        prompt=prompt,
        response_model=response_model,
        system_prompt=system_prompt
    )
