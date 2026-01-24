"""
Client für den LLM MCP HTTP Gateway.

Einfache Nutzung von LLM-Funktionen aus beliebigen Django-Services.

Usage:
    from apps.bfagent.services.llm_gateway_client import LLMGatewayClient
    
    client = LLMGatewayClient()
    
    # Text generieren
    result = client.generate("Erkläre mir Python in 3 Sätzen")
    if result["success"]:
        print(result["content"])
    
    # JSON generieren
    result = client.generate_json(
        prompt="Gib mir 3 Buchideen",
        system_prompt="Du bist ein kreativer Autor. Antworte als JSON-Array."
    )
    if result["success"]:
        ideas = result["content"]  # Bereits als Python list/dict
"""
import logging
import os
from typing import Optional, Any

import httpx

logger = logging.getLogger(__name__)

# Default Gateway URL
DEFAULT_GATEWAY_URL = os.environ.get("LLM_GATEWAY_URL", "http://127.0.0.1:8100")


class LLMGatewayClient:
    """Client für LLM MCP HTTP Gateway."""
    
    def __init__(self, gateway_url: str = None, timeout: float = 120.0):
        """
        Initialisiere den Client.
        
        Args:
            gateway_url: URL des Gateways (default: LLM_GATEWAY_URL env oder localhost:8100)
            timeout: Request timeout in Sekunden
        """
        self.gateway_url = gateway_url or DEFAULT_GATEWAY_URL
        self.timeout = timeout
    
    def generate(
        self,
        prompt: str,
        model: str = None,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: str = "text"
    ) -> dict[str, Any]:
        """
        Generiere Text mit einem LLM.
        
        Args:
            prompt: Der Prompt
            model: LLM Name/ID (optional, nutzt Default)
            system_prompt: System-Prompt (optional)
            temperature: Kreativität (0.0-2.0)
            max_tokens: Max Output Tokens
            response_format: "text" oder "json"
        
        Returns:
            dict mit:
                - success: bool
                - content: str | dict | list (bei json bereits geparst)
                - error: str (bei Fehler)
                - model_used: str
                - usage: dict mit tokens_in/tokens_out
                - cost_estimate: float
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.gateway_url}/generate",
                    json={
                        "prompt": prompt,
                        "model": model,
                        "system_prompt": system_prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "response_format": response_format
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logger.error(f"LLM Gateway nicht erreichbar: {self.gateway_url}")
            return {
                "success": False,
                "error": f"LLM Gateway nicht erreichbar ({self.gateway_url}). Bitte starten mit: python -m llm_mcp.http_gateway",
                "content": None
            }
        except httpx.TimeoutException:
            logger.error("LLM Gateway Timeout")
            return {
                "success": False,
                "error": "LLM Gateway Timeout - Anfrage dauerte zu lange",
                "content": None
            }
        except Exception as e:
            logger.error(f"LLM Gateway Fehler: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
    
    def generate_json(
        self,
        prompt: str,
        model: str = None,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> dict[str, Any]:
        """
        Generiere JSON mit einem LLM.
        
        Convenience-Methode die response_format="json" setzt.
        Bei Erfolg ist content bereits ein Python dict/list.
        
        Args:
            prompt: Der Prompt (sollte JSON-Ausgabe beschreiben)
            model: LLM Name/ID (optional)
            system_prompt: System-Prompt (optional)
            temperature: Kreativität (0.0-2.0)
            max_tokens: Max Output Tokens
        
        Returns:
            dict mit content als dict/list bei Erfolg
        """
        return self.generate(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json"
        )
    
    def list_models(self) -> list[dict]:
        """
        Liste verfügbare LLMs auf.
        
        Returns:
            Liste von Model-Infos oder leere Liste bei Fehler
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.gateway_url}/models")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Models: {e}")
            return []
    
    def health_check(self) -> bool:
        """
        Prüfe ob der Gateway erreichbar ist.
        
        Returns:
            True wenn Gateway läuft, sonst False
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.gateway_url}/health")
                return response.status_code == 200
        except Exception:
            return False


# Singleton für einfache Nutzung
_default_client: LLMGatewayClient = None


def get_llm_client() -> LLMGatewayClient:
    """Hole den Default LLM Gateway Client (Singleton)."""
    global _default_client
    if _default_client is None:
        _default_client = LLMGatewayClient()
    return _default_client
