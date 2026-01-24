"""
Style Quality Handler
=====================

LLM-basierte Stilanalyse gegen Style DNA.
Unterstützt OpenAI und Ollama (NSFW-fähig).
"""
import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StyleQualityHandler:
    """
    Handler für LLM-basierte Style-Qualitätsanalyse.
    
    Analysiert Kapiteltext gegen Style DNA Profile und
    gibt strukturierte Scores + Issues zurück.
    """
    
    ANALYSIS_PROMPT = '''Du bist ein erfahrener Lektor und Stilanalyst.

Analysiere folgenden Text gegen das AUTHOR STYLE DNA Profil.

=== STYLE DNA ===
Name: {dna_name}

SIGNATURE MOVES (muss der Text enthalten):
{signature_moves}

DO (erwünschte Stilmittel):
{do_list}

DON'T (zu vermeidende Stilmittel):
{dont_list}

TABU-WÖRTER (niemals verwenden):
{taboo_list}

=== TEXT ZU ANALYSIEREN ===
{chapter_text}

=== DEINE AUFGABE ===

Bewerte den Text auf einer Skala von 1-10 für jede Dimension:

1. **style_adherence**: Wie gut folgt der Text den DO/DON'T Regeln?
2. **signature_moves**: Werden die Signature Moves effektiv eingesetzt?
3. **taboo_compliance**: Werden Tabu-Wörter konsequent vermieden? (10 = keine Tabu-Wörter)
4. **pacing**: Ist das Tempo/Rhythmus angemessen?
5. **dialogue_quality**: Qualität und Natürlichkeit der Dialoge?

Finde konkrete Stil-Probleme im Text.

ANTWORTE NUR mit diesem JSON Format:
```json
{{
  "style_adherence": 8.5,
  "signature_moves": 7.0,
  "taboo_compliance": 10.0,
  "pacing": 7.5,
  "dialogue_quality": 8.0,
  "issues": [
    {{
      "issue_type_code": "taboo_word|passive_voice|repetition|dont_violation|missing_signature",
      "text_excerpt": "...der betroffene Textausschnitt...",
      "suggestion": "Vorgeschlagene Verbesserung",
      "explanation": "Warum es ein Problem ist"
    }}
  ],
  "findings": {{
    "strengths": ["Stärke 1", "Stärke 2"],
    "weaknesses": ["Schwäche 1"],
    "overall_impression": "Kurze Gesamteinschätzung"
  }}
}}
```

WICHTIG: Antworte NUR mit dem JSON, keine Erklärungen davor oder danach!'''

    # Ollama NSFW-fähige Modelle
    NSFW_MODELS = [
        'dolphin-llama3:8b',
        'nous-hermes2:latest', 
        'dolphin-mixtral:latest',
    ]
    
    def __init__(self, llm_id: Optional[int] = None, use_ollama: bool = False):
        """
        Args:
            llm_id: Spezifische LLM ID (optional)
            use_ollama: Ollama für NSFW-Inhalte verwenden
        """
        self.llm_id = llm_id
        self.use_ollama = use_ollama
        self._llm = None
    
    def analyze_style(
        self,
        chapter_text: str,
        style_dna: dict,
        max_text_length: int = 15000
    ) -> dict[str, Any]:
        """
        Analysiert Kapiteltext gegen Style DNA.
        
        Args:
            chapter_text: Der zu analysierende Text
            style_dna: Dict mit name, signature_moves, do_list, dont_list, taboo_list
            max_text_length: Max Textlänge für LLM
            
        Returns:
            Dict mit scores, issues, findings, success, error
        """
        if not chapter_text or not chapter_text.strip():
            return {'success': False, 'error': 'Kein Text zum Analysieren'}
        
        # Text kürzen wenn nötig
        if len(chapter_text) > max_text_length:
            chapter_text = chapter_text[:max_text_length] + "\n\n[...Text gekürzt...]"
        
        # Prompt bauen
        prompt = self._build_prompt(chapter_text, style_dna)
        
        # LLM aufrufen
        if self.use_ollama:
            response = self._call_ollama(prompt)
        else:
            response = self._call_llm(prompt)
        
        if not response.get('ok'):
            return {
                'success': False,
                'error': response.get('error', 'LLM-Aufruf fehlgeschlagen'),
                'llm_used': response.get('llm_used', ''),
            }
        
        # JSON parsen
        result = self._parse_response(response.get('text', ''))
        result['llm_used'] = response.get('llm_used', '')
        result['tokens_used'] = response.get('tokens_used', 0)
        
        return result
    
    def _build_prompt(self, chapter_text: str, style_dna: dict) -> str:
        """Baut den Analyse-Prompt"""
        
        def format_list(items: list) -> str:
            if not items:
                return "- (keine definiert)"
            return "\n".join(f"- {item}" for item in items[:10])
        
        return self.ANALYSIS_PROMPT.format(
            dna_name=style_dna.get('name', 'Unbekannt'),
            signature_moves=format_list(style_dna.get('signature_moves', [])),
            do_list=format_list(style_dna.get('do_list', [])),
            dont_list=format_list(style_dna.get('dont_list', [])),
            taboo_list=", ".join(style_dna.get('taboo_list', [])[:20]) or "(keine)",
            chapter_text=chapter_text,
        )
    
    def _call_llm(self, prompt: str) -> dict:
        """Ruft Standard-LLM auf (OpenAI etc.)"""
        try:
            from apps.bfagent.models import Llms
            from apps.bfagent.services.llm_client import LlmRequest, generate_text
            
            # LLM holen
            if self.llm_id:
                llm = Llms.objects.filter(id=self.llm_id, is_active=True).first()
            else:
                llm = Llms.objects.filter(is_active=True, provider='openai').first()
            
            if not llm:
                llm = Llms.objects.filter(is_active=True).first()
            
            if not llm:
                return {'ok': False, 'error': 'Kein aktives LLM verfügbar'}
            
            req = LlmRequest(
                provider=llm.provider or 'openai',
                api_endpoint=llm.api_endpoint or 'https://api.openai.com',
                api_key=llm.api_key or '',
                model=llm.llm_name or 'gpt-4o-mini',
                system="Du bist ein Stilanalyst. Antworte nur mit JSON.",
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            
            response = generate_text(req)
            
            if response and response.get('ok'):
                return {
                    'ok': True,
                    'text': response.get('text', ''),
                    'llm_used': llm.name,
                    'tokens_used': response.get('tokens_used', 0),
                }
            else:
                return {
                    'ok': False,
                    'error': response.get('error', 'LLM Fehler') if response else 'Keine Antwort',
                    'llm_used': llm.name,
                }
                
        except Exception as e:
            logger.error(f"LLM call error: {e}")
            return {'ok': False, 'error': str(e)}
    
    def _call_ollama(self, prompt: str) -> dict:
        """Ruft Ollama für NSFW-Inhalte auf"""
        import requests
        
        ollama_base = "http://localhost:11434"
        
        for model in self.NSFW_MODELS:
            try:
                response = requests.post(
                    f"{ollama_base}/api/generate",
                    json={
                        "model": model,
                        "prompt": f"Du bist ein Stilanalyst. Antworte nur mit JSON.\n\n{prompt}",
                        "stream": False,
                        "options": {
                            "num_predict": 2000,
                            "temperature": 0.3,
                        }
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        'ok': True,
                        'text': result.get('response', ''),
                        'llm_used': f"Ollama/{model}",
                        'tokens_used': result.get('eval_count', 0),
                    }
                    
            except Exception as e:
                logger.warning(f"Ollama {model} failed: {e}")
                continue
        
        return {'ok': False, 'error': 'Alle Ollama-Modelle fehlgeschlagen'}
    
    def _parse_response(self, text: str) -> dict:
        """Parst LLM-Antwort zu strukturiertem Dict"""
        
        # JSON aus Response extrahieren
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Versuche direkt zu parsen
            json_str = text.strip()
            # Bereinige potentielle Markdown-Reste
            if json_str.startswith('```'):
                json_str = json_str.split('```')[1] if '```' in json_str[3:] else json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
        
        try:
            data = json.loads(json_str)
            
            # Validierung und Defaults
            result = {
                'success': True,
                'style_adherence': float(data.get('style_adherence', 7.0)),
                'signature_moves': float(data.get('signature_moves', 7.0)),
                'taboo_compliance': float(data.get('taboo_compliance', 10.0)),
                'pacing': float(data.get('pacing', 7.0)),
                'dialogue_quality': float(data.get('dialogue_quality', 7.0)),
                'issues': data.get('issues', []),
                'findings': data.get('findings', {}),
            }
            
            # Scores auf 0-10 begrenzen
            for key in ['style_adherence', 'signature_moves', 'taboo_compliance', 'pacing', 'dialogue_quality']:
                result[key] = max(0.0, min(10.0, result[key]))
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nText: {json_str[:500]}")
            
            # Fallback: Versuche Scores aus Text zu extrahieren
            return self._extract_scores_fallback(text)
    
    def _extract_scores_fallback(self, text: str) -> dict:
        """Fallback-Extraktion wenn JSON-Parsing fehlschlägt"""
        
        result = {
            'success': True,
            'style_adherence': 7.0,
            'signature_moves': 7.0,
            'taboo_compliance': 10.0,
            'pacing': 7.0,
            'dialogue_quality': 7.0,
            'issues': [],
            'findings': {'note': 'Scores aus Fallback-Extraktion'},
        }
        
        # Versuche Zahlen nach Schlüsselwörtern zu finden
        patterns = {
            'style_adherence': r'style[_\s]?adherence["\s:]+(\d+(?:\.\d+)?)',
            'signature_moves': r'signature[_\s]?moves["\s:]+(\d+(?:\.\d+)?)',
            'taboo_compliance': r'taboo[_\s]?compliance["\s:]+(\d+(?:\.\d+)?)',
            'pacing': r'pacing["\s:]+(\d+(?:\.\d+)?)',
            'dialogue_quality': r'dialogue[_\s]?quality["\s:]+(\d+(?:\.\d+)?)',
        }
        
        text_lower = text.lower()
        for key, pattern in patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                try:
                    result[key] = max(0.0, min(10.0, float(match.group(1))))
                except ValueError:
                    pass
        
        return result


# Singleton für einfachen Import
style_quality_handler = StyleQualityHandler()
