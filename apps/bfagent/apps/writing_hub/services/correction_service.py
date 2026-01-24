"""
Correction Service - Genre-abhängige Korrekturvorschläge
=========================================================

Kombiniert:
- Korrektur-Strategien aus Konzept.md
- Genre-Profile für stil-gerechte Vorschläge
- PromptTemplates für LLM-Integration
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple

from django.db.models import QuerySet
from django.utils import timezone

from apps.bfagent.models import PromptTemplate, BookProjects
from apps.writing_hub.models_lektorat import (
    LektoratsFehler,
    GenreStyleProfile,
    CorrectionSuggestion,
)

logger = logging.getLogger(__name__)


class CorrectionStrategy(Enum):
    """Korrektur-Strategien aus Konzept.md"""
    SYNONYM = "synonym"
    REFORMULATE = "reformulate"
    DELETE = "delete"
    MERGE = "merge"
    VARY_STRUCTURE = "vary"
    KEEP = "keep"


@dataclass
class CorrectionContext:
    """Kontext für eine Korrektur"""
    sentence: str
    paragraph: str
    context_before: str
    context_after: str
    chapter_id: Optional[int]
    is_dialogue: bool
    character_name: Optional[str]


@dataclass
class SynonymSuggestion:
    """Ein Synonym-Vorschlag"""
    word: str
    confidence: float
    reason: str


@dataclass
class ReformulationSuggestion:
    """Ein Umformulierungs-Vorschlag"""
    text: str
    confidence: float
    technique: str


class CorrectionService:
    """
    Haupt-Service für Korrekturvorschläge.
    
    Workflow:
    1. Genre-Profil laden (basierend auf BookProject.genre)
    2. Fehler analysieren und Strategie wählen
    3. Korrektur generieren (LLM-basiert)
    4. Validieren und speichern
    """
    
    def __init__(self, project: BookProjects):
        self.project = project
        self.genre_profile = self._load_genre_profile()
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_genre_profile(self) -> GenreStyleProfile:
        """Lädt oder erstellt Genre-Profil für das Projekt."""
        genre = (self.project.genre or 'default').lower().strip()
        
        # Versuche exaktes Match
        profile = GenreStyleProfile.objects.filter(genre__iexact=genre).first()
        
        if not profile:
            # Fallback: Erstes Wort des Genres
            first_word = genre.split()[0] if genre else 'default'
            profile = GenreStyleProfile.objects.filter(
                genre__icontains=first_word
            ).first()
        
        if not profile:
            # Default-Profil
            profile = GenreStyleProfile.objects.filter(genre='default').first()
        
        if not profile:
            # Letzter Fallback: Erstes verfügbares Profil
            profile = GenreStyleProfile.objects.first()
            
        if profile:
            logger.info(f"[CORRECTION] Using genre profile: {profile}")
        else:
            logger.warning("[CORRECTION] No genre profile found!")
            
        return profile
    
    def _load_prompt_templates(self) -> Dict[str, PromptTemplate]:
        """Lädt die Korrektur-PromptTemplates."""
        templates = {}
        for template in PromptTemplate.objects.filter(
            category='correction',
            is_active=True
        ):
            templates[template.template_key] = template
        logger.info(f"[CORRECTION] Loaded {len(templates)} prompt templates")
        return templates
    
    def process_fehler(
        self, 
        fehler: LektoratsFehler,
        generate_alternatives: bool = True,
        use_llm: bool = True
    ) -> Optional[CorrectionSuggestion]:
        """
        Verarbeitet einen einzelnen Fehler und generiert Korrekturvorschlag.
        
        Args:
            fehler: Der zu korrigierende Fehler
            generate_alternatives: Ob Alternativen generiert werden sollen
            use_llm: Ob LLM für Generierung verwendet werden soll
            
        Returns:
            CorrectionSuggestion oder None
        """
        # Prüfe ob bereits GÜLTIGE Korrektur existiert (nicht manuelle Review)
        existing = fehler.corrections.filter(
            status__in=['pending', 'accepted', 'auto'],
            confidence__gt=0.0  # Nur gültige Vorschläge, nicht manuelle Reviews
        ).first()
        if existing:
            logger.debug(f"[CORRECTION] Existing correction found for fehler {fehler.id}")
            return existing
        
        # Lösche alte manuelle Reviews (confidence=0) damit neue generiert werden können
        fehler.corrections.filter(confidence=0.0).delete()
        
        # Strategie wählen
        strategy = self._select_strategy(fehler)
        logger.info(f"[CORRECTION] Selected strategy: {strategy.value} for fehler {fehler.id}")
        
        if strategy == CorrectionStrategy.KEEP:
            # Als Stilmittel markieren
            fehler.is_intentional = True
            fehler.correction_status = 'accepted'
            fehler.save()
            return None
        
        # Kontext extrahieren
        context = self._extract_context(fehler)
        
        # Korrektur generieren
        if strategy == CorrectionStrategy.SYNONYM:
            suggestion = self._generate_synonym_correction(fehler, context, use_llm)
        elif strategy == CorrectionStrategy.REFORMULATE:
            suggestion = self._generate_reformulation(fehler, context, use_llm)
        elif strategy == CorrectionStrategy.VARY_STRUCTURE:
            suggestion = self._generate_structure_variation(fehler, context, use_llm)
        else:
            # DELETE, MERGE → Manuell
            suggestion = self._create_manual_review(fehler, context, strategy)
        
        return suggestion
    
    def _select_strategy(self, fehler: LektoratsFehler) -> CorrectionStrategy:
        """
        Wählt die beste Strategie basierend auf Fehlertyp und Genre-Profil.
        
        Implementiert den Entscheidungsbaum aus Konzept.md
        """
        # Extrahiere Fehler-Info
        beschreibung = fehler.beschreibung.lower()
        fehler_typ = fehler.fehler_typ.lower() if fehler.fehler_typ else ''
        
        # Check: Ist es ein bekanntes akzeptables Pattern?
        if self.genre_profile:
            for phrase in (self.genre_profile.acceptable_phrases or []):
                if phrase.lower() in beschreibung:
                    return CorrectionStrategy.KEEP
        
        # Wort-Wiederholung
        if 'wort' in fehler_typ or 'proximity' in fehler_typ or 'häufig' in beschreibung:
            # Bei lockerer Toleranz: Mehr behalten
            if self.genre_profile and self.genre_profile.repetition_tolerance == 'relaxed':
                # Nur bei hoher Frequenz korrigieren
                if self._extract_count(beschreibung) < 5:
                    return CorrectionStrategy.KEEP
            return CorrectionStrategy.SYNONYM
        
        # Phrasen-Wiederholung
        if 'phrase' in fehler_typ:
            if 'dialog' in beschreibung or 'sagte' in beschreibung:
                return CorrectionStrategy.VARY_STRUCTURE
            return CorrectionStrategy.REFORMULATE
        
        # Struktur-Monotonie
        if 'struktur' in fehler_typ or 'satzanfang' in beschreibung:
            return CorrectionStrategy.VARY_STRUCTURE
        
        # Dialog-Tags
        if 'sagte' in beschreibung or 'dialog' in fehler_typ:
            return CorrectionStrategy.VARY_STRUCTURE
        
        # Default: Umformulierung
        return CorrectionStrategy.REFORMULATE
    
    def _extract_count(self, text: str) -> int:
        """Extrahiert die Anzahl aus Beschreibung wie '5x' oder '10 mal'."""
        match = re.search(r'(\d+)\s*[xX×]', text)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+)\s*mal', text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0
    
    def _extract_context(self, fehler: LektoratsFehler) -> CorrectionContext:
        """Extrahiert den Kontext um den Fehler."""
        # Basis-Kontext: Originaltext oder extrahiertes Wort aus Beschreibung
        sentence = fehler.originaltext
        if not sentence and fehler.beschreibung:
            # Für Wiederholungen: Extrahiere das Wort aus "'wort' erscheint Nx"
            extracted = self._extract_word(fehler.beschreibung)
            sentence = extracted if extracted else fehler.beschreibung
        
        # Versuche Kontext aus Kapitel zu extrahieren
        context_before = ""
        context_after = ""
        chapter_id = fehler.chapter_id if fehler.chapter else None
        
        if fehler.chapter and fehler.chapter.content:
            content = fehler.chapter.content
            # Versuche Position zu finden
            if fehler.position_start and fehler.position_end:
                start = max(0, fehler.position_start - 200)
                end = min(len(content), fehler.position_end + 200)
                context_before = content[start:fehler.position_start]
                context_after = content[fehler.position_end:end]
        
        # Dialog-Erkennung
        is_dialogue = bool(re.search(r'[„"""\'](.*?)[„"""\']', sentence))
        
        return CorrectionContext(
            sentence=sentence,
            paragraph="",
            context_before=context_before,
            context_after=context_after,
            chapter_id=chapter_id,
            is_dialogue=is_dialogue,
            character_name=None
        )
    
    def _generate_synonym_correction(
        self, 
        fehler: LektoratsFehler,
        context: CorrectionContext,
        use_llm: bool = True
    ) -> Optional[CorrectionSuggestion]:
        """Generiert Synonym-basierte Korrektur."""
        
        # Extrahiere das Wort aus der Beschreibung
        word = self._extract_word(fehler.beschreibung)
        count = self._extract_count(fehler.beschreibung)
        
        if not word:
            logger.warning(f"[CORRECTION] Could not extract word from: {fehler.beschreibung}")
            return self._create_manual_review(fehler, context, CorrectionStrategy.SYNONYM)
        
        # Prüfe Genre-Profil für vordefinierte Synonyme
        suggestions = []
        if self.genre_profile and self.genre_profile.synonym_preferences:
            prefs = self.genre_profile.synonym_preferences.get(word.lower(), [])
            for i, syn in enumerate(prefs[:5]):
                suggestions.append(SynonymSuggestion(
                    word=syn,
                    confidence=0.9 - (i * 0.05),
                    reason="Genre-spezifisches Synonym"
                ))
        
        # LLM-basierte Synonyme generieren
        if use_llm and len(suggestions) < 3:
            llm_suggestions = self._generate_synonyms_llm(word, count, context)
            suggestions.extend(llm_suggestions)
        
        # Fallback: Einfache Synonyme
        if not suggestions:
            suggestions = self._get_fallback_synonyms(word)
        
        if suggestions:
            best = suggestions[0]
            
            return CorrectionSuggestion.objects.create(
                fehler=fehler,
                strategy=CorrectionStrategy.SYNONYM.value,
                original_text=word,
                suggested_text=best.word,
                alternatives=[s.word for s in suggestions[1:4]],
                confidence=best.confidence,
                context_before=context.context_before,
                context_after=context.context_after,
                chapter_id=context.chapter_id,
            )
        
        return self._create_manual_review(fehler, context, CorrectionStrategy.SYNONYM)
    
    def _generate_synonyms_llm(
        self, 
        word: str, 
        count: int, 
        context: CorrectionContext
    ) -> List[SynonymSuggestion]:
        """Generiert Synonyme via LLM."""
        template = self.prompt_templates.get('correction_synonyms_v1')
        if not template:
            logger.warning("[CORRECTION] Synonym template not found")
            return []
        
        try:
            from apps.bfagent.services.llm_client import generate_text
            
            # Baue Prompt-Variablen
            variables = {
                'word': word,
                'count': count,
                'context': context.sentence,
                'genre': self.project.genre or 'allgemein',
                'atmosphere_tone': self.project.atmosphere_tone or 'neutral',
                'target_audience': self.project.target_audience or 'Erwachsene',
                'style_instructions': self.genre_profile.style_instructions if self.genre_profile else '',
            }
            
            # Rendere Prompt
            system_prompt = template.system_prompt.format(**variables)
            user_prompt = template.user_prompt_template.format(**variables)
            
            # LLM-Aufruf
            response = generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=template.max_tokens,
                temperature=template.temperature
            )
            
            # Parse Response
            return self._parse_synonym_response(response, word)
        
        except Exception as e:
            logger.error(f"[CORRECTION] LLM error: {e}")
            return []
    
    def _extract_word(self, text: str) -> Optional[str]:
        """Extrahiert das wiederholte Wort aus der Beschreibung."""
        # Pattern 1: 'wort' mit einfachen Anführungszeichen (ASCII 39)
        match = re.search(r"'(\w+)'", text)
        if match:
            return match.group(1)
        
        # Pattern 2: "wort" mit doppelten Anführungszeichen
        match = re.search(r'"(\w+)"', text)
        if match:
            return match.group(1)
        
        # Pattern 3: Typografische Anführungszeichen (Unicode)
        match = re.search(r'[\u201E\u201C\u201A\u2018](\w+)[\u201D\u201C\u2019\u2018]', text)
        if match:
            return match.group(1)
        
        # Pattern 4: Wort XYZ erscheint/kommt
        match = re.search(r"[Ww]ort\s+['\"]?(\w+)['\"]?", text)
        if match:
            return match.group(1)
            
        return None
    
    def _parse_synonym_response(
        self, 
        response: str, 
        original: str
    ) -> List[SynonymSuggestion]:
        """Parsed LLM-Response zu Synonym-Vorschlägen."""
        suggestions = []
        
        for line in response.strip().split('\n'):
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    word = parts[0].strip('0123456789. ')
                    try:
                        confidence = float(parts[1])
                    except ValueError:
                        confidence = 0.5
                    reason = parts[2] if len(parts) > 2 else ""
                    
                    if word and word.lower() != original.lower():
                        suggestions.append(SynonymSuggestion(
                            word=word,
                            confidence=confidence,
                            reason=reason
                        ))
        
        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)
    
    def _get_fallback_synonyms(self, word: str) -> List[SynonymSuggestion]:
        """Einfache Fallback-Synonyme für häufige Wörter."""
        fallbacks = {
            # Verben - Sprechen
            'sagte': ['erwiderte', 'meinte', 'antwortete', 'bemerkte'],
            'fragte': ['erkundigte sich', 'wollte wissen', 'hakte nach'],
            'rief': ['schrie', 'brüllte', 'rief aus'],
            # Verben - Bewegung  
            'ging': ['schritt', 'wanderte', 'bewegte sich', 'lief'],
            'gehen': ['schreiten', 'wandern', 'laufen', 'spazieren'],
            'lief': ['rannte', 'eilte', 'hastete', 'spurtete'],
            'kam': ['erschien', 'traf ein', 'tauchte auf'],
            'stand': ['verharrte', 'wartete', 'befand sich'],
            # Verben - Kampf/Aktion
            'kämpfen': ['ringen', 'streiten', 'fechten', 'sich wehren'],
            'kämpfte': ['rang', 'stritt', 'focht', 'wehrte sich'],
            'ankämpfen': ['sich widersetzen', 'trotzen', 'standhalten'],
            'schlug': ['traf', 'hieb', 'prügelte'],
            # Verben - Sehen/Wahrnehmen
            'sah': ['blickte', 'schaute', 'betrachtete', 'erblickte'],
            'sehen': ['erblicken', 'wahrnehmen', 'betrachten'],
            'schaute': ['blickte', 'sah', 'beobachtete'],
            # Verben - Sein/Haben
            'war': ['schien', 'wirkte', 'erschien'],
            'hatte': ['besaß', 'verfügte über', 'hielt'],
            'wurde': ['verwandelte sich', 'entwickelte sich'],
            # Verben - Fühlen/Denken
            'fühlte': ['empfand', 'spürte', 'verspürte'],
            'dachte': ['überlegte', 'grübelte', 'sinnierte'],
            'wusste': ['ahnte', 'erkannte', 'verstand'],
            # Adjektive - Allgemein
            'groß': ['gewaltig', 'mächtig', 'beachtlich', 'riesig'],
            'klein': ['winzig', 'gering', 'bescheiden', 'zierlich'],
            'schön': ['hübsch', 'anmutig', 'prächtig', 'bezaubernd'],
            'gut': ['hervorragend', 'ausgezeichnet', 'trefflich'],
            'schlecht': ['übel', 'miserabel', 'mangelhaft'],
            'alt': ['betagt', 'erfahren', 'antik'],
            'neu': ['frisch', 'unberührt', 'modern'],
            'dunkel': ['finster', 'schwarz', 'düster', 'schattig'],
            'hell': ['licht', 'strahlend', 'leuchtend'],
            # Adverbien
            'plötzlich': ['auf einmal', 'unvermittelt', 'unerwartet', 'jäh'],
            'langsam': ['allmählich', 'gemächlich', 'bedächtig'],
            'schnell': ['rasch', 'zügig', 'flink', 'eilig'],
            'gemeinsam': ['zusammen', 'miteinander', 'vereint'],
            'wieder': ['erneut', 'abermals', 'nochmals'],
            'immer': ['stets', 'fortwährend', 'ständig'],
            'etwas': ['ein wenig', 'leicht', 'geringfügig'],
            'sehr': ['überaus', 'äußerst', 'besonders'],
            # Substantive
            'dunkelheit': ['Finsternis', 'Schwärze', 'Nacht'],
            'stadt': ['Metropole', 'Ortschaft', 'Kommune'],
            'ort': ['Platz', 'Stelle', 'Stätte', 'Standort'],
            'haus': ['Gebäude', 'Anwesen', 'Domizil', 'Heim'],
            'mann': ['Herr', 'Kerl', 'Bursche'],
            'frau': ['Dame', 'Weib', 'Person'],
            'kind': ['Junge', 'Mädchen', 'Sprössling'],
            'tag': ['Zeitpunkt', 'Moment'],
            'nacht': ['Dunkelheit', 'Finsternis', 'Abend'],
            'zeit': ['Moment', 'Augenblick', 'Periode'],
            'leben': ['Dasein', 'Existenz', 'Alltag'],
            'welt': ['Erde', 'Kosmos', 'Universum'],
            'blick': ['Ansicht', 'Perspektive', 'Sicht'],
            'festung': ['Burg', 'Bollwerk', 'Bastion', 'Zitadelle'],
            'können': ['vermögen', 'in der Lage sein', 'fähig sein'],
            'ansah': ['betrachtete', 'musterte', 'fixierte'],
        }
        
        word_lower = word.lower()
        if word_lower in fallbacks:
            return [
                SynonymSuggestion(word=syn, confidence=0.7 - (i * 0.1), reason="Fallback")
                for i, syn in enumerate(fallbacks[word_lower])
            ]
        return []
    
    def _generate_reformulation(
        self, 
        fehler: LektoratsFehler,
        context: CorrectionContext,
        use_llm: bool = True
    ) -> Optional[CorrectionSuggestion]:
        """Generiert Umformulierungs-Vorschlag."""
        
        if not use_llm:
            return self._create_manual_review(fehler, context, CorrectionStrategy.REFORMULATE)
        
        template = self.prompt_templates.get('correction_reformulate_v1')
        if not template:
            logger.warning("[CORRECTION] Reformulation template not found")
            return self._create_manual_review(fehler, context, CorrectionStrategy.REFORMULATE)
        
        try:
            from apps.bfagent.services.llm_client import generate_text
            
            # Baue Prompt-Variablen
            variables = {
                'sentence': context.sentence,
                'context_before': context.context_before or '(kein Kontext)',
                'context_after': context.context_after or '(kein Kontext)',
                'problem_description': fehler.beschreibung,
                'genre': self.project.genre or 'allgemein',
                'atmosphere_tone': self.project.atmosphere_tone or 'neutral',
                'style_instructions': self.genre_profile.style_instructions if self.genre_profile else '',
            }
            
            # Rendere Prompt
            system_prompt = template.system_prompt.format(**variables)
            user_prompt = template.user_prompt_template.format(**variables)
            
            response = generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=template.max_tokens,
                temperature=template.temperature
            )
            
            # Parse Response
            reformulations = self._parse_reformulation_response(response)
            
            if reformulations:
                best = reformulations[0]
                
                return CorrectionSuggestion.objects.create(
                    fehler=fehler,
                    strategy=CorrectionStrategy.REFORMULATE.value,
                    original_text=context.sentence,
                    suggested_text=best.text,
                    alternatives=[r.text for r in reformulations[1:3]],
                    confidence=best.confidence,
                    context_before=context.context_before,
                    context_after=context.context_after,
                    chapter_id=context.chapter_id,
                )
        
        except Exception as e:
            logger.error(f"[CORRECTION] LLM reformulation error: {e}")
        
        return self._create_manual_review(fehler, context, CorrectionStrategy.REFORMULATE)
    
    def _parse_reformulation_response(
        self, 
        response: str
    ) -> List[ReformulationSuggestion]:
        """Parsed LLM-Response zu Umformulierungs-Vorschlägen."""
        suggestions = []
        
        lines = [l.strip() for l in response.strip().split('\n') if l.strip()]
        
        for i, line in enumerate(lines):
            # Entferne Nummerierung
            text = re.sub(r'^[\d]+[.)\s]+', '', line)
            if text and len(text) > 10:
                suggestions.append(ReformulationSuggestion(
                    text=text,
                    confidence=0.8 - (i * 0.1),
                    technique="LLM-Umformulierung"
                ))
        
        return suggestions[:3]
    
    def _generate_structure_variation(
        self, 
        fehler: LektoratsFehler,
        context: CorrectionContext,
        use_llm: bool = True
    ) -> Optional[CorrectionSuggestion]:
        """Generiert Struktur-Variation (Dialog-Tags, Satzanfänge)."""
        
        # Prüfe ob es ein Dialog-Tag Problem ist
        if 'sagte' in fehler.beschreibung.lower() or 'dialog' in (fehler.fehler_typ or '').lower():
            template = self.prompt_templates.get('correction_dialog_tags_v1')
        else:
            template = self.prompt_templates.get('correction_structure_v1')
        
        if not template or not use_llm:
            return self._create_manual_review(fehler, context, CorrectionStrategy.VARY_STRUCTURE)
        
        # Fallback: Nutze Reformulierung
        return self._generate_reformulation(fehler, context, use_llm)
    
    def _create_manual_review(
        self, 
        fehler: LektoratsFehler,
        context: CorrectionContext,
        strategy: CorrectionStrategy
    ) -> CorrectionSuggestion:
        """Erstellt einen manuellen Review-Eintrag."""
        return CorrectionSuggestion.objects.create(
            fehler=fehler,
            strategy=strategy.value,
            original_text=context.sentence,
            suggested_text="[Manuelle Prüfung erforderlich]",
            alternatives=[],
            confidence=0.0,
            context_before=context.context_before,
            context_after=context.context_after,
            chapter_id=context.chapter_id,
            status=CorrectionSuggestion.Status.PENDING,
        )
    
    # === Batch-Processing ===
    
    def process_all_fehler(
        self,
        fehler_qs: Optional[QuerySet] = None,
        auto_apply_threshold: float = 0.9,
        use_llm: bool = True
    ) -> Dict[str, int]:
        """
        Verarbeitet alle Fehler einer Session.
        
        Args:
            fehler_qs: Optional QuerySet, sonst alle aus aktueller Session
            auto_apply_threshold: Ab welcher Confidence auto-anwenden
            use_llm: Ob LLM verwendet werden soll
            
        Returns:
            Statistik: {'processed': X, 'auto_applied': Y, 'manual': Z}
        """
        if fehler_qs is None:
            fehler_qs = LektoratsFehler.objects.filter(
                session__project=self.project,
                modul='wiederholungen',
                correction_status='new'
            )
        
        stats = {'processed': 0, 'auto_applied': 0, 'manual': 0, 'kept': 0, 'errors': 0}
        
        for fehler in fehler_qs:
            try:
                suggestion = self.process_fehler(fehler, use_llm=use_llm)
                stats['processed'] += 1
                
                if suggestion is None:
                    stats['kept'] += 1
                elif suggestion.confidence >= auto_apply_threshold:
                    suggestion.status = CorrectionSuggestion.Status.AUTO_APPLIED
                    suggestion.save()
                    fehler.correction_status = 'corrected'
                    fehler.save()
                    stats['auto_applied'] += 1
                else:
                    stats['manual'] += 1
            except Exception as e:
                logger.error(f"[CORRECTION] Error processing fehler {fehler.id}: {e}")
                stats['errors'] += 1
        
        logger.info(f"[CORRECTION] Batch complete: {stats}")
        return stats
    
    def get_pending_corrections(self) -> QuerySet:
        """Gibt alle ausstehenden Korrekturen zurück."""
        return CorrectionSuggestion.objects.filter(
            fehler__session__project=self.project,
            status=CorrectionSuggestion.Status.PENDING
        ).select_related('fehler', 'fehler__chapter')
    
    def apply_correction(
        self, 
        suggestion: CorrectionSuggestion,
        final_text: Optional[str] = None,
        user_note: Optional[str] = None
    ) -> bool:
        """
        Wendet eine Korrektur an.
        
        Args:
            suggestion: Die anzuwendende Korrektur
            final_text: Optional modifizierter Text
            user_note: Optionale Notiz
            
        Returns:
            True wenn erfolgreich
        """
        try:
            if final_text:
                suggestion.final_text = final_text
                suggestion.status = CorrectionSuggestion.Status.MODIFIED
            else:
                suggestion.status = CorrectionSuggestion.Status.ACCEPTED
            
            if user_note:
                suggestion.user_note = user_note
            
            suggestion.reviewed_at = timezone.now()
            suggestion.save()
            
            # Update Fehler-Status
            suggestion.fehler.correction_status = 'corrected'
            suggestion.fehler.save()
            
            return True
        except Exception as e:
            logger.error(f"[CORRECTION] Error applying correction: {e}")
            return False
    
    def reject_correction(
        self, 
        suggestion: CorrectionSuggestion,
        user_note: Optional[str] = None,
        mark_as_intentional: bool = False
    ) -> bool:
        """
        Lehnt eine Korrektur ab.
        
        Args:
            suggestion: Die abzulehnende Korrektur
            user_note: Optionale Begründung
            mark_as_intentional: Als Stilmittel markieren
            
        Returns:
            True wenn erfolgreich
        """
        try:
            suggestion.status = CorrectionSuggestion.Status.REJECTED
            if user_note:
                suggestion.user_note = user_note
            suggestion.reviewed_at = timezone.now()
            suggestion.save()
            
            # Update Fehler-Status
            if mark_as_intentional:
                suggestion.fehler.is_intentional = True
                suggestion.fehler.correction_status = 'accepted'
            else:
                suggestion.fehler.correction_status = 'ignored'
            suggestion.fehler.save()
            
            return True
        except Exception as e:
            logger.error(f"[CORRECTION] Error rejecting correction: {e}")
            return False
