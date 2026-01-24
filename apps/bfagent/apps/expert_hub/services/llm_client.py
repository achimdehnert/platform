"""
LLM Client für Expert Hub.

Nutzt den LLM MCP HTTP Gateway für echte KI-Generierung.
"""

import logging
import httpx
from typing import Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)

# LLM Gateway Konfiguration
LLM_GATEWAY_URL = getattr(settings, 'LLM_GATEWAY_URL', 'http://127.0.0.1:8100')
LLM_GATEWAY_TIMEOUT = getattr(settings, 'LLM_GATEWAY_TIMEOUT', 120.0)
DEFAULT_LLM_MODEL = getattr(settings, 'DEFAULT_LLM_MODEL', 'gpt-4o-mini')


async def generate_async(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    response_format: str = "text"
) -> Tuple[bool, str, Optional[dict]]:
    """
    Async LLM-Generierung über HTTP Gateway.
    
    Args:
        prompt: User-Prompt
        system_prompt: Optional System-Prompt
        model: LLM Name oder ID (default: gpt-4o-mini)
        temperature: Kreativität (0.0-2.0)
        max_tokens: Max Output Tokens
        response_format: 'text', 'json' oder 'markdown'
        
    Returns:
        Tuple[success, content, usage_info]
    """
    try:
        async with httpx.AsyncClient(timeout=LLM_GATEWAY_TIMEOUT) as client:
            response = await client.post(
                f"{LLM_GATEWAY_URL}/generate",
                json={
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "model": model or DEFAULT_LLM_MODEL,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": response_format
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                logger.info(f"LLM generation successful: {data.get('model_used')}")
                return True, data.get("content", ""), data.get("usage")
            else:
                error = data.get("error", "Unknown error")
                logger.warning(f"LLM generation failed: {error}")
                return False, error, None
                
    except httpx.ConnectError:
        logger.error(f"LLM Gateway not reachable at {LLM_GATEWAY_URL}")
        return False, "LLM Gateway nicht erreichbar. Bitte starten Sie den Gateway-Service.", None
    except httpx.TimeoutException:
        logger.error("LLM Gateway timeout")
        return False, "LLM Anfrage Timeout. Bitte versuchen Sie es erneut.", None
    except Exception as e:
        logger.exception(f"LLM generation error: {e}")
        return False, str(e), None


def generate_sync(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    response_format: str = "text"
) -> Tuple[bool, str, Optional[dict]]:
    """
    Sync LLM-Generierung über HTTP Gateway.
    
    Verwendet synchrones httpx für Django Views.
    """
    logger.info(f"=== LLM Client generate_sync aufgerufen ===")
    logger.info(f"Gateway URL: {LLM_GATEWAY_URL}")
    logger.info(f"Model: {model or DEFAULT_LLM_MODEL}")
    logger.info(f"Prompt-Länge: {len(prompt)}")
    
    try:
        with httpx.Client(timeout=LLM_GATEWAY_TIMEOUT) as client:
            response = client.post(
                f"{LLM_GATEWAY_URL}/generate",
                json={
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "model": model or DEFAULT_LLM_MODEL,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": response_format
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                logger.info(f"LLM generation successful: {data.get('model_used')}")
                return True, data.get("content", ""), data.get("usage")
            else:
                error = data.get("error", "Unknown error")
                logger.warning(f"LLM generation failed: {error}")
                return False, error, None
                
    except httpx.ConnectError:
        logger.error(f"LLM Gateway not reachable at {LLM_GATEWAY_URL}")
        return False, "LLM Gateway nicht erreichbar. Bitte starten Sie den Gateway-Service.", None
    except httpx.TimeoutException:
        logger.error("LLM Gateway timeout")
        return False, "LLM Anfrage Timeout. Bitte versuchen Sie es erneut.", None
    except Exception as e:
        logger.exception(f"LLM generation error: {e}")
        return False, str(e), None


def check_gateway_health() -> bool:
    """Prüfe ob LLM Gateway erreichbar ist."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{LLM_GATEWAY_URL}/health")
            return response.status_code == 200
    except Exception:
        return False


def list_available_models() -> list:
    """Liste verfügbare LLM-Modelle."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{LLM_GATEWAY_URL}/models")
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
    except Exception as e:
        logger.error(f"Error listing models: {e}")
    return []
