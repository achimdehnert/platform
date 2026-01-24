"""
Provider-agnostic LLM client with an OpenAI-compatible HTTP implementation.

This module centralizes outbound LLM calls used by views, keeping views slim and
allowing easy swaps of providers/SDKs later (e.g., OpenAI Agents SDK, Anthropic,
local vLLM/Ollama, etc.).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type

import requests

try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = None  # type: ignore
    PYDANTIC_AVAILABLE = False

try:
    from django.conf import settings  # type: ignore
except Exception:  # pragma: no cover
    settings = None  # Fallback if Django settings not available

DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_TIMEOUT_SECONDS = 120  # 2 minutes for long-form generation


if PYDANTIC_AVAILABLE:

    class PromptResponse(BaseModel):  # type: ignore
        """Structured response schema for LLM prompts"""

        content: str
        reasoning: Optional[str] = None
        confidence: Optional[float] = None

else:
    PromptResponse = None  # type: ignore


@dataclass(frozen=True)
class LlmRequest:
    provider: str
    api_endpoint: str
    api_key: str
    model: Optional[str]
    system: str
    prompt: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    response_format: Optional[str] = None  # "text" | "json"
    response_schema: Optional[Type[BaseModel]] = None  # Pydantic schema for structured outputs


def _pretty_json(text: str) -> str:
    try:
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
    except Exception:
        return text


def generate_text(req: LlmRequest) -> Dict[str, Any]:
    """Execute a text generation call and return a unified result dict.

    Returns a dict with keys: { "ok": bool, "text": Optional[str], "raw": Any, "error": Optional[str] }.
    """
    provider = (req.provider or "").lower()
    url = (req.api_endpoint or "").strip()
    # Auto-normalize: if URL provided without scheme, assume https
    if url and not (url.startswith("http://") or url.startswith("https://")):
        url = f"https://{url}"
    headers = {"Content-Type": "application/json"}

    # Basic config validation before making requests (after normalization)
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return {
            "ok": False,
            "text": None,
            "raw": None,
            "error": "LLM config error: API endpoint is missing or has no scheme (use https://...)",
            "latency_ms": None,
        }

    # Resolve API key with env fallback per provider
    resolved_key = (req.api_key or "").strip()
    if not resolved_key:
        if "openai" in provider:
            resolved_key = (
                (getattr(settings, "OPENAI_API_KEY", None) or "") if settings else ""
            ).strip() or os.environ.get("OPENAI_API_KEY", "").strip()
        elif "anthropic" in provider:
            resolved_key = (
                (getattr(settings, "ANTHROPIC_API_KEY", None) or "") if settings else ""
            ).strip() or os.environ.get("ANTHROPIC_API_KEY", "").strip()

    # For well-known providers, require a resolved key
    if ("openai" in provider or "anthropic" in provider) and not resolved_key:
        return {
            "ok": False,
            "text": None,
            "raw": None,
            "error": "LLM config error: Missing API key for provider.",
            "latency_ms": None,
        }

    try:
        started = time.perf_counter()
        # Debug: Log routing decision
        import logging
        _log = logging.getLogger(__name__)
        _log.info(f"LLM routing: provider={provider}, url={url}, openai_in_url={'openai' in (url or '').lower()}")
        
        if "openai" in provider or "openai" in (url or "").lower() or "/openai" in (url or "").lower():
            # OpenAI Chat Completions API over HTTP (keeps deps minimal)
            headers["Authorization"] = f"Bearer {resolved_key}"

            # Ensure proper Chat Completions endpoint
            chat_url = url.rstrip("/")
            if not chat_url.endswith("/chat/completions"):
                # Check if URL already ends with /v1 or contains /v1/
                if chat_url.endswith("/v1") or "/v1/" in chat_url:
                    chat_url = f"{chat_url}/chat/completions"
                else:
                    chat_url = f"{chat_url}/v1/chat/completions"

            payload: Dict[str, Any] = {
                "model": req.model or DEFAULT_OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": req.system or ""},
                    {"role": "user", "content": req.prompt},
                ],
                "temperature": float(req.temperature or 0.7),
                "top_p": float(req.top_p or 1.0),
                "max_tokens": int(req.max_tokens or 512),
            }

            # Handle response format
            if req.response_schema and PYDANTIC_AVAILABLE:
                # OpenAI Structured Outputs with Pydantic schema
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": req.response_schema.__name__,
                        "schema": req.response_schema.model_json_schema(),
                        "strict": True,
                    },
                }
            elif (req.response_format or "").lower() == "json":
                payload["response_format"] = {"type": "json_object"}

            resp = requests.post(
                chat_url, headers=headers, data=json.dumps(payload), timeout=DEFAULT_TIMEOUT_SECONDS
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            
            # Handle empty response
            if not resp.text or not resp.text.strip():
                return {
                    "ok": False,
                    "text": None,
                    "raw": None,
                    "error": f"Empty response from API (Status: {resp.status_code}, URL: {chat_url})",
                    "latency_ms": latency_ms,
                }
            
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                return {
                    "ok": False,
                    "text": None,
                    "raw": resp.text[:500],
                    "error": f"Invalid JSON from API: {e} (Response: {resp.text[:200]})",
                    "latency_ms": latency_ms,
                }
            
            if resp.status_code >= 400:
                error_obj = data.get("error", {})
                if isinstance(error_obj, dict):
                    message = error_obj.get("message", resp.text)
                elif isinstance(error_obj, list):
                    message = str(error_obj[0]) if error_obj else resp.text
                else:
                    message = str(error_obj) if error_obj else resp.text
                return {
                    "ok": False,
                    "text": None,
                    "raw": data,
                    "error": f"OpenAI error: {message}",
                    "latency_ms": latency_ms,
                }

            # Chat Completions style - with defensive parsing
            text = None
            choices = data.get("choices", [])
            if choices and isinstance(choices, list) and len(choices) > 0:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    message = first_choice.get("message", {})
                    if isinstance(message, dict):
                        text = message.get("content")
                    if not text:
                        text = first_choice.get("text")
            if not text:
                text = data.get("output_text")
            if not text:
                # Log the raw response for debugging
                _log.warning(f"Could not extract text from response: {json.dumps(data)[:500]}")
                text = json.dumps(data, indent=2)

            # Validate against Pydantic schema if provided
            if req.response_schema and isinstance(text, str) and PYDANTIC_AVAILABLE:
                try:
                    parsed_obj = req.response_schema.model_validate_json(text)
                    return {
                        "ok": True,
                        "text": text,
                        "structured": parsed_obj.model_dump(),
                        "raw": data,
                        "error": None,
                        "latency_ms": latency_ms,
                    }
                except Exception as validation_error:
                    return {
                        "ok": False,
                        "text": text,
                        "raw": data,
                        "error": f"Schema validation failed: {validation_error}",
                        "latency_ms": latency_ms,
                    }

            if isinstance(text, str) and (req.response_format or "").lower() == "json":
                text = _pretty_json(text)
            return {
                "ok": True,
                "text": text or json.dumps(data, indent=2),
                "raw": data,
                "error": None,
                "latency_ms": latency_ms,
            }

        elif ("gemini" in provider or "google" in provider or "generativelanguage.googleapis.com" in (url or "").lower()) and "/openai" not in (url or "").lower():
            # Google Gemini API
            gemini_key = resolved_key or os.environ.get("GEMINI_API_KEY", "").strip()
            if not gemini_key:
                return {
                    "ok": False,
                    "text": None,
                    "raw": None,
                    "error": "LLM config error: Missing API key for Gemini.",
                    "latency_ms": None,
                }
            
            model_name = req.model or "gemini-1.5-flash"
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{req.system or ''}\n\n{req.prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": float(req.temperature or 0.7),
                    "topP": float(req.top_p or 1.0),
                    "maxOutputTokens": int(req.max_tokens or 512),
                }
            }
            
            resp = requests.post(
                gemini_url, headers={"Content-Type": "application/json"}, 
                data=json.dumps(payload), timeout=DEFAULT_TIMEOUT_SECONDS
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            
            if not resp.text or not resp.text.strip():
                return {
                    "ok": False,
                    "text": None,
                    "raw": None,
                    "error": f"Empty response from Gemini API (Status: {resp.status_code})",
                    "latency_ms": latency_ms,
                }
            
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                return {
                    "ok": False,
                    "text": None,
                    "raw": resp.text[:500],
                    "error": f"Invalid JSON from Gemini: {e} (Response: {resp.text[:200]})",
                    "latency_ms": latency_ms,
                }
            
            if resp.status_code >= 400:
                error_obj = data.get("error", {})
                if isinstance(error_obj, dict):
                    error_msg = error_obj.get("message", resp.text)
                elif isinstance(error_obj, list):
                    error_msg = str(error_obj[0]) if error_obj else resp.text
                else:
                    error_msg = str(error_obj) if error_obj else resp.text
                return {
                    "ok": False,
                    "text": None,
                    "raw": data,
                    "error": f"Gemini error: {error_msg}",
                    "latency_ms": latency_ms,
                }
            
            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                else:
                    text = json.dumps(data, indent=2)
            else:
                text = json.dumps(data, indent=2)
            
            return {"ok": True, "text": text, "raw": data, "error": None, "latency_ms": latency_ms}

        elif "groq" in provider or "groq.com" in (url or "").lower():
            # Groq API (OpenAI-compatible)
            groq_key = resolved_key or os.environ.get("GROQ_API_KEY", "").strip()
            if not groq_key:
                return {
                    "ok": False,
                    "text": None,
                    "raw": None,
                    "error": "LLM config error: Missing API key for Groq.",
                    "latency_ms": None,
                }
            
            groq_url = url or "https://api.groq.com/openai/v1/chat/completions"
            headers["Authorization"] = f"Bearer {groq_key}"
            
            messages = []
            if req.system:
                messages.append({"role": "system", "content": req.system})
            messages.append({"role": "user", "content": req.prompt})
            
            payload = {
                "model": req.model or "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": float(req.temperature or 0.7),
                "max_tokens": int(req.max_tokens or 512),
                "top_p": float(req.top_p or 1.0),
            }
            
            resp = requests.post(
                groq_url, headers=headers, data=json.dumps(payload), timeout=DEFAULT_TIMEOUT_SECONDS
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            
            if not resp.text or not resp.text.strip():
                return {
                    "ok": False,
                    "text": None,
                    "raw": None,
                    "error": f"Empty response from Groq API (Status: {resp.status_code})",
                    "latency_ms": latency_ms,
                }
            
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                return {
                    "ok": False,
                    "text": None,
                    "raw": resp.text[:500],
                    "error": f"Invalid JSON from Groq: {e} (Response: {resp.text[:200]})",
                    "latency_ms": latency_ms,
                }
            
            if resp.status_code >= 400:
                error_obj = data.get("error", {})
                if isinstance(error_obj, dict):
                    error_msg = error_obj.get("message", resp.text)
                else:
                    error_msg = str(error_obj) if error_obj else resp.text
                return {
                    "ok": False,
                    "text": None,
                    "raw": data,
                    "error": f"Groq error: {error_msg}",
                    "latency_ms": latency_ms,
                }
            
            # Extract text from OpenAI-compatible response
            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "")
            else:
                text = json.dumps(data, indent=2)
            
            return {"ok": True, "text": text, "raw": data, "error": None, "latency_ms": latency_ms}

        elif "anthropic" in provider or "anthropic" in (url or "").lower():
            headers["x-api-key"] = resolved_key
            headers["anthropic-version"] = "2023-06-01"
            payload = {
                "model": req.model,
                "max_tokens": int(req.max_tokens or 512),
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{req.system or ''}\n\n{req.prompt}"}
                        ],
                    }
                ],
                "temperature": float(req.temperature or 0.7),
                "top_p": float(req.top_p or 1.0),
            }
            resp = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=DEFAULT_TIMEOUT_SECONDS
            )
            data = resp.json()
            latency_ms = int((time.perf_counter() - started) * 1000)
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "text": None,
                    "raw": data,
                    "error": f"Anthropic error: {data}",
                    "latency_ms": latency_ms,
                }
            content = data.get("content") or []
            if isinstance(content, list) and content:
                piece = content[0]
                text = piece.get("text") if isinstance(piece, dict) else str(piece)
            else:
                text = json.dumps(data, indent=2)
            return {"ok": True, "text": text, "raw": data, "error": None, "latency_ms": latency_ms}

        elif "ollama" in provider or "ollama" in (url or "").lower() or ":11434" in (url or ""):
            # Ollama API (OpenAI-compatible endpoint)
            _log.info(f"Using Ollama provider: {url}")
            
            # Ollama uses OpenAI-compatible /v1/chat/completions or native /api/chat
            chat_url = url.rstrip("/")
            if "/api/chat" in chat_url:
                # Native Ollama API
                payload = {
                    "model": req.model or "llama3.1",
                    "messages": [
                        {"role": "system", "content": req.system or ""},
                        {"role": "user", "content": req.prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": float(req.temperature or 0.7),
                        "num_predict": int(req.max_tokens or 2048),
                    }
                }
            else:
                # OpenAI-compatible endpoint
                if not chat_url.endswith("/chat/completions"):
                    if "/v1" in chat_url:
                        chat_url = f"{chat_url.rstrip('/')}/chat/completions"
                    else:
                        chat_url = f"{chat_url}/v1/chat/completions"
                
                payload = {
                    "model": req.model or "llama3.1",
                    "messages": [
                        {"role": "system", "content": req.system or ""},
                        {"role": "user", "content": req.prompt},
                    ],
                    "temperature": float(req.temperature or 0.7),
                    "max_tokens": int(req.max_tokens or 2048),
                }
            
            # Ollama doesn't require auth for local
            resp = requests.post(
                chat_url, headers=headers, data=json.dumps(payload), timeout=300  # Longer timeout for local
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            
            if resp.status_code >= 400:
                return {
                    "ok": False, "text": None, "raw": resp.text,
                    "error": f"Ollama error ({resp.status_code}): {resp.text[:500]}",
                    "latency_ms": latency_ms,
                }
            
            data = resp.json()
            # Handle both native and OpenAI-compatible responses
            if "message" in data:
                text = data.get("message", {}).get("content", "")
            else:
                text = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
            
            return {"ok": True, "text": text, "raw": data, "error": None, "latency_ms": latency_ms}

        elif "vllm" in provider or "vllm" in (url or "").lower() or ":8000" in (url or ""):
            # vLLM API (OpenAI-compatible)
            _log.info(f"Using vLLM provider: {url}")
            
            chat_url = url.rstrip("/")
            if not chat_url.endswith("/chat/completions"):
                if "/v1" in chat_url:
                    chat_url = f"{chat_url.rstrip('/')}/chat/completions"
                else:
                    chat_url = f"{chat_url}/v1/chat/completions"
            
            payload = {
                "model": req.model,  # vLLM requires exact model name
                "messages": [
                    {"role": "system", "content": req.system or ""},
                    {"role": "user", "content": req.prompt},
                ],
                "temperature": float(req.temperature or 0.7),
                "max_tokens": int(req.max_tokens or 4096),
                "top_p": float(req.top_p or 1.0),
            }
            
            # vLLM may or may not require auth
            if req.api_key:
                headers["Authorization"] = f"Bearer {req.api_key}"
            
            resp = requests.post(
                chat_url, headers=headers, data=json.dumps(payload), timeout=300
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            
            if resp.status_code >= 400:
                return {
                    "ok": False, "text": None, "raw": resp.text,
                    "error": f"vLLM error ({resp.status_code}): {resp.text[:500]}",
                    "latency_ms": latency_ms,
                }
            
            data = resp.json()
            text = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
            
            return {"ok": True, "text": text, "raw": data, "error": None, "latency_ms": latency_ms}

        else:
            # Generic JSON API
            headers["Authorization"] = f"Bearer {req.api_key}"
            payload = {
                "model": req.model,
                "system": req.system or "",
                "prompt": req.prompt,
                "temperature": float(req.temperature or 0.7),
                "max_tokens": int(req.max_tokens or 512),
                "top_p": float(req.top_p or 1.0),
            }
            resp = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=DEFAULT_TIMEOUT_SECONDS
            )
            data = resp.json()
            latency_ms = int((time.perf_counter() - started) * 1000)
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "text": None,
                    "raw": data,
                    "error": f"Generic LLM error: {data}",
                    "latency_ms": latency_ms,
                }
            text = (
                data.get("text")
                or data.get("result")
                or (data.get("choices", [{}])[0].get("message", {}) or {}).get("content")
            )
            if isinstance(text, str) and (req.response_format or "").lower() == "json":
                text = _pretty_json(text)
            return {
                "ok": True,
                "text": text or json.dumps(data, indent=2),
                "raw": data,
                "error": None,
                "latency_ms": latency_ms,
            }

    except Exception as exc:  # Catch connection/JSON errors
        return {
            "ok": False,
            "text": None,
            "raw": None,
            "error": f"LLM request failed: {exc}",
            "latency_ms": None,
        }


def execute_workflow(
    workflow_id: str,
    variables: Dict[str, Any],
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Execute a complete workflow template (handlers + prompts).
    
    Args:
        workflow_id: Workflow template ID (e.g., "chapter_gen")
        variables: Template variables
        context: Runtime context (project, agent, etc.)
        
    Returns:
        Workflow execution results
    """
    try:
        from .workflow_templates import WORKFLOWS
        from .pipeline_orchestrator import PipelineOrchestrator
        
        workflow = WORKFLOWS.get(workflow_id)
        if not workflow:
            return {"ok": False, "error": f"Workflow '{workflow_id}' not found"}
        
        pipeline = PipelineOrchestrator(workflow.to_pipeline_config())
        
        exec_context = context or {}
        exec_context.update(variables)
        
        result = pipeline.execute(exec_context)
        
        return {
            "ok": True,
            "workflow_id": workflow_id,
            "result": result
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute_template(
    template_key: str,
    variables: Dict[str, Any],
    version: str = "latest",
    agent=None,
    llm=None,
    project=None,
    target_model: str = None,
    target_id: int = None,
) -> Dict[str, Any]:
    """
    Execute a prompt template with LLM fallback logic and execution tracking.
    
    Args:
        template_key: Unique template identifier (e.g., "character_generation")
        variables: Dictionary of template variables to render
        version: Template version ("latest", "1.0", "2.0-beta", etc.)
        agent: Optional Agent instance (for default LLM fallback)
        llm: Optional specific Llms instance to use (overrides all defaults)
        project: Optional BookProjects instance (for execution tracking)
        target_model: Optional model name for tracking (e.g., "characters")
        target_id: Optional target model ID for tracking
        
    Returns:
        Dict with keys: {
            "ok": bool,
            "text": str,
            "rendered_prompt": str,
            "template": PromptTemplate,
            "llm_used": Llms,
            "execution": PromptExecution,
            "error": Optional[str]
        }
        
    LLM Fallback Order:
        1. Provided 'llm' parameter
        2. template.preferred_llm (if set)
        3. agent.default_llm (if agent provided)
        4. System default LLM (first active LLM)
    """
    try:
        # Django imports (lazy to avoid circular imports)
        from apps.bfagent.models import PromptTemplate, PromptExecution, Llms
        
        # Get template
        if version == "latest":
            template = PromptTemplate.objects.filter(
                template_key=template_key,
                is_active=True
            ).order_by('-version').first()
        else:
            template = PromptTemplate.objects.filter(
                template_key=template_key,
                version=version
            ).first()
        
        if not template:
            return {
                "ok": False,
                "text": None,
                "rendered_prompt": None,
                "template": None,
                "llm_used": None,
                "execution": None,
                "error": f"Template '{template_key}' version '{version}' not found"
            }
        
        # Render template with variables
        try:
            rendered_prompt = template.render(variables)
        except ValueError as e:
            return {
                "ok": False,
                "text": None,
                "rendered_prompt": None,
                "template": template,
                "llm_used": None,
                "execution": None,
                "error": f"Template rendering failed: {e}"
            }
        
        # Determine which LLM to use (fallback logic)
        selected_llm = llm
        if not selected_llm and template.preferred_llm:
            selected_llm = template.preferred_llm
        if not selected_llm and agent and hasattr(agent, 'default_llm'):
            selected_llm = agent.default_llm
        if not selected_llm:
            # System default: first active LLM
            selected_llm = Llms.objects.filter(is_active=True).first()
        
        if not selected_llm:
            return {
                "ok": False,
                "text": None,
                "rendered_prompt": rendered_prompt,
                "template": template,
                "llm_used": None,
                "execution": None,
                "error": "No LLM available (no preferred_llm, agent default, or system default)"
            }
        
        # Build LLM request
        llm_request = LlmRequest(
            provider=selected_llm.provider,
            api_endpoint=selected_llm.api_endpoint,
            api_key=selected_llm.api_key,
            model=selected_llm.llm_name,
            system=template.system_prompt if hasattr(template, 'system_prompt') else "",
            prompt=rendered_prompt,
            temperature=template.temperature,
            top_p=template.top_p,
            max_tokens=template.max_tokens,
            response_format=template.output_format if hasattr(template, 'output_format') else None,
        )
        
        # Execute LLM call
        result = generate_text(llm_request)
        
        # Track execution
        execution = PromptExecution.objects.create(
            template=template,
            agent=agent,
            project=project,
            target_model=target_model or "",
            target_id=target_id or 0,
            rendered_prompt=rendered_prompt,
            context_used=variables,
            llm_response=result.get("text", ""),
            parsed_output=result.get("structured") if result.get("structured") else None,
            confidence_score=None,  # Can be extracted from response if available
            execution_time=result.get("latency_ms", 0) / 1000.0,  # Convert to seconds
            tokens_used=0,  # Would need to parse from response
            cost=0.0,  # Would calculate based on tokens and LLM pricing
            error_message=result.get("error", ""),
            user_accepted=None,
            user_edited=False,
        )
        
        # Update template usage stats
        template.usage_count += 1
        if result.get("ok"):
            template.success_count += 1
        else:
            template.failure_count += 1
        template.save(update_fields=['usage_count', 'success_count', 'failure_count'])
        
        return {
            "ok": result.get("ok", False),
            "text": result.get("text"),
            "rendered_prompt": rendered_prompt,
            "template": template,
            "llm_used": selected_llm,
            "execution": execution,
            "error": result.get("error"),
            "raw": result.get("raw"),
            "latency_ms": result.get("latency_ms"),
        }
        
    except Exception as exc:
        return {
            "ok": False,
            "text": None,
            "rendered_prompt": None,
            "template": None,
            "llm_used": None,
            "execution": None,
            "error": f"execute_template failed: {exc}"
        }
