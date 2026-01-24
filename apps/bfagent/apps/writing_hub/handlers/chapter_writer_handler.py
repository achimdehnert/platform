"""
Chapter Writer Handler
Generates chapter content using LLM with full project context from outline, characters, and worlds.

Event-Driven Architecture:
- Publishes CHAPTER_UPDATED and CONTENT_GENERATED events when USE_EVENT_BUS is enabled
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Event Bus imports (Feature Flag controlled)
from apps.core.event_bus import event_bus
from apps.core.events import Events

logger = logging.getLogger(__name__)


@dataclass
class ChapterContext:
    """Context for chapter writing - pulls from outline, characters, worlds"""
    project_id: int
    chapter_id: int
    # Project info
    title: str = ""
    genre: str = ""
    premise: str = ""
    target_audience: str = ""
    writing_style: str = ""
    # Chapter info
    chapter_number: int = 1
    chapter_title: str = ""
    chapter_outline: str = ""
    chapter_beat: str = ""
    emotional_arc: str = ""
    target_word_count: int = 2000
    existing_content: str = ""
    # Previous/Next chapter for continuity
    prev_chapter_summary: str = ""
    next_chapter_outline: str = ""
    # Characters in this chapter
    characters: List[Dict] = field(default_factory=list)
    # World/Setting
    worlds: List[Dict] = field(default_factory=list)
    # All chapters for context
    all_chapters_outline: List[Dict] = field(default_factory=list)
    # Style DNA Integration
    style_dna: Optional[Dict] = None
    use_nsfw_model: bool = False
    
    def to_prompt_context(self) -> str:
        """Build comprehensive context string for LLM prompt"""
        parts = []
        
        # ===== BOOK INFO =====
        parts.append("=" * 50)
        parts.append("📚 BUCH-INFORMATIONEN")
        parts.append("=" * 50)
        parts.append(f"**Titel:** {self.title}")
        parts.append(f"**Genre:** {self.genre}")
        if self.premise:
            parts.append(f"**Premise:** {self.premise}")
        if self.target_audience:
            parts.append(f"**Zielgruppe:** {self.target_audience}")
        
        # ===== CHAPTER TO WRITE =====
        parts.append("")
        parts.append("=" * 50)
        parts.append(f"📖 ZU SCHREIBENDES KAPITEL: {self.chapter_number} - {self.chapter_title}")
        parts.append("=" * 50)
        
        # OUTLINE is the most important part!
        if self.chapter_outline:
            parts.append(f"\n🎯 **KAPITEL-OUTLINE (WAS PASSIEREN SOLL):**")
            parts.append(f"{self.chapter_outline}")
        else:
            parts.append(f"\n⚠️ Kein Outline vorhanden - schreibe ein einführendes Kapitel")
        
        if self.chapter_beat:
            parts.append(f"\n**Story-Beat:** {self.chapter_beat}")
        if self.emotional_arc:
            parts.append(f"**Emotionaler Bogen:** {self.emotional_arc}")
        parts.append(f"**Ziel-Wortanzahl:** ca. {self.target_word_count} Wörter")
        
        # ===== STORY CONTINUITY =====
        if self.prev_chapter_summary:
            parts.append("")
            parts.append("📝 **WAS BISHER GESCHAH (vorheriges Kapitel):**")
            parts.append(self.prev_chapter_summary[:600])
        
        if self.next_chapter_outline:
            parts.append("")
            parts.append("➡️ **VORSCHAU NÄCHSTES KAPITEL (für Übergänge):**")
            parts.append(self.next_chapter_outline[:200])
        
        # ===== CHARACTERS =====
        if self.characters:
            parts.append("")
            parts.append("=" * 50)
            parts.append("👥 CHARAKTERE")
            parts.append("=" * 50)
            for char in self.characters[:5]:
                name = char.get('name') or 'Unbekannt'
                role = char.get('role') or 'Nebenrolle'
                desc = (char.get('description') or '')[:200]
                motivation = (char.get('motivation') or '')[:150]
                personality = (char.get('personality') or '')[:100]
                parts.append(f"\n**{name}** ({role})")
                if desc:
                    parts.append(f"  Beschreibung: {desc}")
                if motivation:
                    parts.append(f"  Motivation: {motivation}")
                if personality:
                    parts.append(f"  Persönlichkeit: {personality}")
        
        # ===== WORLD/SETTING =====
        if self.worlds:
            parts.append("")
            parts.append("=" * 50)
            parts.append("🌍 SETTING & WELT")
            parts.append("=" * 50)
            for world in self.worlds[:2]:
                name = world.get('name') or 'Unbekannt'
                desc = (world.get('description') or '')[:300]
                setting = (world.get('setting_details') or '')[:200]
                parts.append(f"\n**{name}**")
                if desc:
                    parts.append(f"  {desc}")
                if setting:
                    parts.append(f"  Details: {setting}")
        
        # ===== STORY STRUCTURE =====
        if self.all_chapters_outline and len(self.all_chapters_outline) > 1:
            parts.append("")
            parts.append("📋 **STORY-STRUKTUR (alle Kapitel):**")
            for ch in self.all_chapters_outline[:15]:
                num = ch.get('chapter_number', '?')
                title = ch.get('title') or f'Kapitel {num}'
                outline = (ch.get('outline') or '')[:80]
                marker = "👉" if num == self.chapter_number else "  "
                if outline:
                    parts.append(f"{marker} Kap. {num}: {title} - {outline}...")
                else:
                    parts.append(f"{marker} Kap. {num}: {title}")
        
        # ===== STYLE DNA =====
        if self.style_dna:
            parts.append("")
            parts.append("=" * 50)
            parts.append("✨ AUTHOR STYLE DNA (WICHTIG!)")
            parts.append("=" * 50)
            
            dna = self.style_dna
            if dna.get('name'):
                parts.append(f"**Stilprofil:** {dna['name']}")
            
            if dna.get('signature_moves'):
                parts.append("\n🎯 **Signature Moves (UNBEDINGT VERWENDEN):**")
                for move in dna['signature_moves'][:5]:
                    parts.append(f"  • {move}")
            
            if dna.get('do_list'):
                parts.append("\n✅ **DO (diese Stilmittel einsetzen):**")
                for item in dna['do_list'][:8]:
                    parts.append(f"  • {item}")
            
            if dna.get('dont_list'):
                parts.append("\n❌ **DON'T (diese Stilmittel VERMEIDEN):**")
                for item in dna['dont_list'][:5]:
                    parts.append(f"  • {item}")
            
            if dna.get('taboo_list'):
                parts.append("\n🚫 **TABU-WÖRTER (NIEMALS verwenden):**")
                parts.append(f"  {', '.join(dna['taboo_list'][:10])}")
        
        parts.append("")
        parts.append("=" * 50)
        
        return "\n".join(parts)
    
    @classmethod
    def from_chapter(cls, project_id: int, chapter_id: int) -> 'ChapterContext':
        """Create ChapterContext from chapter ID, loading all related data"""
        from apps.bfagent.models import BookProjects, BookChapters, Characters, Worlds
        from apps.writing_hub.models import IdeaSession
        
        try:
            project = BookProjects.objects.get(id=project_id)
            chapter = BookChapters.objects.get(id=chapter_id, project=project)
        except (BookProjects.DoesNotExist, BookChapters.DoesNotExist):
            return cls(project_id=project_id, chapter_id=chapter_id)
        
        # Load characters
        characters = list(Characters.objects.filter(project=project).values(
            'name', 'role', 'description', 'motivation', 'personality', 'background'
        )[:10])
        
        # Load worlds
        worlds = list(Worlds.objects.filter(project=project).values(
            'name', 'description', 'setting_details', 'culture', 'technology_level'
        )[:3])
        
        # Get previous chapter summary
        prev_chapter_summary = ""
        if chapter.chapter_number > 1:
            prev_ch = BookChapters.objects.filter(
                project=project, 
                chapter_number=chapter.chapter_number - 1
            ).first()
            if prev_ch:
                if prev_ch.content:
                    prev_chapter_summary = prev_ch.content[:500] + "..."
                elif prev_ch.outline:
                    prev_chapter_summary = f"(Outline) {prev_ch.outline}"
        
        # Get next chapter outline for foreshadowing
        next_chapter_outline = ""
        next_ch = BookChapters.objects.filter(
            project=project, 
            chapter_number=chapter.chapter_number + 1
        ).first()
        if next_ch and next_ch.outline:
            next_chapter_outline = next_ch.outline
        
        # Parse chapter notes for beat/emotional_arc
        beat = ""
        emotional_arc = ""
        if chapter.notes:
            try:
                notes_data = json.loads(chapter.notes) if isinstance(chapter.notes, str) else chapter.notes
                beat = notes_data.get('beat', '')
                emotional_arc = notes_data.get('emotional_arc', '')
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Get premise from IdeaSession
        premise = project.story_premise or ''
        try:
            idea_session = IdeaSession.objects.filter(
                project=project, 
                status='completed'
            ).order_by('-updated_at').first()
            if idea_session:
                for resp in idea_session.responses.filter(is_accepted=True).select_related('step'):
                    step_key = resp.step.step_key if resp.step else ''
                    if step_key == 'premise' and resp.content:
                        premise = resp.content
                        break
        except Exception:
            pass
        
        # All chapters outline for story structure
        all_chapters = list(BookChapters.objects.filter(project=project).order_by('chapter_number').values(
            'chapter_number', 'title', 'outline'
        )[:20])
        
        # Load Style DNA for this author/project
        style_dna = None
        use_nsfw = False
        try:
            from apps.writing_hub.models import AuthorStyleDNA
            # Get the project owner (user or owner field)
            project_owner = project.owner or project.user
            dna_obj = None
            if not project_owner:
                logger.warning(f"Project {project_id} has no owner - cannot load Style DNA")
            else:
                # Try author's primary DNA
                dna_obj = AuthorStyleDNA.objects.filter(
                    author=project_owner,
                    is_primary=True
                ).first()
            
            if dna_obj:
                style_dna = {
                    'name': dna_obj.name,
                    'signature_moves': dna_obj.signature_moves or [],
                    'do_list': dna_obj.do_list or [],
                    'dont_list': dna_obj.dont_list or [],
                    'taboo_list': dna_obj.taboo_list or [],
                }
                # Check if this is adult content that needs NSFW model
                use_nsfw = any(
                    keyword in (project.genre or '').lower() 
                    for keyword in ['erotik', 'romance', 'adult', 'erotic', 'nsfw']
                )
                logger.info(f"Loaded Style DNA: {dna_obj.name}, NSFW: {use_nsfw}")
        except Exception as e:
            logger.warning(f"Could not load Style DNA: {e}")
        
        return cls(
            project_id=project_id,
            chapter_id=chapter_id,
            title=project.title or '',
            genre=project.genre or '',
            premise=premise,
            target_audience=project.target_audience or '',
            chapter_number=chapter.chapter_number,
            chapter_title=chapter.title or f'Kapitel {chapter.chapter_number}',
            chapter_outline=chapter.outline or '',
            chapter_beat=beat,
            emotional_arc=emotional_arc,
            target_word_count=chapter.target_word_count or 2000,
            existing_content=chapter.content or '',
            prev_chapter_summary=prev_chapter_summary,
            next_chapter_outline=next_chapter_outline,
            characters=characters,
            worlds=worlds,
            all_chapters_outline=all_chapters,
            style_dna=style_dna,
            use_nsfw_model=use_nsfw,
        )


class ChapterWriterHandler:
    """
    Handler for writing chapter content using LLM with full project context.
    
    Usage:
        handler = ChapterWriterHandler()
        result = handler.write_chapter(context)
        result = handler.write_all_chapters(project_id)
        result = handler.refine_chapter(context, instruction)
    """
    
    PROMPTS = {
        'write_chapter': {
            'system': """Du bist ein preisgekrönter Romanautor, spezialisiert auf fesselnde Erzählungen.

DEINE AUFGABE: Schreibe ein vollständiges Kapitel basierend auf dem gegebenen Outline und Kontext.

WICHTIG:
- Schreibe das Kapitel KOMPLETT NEU basierend auf dem Outline
- Verwende die Charaktere und das Setting aus dem Kontext
- Beachte den Story-Beat und emotionalen Bogen
- Schreibe auf Deutsch, lebendig und literarisch hochwertig
- KEINE Metakommentare, KEINE Entschuldigungen - NUR den Romantext!""",
            'user': """# KAPITEL SCHREIBEN

## STORY-KONTEXT:
{context}

## DEINE AUFGABE:
Schreibe das vollständige Kapitel ({target_words} Wörter) basierend auf dem OUTLINE oben.

### SCHREIB-ANWEISUNGEN:
1. **Eröffnung**: Beginne mitten in der Szene (in medias res) - zeige, erzähle nicht nur
2. **Charaktere**: Lass Charaktere durch Dialog und Handlung lebendig werden
3. **Setting**: Webe Beschreibungen des Ortes natürlich in die Handlung ein
4. **Konflikt**: Baue Spannung gemäß dem Story-Beat auf
5. **Emotionaler Bogen**: Führe den Leser durch die emotionale Entwicklung
6. **Abschluss**: Ende mit einem Hook oder Übergang zum nächsten Kapitel

### FORMAT:
- Schreibe NUR den Kapiteltext
- Verwende Absätze, Dialoge und Beschreibungen
- Keine Überschriften außer optional dem Kapiteltitel am Anfang
- KEINE Kommentare wie "Hier ist das Kapitel" oder "Ich schreibe jetzt..."

BEGINNE JETZT MIT DEM KAPITELTEXT:"""
        },
        'refine_chapter': {
            'system': """Du bist ein erfahrener Lektor und Romanautor.
Du verbesserst und verfeinst Kapiteltext basierend auf spezifischen Anweisungen.
Behalte den Stil und die Stimme bei, verbessere aber Qualität und Wirkung.
Schreibe NUR den verbesserten Text, keine Erklärungen.""",
            'user': """# KAPITEL VERFEINERN

## KONTEXT:
{context}

## AKTUELLER TEXT:
{existing_content}

## VERFEINERUNGS-AUFTRAG:
{instruction}

Schreibe das verbesserte Kapitel. Behalte die guten Teile bei und verbessere gemäß der Anweisung.
NUR den Romantext ausgeben, keine Erklärungen!"""
        },
        'continue_chapter': {
            'system': """Du bist ein Romanautor, der einen begonnenen Text fortsetzt.
Halte Stil, Ton und Erzählperspektive exakt konsistent.
Führe die Handlung nahtlos weiter basierend auf dem Outline.
Schreibe NUR die Fortsetzung, keine Kommentare.""",
            'user': """# KAPITEL FORTSETZEN

## STORY-KONTEXT:
{context}

## BISHERIGER TEXT (fortsetzen!):
{existing_content}

## AUFTRAG:
Setze den Text NAHTLOS fort bis ca. {target_words} zusätzliche Wörter erreicht sind.
- Behalte exakt den gleichen Stil und Ton bei
- Führe die Szene/Handlung gemäß Outline weiter
- Schreibe NUR die Fortsetzung, keine Wiederholung des bisherigen Textes

FORTSETZUNG:"""
        },
        'chapter_summary': {
            'system': "Du fasst Kapitelinhalte prägnant in 2-3 Sätzen zusammen. NUR die Zusammenfassung, nichts anderes.",
            'user': """Fasse dieses Kapitel in 2-3 Sätzen zusammen (Handlung, wichtige Ereignisse, Charakterentwicklung):

{existing_content}

ZUSAMMENFASSUNG:"""
        }
    }
    
    # NSFW-capable Ollama models for adult content
    NSFW_OLLAMA_MODELS = [
        'dolphin-llama3:8b',
        'nous-hermes2:latest',
        'dolphin-mixtral:latest',
        'dolphin-mistral:latest',
    ]
    
    def __init__(self, llm_id: Optional[int] = None, use_nsfw: bool = False, ollama_model: str = None):
        """Initialize handler with optional specific LLM or NSFW mode."""
        self.llm_id = llm_id
        self.use_nsfw = use_nsfw
        self.ollama_model = ollama_model
        self._llm = None
        self._use_ollama_direct = False
    
    def get_llm(self, context: ChapterContext = None):
        """Get the LLM to use - supports NSFW Ollama models for adult content."""
        if self._llm:
            return self._llm
        
        from apps.bfagent.models import Llms
        from apps.writing_hub.models import WorkflowPhaseLLMConfig
        
        # Check if NSFW mode is needed
        use_nsfw = self.use_nsfw or (context and context.use_nsfw_model)
        
        # 1. NSFW MODE: Use Ollama NSFW model directly
        if use_nsfw:
            self._use_ollama_direct = True
            self.ollama_model = self.ollama_model or self.NSFW_OLLAMA_MODELS[0]
            logger.info(f"Using Ollama NSFW model for writing: {self.ollama_model}")
            return None  # Signal to use Ollama direct
        
        # 2. USER SELECTED LLM takes highest priority (for testing/comparison)
        if self.llm_id:
            self._llm = Llms.objects.filter(id=self.llm_id, is_active=True).first()
            if self._llm:
                logger.info(f"Using user-selected LLM ID {self.llm_id}: {self._llm.name}")
                return self._llm
        
        # 3. Prefer OpenAI for chapter writing (faster, more reliable)
        self._llm = Llms.objects.filter(is_active=True, provider='openai').first()
        if self._llm:
            logger.info(f"Using OpenAI LLM for writing: {self._llm.name}")
            return self._llm
        
        # 4. Try WorkflowPhaseLLMConfig for 'writing' phase
        config_llm = WorkflowPhaseLLMConfig.get_llm_for_phase('writing')
        if config_llm:
            self._llm = config_llm
            logger.info(f"Using workflow config LLM for writing: {self._llm.name}")
            return self._llm
        
        # 5. Fallback: any active LLM
        self._llm = Llms.objects.filter(is_active=True).first()
        if self._llm:
            logger.info(f"Using fallback LLM: {self._llm.name}")
        
        return self._llm
    
    def _call_ollama_direct(self, system: str, prompt: str, max_tokens: int = 4096) -> Dict[str, Any]:
        """Call Ollama API directly for NSFW content generation."""
        import requests
        
        ollama_base = "http://localhost:11434"
        model = self.ollama_model or self.NSFW_OLLAMA_MODELS[0]
        
        for attempt_model in [model] + [m for m in self.NSFW_OLLAMA_MODELS if m != model]:
            try:
                full_prompt = f"{system}\n\n{prompt}"
                response = requests.post(
                    f"{ollama_base}/api/generate",
                    json={
                        "model": attempt_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": 0.8,
                        }
                    },
                    timeout=180
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        'ok': True,
                        'text': result.get('response', ''),
                        'llm_used': f"Ollama/{attempt_model}",
                        'tokens_used': result.get('eval_count', 0),
                    }
                else:
                    logger.warning(f"Ollama {attempt_model} failed: {response.status_code}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Ollama {attempt_model} error: {e}")
                continue
        
        return {'ok': False, 'error': 'All Ollama models failed'}
    
    def _get_model_max_tokens(self, llm) -> int:
        """Get max output tokens for a model."""
        model_name = (llm.llm_name or '').lower()
        
        # Local LLMs (Ollama, vLLM) typically have higher limits
        if llm.provider in ('ollama', 'vllm', 'local'):
            return 8192  # Local models can handle more
        
        # OpenAI models
        if llm.provider == 'openai' or 'gpt' in model_name:
            return 4096  # Safe limit for all OpenAI models
        
        # Anthropic models
        if 'claude-3-opus' in model_name:
            return 4096
        if 'claude-3-5' in model_name or 'claude-3.5' in model_name:
            return 8192
        
        return 4096  # Safe default
    
    def write_chapter(self, context: ChapterContext) -> Dict[str, Any]:
        """
        Write a complete chapter using LLM.
        Uses chunked generation for large chapters to avoid token limits.
        Supports NSFW Ollama models for adult content.
        
        Publishes events (if USE_EVENT_BUS enabled):
        - CONTENT_GENERATED: When chapter content is successfully generated
        
        Args:
            context: ChapterContext with all project/chapter data
        
        Returns:
            Dict with 'success', 'content', 'word_count', 'llm_used', 'error'
        """
        # Check for NSFW mode first
        llm = self.get_llm(context)
        
        # Use Ollama direct for NSFW content
        if self._use_ollama_direct:
            result = self._write_chapter_ollama(context)
        elif not llm:
            return {
                'success': False,
                'error': 'Kein aktives LLM konfiguriert. Bitte im Control Center ein LLM aktivieren.'
            }
        else:
            model_max = self._get_model_max_tokens(llm)
            words_per_chunk = int(model_max / 1.5)  # ~2700 words for 4096 tokens
            
            # If target is larger than one chunk, use chunked generation
            if context.target_word_count > words_per_chunk:
                logger.info(f"Using chunked generation: {context.target_word_count} words > {words_per_chunk} per chunk")
                result = self._write_chapter_chunked(context, llm, model_max)
            else:
                # Standard single-chunk generation
                result = self._write_chapter_single(context, llm, model_max)
        
        # Publish event on success (only if feature flag enabled)
        if result.get('success'):
            event_bus.publish(
                Events.CONTENT_GENERATED,
                source="ChapterWriterHandler",
                content_type="chapter",
                content_id=context.chapter_id,
                project_id=context.project_id,
                chapter_number=context.chapter_number,
                word_count=result.get('word_count', 0),
                llm_used=result.get('llm_used', 'unknown'),
            )
        
        return result
    
    def _write_chapter_ollama(self, context: ChapterContext) -> Dict[str, Any]:
        """Write a chapter using Ollama NSFW model directly."""
        prompt_config = self.PROMPTS['write_chapter']
        context_str = context.to_prompt_context()
        
        # Add Style DNA emphasis for NSFW content
        system = prompt_config['system']
        if context.style_dna:
            system += "\n\nWICHTIG: Befolge die AUTHOR STYLE DNA Regeln im Kontext STRIKT!"
        
        prompt = prompt_config['user'].format(
            context=context_str,
            target_words=context.target_word_count
        )
        
        logger.info(f"Writing chapter {context.chapter_number} with Ollama NSFW model: {self.ollama_model}")
        
        response = self._call_ollama_direct(
            system=system,
            prompt=prompt,
            max_tokens=8192
        )
        
        if not response.get('ok'):
            return {
                'success': False,
                'error': response.get('error', 'Ollama generation failed'),
                'llm_used': f"Ollama/{self.ollama_model}"
            }
        
        content = response.get('text', '').strip()
        word_count = len(content.split())
        
        logger.info(f"Successfully wrote chapter {context.chapter_number}: {word_count} words (Ollama NSFW)")
        
        return {
            'success': True,
            'content': content,
            'word_count': word_count,
            'llm_used': response.get('llm_used', f"Ollama/{self.ollama_model}"),
            'tokens_used': response.get('tokens_used', 0),
        }
    
    def _write_chapter_single(self, context: ChapterContext, llm, model_max: int) -> Dict[str, Any]:
        """Write a chapter in a single LLM call (for smaller chapters)."""
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        prompt_config = self.PROMPTS['write_chapter']
        context_str = context.to_prompt_context()
        estimated_tokens = int(context.target_word_count * 1.5)
        max_tokens = min(max(estimated_tokens, 2000), model_max)
        
        logger.info(f"Single-chunk generation: {context.target_word_count} words, max_tokens={max_tokens}")
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(
                context=context_str,
                target_words=context.target_word_count
            ),
            temperature=0.8,
            max_tokens=max_tokens,
        )
        
        try:
            response = generate_text(req)
        except Exception as e:
            logger.error(f"LLM exception: {e}")
            return {'success': False, 'error': str(e), 'llm_used': llm.name}
        
        if not response or not response.get('ok'):
            error_msg = response.get('error', 'Unbekannter Fehler') if response else 'Keine Antwort'
            return {'success': False, 'error': f"LLM Fehler: {error_msg}", 'llm_used': llm.name}
        
        content = response.get('text', '').strip()
        word_count = len(content.split())
        
        logger.info(f"Successfully wrote chapter {context.chapter_number}: {word_count} words")
        
        return {
            'success': True,
            'content': content,
            'word_count': word_count,
            'llm_used': llm.name,
            'latency_ms': response.get('latency_ms')
        }
    
    def _write_chapter_chunked(self, context: ChapterContext, llm, model_max: int) -> Dict[str, Any]:
        """Write a chapter in multiple chunks for large target word counts."""
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        words_per_chunk = int(model_max / 1.5) - 200  # Leave margin
        num_chunks = (context.target_word_count // words_per_chunk) + 1
        
        logger.info(f"Chunked generation: {context.target_word_count} words in {num_chunks} chunks of ~{words_per_chunk} words")
        
        context_str = context.to_prompt_context()
        all_content = []
        total_latency = 0
        
        for chunk_num in range(num_chunks):
            is_first = chunk_num == 0
            is_last = chunk_num == num_chunks - 1
            
            # Build chunk-specific prompt
            if is_first:
                chunk_prompt = f"""Schreibe den ANFANG von Kapitel {context.chapter_number}.

{context_str}

Schreibe etwa {words_per_chunk} Wörter. Dies ist Teil 1 von {num_chunks}.
Beginne mit einer fesselnden Eröffnung. ENDE NICHT mit dem Kapitel - es wird fortgesetzt."""
            elif is_last:
                previous_content = "\n\n".join(all_content[-2:])  # Last 2 chunks for context
                chunk_prompt = f"""Schreibe das ENDE von Kapitel {context.chapter_number}.

BISHERIGER INHALT (letzte Absätze):
{previous_content[-3000:]}

Schreibe etwa {words_per_chunk} Wörter. Dies ist der letzte Teil ({chunk_num + 1} von {num_chunks}).
Führe die Geschichte zum Kapitelende. Schließe mit einem befriedigenden Abschluss ab."""
            else:
                previous_content = "\n\n".join(all_content[-2:])
                chunk_prompt = f"""Setze Kapitel {context.chapter_number} fort.

BISHERIGER INHALT (letzte Absätze):
{previous_content[-3000:]}

Schreibe etwa {words_per_chunk} Wörter. Dies ist Teil {chunk_num + 1} von {num_chunks}.
Führe die Geschichte nahtlos weiter. ENDE NICHT - es wird fortgesetzt."""
            
            req = LlmRequest(
                provider=llm.provider or 'openai',
                api_endpoint=llm.api_endpoint or 'https://api.openai.com',
                api_key=llm.api_key or '',
                model=llm.llm_name or 'gpt-4o-mini',
                system=self.PROMPTS['write_chapter']['system'],
                prompt=chunk_prompt,
                temperature=0.8,
                max_tokens=model_max,
            )
            
            try:
                response = generate_text(req)
            except Exception as e:
                logger.error(f"Chunk {chunk_num + 1} error: {e}")
                if all_content:
                    # Return partial content if we have some
                    partial = "\n\n".join(all_content)
                    return {
                        'success': True,
                        'content': partial + f"\n\n[Generation nach Teil {chunk_num} abgebrochen: {e}]",
                        'word_count': len(partial.split()),
                        'llm_used': f"{llm.name} (partial)",
                        'latency_ms': total_latency
                    }
                return {'success': False, 'error': str(e), 'llm_used': llm.name}
            
            if not response or not response.get('ok'):
                error_msg = response.get('error', 'Fehler') if response else 'Keine Antwort'
                if all_content:
                    partial = "\n\n".join(all_content)
                    return {
                        'success': True,
                        'content': partial + f"\n\n[Generation nach Teil {chunk_num} abgebrochen]",
                        'word_count': len(partial.split()),
                        'llm_used': f"{llm.name} (partial)",
                        'latency_ms': total_latency
                    }
                return {'success': False, 'error': error_msg, 'llm_used': llm.name}
            
            chunk_content = response.get('text', '').strip()
            all_content.append(chunk_content)
            total_latency += response.get('latency_ms', 0)
            
            logger.info(f"Chunk {chunk_num + 1}/{num_chunks}: {len(chunk_content.split())} words")
        
        # Combine all chunks
        full_content = "\n\n".join(all_content)
        word_count = len(full_content.split())
        
        logger.info(f"Chunked generation complete: {word_count} total words in {num_chunks} chunks")
        
        return {
            'success': True,
            'content': full_content,
            'word_count': word_count,
            'llm_used': f"{llm.name} ({num_chunks} chunks)",
            'latency_ms': total_latency
        }
    
    def refine_chapter(self, context: ChapterContext, instruction: str) -> Dict[str, Any]:
        """
        Refine/improve existing chapter content based on instruction.
        
        Args:
            context: ChapterContext with existing content
            instruction: What to improve/change
        
        Returns:
            Dict with 'success', 'content', 'word_count', 'llm_used', 'error'
        """
        if not context.existing_content:
            return {'success': False, 'error': 'Kein bestehender Inhalt zum Verfeinern'}
        
        llm = self.get_llm()
        if not llm:
            return {'success': False, 'error': 'Kein aktives LLM konfiguriert.'}
        
        prompt_config = self.PROMPTS['refine_chapter']
        context_str = context.to_prompt_context()
        
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(
                context=context_str,
                existing_content=context.existing_content,
                instruction=instruction
            ),
            temperature=0.7,
            max_tokens=8000,
        )
        
        logger.info(f"Refining chapter {context.chapter_number} with instruction: {instruction[:50]}...")
        
        try:
            response = generate_text(req)
        except Exception as e:
            return {'success': False, 'error': f"LLM Aufruf fehlgeschlagen: {str(e)}", 'llm_used': llm.name}
        
        if response is None or not response.get('ok'):
            return {'success': False, 'error': (response or {}).get('error', 'Unbekannter Fehler'), 'llm_used': llm.name}
        
        content = response.get('text', '').strip()
        word_count = len(content.split())
        
        return {
            'success': True,
            'content': content,
            'word_count': word_count,
            'llm_used': llm.name,
            'latency_ms': response.get('latency_ms')
        }
    
    def continue_chapter(self, context: ChapterContext) -> Dict[str, Any]:
        """Continue writing an incomplete chapter."""
        if not context.existing_content:
            return self.write_chapter(context)
        
        current_words = len(context.existing_content.split())
        if current_words >= context.target_word_count * 0.9:
            return {'success': True, 'content': context.existing_content, 'word_count': current_words, 'message': 'Kapitel bereits vollständig'}
        
        llm = self.get_llm()
        if not llm:
            return {'success': False, 'error': 'Kein aktives LLM konfiguriert.'}
        
        prompt_config = self.PROMPTS['continue_chapter']
        context_str = context.to_prompt_context()
        
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        remaining_words = context.target_word_count - current_words
        estimated_tokens = int(remaining_words * 1.5)
        
        # Model-specific max output token limits
        model_name = (llm.llm_name or '').lower()
        if 'gpt-4o-mini' in model_name:
            model_max = 4096  # gpt-4o-mini has 4096 output limit
        elif 'gpt-4o' in model_name or 'gpt-4-turbo' in model_name:
            model_max = 16384
        elif 'gpt-4' in model_name:
            model_max = 8192
        elif 'gpt-3.5' in model_name:
            model_max = 4096
        elif 'claude-3-opus' in model_name:
            model_max = 4096
        elif 'claude-3-5' in model_name or 'claude-3.5' in model_name:
            model_max = 8192
        else:
            model_max = 4096  # Safe default
        
        max_tokens = min(max(estimated_tokens, 1000), model_max)
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(
                context=context_str,
                existing_content=context.existing_content,
                target_words=remaining_words
            ),
            temperature=0.8,
            max_tokens=max_tokens,
        )
        
        try:
            response = generate_text(req)
        except Exception as e:
            return {'success': False, 'error': f"LLM Aufruf fehlgeschlagen: {str(e)}", 'llm_used': llm.name}
        
        if response is None or not response.get('ok'):
            return {'success': False, 'error': (response or {}).get('error', 'Unbekannter Fehler'), 'llm_used': llm.name}
        
        continuation = response.get('text', '').strip()
        full_content = context.existing_content + "\n\n" + continuation
        word_count = len(full_content.split())
        
        return {
            'success': True,
            'content': full_content,
            'word_count': word_count,
            'llm_used': llm.name
        }
    
    def generate_summary(self, content: str, llm=None) -> str:
        """
        Generate a brief summary of chapter content for continuity.
        
        Args:
            content: The chapter content to summarize
            llm: Optional LLM to use (uses default if not provided)
        
        Returns:
            Summary string (or empty string on failure)
        """
        if not content or len(content) < 100:
            return ""
        
        if llm is None:
            llm = self.get_llm()
        if not llm:
            # Fallback: extract first 200 chars as basic summary
            return content[:200] + "..."
        
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        prompt_config = self.PROMPTS['chapter_summary']
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(existing_content=content[:3000]),
            temperature=0.3,  # Lower for factual summary
            max_tokens=200,
        )
        
        try:
            response = generate_text(req)
            if response and response.get('ok'):
                return response.get('text', '').strip()
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
        
        # Fallback
        return content[:200] + "..."
    
    def write_all_chapters(self, project_id: int, callback=None) -> Dict[str, Any]:
        """
        Write all chapters for a project sequentially.
        After each chapter, generates a summary to use as context for the next chapter.
        
        Args:
            project_id: Project ID
            callback: Optional callback(chapter_num, status, result) for progress
        
        Returns:
            Dict with 'success', 'chapters_written', 'total_words', 'errors'
        """
        from apps.bfagent.models import BookProjects, BookChapters
        
        try:
            project = BookProjects.objects.get(id=project_id)
            chapters = list(BookChapters.objects.filter(project=project).order_by('chapter_number'))
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': 'Projekt nicht gefunden'}
        
        results = {
            'success': True,
            'chapters_written': 0,
            'total_words': 0,
            'errors': [],
            'chapters': []
        }
        
        # Track summaries for continuity
        prev_summary = ""
        llm = self.get_llm()
        
        for i, chapter in enumerate(chapters):
            if callback:
                callback(chapter.chapter_number, 'writing', None)
            
            # Build context with previous chapter summary
            context = ChapterContext.from_chapter(project_id, chapter.id)
            
            # Override prev_chapter_summary with freshly generated summary
            if prev_summary:
                context.prev_chapter_summary = prev_summary
            
            result = self.write_chapter(context)
            
            if result.get('success'):
                # Save to database
                chapter.content = result['content']
                chapter.word_count = result['word_count']
                chapter.save()
                
                results['chapters_written'] += 1
                results['total_words'] += result['word_count']
                results['chapters'].append({
                    'chapter_number': chapter.chapter_number,
                    'word_count': result['word_count'],
                    'llm_used': result.get('llm_used')
                })
                
                # Generate summary for next chapter (except for last chapter)
                if i < len(chapters) - 1:
                    if callback:
                        callback(chapter.chapter_number, 'summarizing', None)
                    prev_summary = self.generate_summary(result['content'], llm)
                    logger.info(f"Generated summary for chapter {chapter.chapter_number}: {len(prev_summary)} chars")
                
                if callback:
                    callback(chapter.chapter_number, 'complete', result)
            else:
                results['errors'].append({
                    'chapter_number': chapter.chapter_number,
                    'error': result.get('error')
                })
                if callback:
                    callback(chapter.chapter_number, 'error', result)
                # Keep prev_summary from last successful chapter
        
        if results['errors']:
            results['success'] = len(results['errors']) < len(chapters)
        
        return results


# Singleton instance
chapter_writer_handler = ChapterWriterHandler()
