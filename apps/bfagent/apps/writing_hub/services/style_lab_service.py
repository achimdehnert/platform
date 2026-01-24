"""
StyleLabService - LLM-gestützte Stil-Analyse und Szenen-Generierung.

Unterstützt lokale LLMs (Ollama, vLLM) und Cloud-Provider (OpenAI, Anthropic, etc.).
Fallback zu Mock-Daten wenn kein LLM verfügbar.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class StyleAnalysisResult:
    """Ergebnis einer Stil-Analyse."""
    observations: Dict[str, Any]
    patterns: List[str]
    metrics: Dict[str, float]
    raw_response: Optional[str] = None
    llm_used: Optional[str] = None
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class SceneGenerationResult:
    """Ergebnis einer Szenen-Generierung."""
    text: str
    scene_type: str
    used_features: List[str]
    raw_response: Optional[str] = None
    llm_used: Optional[str] = None
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None


class StyleLabService:
    """
    Service für Style Lab Operationen mit LLM-Integration.
    
    Features:
    - Stil-Extraktion aus Autor-Texten
    - Szenen-Generierung im extrahierten Stil
    - Konfigurierbares LLM (lokal/cloud)
    - Graceful Fallback zu Mock-Daten
    """
    
    # System-Prompts
    STYLE_ANALYSIS_SYSTEM = """Du bist ein erfahrener Literatur-Analyst und Lektor.
Deine Aufgabe ist es, den einzigartigen Schreibstil eines Autors zu analysieren und zu dokumentieren.
Konzentriere dich auf:
- Satzstruktur und Rhythmus
- Wortwahl und Vokabular
- Narrative Perspektive
- Dialogführung
- Beschreibungstechniken
- Emotionale Tiefe
- Metaphern und Bildsprache

Antworte IMMER im JSON-Format."""

    SCENE_GENERATION_SYSTEM = """Du bist ein kreativer Schriftsteller.
Deine Aufgabe ist es, eine Szene im vorgegebenen Stil zu schreiben.
Halte dich strikt an die Stil-Vorgaben (DO/DON'T).
Schreibe authentisch und lebendig.
Die Szene sollte 150-300 Wörter haben."""

    STYLE_ANALYSIS_PROMPT = """Analysiere den folgenden Text und extrahiere den Schreibstil des Autors.

TEXT:
{text}

Gib deine Analyse als JSON zurück mit diesem Schema:
{{
    "observations": {{
        "sentence_structure": "Beschreibung der Satzstruktur",
        "vocabulary": "Beschreibung der Wortwahl",
        "narrative_voice": "Beschreibung der Erzählstimme",
        "dialogue_style": "Beschreibung der Dialogführung",
        "description_technique": "Beschreibung der Beschreibungstechnik",
        "emotional_depth": "Beschreibung der emotionalen Tiefe",
        "imagery": "Beschreibung der Bildsprache"
    }},
    "patterns": [
        "pattern_name_1",
        "pattern_name_2"
    ],
    "metrics": {{
        "avg_sentence_length": 15.5,
        "dialogue_ratio": 0.3,
        "adjective_density": 0.08
    }}
}}"""

    # =========================================================================
    # STYLE EXTRACTION PROMPT - Extrahiert DO/DON'T/Signature/Taboo aus Text
    # =========================================================================
    STYLE_EXTRACTION_SYSTEM = """Du bist ein erfahrener Literatur-Analyst und Stilexperte.
Deine Aufgabe ist es, aus Beispieltexten konkrete Stilregeln zu extrahieren.
Sei PRÄZISE und KONKRET - keine vagen Beschreibungen!
Formuliere Regeln so, dass ein KI-Modell sie direkt umsetzen kann.
Antworte IMMER im JSON-Format."""

    STYLE_EXTRACTION_PROMPT = """Analysiere den folgenden Beispieltext und extrahiere KONKRETE Stilregeln.

=== BEISPIELTEXT ===
{example_text}
=== ENDE ===

Extrahiere folgende Listen als JSON:

1. **DO-LISTE** (Was der Autor MACHT - nachahmenswert):
   - Konkrete Stilmittel, die verwendet werden
   - Satzstrukturen, Rhythmus, Wortwahl
   - Erzähltechniken, Perspektive

2. **DON'T-LISTE** (Was der Autor VERMEIDET):
   - Was im Text NICHT vorkommt
   - Stilmittel, die bewusst gemieden werden

3. **SIGNATURE MOVES** (Einzigartige Merkmale):
   - Das Besondere, das den Stil unverwechselbar macht
   - Wiederkehrende Muster, die typisch sind

4. **TABOO-LISTE** (Absolut verboten):
   - Wörter/Phrasen, die NIE verwendet werden sollten
   - Klischees, die der Autor meidet

Antworte als JSON:
{{
    "do_list": [
        "Kurze, prägnante Sätze für Spannung",
        "Sinnliche Details (Gerüche, Texturen)",
        "Dialoge ohne 'sagte er/sie'",
        "..."
    ],
    "dont_list": [
        "Keine Adverbien bei Dialogen",
        "Keine Erklärungen von Emotionen",
        "..."
    ],
    "signature_moves": [
        "Abgehackte Sätze bei Action",
        "Innerer Monolog in Kursiv",
        "..."
    ],
    "taboo_list": [
        "plötzlich",
        "irgendwie",
        "ein Lächeln umspielte",
        "..."
    ],
    "style_summary": "Kurze Zusammenfassung des Gesamtstils in 2-3 Sätzen"
}}"""

    # =========================================================================
    # STYLE REFINEMENT PROMPT - Verfeinert bestehende Regeln mit neuem Text
    # =========================================================================
    STYLE_REFINEMENT_PROMPT = """Analysiere den neuen Beispieltext und VERFEINERE die bestehenden Stilregeln.

=== NEUER BEISPIELTEXT ===
{new_text}
=== ENDE ===

=== BESTEHENDE REGELN ===
DO-Liste: {existing_do}
DON'T-Liste: {existing_dont}
Signature Moves: {existing_signature}
Taboo-Liste: {existing_taboo}
=== ENDE ===

Aufgaben:
1. Bestätige Regeln, die auch im neuen Text zutreffen
2. Füge NEUE Regeln hinzu, die du entdeckst
3. Entferne Regeln, die im neuen Text WIDERLEGT werden
4. Schärfe vage Regeln zu konkreteren

Antworte als JSON mit den AKTUALISIERTEN Listen:
{{
    "do_list": ["..."],
    "dont_list": ["..."],
    "signature_moves": ["..."],
    "taboo_list": ["..."],
    "changes_made": [
        "Hinzugefügt: ...",
        "Entfernt: ...",
        "Geschärft: ..."
    ]
}}"""

    SCENE_GENERATION_PROMPT = """Schreibe eine {scene_type}-Szene basierend auf dem folgenden Stil-Profil.

STIL-PROFIL:
{style_profile}

DO (Stilmerkmale verwenden):
{do_patterns}

DON'T (Vermeiden):
{dont_patterns}

SZENEN-TYP: {scene_type_description}

{theme_context}

WICHTIG: Halte dich STRIKT an die DO/DON'T Regeln und den Szenen-Typ!
Schreibe eine lebendige, packende Szene.

Schreibe jetzt die Szene (150-300 Wörter):"""

    SCENE_TYPE_DESCRIPTIONS = {
        'arrival': 'Eine Ankunftsszene - Der Protagonist kommt an einem neuen Ort an. Beschreibe erste Eindrücke, Atmosphäre, Details.',
        'dialogue': 'Eine Dialogszene - Ein Gespräch zwischen zwei Charakteren. Zeige Persönlichkeit durch Sprache.',
        'introspection': 'Eine Introspektions-Szene - Innerer Monolog, Gedanken, Reflexion des Protagonisten.',
        'reflection': 'Eine Reflexions-Szene - Innerer Monolog, Gedanken, Nachdenken über Geschehenes.',
        'action': 'Eine Aktions-Szene - Dynamische Handlung, Spannung, Bewegung.',
        'tension': 'Eine Spannungsszene - Aufbau von Spannung, Konflikt, emotionale Intensität.',
        'description': 'Eine Beschreibungs-Szene - Detaillierte Beschreibung einer Person, eines Ortes oder Objekts.',
        'transition': 'Eine Übergangs-Szene - Zeitsprung oder Ortswechsel, verbindendes Element.',
    }

    def __init__(self, llm=None, ollama_model: str = None):
        """
        Initialisiert den Service.
        
        Args:
            llm: Optional - spezifisches LLM-Objekt aus der DB.
            ollama_model: Optional - Name eines lokalen Ollama-Modells (z.B. 'llama3:8b').
                 Wenn None, wird das System-Default verwendet.
        """
        self.llm = llm
        self.ollama_model = ollama_model  # Direkter Ollama-Modellname
        self._llm_client = None
    
    def _get_llm(self):
        """
        Holt das zu verwendende LLM mit intelligenter Fallback-Kette.
        
        Fallback-Reihenfolge:
        1. Explizit gesetztes LLM (self.llm)
        2. Ollama lokal (kostenlos, schnell, NSFW-fähig)
        3. Groq (schnell, günstig)
        4. OpenAI GPT-4o-mini (günstig)
        5. Anthropic Claude
        6. Beliebiges aktives LLM
        
        Returns:
            Llms-Objekt oder None (sollte nie None sein wenn LLMs konfiguriert)
        """
        if self.llm:
            logger.info(f"Verwende explizit gesetztes LLM: {self.llm.llm_name} ({self.llm.provider})")
            return self.llm
        
        try:
            from apps.bfagent.models import Llms
            
            # Fallback-Kette mit Prioritäten
            fallback_providers = [
                ('ollama', None),           # Lokal, NSFW-fähig
                ('groq', None),             # Schnell, günstig
                ('openai', 'gpt-4o-mini'),  # Günstig
                ('openai', None),           # Beliebiges OpenAI
                ('anthropic', None),        # Claude
            ]
            
            for provider, model_hint in fallback_providers:
                query = Llms.objects.filter(is_active=True, provider__icontains=provider)
                if model_hint:
                    query = query.filter(llm_name__icontains=model_hint)
                llm = query.first()
                if llm:
                    logger.info(f"LLM Fallback: Verwende {llm.llm_name} ({llm.provider})")
                    return llm
            
            # Letzter Fallback: Beliebiges aktives LLM
            any_llm = Llms.objects.filter(is_active=True).first()
            if any_llm:
                logger.info(f"LLM Fallback (beliebig): Verwende {any_llm.llm_name}")
                return any_llm
            
            logger.warning("Kein aktives LLM in der Datenbank gefunden!")
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim LLM-Laden: {e}")
            return None
    
    def _call_llm(self, system: str, prompt: str, max_tokens: int = 1024) -> Dict[str, Any]:
        """
        Führt einen LLM-Call aus.
        
        Returns:
            Dict mit keys: ok, text, error, llm_used, tokens_used
        """
        # Priorität 1: Direkt angegebenes Ollama-Modell
        if self.ollama_model:
            return self._call_ollama_direct(system, prompt, max_tokens)
        
        llm = self._get_llm()
        
        if not llm:
            logger.info("Kein LLM verfügbar, verwende Mock-Daten")
            return {
                'ok': False,
                'text': None,
                'error': 'Kein LLM konfiguriert',
                'llm_used': None,
                'tokens_used': 0,
            }
        
        try:
            from apps.bfagent.services.llm_client import LlmRequest, generate_text
            
            request = LlmRequest(
                provider=llm.provider,
                api_endpoint=llm.api_endpoint,
                api_key=llm.api_key or '',
                model=llm.llm_name,
                system=system,
                prompt=prompt,
                temperature=0.7,
                max_tokens=max_tokens,
            )
            
            result = generate_text(request)
            
            return {
                'ok': result.get('ok', False),
                'text': result.get('text'),
                'error': result.get('error'),
                'llm_used': llm.llm_name,
                'tokens_used': 0,  # TODO: Parse from response
                'latency_ms': result.get('latency_ms'),
            }
        except Exception as e:
            logger.error(f"LLM-Call fehlgeschlagen: {e}")
            return {
                'ok': False,
                'text': None,
                'error': str(e),
                'llm_used': llm.llm_name if llm else None,
                'tokens_used': 0,
            }
    
    def _call_ollama_direct(self, system: str, prompt: str, max_tokens: int = 1024) -> Dict[str, Any]:
        """
        DEPRECATED: Leitet jetzt zu _call_configured_llm weiter.
        
        REGEL: Alle LLM-Aufrufe verwenden NUR die konfigurierten LLMs aus der DB.
        Lokale Ollama-Modelle müssen unter /control-center/ai-config/llms/ angelegt werden!
        """
        logger.info(f"Session wollte Ollama-Modell '{self.ollama_model}' - verwende stattdessen DB-konfigurierte LLMs")
        return self._call_configured_llm(system, prompt, max_tokens, preferred_model=self.ollama_model)
    
    def _call_configured_llm(self, system: str, prompt: str, max_tokens: int = 1024, preferred_model: str = None) -> Dict[str, Any]:
        """
        Verwendet NUR die in der Datenbank konfigurierten und aktiven LLMs.
        
        ALLE LLMs (auch lokale NSFW-Modelle) müssen unter:
        /control-center/ai-config/llms/ angelegt werden!
        
        Args:
            system: System-Prompt
            prompt: User-Prompt  
            max_tokens: Maximale Tokens
            preferred_model: Bevorzugtes Modell (wird zuerst versucht falls aktiv)
        """
        from apps.bfagent.models import Llms
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        # Hole alle aktiven LLMs
        active_llms = list(Llms.objects.filter(is_active=True).order_by('id'))
        
        if not active_llms:
            logger.error("Keine aktiven LLMs konfiguriert!")
            return {
                'ok': False,
                'text': None,
                'error': 'Keine aktiven LLMs verfügbar. Bitte unter /control-center/ai-config/llms/ konfigurieren.',
                'llm_used': None,
                'tokens_used': 0,
            }
        
        # Falls bevorzugtes Modell angegeben, sortiere es nach vorne
        if preferred_model:
            preferred = [l for l in active_llms if preferred_model.lower() in l.llm_name.lower()]
            others = [l for l in active_llms if l not in preferred]
            active_llms = preferred + others
        
        # Versuche jedes aktive LLM der Reihe nach
        for llm in active_llms:
            try:
                logger.info(f"LLM-Call: {llm.llm_name} ({llm.provider})")
                
                request = LlmRequest(
                    provider=llm.provider,
                    api_endpoint=llm.api_endpoint,
                    api_key=llm.api_key or '',
                    model=llm.llm_name,
                    system=system,
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                
                result = generate_text(request)
                
                if result.get('ok') and result.get('text'):
                    clean_text = self._clean_llm_response(result['text'])
                    return {
                        'ok': True,
                        'text': clean_text,
                        'error': None,
                        'llm_used': llm.llm_name,
                        'tokens_used': result.get('tokens_used', 0),
                    }
                else:
                    logger.warning(f"LLM {llm.llm_name} fehlgeschlagen: {result.get('error')}")
                    
            except Exception as e:
                logger.warning(f"LLM {llm.llm_name} Exception: {e}")
                continue
        
        logger.error("Alle konfigurierten LLMs fehlgeschlagen!")
        return {
            'ok': False,
            'text': None,
            'error': 'Alle LLMs fehlgeschlagen. Bitte LLM-Konfiguration prüfen.',
            'llm_used': None,
            'tokens_used': 0,
        }
    
    def _clean_llm_response(self, text: str) -> str:
        """
        Bereinigt LLM-Antworten von Prompt-Echos und Artefakten.
        
        Einige Modelle (besonders lokale) geben Teile des Prompts zurück.
        Diese Methode entfernt bekannte Prompt-Fragmente.
        """
        if not text:
            return text
        
        # Bekannte Prompt-Fragmente, die entfernt werden sollen
        prompt_fragments = [
            "Imitiere den Schreibstil",
            "Schreibe jetzt die Szene",
            "WICHTIG: Imitiere",
            "=== ORIGINAL-BEISPIELTEXT",
            "=== ENDE BEISPIELTEXT ===",
            "STIL-PROFIL (extrahiert",
            "DO (Stilmerkmale",
            "DON'T (Vermeiden)",
            "SZENEN-TYP:",
            "(150-300 Wörter):",
        ]
        
        # Finde den Startpunkt nach allen Prompt-Fragmenten
        clean_start = 0
        for fragment in prompt_fragments:
            idx = text.find(fragment)
            if idx != -1:
                # Finde das Ende dieser Zeile
                end_of_line = text.find('\n', idx)
                if end_of_line != -1 and end_of_line > clean_start:
                    clean_start = end_of_line + 1
        
        # Wenn wir Prompt-Fragmente gefunden haben, schneide sie ab
        if clean_start > 0 and clean_start < len(text):
            text = text[clean_start:].strip()
        
        # Entferne auch führende Marker wie "---" oder "***"
        while text and text[0] in '-*=\n ':
            text = text[1:]
        
        return text.strip()
    
    def analyze_style(self, text: str) -> StyleAnalysisResult:
        """
        Analysiert den Schreibstil eines Textes.
        
        Args:
            text: Der zu analysierende Text
            
        Returns:
            StyleAnalysisResult mit Beobachtungen, Patterns und Metriken
        """
        prompt = self.STYLE_ANALYSIS_PROMPT.format(text=text[:3000])  # Limit text length
        
        result = self._call_llm(
            system=self.STYLE_ANALYSIS_SYSTEM,
            prompt=prompt,
            max_tokens=1024
        )
        
        if result['ok'] and result['text']:
            try:
                # Parse JSON response
                json_match = re.search(r'\{[\s\S]*\}', result['text'])
                if json_match:
                    data = json.loads(json_match.group())
                    return StyleAnalysisResult(
                        observations=data.get('observations', {}),
                        patterns=data.get('patterns', []),
                        metrics=data.get('metrics', {}),
                        raw_response=result['text'],
                        llm_used=result['llm_used'],
                        tokens_used=result['tokens_used'],
                        success=True,
                    )
            except json.JSONDecodeError as e:
                logger.warning(f"JSON-Parse fehlgeschlagen: {e}")
        
        # Fallback zu Mock-Analyse
        return self._mock_style_analysis(text)
    
    def extract_style_rules(self, example_text: str) -> Dict[str, Any]:
        """
        Extrahiert konkrete Stilregeln aus einem Beispieltext.
        
        Returns:
            Dict mit do_list, dont_list, signature_moves, taboo_list, style_summary
        """
        prompt = self.STYLE_EXTRACTION_PROMPT.format(example_text=example_text[:4000])
        
        result = self._call_llm(
            system=self.STYLE_EXTRACTION_SYSTEM,
            prompt=prompt,
            max_tokens=2048
        )
        
        if result['ok'] and result['text']:
            try:
                # JSON aus Antwort extrahieren
                text = result['text']
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    data = json.loads(json_match.group())
                    return {
                        'ok': True,
                        'do_list': data.get('do_list', []),
                        'dont_list': data.get('dont_list', []),
                        'signature_moves': data.get('signature_moves', []),
                        'taboo_list': data.get('taboo_list', []),
                        'style_summary': data.get('style_summary', ''),
                        'llm_used': result['llm_used'],
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"JSON-Parse bei Style-Extraktion fehlgeschlagen: {e}")
        
        return {
            'ok': False,
            'error': result.get('error', 'Extraktion fehlgeschlagen'),
            'do_list': [],
            'dont_list': [],
            'signature_moves': [],
            'taboo_list': [],
            'llm_used': result.get('llm_used'),
        }
    
    def refine_style_rules(
        self, 
        new_text: str, 
        existing_do: List[str],
        existing_dont: List[str],
        existing_signature: List[str],
        existing_taboo: List[str],
    ) -> Dict[str, Any]:
        """
        Verfeinert bestehende Stilregeln mit einem neuen Beispieltext.
        
        Returns:
            Dict mit aktualisierten Listen und changes_made
        """
        prompt = self.STYLE_REFINEMENT_PROMPT.format(
            new_text=new_text[:4000],
            existing_do=json.dumps(existing_do, ensure_ascii=False),
            existing_dont=json.dumps(existing_dont, ensure_ascii=False),
            existing_signature=json.dumps(existing_signature, ensure_ascii=False),
            existing_taboo=json.dumps(existing_taboo, ensure_ascii=False),
        )
        
        result = self._call_llm(
            system=self.STYLE_EXTRACTION_SYSTEM,
            prompt=prompt,
            max_tokens=2048
        )
        
        if result['ok'] and result['text']:
            try:
                text = result['text']
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    data = json.loads(json_match.group())
                    return {
                        'ok': True,
                        'do_list': data.get('do_list', existing_do),
                        'dont_list': data.get('dont_list', existing_dont),
                        'signature_moves': data.get('signature_moves', existing_signature),
                        'taboo_list': data.get('taboo_list', existing_taboo),
                        'changes_made': data.get('changes_made', []),
                        'llm_used': result['llm_used'],
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"JSON-Parse bei Style-Refinement fehlgeschlagen: {e}")
        
        # Bei Fehler: Original-Listen zurückgeben
        return {
            'ok': False,
            'error': result.get('error', 'Refinement fehlgeschlagen'),
            'do_list': existing_do,
            'dont_list': existing_dont,
            'signature_moves': existing_signature,
            'taboo_list': existing_taboo,
            'changes_made': [],
            'llm_used': result.get('llm_used'),
        }
    
    def generate_scene(
        self,
        scene_type: str,
        style_profile: Dict[str, Any],
        do_patterns: List[str],
        dont_patterns: List[str],
        original_text: str = None,
    ) -> SceneGenerationResult:
        """
        Generiert eine Szene im vorgegebenen Stil.
        
        Args:
            scene_type: Typ der Szene (arrival, dialogue, etc.)
            style_profile: Extrahiertes Stil-Profil
            do_patterns: Liste von DO-Patterns
            dont_patterns: Liste von DON'T-Patterns
            original_text: Der Original-Beispieltext zum Imitieren
            
        Returns:
            SceneGenerationResult mit generiertem Text
        """
        scene_desc = self.SCENE_TYPE_DESCRIPTIONS.get(
            scene_type, 
            f'Eine {scene_type}-Szene'
        )
        
        # Theme context als inhaltliche Vorgabe
        theme_context = ""
        if original_text and original_text.strip():
            theme_context = f"""THEMA/INHALT der Szene:
{original_text}

Schreibe die Szene GENAU zu diesem Thema/Inhalt!"""
        
        prompt = self.SCENE_GENERATION_PROMPT.format(
            scene_type=scene_type,
            scene_type_description=scene_desc,
            theme_context=theme_context,
            style_profile=json.dumps(style_profile, indent=2, ensure_ascii=False),
            do_patterns='\n'.join(f'- {p}' for p in do_patterns) or '(keine spezifischen Vorgaben)',
            dont_patterns='\n'.join(f'- {p}' for p in dont_patterns) or '(keine spezifischen Vorgaben)',
        )
        
        # DEBUG: Log the prompt
        logger.info(f"=== SCENE GENERATION PROMPT ===")
        logger.info(f"Theme Context: {theme_context[:200] if theme_context else 'NONE'}...")
        logger.info(f"DO patterns count: {len(do_patterns)}")
        logger.info(f"DON'T patterns count: {len(dont_patterns)}")
        logger.info(f"Full prompt length: {len(prompt)} chars")
        
        result = self._call_llm(
            system=self.SCENE_GENERATION_SYSTEM,
            prompt=prompt,
            max_tokens=1024
        )
        
        logger.info(f"LLM Result: ok={result['ok']}, llm_used={result.get('llm_used')}")
        
        if result['ok'] and result['text']:
            return SceneGenerationResult(
                text=result['text'],
                scene_type=scene_type,
                used_features=do_patterns[:5],  # Top features used
                raw_response=result['text'],
                llm_used=result['llm_used'],
                tokens_used=result['tokens_used'],
                success=True,
            )
        
        # Fallback zu Mock-Generierung
        return self._mock_scene_generation(scene_type, style_profile)
    
    def generate_scene_from_dna(
        self,
        dna,
        style_profile: Dict[str, Any],
        original_excerpts: List[str] = None,
    ) -> SceneGenerationResult:
        """
        Generiert eine Szene basierend auf Style DNA und Original-Texten.
        
        Args:
            dna: AuthorStyleDNA Objekt
            style_profile: Extrahiertes Stil-Profil mit Kontext
            original_excerpts: Ausschnitte aus Original-Texten für thematischen Kontext
            
        Returns:
            SceneGenerationResult mit generiertem Text
        """
        # Thematischen Kontext aus Original-Texten aufbauen
        theme_context = ""
        if original_excerpts:
            theme_context = f"""
THEMATISCHER KONTEXT (aus Original-Texten des Autors):
{chr(10).join(f'--- Auszug {i+1} ---{chr(10)}{excerpt[:400]}...' for i, excerpt in enumerate(original_excerpts[:2]))}

Schreibe eine NEUE Szene, die thematisch und stilistisch zu diesen Texten passt.
"""
        
        # Prompt für thematische Generierung
        prompt = f"""Schreibe eine kurze Szene (ca. 200-300 Wörter) im Stil des Autors.

STYLE DNA "{dna.name}":

Signature Moves:
{chr(10).join(f'- {m}' for m in (dna.signature_moves or [])[:5]) or '(keine)'}

DO (diese Stilmittel verwenden):
{chr(10).join(f'- {d}' for d in (dna.do_list or [])[:8]) or '(keine spezifischen Vorgaben)'}

DON'T (diese Stilmittel vermeiden):
{chr(10).join(f'- {d}' for d in (dna.dont_list or [])[:5]) or '(keine spezifischen Vorgaben)'}

{theme_context}

WICHTIG:
- Schreibe NUR die Szene, keine Erklärungen
- Halte dich strikt an die DO/DON'T Regeln
- Die Szene soll den Stil des Autors widerspiegeln
- Sei kreativ mit dem Inhalt, aber treu zum Stil
"""
        
        system = """Du bist ein erfahrener Autor, der Texte im Stil anderer Autoren schreiben kann.
Du analysierst die Style DNA und Original-Texte sorgfältig und erzeugst Texte, die stilistisch und thematisch passen.
Schreibe NUR die Szene selbst - keine Einleitungen, Erklärungen oder Kommentare."""
        
        result = self._call_llm(
            system=system,
            prompt=prompt,
            max_tokens=1024
        )
        
        if result['ok'] and result['text']:
            return SceneGenerationResult(
                text=result['text'],
                scene_type='dna_sample',
                used_features=(dna.signature_moves or [])[:5],
                raw_response=result['text'],
                llm_used=result['llm_used'],
                tokens_used=result['tokens_used'],
                success=True,
            )
        
        # Fallback
        return SceneGenerationResult(
            text="Beispieltext konnte nicht generiert werden. Bitte versuche es erneut.",
            scene_type='dna_sample',
            used_features=[],
            llm_used=result.get('llm_used', 'error'),
            success=False,
        )
    
    def _mock_style_analysis(self, text: str) -> StyleAnalysisResult:
        """Mock-Analyse für Tests oder wenn kein LLM verfügbar."""
        # Einfache Textanalyse
        sentences = text.split('.')
        words = text.split()
        avg_sentence_len = len(words) / max(len(sentences), 1)
        
        # Dialogue detection
        dialogue_chars = text.count('"') + text.count('„') + text.count('"')
        dialogue_ratio = dialogue_chars / max(len(text), 1)
        
        return StyleAnalysisResult(
            observations={
                'sentence_structure': 'Variierte Satzlängen mit Mischung aus kurzen und langen Sätzen',
                'vocabulary': 'Gehobene Alltagssprache mit gelegentlichen Fachbegriffen',
                'narrative_voice': 'Dritte Person, personaler Erzähler',
                'dialogue_style': 'Natürliche Dialogführung mit Subtext',
                'description_technique': 'Sensorische Details, Show dont tell',
                'emotional_depth': 'Moderate emotionale Tiefe durch innere Reflexion',
                'imagery': 'Vereinzelte Metaphern und Vergleiche',
            },
            patterns=[
                'short_punchy_sentences',
                'sensory_details',
                'dialogue_with_subtext',
                'show_dont_tell',
                'varied_sentence_length',
            ],
            metrics={
                'avg_sentence_length': round(avg_sentence_len, 1),
                'dialogue_ratio': round(dialogue_ratio, 2),
                'adjective_density': 0.07,
            },
            llm_used='mock',
            success=True,
        )
    
    def _mock_scene_generation(
        self, 
        scene_type: str, 
        style_profile: Dict[str, Any]
    ) -> SceneGenerationResult:
        """Mock-Generierung für Tests oder wenn kein LLM verfügbar."""
        mock_scenes = {
            'arrival': '''Der Zug hielt mit einem letzten Seufzer. Marie stieg aus, der Koffer schlug gegen ihre Knie. Bahnsteig 3, wie versprochen.

Die Luft hier war anders. Salzig, feucht, mit einem Hauch von Diesel. Sie blinzelte gegen das Licht, das von der Glasdecke fiel.

Menschen strömten an ihr vorbei. Niemand schaute. Niemand wartete. Genau so hatte sie es gewollt.

Der Ausgang lag rechts. Sie folgte den Schildern, den Koffer nun hinter sich herziehend. Die Räder ratterten über alte Fliesen. Ein Rhythmus. Ihr neuer Rhythmus.

Draußen dann: Möwen. Tatsächlich Möwen. Sie musste lächeln.''',

            'dialogue': '''"Du hast es also doch getan." Sein Blick war hart.

"War das eine Frage?"

"Nein." Er wandte sich ab, griff nach seinem Glas. Das Eis klirrte. "Eher eine Feststellung."

Sie setzte sich ihm gegenüber. Der Stuhl quietschte. "Und jetzt?"

"Jetzt?" Ein Lachen, das keines war. "Jetzt müssen wir damit leben."

"Wir?"

Er stellte das Glas ab. Zu hart. Ein Sprung im Kristall. "Wir", wiederholte er. "Ob dir das passt oder nicht."

Die Uhr an der Wand tickte. Siebenundzwanzig Sekunden, bevor sie antwortete.''',

            'introspection': '''Die Frage war einfach. Die Antwort nicht.

Er stand am Fenster, die Stirn am kalten Glas. Draußen ging die Stadt schlafen. Laternen flackerten orange. Ein Auto, dann Stille.

Hätte er anders handeln können? Ja. Hätte er anders handeln sollen? Das war der eigentliche Punkt.

Die Erinnerung an ihren Blick. Dieses kurze Zögern, bevor sie sich abwandte. Er hatte es gesehen. Ignoriert. Weitergeredet.

Fehler. Das Wort schmeckte bitter.

Morgen würde er anrufen. Oder übermorgen. Oder—

Nein. Morgen. Definitiv morgen.

Er löste sich vom Fenster. Das Bett wartete. Der Schlaf weniger.''',

            'action': '''Sie rannte.

Pflastersteine unter ihren Füßen, nass vom Regen. Ein Stolpern, aufgefangen im letzten Moment. Weiter.

Hinter ihr Schritte. Näher. Immer näher.

Die Gasse machte einen Knick. Sie folgte blind, Schulter gegen die Mauer. Schmerz, ignoriert. Eine Tür, halb offen. Sie schlüpfte hindurch.

Dunkelheit. Geruch nach Öl und altem Papier. Ein Lagerraum. Kisten, gestapelt bis zur Decke.

Die Schritte draußen. Vorbei? Sie hielt den Atem an.

Vorbei.

Noch nicht.

Sie presste sich gegen die Wand und wartete.''',

            'description': '''Das Haus hatte bessere Zeiten gesehen.

Die Fassade, einst weiß, war nun grau mit Flecken von Moos. Fensterläden hingen schief, einer fehlte ganz. Das Dach zeigte Lücken wie ein zahnloses Grinsen.

Doch der Garten lebte. Wild, ungezähmt, aber lebendig. Rosen kletterten über das verrostete Tor, ihre Blüten trotzig rot. Efeu hatte sich die Ostseite erobert, grüne Finger, die nach oben griffen.

Der Weg zur Haustür war kaum noch erkennbar. Gras und Löwenzahn hatten übernommen. Nur ein schmaler Pfad verriet, dass hier noch jemand ein- und ausging.

Die Stufen knarrten unter ihrem Gewicht.''',

            'transition': '''Drei Wochen später war alles anders.

Die Koffer waren ausgepackt, der Mietvertrag unterschrieben. Ein neuer Name am Briefkasten, noch ein wenig schief.

Der Winter kam früh in diesem Jahr. Erster Schnee Ende Oktober, dann Regen, dann wieder Schnee. Sie lernte, die Heizung richtig einzustellen.

Die Nachbarin brachte Kuchen. Die Bäckerin kannte ihren Namen. Der Busfahrer nickte, wenn sie einstieg.

Routine. Das Wort hatte sie immer gefürchtet. Jetzt schmeckte es nach Sicherheit.''',
        }
        
        text = mock_scenes.get(scene_type, mock_scenes['arrival'])
        
        return SceneGenerationResult(
            text=text,
            scene_type=scene_type,
            used_features=['mock_generation'],
            llm_used='mock',
            success=True,
        )
    
    @classmethod
    def get_available_llms(cls, test_models: bool = False) -> List[Dict[str, Any]]:
        """
        Gibt eine Liste verfügbarer LLMs zurück.
        Kombiniert DB-Einträge mit lokal laufenden Ollama-Modellen.
        
        Args:
            test_models: Wenn True, werden Ollama-Modelle auf Funktionalität getestet
        """
        llms_list = []
        
        # 1. LLMs aus Datenbank
        try:
            from apps.bfagent.models import Llms
            db_llms = Llms.objects.filter(is_active=True).values(
                'id', 'llm_name', 'provider', 'description'
            )
            llms_list.extend(list(db_llms))
        except Exception:
            pass
        
        # 2. Lokal laufende Ollama-Modelle hinzufügen (keine Embedding-Modelle)
        try:
            import requests
            resp = requests.get('http://localhost:11434/api/tags', timeout=2)
            if resp.ok:
                models = resp.json().get('models', [])
                existing_names = {l.get('llm_name', '').lower() for l in llms_list}
                
                # Embedding-Modelle ausfiltern (nicht für Textgenerierung geeignet)
                embedding_keywords = ['embed', 'embedding', 'nomic', 'bge', 'e5', 'gte']
                
                # NSFW-fähige Modelle markieren
                nsfw_keywords = ['dolphin', 'nous-hermes', 'uncensored', 'abliterated']
                
                for model in models:
                    model_name = model.get('name', '')
                    model_lower = model_name.lower()
                    
                    # Embedding-Modelle überspringen
                    if any(kw in model_lower for kw in embedding_keywords):
                        continue
                    
                    # NSFW-Fähigkeit prüfen
                    is_nsfw = any(kw in model_lower for kw in nsfw_keywords)
                    
                    # Status testen wenn gewünscht
                    status = 'unknown'
                    if test_models:
                        status = cls._test_ollama_model(model_name)
                    
                    # Nur hinzufügen wenn nicht schon in DB
                    if model_lower not in existing_names:
                        size_bytes = model.get('size', 0)
                        size_gb = f"{size_bytes / 1e9:.1f}GB" if size_bytes else ""
                        
                        description = f'Lokal via Ollama'
                        if is_nsfw:
                            description = f'🔞 NSFW-fähig - {size_gb}'
                        elif size_gb:
                            description = f'Lokal - {size_gb}'
                        
                        if test_models and status != 'ok':
                            description = f'⚠️ {status} - {description}'
                        
                        llms_list.append({
                            'id': f'ollama:{model_name}',
                            'llm_name': model_name,
                            'provider': 'ollama (lokal)',
                            'description': description,
                            'is_nsfw': is_nsfw,
                            'status': status,
                        })
        except Exception:
            pass
        
        # NSFW-Modelle nach oben sortieren
        llms_list.sort(key=lambda x: (not x.get('is_nsfw', False), x.get('llm_name', '')))
        
        return llms_list
    
    @classmethod
    def _test_ollama_model(cls, model_name: str) -> str:
        """Testet ob ein Ollama-Modell funktioniert."""
        import requests
        try:
            resp = requests.post(
                'http://localhost:11434/api/generate',
                json={'model': model_name, 'prompt': 'Hi', 'stream': False},
                timeout=15
            )
            if resp.ok:
                return 'ok'
            else:
                error = resp.json().get('error', 'unknown')[:30]
                return f'error: {error}'
        except Exception as e:
            return f'error: {str(e)[:20]}'
    
    @classmethod
    def check_ollama_available(cls) -> Tuple[bool, str]:
        """Prüft ob Ollama lokal verfügbar ist."""
        import requests
        try:
            resp = requests.get('http://localhost:11434/api/tags', timeout=2)
            if resp.ok:
                models = resp.json().get('models', [])
                model_names = [m['name'] for m in models]
                return True, f"Ollama verfügbar mit Modellen: {', '.join(model_names)}"
            return False, "Ollama antwortet nicht korrekt"
        except requests.exceptions.ConnectionError:
            return False, "Ollama nicht erreichbar (localhost:11434)"
        except Exception as e:
            return False, f"Ollama-Check fehlgeschlagen: {e}"
    
    @classmethod
    def get_recommended_nsfw_llms(cls) -> List[Dict[str, str]]:
        """
        Empfohlene LLMs für NSFW/Erotik-Inhalte.
        
        Diese Modelle haben keine oder gelockerte Content-Filter.
        """
        return [
            {
                'name': 'Mistral Nemo (Ollama)',
                'provider': 'ollama',
                'model': 'mistral-nemo',
                'notes': 'Lokal, schnell, keine Zensur. Empfohlen!',
                'setup': 'ollama pull mistral-nemo',
            },
            {
                'name': 'Llama 3.1 Uncensored (Ollama)',
                'provider': 'ollama',
                'model': 'llama3.1:8b-instruct-uncensored',
                'notes': 'Lokal, NSFW-optimiert',
                'setup': 'ollama pull dolphin-llama3:8b',
            },
            {
                'name': 'Dolphin Mixtral (Ollama)',
                'provider': 'ollama',
                'model': 'dolphin-mixtral',
                'notes': 'Lokal, explizit NSFW-fähig, sehr gut für kreatives Schreiben',
                'setup': 'ollama pull dolphin-mixtral',
            },
            {
                'name': 'OpenRouter (diverse Modelle)',
                'provider': 'openrouter',
                'model': 'verschiedene',
                'notes': 'API-Zugang zu vielen uncensored Modellen',
                'setup': 'API-Key von openrouter.ai',
            },
            {
                'name': 'Together AI',
                'provider': 'together',
                'model': 'verschiedene',
                'notes': 'API mit NSFW-fähigen Modellen (z.B. Nous Hermes)',
                'setup': 'API-Key von together.ai',
            },
        ]
