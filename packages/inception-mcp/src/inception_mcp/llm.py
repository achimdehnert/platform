"""
LLM Integration Module
======================

Claude API integration for intelligent text extraction and generation.
"""

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("inception-mcp.llm")


class LLMClient:
    """Client for LLM API calls."""
    
    def __init__(self):
        self.gateway_url = os.environ.get("LLM_GATEWAY_URL", "http://localhost:8080/v1")
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.model = os.environ.get("LLM_MODEL", "claude-3-sonnet")
        self.timeout = 60.0
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Send chat completion request."""
        url = f"{self.gateway_url}/chat/completions"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM API error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                raise


# Global client instance
_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Get or create LLM client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

SYSTEM_PROMPT_EXTRACTOR = """Du bist ein Assistent für die Extraktion strukturierter Daten aus natürlicher Sprache.
Antworte IMMER mit validem JSON. Keine Erklärungen, nur JSON.
Wenn eine Information nicht vorhanden ist, verwende null oder leere Arrays."""


async def extract_title_from_description(description: str) -> str:
    """Extract a concise title from a problem description."""
    client = get_client()
    
    prompt = f"""Extrahiere einen kurzen, prägnanten Titel (max 80 Zeichen) aus dieser Beschreibung:

"{description}"

Antworte nur mit dem Titel, keine Anführungszeichen, keine Erklärung."""

    try:
        result = await client.chat(
            messages=[
                {"role": "system", "content": "Du extrahierst kurze Titel. Antworte nur mit dem Titel."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=100,
        )
        title = result.strip().strip('"').strip("'")
        return title[:80] if len(title) > 80 else title
    except Exception as e:
        logger.warning(f"Title extraction failed: {e}, using fallback")
        # Fallback: first sentence, max 80 chars
        title = description.split(".")[0].strip()
        return title[:77] + "..." if len(title) > 80 else title


async def extract_list_from_text(text: str, field_name: str) -> list[str]:
    """Extract a list of items from free text."""
    client = get_client()
    
    prompt = f"""Extrahiere eine Liste von "{field_name}" aus diesem Text:

"{text}"

Antworte mit einem JSON-Array von Strings. Beispiel: ["Item 1", "Item 2"]
Wenn nichts gefunden, antworte mit []"""

    try:
        result = await client.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_EXTRACTOR},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        # Parse JSON
        items = json.loads(result.strip())
        if isinstance(items, list):
            return [str(item) for item in items]
        return []
    except Exception as e:
        logger.warning(f"List extraction failed: {e}, using fallback")
        # Fallback: split by newlines or commas
        lines = [l.strip() for l in text.replace(",", "\n").split("\n") if l.strip()]
        return lines


async def extract_risks_from_text(text: str) -> list[dict[str, str]]:
    """Extract structured risks from free text."""
    client = get_client()
    
    prompt = f"""Extrahiere Risiken aus diesem Text:

"{text}"

Antworte mit einem JSON-Array von Objekten:
[{{"description": "Risikobeschreibung", "probability": "low|medium|high", "impact": "low|medium|high"}}]

Wenn nichts gefunden, antworte mit []"""

    try:
        result = await client.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_EXTRACTOR},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        risks = json.loads(result.strip())
        if isinstance(risks, list):
            return risks
        return []
    except Exception as e:
        logger.warning(f"Risk extraction failed: {e}, using fallback")
        # Fallback: create simple risks from lines
        risks = []
        for line in text.split("\n"):
            if line.strip():
                risks.append({
                    "description": line.strip(),
                    "probability": "medium",
                    "impact": "medium",
                })
        return risks


async def extract_boolean_with_reason(text: str, question: str) -> tuple[bool, str]:
    """Extract yes/no answer with optional reason."""
    client = get_client()
    
    prompt = f"""Frage: {question}

Antwort des Benutzers: "{text}"

Extrahiere:
1. Ist die Antwort JA oder NEIN?
2. Was ist die Begründung (falls angegeben)?

Antworte mit JSON: {{"answer": true/false, "reason": "Begründung oder leer"}}"""

    try:
        result = await client.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_EXTRACTOR},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        data = json.loads(result.strip())
        return bool(data.get("answer", False)), str(data.get("reason", ""))
    except Exception as e:
        logger.warning(f"Boolean extraction failed: {e}, using fallback")
        # Fallback: simple keyword check
        lower = text.lower()
        is_yes = any(kw in lower for kw in ["ja", "yes", "true", "richtig", "korrekt", "benötigt", "erforderlich"])
        return is_yes, text if is_yes else ""


async def derive_use_cases_from_bc(
    title: str,
    problem_statement: str,
    scope: str,
    target_audience: str,
) -> list[dict[str, Any]]:
    """Derive Use Cases from Business Case content."""
    client = get_client()
    
    prompt = f"""Basierend auf diesem Business Case, schlage 1-3 Use Cases vor:

Titel: {title}
Problem: {problem_statement}
Scope: {scope}
Zielgruppe: {target_audience}

Antworte mit JSON-Array:
[{{
  "title": "UC Titel",
  "actor": "Hauptakteur",
  "main_flow": ["Schritt 1", "Schritt 2", "..."],
  "preconditions": ["Vorbedingung 1"],
  "postconditions": ["Nachbedingung 1"]
}}]"""

    try:
        result = await client.chat(
            messages=[
                {"role": "system", "content": "Du bist ein Business Analyst. Erstelle strukturierte Use Cases."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        use_cases = json.loads(result.strip())
        if isinstance(use_cases, list):
            return use_cases[:3]  # Max 3
        return []
    except Exception as e:
        logger.warning(f"UC derivation failed: {e}, using fallback")
        # Fallback: create one generic UC
        return [{
            "title": f"Hauptanwendungsfall für {title}",
            "actor": target_audience.split(",")[0].strip() if target_audience else "Benutzer",
            "main_flow": ["Benutzer öffnet die Anwendung", "Details aus Scope ableiten"],
            "preconditions": ["Benutzer ist angemeldet"],
            "postconditions": ["Aktion wurde durchgeführt"],
        }]


async def generate_clarifying_question(
    current_bc_state: dict[str, Any],
    field: str,
    question_template: str,
) -> str:
    """Generate a contextual clarifying question."""
    client = get_client()
    
    prompt = f"""Basierend auf diesem Business Case Draft:
Titel: {current_bc_state.get('title', 'N/A')}
Problem: {current_bc_state.get('problem_statement', 'N/A')[:200]}

Formuliere eine kontextbezogene Frage für das Feld "{field}".
Standard-Frage: {question_template}

Passe die Frage an den Kontext an, aber behalte die Kernfrage bei.
Antworte nur mit der Frage."""

    try:
        result = await client.chat(
            messages=[
                {"role": "system", "content": "Du formulierst klare, kontextbezogene Fragen."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return result.strip()
    except Exception as e:
        logger.warning(f"Question generation failed: {e}, using template")
        return question_template
