"""
Lektorats-Service
=================

AI-gestützter Service für systematische Qualitätsprüfung von Manuskripten.
Implementiert das Lektorats-Pass Framework mit 5 Modulen.
"""

import json
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from django.db.models import Q

from apps.bfagent.models import BookProjects, BookChapters
from apps.writing_hub.models_lektorat import (
    LektoratsSession,
    LektoratsFehler,
    FigurenRegister,
    ZeitlinienEintrag,
    StilProfil,
    WiederholungsAnalyse,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes für AI-Responses
# =============================================================================

@dataclass
class ExtractedCharacter:
    """Extrahierte Figur aus dem Text."""
    name: str
    varianten: List[str] = field(default_factory=list)
    rolle: str = 'nebenfigur'
    alter: str = ''
    geschlecht: str = ''
    haarfarbe: str = ''
    augenfarbe: str = ''
    groesse: str = ''
    besondere_merkmale: str = ''
    herkunft: str = ''
    beruf: str = ''
    charakterzuege: str = ''
    beziehungen: List[Dict] = field(default_factory=list)
    kapitel_referenzen: List[Dict] = field(default_factory=list)


@dataclass
class CharacterInconsistency:
    """Gefundene Inkonsistenz bei einer Figur."""
    figur_name: str
    attribut: str
    wert1: str
    kapitel1: int
    wert2: str
    kapitel2: int
    severity: str = 'C'
    beschreibung: str = ''


# =============================================================================
# LektoratService - Hauptklasse
# =============================================================================

class LektoratService:
    """
    Service für AI-gestützte Lektoratsprüfung.
    """
    
    def __init__(self, session: LektoratsSession):
        self.session = session
        self.project = session.project
        self.chapters = BookChapters.objects.filter(
            project=self.project
        ).order_by('chapter_number')
        
        # LLM-Client (optional)
        self.llm_client = None
        self._init_llm_client()
    
    def _init_llm_client(self):
        """Initialisiert den LLM-Client falls verfügbar."""
        try:
            from apps.bfagent.services.llm_client import get_llm_client
            self.llm_client = get_llm_client()
        except ImportError:
            logger.warning("LLM client not available, using fallback mode")
        except Exception as e:
            logger.error(f"Error initializing LLM client: {e}")
    
    # =========================================================================
    # Modul 1: Figurenkonsistenz
    # =========================================================================
    
    def analyze_figuren(self) -> Dict[str, Any]:
        """
        Analysiert alle Kapitel auf Figuren und prüft Konsistenz.
        
        Returns:
            Dict mit figuren_count und fehler_count
        """
        logger.info(f"Starting character analysis for project {self.project.id}")
        
        # Alte Daten löschen
        self.session.fehler.filter(modul='figuren').delete()
        self.session.figuren.all().delete()
        
        # 1. Figuren aus allen Kapiteln extrahieren
        all_characters = {}
        
        for chapter in self.chapters:
            chapter_chars = self._extract_characters_from_chapter(chapter)
            
            for char in chapter_chars:
                if char.name in all_characters:
                    # Merge mit existierender Figur
                    self._merge_character_data(all_characters[char.name], char, chapter.chapter_number)
                else:
                    all_characters[char.name] = char
                    char.kapitel_referenzen.append({
                        'kapitel': chapter.chapter_number,
                        'erste_erwaehnung': True
                    })
        
        # 2. Figuren in DB speichern
        for name, char_data in all_characters.items():
            self._save_character_to_register(char_data)
        
        # 3. Inkonsistenzen prüfen
        inconsistencies = self._check_character_consistency()
        
        # 4. Fehler erstellen
        for inc in inconsistencies:
            self._create_fehler_from_inconsistency(inc)
        
        # 5. Modul-Status aktualisieren
        self.session.modul_status['figuren'] = 'completed'
        self.session.save()
        self.session.update_statistics()
        
        return {
            'figuren_count': len(all_characters),
            'fehler_count': len(inconsistencies),
        }
    
    def _extract_characters_from_chapter(self, chapter: BookChapters) -> List[ExtractedCharacter]:
        """
        Extrahiert Figuren aus einem Kapitel.
        Nutzt AI wenn verfügbar, sonst Regex-basierte Extraktion.
        """
        content = chapter.content or ''
        if not content.strip():
            return []
        
        # Versuche AI-Extraktion
        if self.llm_client:
            try:
                return self._extract_characters_with_ai(content, chapter.chapter_number)
            except Exception as e:
                logger.warning(f"AI extraction failed, using fallback: {e}")
        
        # Fallback: Regex-basierte Extraktion
        return self._extract_characters_with_regex(content, chapter.chapter_number)
    
    def _extract_characters_with_ai(self, content: str, chapter_number: int) -> List[ExtractedCharacter]:
        """AI-gestützte Figurenextraktion."""
        prompt = self._build_character_extraction_prompt(content)
        
        try:
            response = self.llm_client.generate(prompt)
            characters = self._parse_character_response(response, chapter_number)
            return characters
        except Exception as e:
            logger.error(f"AI character extraction failed: {e}")
            raise
    
    def _build_character_extraction_prompt(self, content: str) -> str:
        """Baut den Prompt für Figurenextraktion."""
        return f"""Analysiere den folgenden Textabschnitt und extrahiere alle erwähnten Figuren/Charaktere.

Für jede Figur, gib folgende Informationen zurück (wenn vorhanden):
- name: Hauptname der Figur
- varianten: Andere Namen/Spitznamen
- rolle: protagonist/antagonist/hauptfigur/nebenfigur/erwaehnt
- alter: Alter oder Altersangabe
- geschlecht: männlich/weiblich/divers
- haarfarbe: Haarfarbe wenn erwähnt
- augenfarbe: Augenfarbe wenn erwähnt
- besondere_merkmale: Auffällige Merkmale
- beruf: Beruf wenn erwähnt
- charakterzuege: Persönlichkeitsmerkmale

Antworte im JSON-Format als Liste von Objekten.

TEXT:
{content[:4000]}

JSON:"""
    
    def _parse_character_response(self, response: str, chapter_number: int) -> List[ExtractedCharacter]:
        """Parst die AI-Antwort zu ExtractedCharacter-Objekten."""
        try:
            # JSON aus Response extrahieren
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                return []
            
            data = json.loads(json_match.group())
            characters = []
            
            for item in data:
                char = ExtractedCharacter(
                    name=item.get('name', ''),
                    varianten=item.get('varianten', []),
                    rolle=item.get('rolle', 'nebenfigur'),
                    alter=item.get('alter', ''),
                    geschlecht=item.get('geschlecht', ''),
                    haarfarbe=item.get('haarfarbe', ''),
                    augenfarbe=item.get('augenfarbe', ''),
                    besondere_merkmale=item.get('besondere_merkmale', ''),
                    beruf=item.get('beruf', ''),
                    charakterzuege=item.get('charakterzuege', ''),
                )
                
                # Kapitel-Referenz hinzufügen
                for attr in ['alter', 'haarfarbe', 'augenfarbe', 'geschlecht']:
                    val = getattr(char, attr)
                    if val:
                        char.kapitel_referenzen.append({
                            'kapitel': chapter_number,
                            'attribut': attr,
                            'wert': val,
                        })
                
                if char.name:
                    characters.append(char)
            
            return characters
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            return []
    
    # Blacklist für deutsche Wörter die keine Namen sind
    GERMAN_NON_NAMES = {
        # Grußformeln und Ausdrücke
        'Danke', 'Bitte', 'Hallo', 'Tschüss', 'Guten', 'Morgen', 'Abend', 'Nacht',
        'Ja', 'Nein', 'Gut', 'Schlecht', 'Okay', 'Also', 'Ach', 'Oh', 'Ah',
        # Häufige Substantive die groß geschrieben werden
        'Mama', 'Papa', 'Oma', 'Opa', 'Tante', 'Onkel', 'Vater', 'Mutter',
        'Bruder', 'Schwester', 'Kind', 'Kinder', 'Mann', 'Frau', 'Junge', 'Mädchen',
        # Adverbien und Konjunktionen am Satzanfang
        'Aber', 'Oder', 'Und', 'Denn', 'Weil', 'Wenn', 'Dann', 'Dort', 'Hier',
        'Heute', 'Gestern', 'Morgen', 'Jetzt', 'Später', 'Früher', 'Bald',
        # Verben im Imperativ
        'Komm', 'Geh', 'Schau', 'Hör', 'Warte', 'Bleib', 'Nimm', 'Gib',
        # Pronomen und Artikel
        'Sie', 'Er', 'Es', 'Wir', 'Ihr', 'Das', 'Die', 'Der', 'Ein', 'Eine',
        # Andere häufige Wörter
        'Nichts', 'Alles', 'Etwas', 'Jemand', 'Niemand', 'Keiner', 'Beide',
        'Viele', 'Wenige', 'Einige', 'Manche', 'Alle', 'Keine',
        'Herr', 'Frau', 'Doktor', 'Professor', 'König', 'Königin', 'Prinz', 'Prinzessin',
        # Emotionen und Zustände
        'Angst', 'Freude', 'Trauer', 'Wut', 'Liebe', 'Hass', 'Hoffnung', 'Zweifel',
        # Weitere Substantive
        'Zeit', 'Platz', 'Haus', 'Zimmer', 'Tür', 'Fenster', 'Weg', 'Straße',
        'Stadt', 'Land', 'Welt', 'Himmel', 'Erde', 'Wasser', 'Feuer', 'Luft',
    }
    
    def _extract_characters_with_regex(self, content: str, chapter_number: int) -> List[ExtractedCharacter]:
        """
        Fallback: Regex-basierte Figurenextraktion.
        Findet Eigennamen durch Heuristiken.
        """
        characters = []
        
        # Pattern für deutsche Eigennamen
        name_patterns = [
            # Anrede + Name (sehr zuverlässig)
            r'(?:Herr|Frau|Dr\.|Prof\.|Doktor|Professor)\s+([A-ZÄÖÜ][a-zäöüß]+)',
            # Dialog-Attribution (Name nach Verb)
            r'(?:sagte|fragte|rief|flüsterte|meinte|antwortete|erwiderte|murmelte|schrie|brüllte|seufzte|lachte)\s+([A-ZÄÖÜ][a-zäöüß]{2,})',
            # Possessiv-Konstruktionen (Marias Augen, Toms Stimme)
            r'([A-ZÄÖÜ][a-zäöüß]{2,})s\s+(?:Augen|Stimme|Hand|Gesicht|Herz|Kopf|Blick|Lächeln)',
            # Direkte Anrede im Dialog
            r'[„"»](?:Hallo|Hey|Na),?\s+([A-ZÄÖÜ][a-zäöüß]{2,})[!?.,]',
        ]
        
        found_names = set()
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            found_names.update(matches)
        
        # Für jeden gefundenen Namen eine Figur erstellen
        for name in found_names:
            # Filter: Mindestlänge 3, nicht in Blacklist, nicht nur Großbuchstaben
            if (len(name) >= 3 and 
                name not in self.GERMAN_NON_NAMES and
                not name.isupper() and
                self._is_likely_name(name)):
                char = ExtractedCharacter(name=name)
                char.kapitel_referenzen.append({
                    'kapitel': chapter_number,
                    'erste_erwaehnung': True
                })
                characters.append(char)
        
        return characters
    
    def _is_likely_name(self, word: str) -> bool:
        """
        Prüft ob ein Wort wahrscheinlich ein Name ist.
        """
        # Zu lang für typische Namen
        if len(word) > 20:
            return False
        
        # Enthält Ziffern
        if any(c.isdigit() for c in word):
            return False
        
        # Endet auf typische Nicht-Namen-Endungen
        non_name_endings = ('ung', 'heit', 'keit', 'schaft', 'tum', 'nis', 'sal', 'chen', 'lein')
        if word.lower().endswith(non_name_endings):
            return False
        
        # Typische Namen-Endungen (erhöht Konfidenz)
        name_endings = ('a', 'e', 'i', 'o', 'y', 'n', 's', 'r', 'l', 'k', 'd', 't')
        
        return True
    
    def _merge_character_data(self, existing: ExtractedCharacter, new: ExtractedCharacter, chapter_number: int):
        """Merged neue Daten in existierende Figur."""
        # Varianten erweitern
        for var in new.varianten:
            if var not in existing.varianten:
                existing.varianten.append(var)
        
        # Attribute übernehmen wenn nicht vorhanden
        for attr in ['alter', 'geschlecht', 'haarfarbe', 'augenfarbe', 'beruf', 'charakterzuege']:
            new_val = getattr(new, attr)
            existing_val = getattr(existing, attr)
            
            if new_val:
                if existing_val and existing_val != new_val:
                    # Potenzielle Inkonsistenz - als Referenz speichern
                    existing.kapitel_referenzen.append({
                        'kapitel': chapter_number,
                        'attribut': attr,
                        'wert': new_val,
                        'konflikt': True
                    })
                elif not existing_val:
                    setattr(existing, attr, new_val)
                    existing.kapitel_referenzen.append({
                        'kapitel': chapter_number,
                        'attribut': attr,
                        'wert': new_val,
                    })
    
    def _save_character_to_register(self, char: ExtractedCharacter):
        """Speichert eine extrahierte Figur ins Register."""
        # Erste und letzte Erwähnung ermitteln
        kapitel_nummern = [ref['kapitel'] for ref in char.kapitel_referenzen]
        erste = min(kapitel_nummern) if kapitel_nummern else None
        letzte = max(kapitel_nummern) if kapitel_nummern else None
        
        figur, created = FigurenRegister.objects.update_or_create(
            session=self.session,
            name=char.name,
            defaults={
                'name_varianten': char.varianten,
                'rolle': char.rolle,
                'erste_erwaehnung_kapitel': erste,
                'letzte_erwaehnung_kapitel': letzte,
                'alter': char.alter,
                'geschlecht': char.geschlecht,
                'haarfarbe': char.haarfarbe,
                'augenfarbe': char.augenfarbe,
                'besondere_merkmale': char.besondere_merkmale,
                'herkunft': char.herkunft,
                'beruf': char.beruf,
                'charakterzuege': char.charakterzuege,
                'beziehungen': char.beziehungen,
                'kapitel_referenzen': char.kapitel_referenzen,
                'ai_extrahiert': self.llm_client is not None,
            }
        )
        
        return figur
    
    def _check_character_consistency(self) -> List[CharacterInconsistency]:
        """Prüft alle Figuren auf Inkonsistenzen."""
        inconsistencies = []
        
        for figur in self.session.figuren.all():
            # Attribute mit Kapitel-Werten sammeln
            attr_values = {}
            
            for ref in figur.kapitel_referenzen:
                attr = ref.get('attribut')
                wert = ref.get('wert')
                kapitel = ref.get('kapitel')
                
                if attr and wert and kapitel:
                    if attr not in attr_values:
                        attr_values[attr] = []
                    attr_values[attr].append({
                        'wert': wert,
                        'kapitel': kapitel
                    })
            
            # Auf Widersprüche prüfen
            for attr, values in attr_values.items():
                unique_values = set(v['wert'] for v in values)
                if len(unique_values) > 1:
                    # Inkonsistenz gefunden
                    sorted_values = sorted(values, key=lambda x: x['kapitel'])
                    inc = CharacterInconsistency(
                        figur_name=figur.name,
                        attribut=attr,
                        wert1=sorted_values[0]['wert'],
                        kapitel1=sorted_values[0]['kapitel'],
                        wert2=sorted_values[-1]['wert'],
                        kapitel2=sorted_values[-1]['kapitel'],
                        severity=self._determine_severity(attr),
                        beschreibung=f"{figur.name}: {attr} ändert sich von '{sorted_values[0]['wert']}' (Kap. {sorted_values[0]['kapitel']}) zu '{sorted_values[-1]['wert']}' (Kap. {sorted_values[-1]['kapitel']})"
                    )
                    inconsistencies.append(inc)
        
        return inconsistencies
    
    def _determine_severity(self, attribute: str) -> str:
        """Bestimmt Schweregrad basierend auf Attribut."""
        critical_attrs = ['geschlecht', 'name']
        severe_attrs = ['alter', 'augenfarbe', 'haarfarbe']
        medium_attrs = ['beruf', 'herkunft']
        
        if attribute in critical_attrs:
            return 'A'
        elif attribute in severe_attrs:
            return 'B'
        elif attribute in medium_attrs:
            return 'C'
        else:
            return 'D'
    
    def _create_fehler_from_inconsistency(self, inc: CharacterInconsistency):
        """Erstellt einen LektoratsFehler aus einer Inkonsistenz."""
        # Kapitel-Objekte holen
        chapter1 = self.chapters.filter(chapter_number=inc.kapitel1).first()
        chapter2 = self.chapters.filter(chapter_number=inc.kapitel2).first()
        
        LektoratsFehler.objects.create(
            session=self.session,
            chapter=chapter1,
            modul='figuren',
            severity=inc.severity,
            fehler_typ='Attribut-Inkonsistenz',
            beschreibung=inc.beschreibung,
            originaltext=f"Kap. {inc.kapitel1}: {inc.attribut} = '{inc.wert1}'",
            korrekturvorschlag=f"Einheitlich '{inc.wert1}' oder '{inc.wert2}' verwenden",
            erklaerung=f"Das Attribut '{inc.attribut}' von {inc.figur_name} hat verschiedene Werte in unterschiedlichen Kapiteln.",
            querverweis_kapitel=chapter2,
            querverweis_text=f"Kap. {inc.kapitel2}: {inc.attribut} = '{inc.wert2}'",
            ai_erkannt=True,
            ai_konfidenz=0.85,
        )
    
    # =========================================================================
    # Modul 2: Stilkonsistenz
    # =========================================================================
    
    def analyze_stil(self) -> Dict[str, Any]:
        """
        Analysiert Stilkonsistenz (Perspektive, Tempus, Tonalität).
        """
        logger.info(f"Starting style analysis for project {self.project.id}")
        
        # Alte Daten löschen
        self.session.fehler.filter(modul='stil').delete()
        # StilProfil ist OneToOne, daher anders löschen
        if hasattr(self.session, 'stil_profil') and self.session.stil_profil:
            self.session.stil_profil.delete()
        
        fehler_count = 0
        stil_profil = getattr(self.session, 'stil_profil', None)
        if not stil_profil:
            stil_profil = StilProfil.objects.create(session=self.session)
        
        # Perspektive und Tempus pro Kapitel analysieren
        chapter_styles = {}
        for chapter in self.chapters:
            if not chapter.content:
                continue
            
            style = self._analyze_chapter_style(chapter)
            chapter_styles[chapter.chapter_number] = style
            
            # Erste Kapitel als Referenz verwenden
            if not stil_profil.perspektive and style.get('perspektive'):
                stil_profil.perspektive = style['perspektive']
            if not stil_profil.tempus and style.get('tempus'):
                stil_profil.tempus = style['tempus']
        
        # Inkonsistenzen finden
        for chapter_num, style in chapter_styles.items():
            chapter = self.chapters.filter(chapter_number=chapter_num).first()
            
            # Perspektiven-Wechsel prüfen
            if stil_profil.perspektive and style.get('perspektive'):
                if style['perspektive'] != stil_profil.perspektive:
                    perspektive_map = {
                        'ich': 'Ich-Erzähler',
                        'er_sie': 'Er/Sie-Erzähler',
                        'du': 'Du-Erzähler',
                        'wir': 'Wir-Erzähler'
                    }
                    erwartet_display = perspektive_map.get(stil_profil.perspektive, stil_profil.perspektive)
                    gefunden_display = perspektive_map.get(style['perspektive'], style['perspektive'])
                    self._create_style_fehler(
                        chapter=chapter,
                        fehler_typ='Perspektiven-Wechsel',
                        beschreibung=f"Kapitel {chapter_num} verwendet {gefunden_display}, erwartet: {erwartet_display}",
                        severity='B',
                        korrekturvorschlag=f"Ändere die Erzählperspektive in Kapitel {chapter_num} von '{gefunden_display}' zu '{erwartet_display}'. Prüfe alle Pronomen und Verben auf konsistente Perspektive."
                    )
                    fehler_count += 1
            
            # Tempus-Wechsel prüfen
            if stil_profil.tempus and style.get('tempus'):
                if style['tempus'] != stil_profil.tempus:
                    tempus_map = {
                        'praesens': 'Präsens',
                        'praeteritum': 'Präteritum',
                        'gemischt': 'gemischtes Tempus'
                    }
                    erwartet_display = tempus_map.get(stil_profil.tempus, stil_profil.tempus)
                    gefunden_display = tempus_map.get(style['tempus'], style['tempus'])
                    self._create_style_fehler(
                        chapter=chapter,
                        fehler_typ='Tempus-Wechsel',
                        beschreibung=f"Kapitel {chapter_num} verwendet {gefunden_display}, erwartet: {erwartet_display}",
                        severity='C',
                        korrekturvorschlag=f"Korrigiere die Zeitform in Kapitel {chapter_num} von '{gefunden_display}' zu '{erwartet_display}'. Achte besonders auf Verben und überprüfe die gesamte Erzählzeit."
                    )
                    fehler_count += 1
        
        stil_profil.ai_analysiert = True
        stil_profil.save()
        
        # Keine Info-Meldung als Fehler erstellen - das verwirrt nur
        
        self.session.modul_status['stil'] = 'completed'
        self.session.save()
        self.session.update_statistics()
        
        return {'fehler_count': fehler_count}
    
    def _analyze_chapter_style(self, chapter: BookChapters) -> Dict[str, str]:
        """Analysiert den Stil eines Kapitels."""
        content = chapter.content[:2000] if chapter.content else ''
        
        # Perspektive erkennen
        perspektive = self._detect_perspective(content)
        
        # Tempus erkennen
        tempus = self._detect_tense(content)
        
        return {
            'perspektive': perspektive,
            'tempus': tempus,
        }
    
    def _detect_perspective(self, content: str) -> str:
        """Erkennt die Erzählperspektive."""
        # Ich-Erzähler Marker
        ich_markers = len(re.findall(r'\b(ich|mir|mich|mein|meine|meiner)\b', content, re.IGNORECASE))
        
        # Er/Sie-Erzähler Marker
        er_sie_markers = len(re.findall(r'\b(er|sie|ihm|ihr|sein|seine|ihrer)\b', content, re.IGNORECASE))
        
        # Du-Erzähler (selten)
        du_markers = len(re.findall(r'\b(du|dir|dich|dein|deine)\b', content, re.IGNORECASE))
        
        total = ich_markers + er_sie_markers + du_markers
        if total == 0:
            return ''
        
        if ich_markers / total > 0.3:
            return 'ich'
        elif du_markers / total > 0.3:
            return 'du'
        else:
            return 'er_sie'
    
    def _detect_tense(self, content: str) -> str:
        """Erkennt das dominante Tempus."""
        # Präsens-Marker (deutsche Verben im Präsens)
        praesens_patterns = r'\b(ist|sind|hat|haben|geht|kommt|sagt|fragt|sieht|macht)\b'
        praesens_count = len(re.findall(praesens_patterns, content, re.IGNORECASE))
        
        # Präteritum-Marker
        praeteritum_patterns = r'\b(war|waren|hatte|hatten|ging|kam|sagte|fragte|sah|machte)\b'
        praeteritum_count = len(re.findall(praeteritum_patterns, content, re.IGNORECASE))
        
        if praesens_count > praeteritum_count * 1.5:
            return 'praesens'
        elif praeteritum_count > praesens_count * 1.5:
            return 'praeteritum'
        else:
            return 'gemischt'
    
    def _create_style_fehler(self, chapter, fehler_typ: str, beschreibung: str, severity: str, 
                              korrekturvorschlag: str = '', originaltext: str = ''):
        """Erstellt einen Stil-Fehler."""
        LektoratsFehler.objects.create(
            session=self.session,
            chapter=chapter,
            modul='stil',
            severity=severity,
            fehler_typ=fehler_typ,
            beschreibung=beschreibung,
            korrekturvorschlag=korrekturvorschlag,
            originaltext=originaltext,
            ai_erkannt=True,
            ai_konfidenz=0.75,
        )
    
    # =========================================================================
    # Modul 3: Handlungslogik
    # =========================================================================
    
    def analyze_logik(self) -> Dict[str, Any]:
        """
        Analysiert Handlungslogik und findet Plotlöcher.
        """
        logger.info(f"Starting logic analysis for project {self.project.id}")
        
        # Alte Daten löschen
        self.session.fehler.filter(modul='logik').delete()
        
        fehler_count = 0
        
        # Objekte und Zustände über Kapitel tracken
        object_states = {}  # {objekt: [(kapitel, zustand)]}
        
        for chapter in self.chapters:
            if not chapter.content:
                continue
            
            # Objekt-Zustände aus diesem Kapitel extrahieren
            states = self._extract_object_states(chapter)
            
            for obj, state in states.items():
                if obj not in object_states:
                    object_states[obj] = []
                object_states[obj].append((chapter.chapter_number, state))
        
        # Auf logische Widersprüche prüfen
        for obj, states in object_states.items():
            if len(states) < 2:
                continue
            
            # Auf Widersprüche prüfen
            for i in range(len(states) - 1):
                kap1, state1 = states[i]
                kap2, state2 = states[i + 1]
                
                if self._is_contradiction(state1, state2):
                    chapter = self.chapters.filter(chapter_number=kap2).first()
                    LektoratsFehler.objects.create(
                        session=self.session,
                        chapter=chapter,
                        modul='logik',
                        severity='B',
                        fehler_typ='Logischer Widerspruch',
                        beschreibung=f"'{obj.capitalize()}' hat widersprüchliche Zustände zwischen Kapitel {kap1} und {kap2}.",
                        originaltext=f"Kapitel {kap1}: '{obj}' ist '{state1}'\nKapitel {kap2}: '{obj}' ist '{state2}'",
                        korrekturvorschlag=f"Überprüfe den Zustand von '{obj}' in beiden Kapiteln und stelle sicher, dass die Änderung erklärt wird oder korrigiere den Widerspruch.",
                        ai_erkannt=True,
                        ai_konfidenz=0.7,
                    )
                    fehler_count += 1
        
        # Keine Info-Meldung als Fehler erstellen - das verwirrt nur
        
        self.session.modul_status['logik'] = 'completed'
        self.session.save()
        self.session.update_statistics()
        
        return {'fehler_count': fehler_count}
    
    def _extract_object_states(self, chapter: BookChapters) -> Dict[str, str]:
        """Extrahiert Objekt-Zustände aus einem Kapitel."""
        content = chapter.content or ''
        states = {}
        
        # Einfache Muster für Zustandsänderungen
        # z.B. "Die Tür war offen", "Das Schwert war zerbrochen"
        patterns = [
            r'(die|das|der)\s+(\w+)\s+war\s+(offen|geschlossen|kaputt|heil|zerbrochen|ganz)',
            r'(\w+)\s+(starb|lebte|verschwand|erschien)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    obj = match[1] if len(match) > 2 else match[0]
                    state = match[-1]
                    states[obj.lower()] = state.lower()
        
        return states
    
    def _is_contradiction(self, state1: str, state2: str) -> bool:
        """Prüft ob zwei Zustände sich widersprechen."""
        contradictions = {
            ('offen', 'geschlossen'),
            ('kaputt', 'heil'),
            ('zerbrochen', 'ganz'),
            ('tot', 'lebendig'),
            ('starb', 'lebte'),
        }
        
        for s1, s2 in contradictions:
            if (state1 == s1 and state2 == s2) or (state1 == s2 and state2 == s1):
                return True
        
        return False
    
    # =========================================================================
    # Modul 4: Wiederholungen
    # =========================================================================
    
    def analyze_wiederholungen(self, analysis_level: str = 'standard') -> Dict[str, Any]:
        """
        Analysiert Wort- und Phrasenwiederholungen mit dem RepetitionAnalyzer.
        
        Args:
            analysis_level: 'basic', 'standard', 'advanced', 'full'
            
        Fokus auf:
        1. Proximity-Wiederholungen (gleiches Wort innerhalb kurzer Distanz)
        2. Übermäßig genutzte Füllwörter
        3. Wiederholte Phrasen (3+ Wörter, nicht trivial)
        4. Lexikalische Diversität (MTLD)
        """
        import sys
        print("[LEKTORAT DEBUG] Importing RepetitionAnalyzer...", file=sys.stderr, flush=True)
        from .repetition_analyzer import RepetitionAnalyzer, get_config
        print(f"[LEKTORAT DEBUG] Import OK, creating analyzer with level={analysis_level}", file=sys.stderr, flush=True)
        
        logger.info(f"[WIEDERHOLUNGEN] Starting analysis for project {self.project.id} (level={analysis_level})")
        
        # Alte Daten löschen
        self.session.fehler.filter(modul='wiederholungen').delete()
        self.session.wiederholungen.all().delete()
        
        fehler_count = 0
        
        # Charakternamen aus dem Projekt extrahieren (werden ignoriert)
        character_names = []
        try:
            figuren = self.session.figuren.all()
            for figur in figuren:
                character_names.append(figur.name)
                for var in (figur.name_varianten or []):
                    character_names.append(var)
        except:
            pass
        
        # Kapitel-Daten sammeln
        chapters_content = {}
        for chapter in self.chapters:
            if chapter.content:
                chapters_content[chapter.chapter_number] = chapter.content
        
        if not chapters_content:
            logger.warning("No chapter content found")
            self.session.modul_status['wiederholungen'] = 'completed'
            self.session.save()
            return {'fehler_count': 0, 'analysen_count': 0}
        
        # RepetitionAnalyzer verwenden
        config = get_config(profile='normal', analysis_level=analysis_level)
        analyzer = RepetitionAnalyzer(config=config)
        
        results = analyzer.analyze(chapters_content, character_names=character_names)
        
        logger.info(f"[WIEDERHOLUNGEN] Analyzer: {results['total_words']} words, {results['total_chapters']} chapters")
        
        # 1. PROXIMITY-ERGEBNISSE speichern
        for item in results.get('proximity_issues', []):
            WiederholungsAnalyse.objects.create(
                session=self.session,
                typ='proximity',
                text=item.word,
                anzahl=item.frequency,
                vorkommen=item.chapters,
                bewertung='warnung' if item.severity == 'HIGH' else 'hinweis',
                bewertung_notiz=f"Wort erscheint {item.frequency}x in kurzem Abstand",
                ai_erkannt=True,
            )
            
            if item.severity == 'HIGH':
                LektoratsFehler.objects.create(
                    session=self.session,
                    modul='wiederholungen',
                    severity='C',
                    fehler_typ='Proximity-Wiederholung',
                    beschreibung=f"'{item.word}' erscheint {item.frequency}x in kurzem Abstand",
                    ai_erkannt=True,
                    ai_konfidenz=0.85,
                )
                fehler_count += 1
        
        # 2. FÜLLWORT-ERGEBNISSE speichern
        for item in results.get('filler_words', []):
            WiederholungsAnalyse.objects.create(
                session=self.session,
                typ='fuellwort',
                text=item.word,
                anzahl=item.frequency,
                bewertung='warnung' if item.severity in ['HIGH', 'MEDIUM'] else 'hinweis',
                bewertung_notiz=f"Füllwort: {item.frequency}x ({item.score:.2f}%)",
                ai_erkannt=True,
            )
            
            if item.severity == 'HIGH':
                LektoratsFehler.objects.create(
                    session=self.session,
                    modul='wiederholungen',
                    severity='D',
                    fehler_typ='Füllwort-Übernutzung',
                    beschreibung=f"'{item.word}' wird {item.frequency}x verwendet",
                    ai_erkannt=True,
                    ai_konfidenz=0.9,
                )
                fehler_count += 1
        
        # 3. PHRASEN-ERGEBNISSE speichern
        for item in results.get('phrase_repetitions', []):
            WiederholungsAnalyse.objects.create(
                session=self.session,
                typ='phrase',
                text=item.phrase,
                anzahl=item.frequency,
                bewertung='warnung' if item.severity in ['HIGH', 'MEDIUM'] else 'hinweis',
                ai_erkannt=True,
            )
            
            if item.severity == 'HIGH':
                LektoratsFehler.objects.create(
                    session=self.session,
                    modul='wiederholungen',
                    severity='D',
                    fehler_typ='Phrasen-Wiederholung',
                    beschreibung=f"'{item.phrase}' erscheint {item.frequency}x im Text",
                    ai_erkannt=True,
                    ai_konfidenz=0.8,
                )
                fehler_count += 1
        
        # 4. ÜBERNUTZTE WÖRTER speichern
        for item in results.get('word_repetitions', []):
            WiederholungsAnalyse.objects.create(
                session=self.session,
                typ='wort',
                text=item.word,
                anzahl=item.frequency,
                vorkommen=item.chapters,
                bewertung='warnung',
                bewertung_notiz=f"{item.frequency}x ({item.score:.2f}%)",
                ai_erkannt=True,
            )
            
            LektoratsFehler.objects.create(
                session=self.session,
                modul='wiederholungen',
                severity='C',
                fehler_typ='Wort-Übernutzung',
                beschreibung=f"'{item.word}' wird {item.frequency}x verwendet",
                ai_erkannt=True,
                ai_konfidenz=0.85,
            )
            fehler_count += 1
        
        # 5. DIVERSITÄT als Info speichern (wenn berechnet)
        diversity = results.get('diversity')
        logger.info(f"[WIEDERHOLUNGEN] Diversity: {diversity}")
        
        if diversity and diversity.mtld > 0:
            severity_map = {'CRITICAL': 'B', 'WARNING': 'C', 'OK': 'E'}
            LektoratsFehler.objects.create(
                session=self.session,
                modul='wiederholungen',
                severity=severity_map.get(diversity.severity, 'E'),
                fehler_typ='Lexikalische Diversität',
                beschreibung=diversity.assessment,
                ai_erkannt=True,
                ai_konfidenz=0.95,
            )
            if diversity.severity in ['CRITICAL', 'WARNING']:
                fehler_count += 1
        
        # Zusammenfassung
        analysen_count = self.session.wiederholungen.count()
        logger.info(f"[WIEDERHOLUNGEN] Complete: {analysen_count} Wiederholungen, {fehler_count} Fehler")
        
        # Keine Info-Meldung als Fehler erstellen - das verwirrt nur
        
        self.session.modul_status['wiederholungen'] = 'completed'
        self.session.save()
        self.session.update_statistics()
        
        return {'fehler_count': fehler_count, 'analysen_count': analysen_count}
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenisiert Text in Wörter."""
        # Einfache Tokenisierung
        words = re.findall(r'\b[a-zäöüßA-ZÄÖÜ]+\b', text)
        return words
    
    def _count_words(self, words: List[str]) -> Dict[str, int]:
        """Zählt Wort-Häufigkeiten."""
        counts = {}
        for word in words:
            word_lower = word.lower()
            counts[word_lower] = counts.get(word_lower, 0) + 1
        return counts
    
    def _find_repeated_phrases(self, words: List[str]) -> Dict[str, int]:
        """Findet wiederholte Phrasen (2-4 Wörter)."""
        phrases = {}
        
        # 2-Wort-Phrasen
        for i in range(len(words) - 1):
            phrase = f"{words[i].lower()} {words[i+1].lower()}"
            if len(phrase) > 10:  # Mindestlänge
                phrases[phrase] = phrases.get(phrase, 0) + 1
        
        # 3-Wort-Phrasen
        for i in range(len(words) - 2):
            phrase = f"{words[i].lower()} {words[i+1].lower()} {words[i+2].lower()}"
            if len(phrase) > 15:
                phrases[phrase] = phrases.get(phrase, 0) + 1
        
        # Nur Phrasen mit mindestens 3 Vorkommen
        return {k: v for k, v in phrases.items() if v >= 3}
    
    def _find_meaningful_phrases(self, words: List[str], stopwords: set) -> Dict[str, int]:
        """
        Findet bedeutungsvolle wiederholte Phrasen (3+ Wörter).
        Filtert Phrasen die nur aus Stopwords bestehen.
        """
        phrases = {}
        
        # Nur 3-Wort-Phrasen (aussagekräftiger)
        for i in range(len(words) - 2):
            w1, w2, w3 = words[i].lower(), words[i+1].lower(), words[i+2].lower()
            
            # Mindestens ein Wort muss kein Stopword sein
            non_stop_count = sum(1 for w in [w1, w2, w3] if w not in stopwords and len(w) >= 4)
            if non_stop_count < 1:
                continue
            
            phrase = f"{w1} {w2} {w3}"
            if len(phrase) >= 12:  # Mindestlänge
                phrases[phrase] = phrases.get(phrase, 0) + 1
        
        # Nur Phrasen mit mindestens 5 Vorkommen
        return {k: v for k, v in phrases.items() if v >= 5}
    
    # =========================================================================
    # Modul 5: Zeitlinien-Analyse
    # =========================================================================
    
    def analyze_zeitlinien(self) -> Dict[str, Any]:
        """
        Analysiert Zeitmarker und chronologische Konsistenz.
        """
        logger.info(f"Starting timeline analysis for project {self.project.id}")
        
        # Alte Daten löschen
        self.session.fehler.filter(modul='zeitlinien').delete()
        self.session.zeitlinien.all().delete()
        
        fehler_count = 0
        timeline_entries = []
        
        for chapter in self.chapters:
            if not chapter.content:
                continue
            
            # Zeitmarker aus Kapitel extrahieren
            markers = self._extract_time_markers(chapter)
            timeline_entries.extend(markers)
        
        # Auf chronologische Inkonsistenzen prüfen
        sorted_entries = sorted(timeline_entries, key=lambda x: (x['chapter'], x.get('sequence', 0)))
        
        last_day = None
        for entry in sorted_entries:
            if entry.get('day') is not None:
                if last_day is not None and entry['day'] < last_day:
                    # Zeitsprung rückwärts gefunden
                    chapter = self.chapters.filter(chapter_number=entry['chapter']).first()
                    LektoratsFehler.objects.create(
                        session=self.session,
                        chapter=chapter,
                        modul='zeitlinien',
                        severity='C',
                        fehler_typ='Zeitsprung rückwärts',
                        beschreibung=f"Kapitel {entry['chapter']}: Zeitmarker '{entry['text']}' springt zurück (Tag {entry['day']} nach Tag {last_day})",
                        ai_erkannt=True,
                        ai_konfidenz=0.7,
                    )
                    fehler_count += 1
                last_day = entry['day']
            
            # Eintrag speichern
            ZeitlinienEintrag.objects.create(
                session=self.session,
                chapter=self.chapters.filter(chapter_number=entry['chapter']).first(),
                beschreibung=entry['text'],
                zeit_typ=entry.get('type', 'unbestimmt'),
                tag_nummer=entry.get('day'),
                reihenfolge=entry.get('sequence', 0),
                ai_extrahiert=True,
            )
        
        self.session.modul_status['zeitlinien'] = 'completed'
        self.session.save()
        self.session.update_statistics()
        
        return {'fehler_count': fehler_count, 'entries_count': len(timeline_entries)}
    
    def _extract_time_markers(self, chapter: BookChapters) -> List[Dict]:
        """Extrahiert Zeitmarker aus einem Kapitel."""
        content = chapter.content or ''
        markers = []
        sequence = 0
        
        # Tageszeit-Muster
        tageszeit_patterns = [
            (r'am\s+(Morgen|Mittag|Abend|Nachmittag)', 'tageszeit'),
            (r'in\s+der\s+(Nacht|Frühe|Dämmerung)', 'tageszeit'),
            (r'(morgens|mittags|abends|nachts)', 'tageszeit'),
        ]
        
        # Relative Zeitangaben
        relativ_patterns = [
            (r'(am nächsten Tag|am folgenden Tag|einen Tag später)', 'relativ', 1),
            (r'(zwei Tage später|nach zwei Tagen)', 'relativ', 2),
            (r'(eine Woche später|nach einer Woche)', 'relativ', 7),
            (r'(am selben Tag|noch am gleichen Tag)', 'relativ', 0),
            (r'(am Vortag|tags zuvor)', 'relativ', -1),
        ]
        
        # Absolute Zeitangaben (Monate, Jahre)
        absolut_patterns = [
            (r'im\s+(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)', 'monat'),
            (r'im\s+(Frühling|Sommer|Herbst|Winter)', 'jahreszeit'),
        ]
        
        for pattern, zeit_typ in tageszeit_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                sequence += 1
                markers.append({
                    'chapter': chapter.chapter_number,
                    'text': match.group(0),
                    'type': zeit_typ,
                    'sequence': sequence,
                })
        
        for pattern, zeit_typ, day_delta in relativ_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                sequence += 1
                markers.append({
                    'chapter': chapter.chapter_number,
                    'text': match.group(0),
                    'type': zeit_typ,
                    'day': day_delta,
                    'sequence': sequence,
                })
        
        return markers
    
    # =========================================================================
    # KI-Korrektur
    # =========================================================================
    
    def ai_correct_error(self, fehler: LektoratsFehler) -> Dict[str, Any]:
        """
        Korrigiert einen Fehler automatisch mit KI.
        
        Args:
            fehler: Der zu korrigierende Fehler
            
        Returns:
            Dict mit success, diff_html, summary
        """
        if not fehler.chapter:
            return {'success': False, 'error': 'Kein Kapitel zugeordnet'}
        
        chapter = fehler.chapter
        original_content = chapter.content or ''
        
        if not original_content:
            return {'success': False, 'error': 'Kapitel hat keinen Inhalt'}
        
        # LLM für Korrektur verwenden
        from apps.bfagent.services.llm_client import generate_text, LlmRequest
        from apps.bfagent.models import Llms
        
        # Standard-LLM holen
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            return {'success': False, 'error': 'Kein aktives LLM konfiguriert'}
        
        # Korrektur-Prompt erstellen
        if fehler.fehler_typ == 'Perspektiven-Wechsel':
            prompt = self._build_perspective_correction_prompt(fehler, chapter)
        elif fehler.fehler_typ == 'Tempus-Wechsel':
            prompt = self._build_tense_correction_prompt(fehler, chapter)
        else:
            prompt = self._build_generic_correction_prompt(fehler, chapter)
        
        try:
            request = LlmRequest(
                provider=llm.provider,
                api_endpoint=llm.api_endpoint,
                api_key=llm.api_key,
                model=llm.llm_name,
                system="Du bist ein professioneller Lektor. Korrigiere den Text gemäß den Anweisungen. Gib NUR den korrigierten Text zurück, keine Erklärungen.",
                prompt=prompt,
                temperature=0.3,
                max_tokens=8000,
            )
            
            response = generate_text(request)
            
            if not response or not response.get('ok'):
                error_msg = response.get('error', 'Unbekannter Fehler') if response else 'Keine Antwort'
                return {'success': False, 'error': f'LLM-Fehler: {error_msg}'}
            
            corrected_text = response.get('text', '').strip()
            
            if not corrected_text:
                return {'success': False, 'error': 'Leere Korrektur erhalten'}
            
            # Kapitel-Inhalt aktualisieren
            chapter.content = corrected_text
            chapter.save()
            
            # Diff für Anzeige erstellen
            diff_html = self._create_diff_summary(original_content, corrected_text)
            
            return {
                'success': True,
                'diff_html': diff_html,
                'summary': f'{fehler.fehler_typ} in Kapitel {chapter.chapter_number} korrigiert',
            }
            
        except Exception as e:
            logger.exception(f"KI-Korrektur fehlgeschlagen: {e}")
            return {'success': False, 'error': str(e)}
    
    def _build_perspective_correction_prompt(self, fehler: LektoratsFehler, chapter: BookChapters) -> str:
        """Erstellt Prompt für Perspektiven-Korrektur."""
        # Ziel-Perspektive aus Stil-Profil holen
        stil_profil = StilProfil.objects.filter(session=self.session).first()
        ziel_perspektive = stil_profil.perspektive if stil_profil else 'er_sie'
        
        perspektive_map = {
            'ich': 'Ich-Perspektive (ich, mir, mein)',
            'er_sie': 'Er/Sie-Perspektive (er, sie, sein, ihr)',
            'du': 'Du-Perspektive (du, dir, dein)',
            'wir': 'Wir-Perspektive (wir, uns, unser)',
        }
        ziel_display = perspektive_map.get(ziel_perspektive, ziel_perspektive)
        
        return f"""Korrigiere die Erzählperspektive in diesem Kapitel.

FEHLER: {fehler.beschreibung}

ZIEL-PERSPEKTIVE: {ziel_display}

ANWEISUNGEN:
1. Ändere alle Pronomen und Verben zur Ziel-Perspektive
2. Behalte den Inhalt und die Bedeutung bei
3. Achte auf konsistente Perspektive im gesamten Text
4. Gib NUR den korrigierten Text zurück

ORIGINAL-TEXT:
{chapter.content}"""
    
    def _build_tense_correction_prompt(self, fehler: LektoratsFehler, chapter: BookChapters) -> str:
        """Erstellt Prompt für Tempus-Korrektur."""
        # Ziel-Tempus aus Stil-Profil holen
        stil_profil = StilProfil.objects.filter(session=self.session).first()
        ziel_tempus = stil_profil.tempus if stil_profil else 'praeteritum'
        
        tempus_map = {
            'praesens': 'Präsens (Gegenwart: er geht, sie sagt)',
            'praeteritum': 'Präteritum (Vergangenheit: er ging, sie sagte)',
        }
        ziel_display = tempus_map.get(ziel_tempus, ziel_tempus)
        
        return f"""Korrigiere die Zeitform in diesem Kapitel.

FEHLER: {fehler.beschreibung}

ZIEL-TEMPUS: {ziel_display}

ANWEISUNGEN:
1. Ändere alle Verben zur Ziel-Zeitform
2. Behalte den Inhalt und die Bedeutung bei
3. Achte auf konsistente Zeitform im gesamten Text
4. Direkte Rede bleibt unverändert
5. Gib NUR den korrigierten Text zurück

ORIGINAL-TEXT:
{chapter.content}"""
    
    def _build_generic_correction_prompt(self, fehler: LektoratsFehler, chapter: BookChapters) -> str:
        """Erstellt generischen Korrektur-Prompt."""
        return f"""Korrigiere den folgenden Fehler im Text.

FEHLER: {fehler.beschreibung}
FEHLERTYP: {fehler.fehler_typ}
VORSCHLAG: {fehler.korrekturvorschlag or 'Keine spezifische Empfehlung'}

ANWEISUNGEN:
1. Korrigiere nur den beschriebenen Fehler
2. Behalte den restlichen Text unverändert
3. Gib NUR den korrigierten Text zurück

ORIGINAL-TEXT:
{chapter.content}"""
    
    def _create_diff_summary(self, original: str, corrected: str) -> str:
        """Erstellt eine kurze Zusammenfassung der Änderungen."""
        original_words = len(original.split())
        corrected_words = len(corrected.split())
        
        # Einfache Änderungszählung
        original_lines = original.split('\n')
        corrected_lines = corrected.split('\n')
        
        changed_lines = 0
        for i, (o, c) in enumerate(zip(original_lines, corrected_lines)):
            if o != c:
                changed_lines += 1
        
        return f"<small>{changed_lines} Zeilen geändert, {corrected_words} Wörter (vorher: {original_words})</small>"
