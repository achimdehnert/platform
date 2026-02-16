"""Base handler class for all creative services."""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field

from creative_services.core.llm_client import LLMClient, LLMConfig, LLMResponse
from creative_services.core.context import BaseContext


TContext = TypeVar("TContext", bound=BaseContext)
TResult = TypeVar("TResult", bound=BaseModel)


class HandlerResult(BaseModel, Generic[TResult]):
    """Standardized handler result."""
    
    success: bool
    data: Optional[TResult] = None
    error: Optional[str] = None
    llm_used: Optional[str] = None
    usage: dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def ok(cls, data: TResult, llm_used: str = None, usage: dict = None):
        return cls(success=True, data=data, llm_used=llm_used, usage=usage or {})
    
    @classmethod
    def fail(cls, error: str):
        return cls(success=False, error=error)


class BaseHandler(ABC, Generic[TContext, TResult]):
    """
    Base class for all creative service handlers.
    
    Handlers follow the BF Agent pattern:
    - Take a context with all required inputs
    - Use LLM to generate creative content
    - Return structured results
    """
    
    # Override in subclass
    SERVICE_NAME: str = "base"
    DEFAULT_SYSTEM_PROMPT: str = "You are a creative writing assistant."
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        self._llm_client = llm_client
        self._llm_config = llm_config
    
    @property
    def llm_client(self) -> LLMClient:
        """Get or create LLM client."""
        if self._llm_client is None:
            self._llm_client = LLMClient(self._llm_config)
        return self._llm_client
    
    @abstractmethod
    def build_prompt(self, context: TContext) -> str:
        """Build the prompt for the LLM. Override in subclass."""
        pass
    
    @abstractmethod
    def parse_response(self, response: LLMResponse, context: TContext) -> TResult:
        """Parse LLM response into structured result. Override in subclass."""
        pass
    
    def get_system_prompt(self, context: TContext) -> str:
        """Get system prompt. Override for custom behavior."""
        return self.DEFAULT_SYSTEM_PROMPT
    
    async def execute(self, context: TContext) -> HandlerResult[TResult]:
        """
        Execute the handler with the given context.
        
        This is the main entry point for using a handler.
        """
        try:
            prompt = self.build_prompt(context)
            system_prompt = self.get_system_prompt(context)
            
            async with LLMClient(self._llm_config) as client:
                response = await client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                )
            
            result = self.parse_response(response, context)
            
            return HandlerResult.ok(
                data=result,
                llm_used=f"{response.provider.value}:{response.model}",
                usage=response.usage,
            )
            
        except Exception as e:
            return HandlerResult.fail(error=str(e))
    
    def execute_sync(self, context: TContext) -> HandlerResult[TResult]:
        """Synchronous wrapper for execute()."""
        import asyncio
        return asyncio.run(self.execute(context))
    
    # Utility methods for parsing
    
    @staticmethod
    def extract_json(text: str) -> dict[str, Any]:
        """Extract JSON from LLM response text."""
        # Try to find JSON in code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to find raw JSON
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        raise ValueError("No JSON found in response")
    
    @staticmethod
    def extract_text_sections(text: str) -> dict[str, str]:
        """Extract sections from markdown-formatted text."""
        sections = {}
        current_section = "content"
        current_content = []
        
        for line in text.split("\n"):
            if line.startswith("## "):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip().lower().replace(" ", "_")
                current_content = []
            elif line.startswith("# "):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[2:].strip().lower().replace(" ", "_")
                current_content = []
            else:
                current_content.append(line)
        
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()
        
        return sections
