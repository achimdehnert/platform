"""
LLMCallProcessingHandler - Feature #45
Centralized LLM call handler for all AI-powered operations

Architecture:
    Reusable LLM integration → Error Handling → Retry Logic → Response Parsing

Features:
    - OpenAI-compatible API calls (Ollama, OpenAI, etc.)
    - Automatic agent/LLM selection
    - Error handling and retries
    - Token counting and logging
    - Fallback mechanisms
    - Response validation

Usage:
    handler = LLMCallHandler()
    response = handler.call_llm(
        agent_id=1,
        system_prompt="You are a writing assistant",
        user_prompt="Generate a story outline",
        max_tokens=1000
    )
"""

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from apps.bfagent.handlers.base import BaseProcessingHandler, ProcessingError
from apps.bfagent.models import Agents, Llms

logger = logging.getLogger(__name__)


class LLMCallHandler(BaseProcessingHandler):
    """
    Centralized handler for LLM API calls

    Provides a consistent interface for calling LLMs across all handlers.
    Handles agent selection, LLM routing, error recovery, and response parsing.
    """

    def __init__(self):
        super().__init__(name="llm_call_handler", version="1.0.0")
        self.default_timeout = 60
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute LLM call

        Args:
            context: Dictionary containing:
                - agent_id: int (optional) - Specific agent to use
                - llm_id: int (optional) - Specific LLM to use
                - system_prompt: str (required) - System message
                - user_prompt: str (required) - User message
                - max_tokens: int (optional, default=800)
                - temperature: float (optional) - Override LLM temperature
                - retry: bool (optional, default=True) - Enable retries

        Returns:
            Dictionary with:
                - success: bool
                - response: str - LLM response text
                - tokens_used: int (estimated)
                - llm_used: str - LLM name
                - execution_time_ms: float

        Raises:
            ProcessingError: If LLM call fails after retries
        """
        system_prompt = context.get('system_prompt')
        user_prompt = context.get('user_prompt')

        if not system_prompt or not user_prompt:
            raise ProcessingError("Both system_prompt and user_prompt are required")

        agent_id = context.get('agent_id')
        llm_id = context.get('llm_id')
        max_tokens = context.get('max_tokens', 800)
        temperature = context.get('temperature')
        enable_retry = context.get('retry', True)

        # Get agent and LLM
        agent = self._get_agent(agent_id)
        llm = self._get_llm(llm_id, agent)

        if not llm:
            raise ProcessingError("No LLM available for processing")

        # Call LLM with retry logic
        start_time = time.time()

        if enable_retry:
            response = self._call_llm_with_retry(
                llm,
                system_prompt,
                user_prompt,
                max_tokens,
                temperature
            )
        else:
            response = self._call_llm_once(
                llm,
                system_prompt,
                user_prompt,
                max_tokens,
                temperature
            )

        execution_time = (time.time() - start_time) * 1000  # ms

        # Estimate tokens (rough approximation)
        tokens_used = self._estimate_tokens(system_prompt, user_prompt, response)

        result = {
            'success': True,
            'response': response,
            'tokens_used': tokens_used,
            'llm_used': llm.llm_name,
            'execution_time_ms': execution_time,
        }

        logger.info(
            f"LLM call successful: {llm.llm_name}, "
            f"{tokens_used} tokens, {execution_time:.0f}ms"
        )

        return result

    # ========================================================================
    # AGENT & LLM SELECTION
    # ========================================================================

    def _get_agent(self, agent_id: Optional[int]) -> Optional[Agents]:
        """Get agent by ID or default active agent"""
        if agent_id:
            try:
                return Agents.objects.get(pk=agent_id, status='active')
            except Agents.DoesNotExist:
                logger.warning(f"Agent {agent_id} not found or inactive")

        # Fallback to first active agent
        return Agents.objects.filter(status='active').first()

    def _get_llm(self, llm_id: Optional[int], agent: Optional[Agents]) -> Optional[Llms]:
        """Get LLM by ID, agent config, or default active LLM"""
        # Priority 1: Explicit LLM ID
        if llm_id:
            try:
                return Llms.objects.get(pk=llm_id, is_active=True)
            except Llms.DoesNotExist:
                logger.warning(f"LLM {llm_id} not found or inactive")

        # Priority 2: Agent's configured LLM
        if agent and agent.llm_model_id:
            try:
                return Llms.objects.get(pk=agent.llm_model_id, is_active=True)
            except Llms.DoesNotExist:
                logger.warning(f"Agent's LLM {agent.llm_model_id} not available")

        # Priority 3: Any active LLM
        return Llms.objects.filter(is_active=True).order_by("id").first()

    # ========================================================================
    # LLM API CALLS
    # ========================================================================

    def _call_llm_with_retry(
        self,
        llm: Llms,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: Optional[float] = None
    ) -> str:
        """Call LLM with retry logic"""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._call_llm_once(
                    llm,
                    system_prompt,
                    user_prompt,
                    max_tokens,
                    temperature
                )
            except ProcessingError as e:
                last_error = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"LLM call attempt {attempt} failed: {e}. "
                        f"Retrying in {self.retry_delay}s..."
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"LLM call failed after {self.max_retries} attempts: {e}"
                    )

        raise ProcessingError(f"LLM call failed after {self.max_retries} attempts: {last_error}")

    def _call_llm_once(
        self,
        llm: Llms,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: Optional[float] = None
    ) -> str:
        """
        Single LLM API call

        Args:
            llm: LLM instance
            system_prompt: System message
            user_prompt: User message
            max_tokens: Maximum tokens in response
            temperature: Temperature override (None = use LLM default)

        Returns:
            LLM response text

        Raises:
            ProcessingError: If API call fails
        """
        if not llm or not llm.is_active:
            raise ProcessingError("LLM is not active")

        # Build API URL
        url = self._build_api_url(llm)

        # Build payload
        payload = {
            "model": llm.llm_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature if temperature is not None else float(llm.temperature or 0.7),
            "max_tokens": max_tokens,
        }

        # Make request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {llm.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.default_timeout) as resp:
                body = resp.read().decode("utf-8")
                return self._parse_response(body)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            logger.error(f"LLM HTTPError {e.code}: {error_body}")
            raise ProcessingError(f"LLM API error: HTTP {e.code}")

        except urllib.error.URLError as e:
            logger.error(f"LLM URLError: {str(e)}")
            raise ProcessingError(f"LLM connection error: {e}")

        except TimeoutError:
            logger.error(f"LLM request timed out after {self.default_timeout}s")
            raise ProcessingError(f"LLM request timed out after {self.default_timeout}s")

        except Exception as e:
            logger.exception(f"Unexpected LLM error: {e}")
            raise ProcessingError(f"Unexpected LLM error: {e}")

    def _build_api_url(self, llm: Llms) -> str:
        """Build API URL from LLM configuration"""
        url = llm.api_endpoint.rstrip("/")
        
        logger.info(f"LLM selected: {llm.name} | original endpoint: {llm.api_endpoint} | model: {llm.llm_name}")

        # Handle different API formats
        if not url.endswith("/chat/completions"):
            if "/v1/" in url:
                url = f"{url}/chat/completions"
            else:
                url = f"{url}/v1/chat/completions"

        logger.info(f"Final API URL: {url}")
        return url

    def _parse_response(self, response_body: str) -> str:
        """
        Parse LLM API response

        Args:
            response_body: Raw JSON response from API

        Returns:
            Extracted content text

        Raises:
            ProcessingError: If response is invalid
        """
        try:
            obj = json.loads(response_body)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ProcessingError("Invalid JSON response from LLM")

        # Extract content from OpenAI-compatible format
        choices = obj.get("choices") or []
        if not choices:
            logger.warning("LLM returned no choices")
            raise ProcessingError("LLM returned empty response")

        message = choices[0].get("message") or {}
        content = message.get("content") or ""

        if not content:
            logger.warning("LLM returned empty content")
            raise ProcessingError("LLM returned empty content")

        logger.debug(f"LLM response: {len(content)} characters")
        return content

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _estimate_tokens(self, system_prompt: str, user_prompt: str, response: str) -> int:
        """
        Rough token estimation

        Uses simple word-based approximation:
        - English: ~0.75 tokens per word
        - Fallback: character count / 4
        """
        total_text = f"{system_prompt} {user_prompt} {response}"
        word_count = len(total_text.split())

        # Rough estimate: 0.75 tokens per word
        estimated_tokens = int(word_count * 0.75)

        return estimated_tokens

    # ========================================================================
    # PUBLIC CONVENIENCE METHODS
    # ========================================================================

    def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        agent_id: Optional[int] = None,
        llm_id: Optional[int] = None,
        max_tokens: int = 800,
        temperature: Optional[float] = None,
        retry: bool = True
    ) -> str:
        """
        Convenience method for direct LLM calls

        Args:
            system_prompt: System message
            user_prompt: User message
            agent_id: Optional agent ID
            llm_id: Optional LLM ID
            max_tokens: Maximum tokens
            temperature: Temperature override
            retry: Enable retry logic

        Returns:
            LLM response text

        Raises:
            ProcessingError: If call fails
        """
        result = self.execute({
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'agent_id': agent_id,
            'llm_id': llm_id,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'retry': retry,
        })

        return result['response']
