"""
Prompt-Template System für Expert Hub
=====================================

Strukturierte Prompts für KI-generierte Inhalte je nach Phase.
Analog zum BookWriting PromptTemplate-System.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple
from django.utils import timezone


@dataclass
class DocumentContext:
    """Kontext eines hochgeladenen Dokuments."""
    filename: str
    document_type: str
    file_size: int
    content_preview: str = ""  # Später: Extrahierter Text
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass 
class PhaseContext:
    """Vollständiger Kontext für eine Phase."""
    # Session-Info
    session_name: str
    project_name: str
    project_location: str
    
    # Phase-Info
    phase_number: str
    phase_title: str
    phase_description: str
    
    # Bestehende Inhalte
    existing_content: str
    existing_notes: str
    
    # Dokumente
    documents: List[DocumentContext]
    
    # Zusätzliche Daten (aus anderen Phasen, Berechnungen etc.)
    related_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.related_data is None:
            self.related_data = {}
    
    @property
    def has_content(self) -> bool:
        return bool(self.existing_content and self.existing_content.strip())
    
    @property
    def has_documents(self) -> bool:
        return len(self.documents) > 0
    
    @property
    def document_list_md(self) -> str:
        """Markdown-Liste der Dokumente."""
        if not self.documents:
            return "- Keine Dokumente zugeordnet"
        return "\n".join([
            f"- **{d.filename}** ({d.document_type})"
            for d in self.documents
        ])


# =============================================================================
# PHASE-SPEZIFISCHE PROMPT-TEMPLATES
# =============================================================================

PHASE_TEMPLATES = {
    # ---------------------------------------------------------------------
    # Phase 1: Betriebsbereich, Anlage
    # ---------------------------------------------------------------------
    '1': {
        'system_prompt': """Du bist ein Explosionsschutz-Experte und erstellst Dokumentation 
gemäß TRGS 720ff und BetrSichV. Deine Aufgabe ist es, den Betriebsbereich und die Anlage 
strukturiert zu beschreiben.

Berücksichtige:
- Anlagenbeschreibung mit Funktion und Zweck
- Räumliche Abgrenzung des Betriebsbereichs
- Verarbeitete Stoffe (Übersicht)
- Anlagentechnik (Hauptkomponenten)
""",
        'user_prompt': """Erstelle eine strukturierte Beschreibung für:

**Projekt:** {project_name}
**Standort:** {project_location}

{existing_section}

**Verfügbare Dokumente:**
{document_list}

Erstelle einen Entwurf für die Beschreibung von Betriebsbereich und Anlage.
Verwende die Informationen aus den Dokumenten und ergänze fehlende Punkte mit [TODO].
""",
        'output_format': """## 1 Betriebsbereich, Anlage

### 1.1 Anlagenbeschreibung
{content}

### 1.2 Betriebsbereich
- **Räumliche Abgrenzung:** 
- **Bereich nach BetrSichV:** 

### 1.3 Verarbeitete Stoffe (Übersicht)
| Stoff | Einsatzzweck | Aggregatzustand |
|-------|--------------|-----------------|
| | | |

### 1.4 Anlagentechnik
- **Hauptkomponenten:**
- **Verbindungstechnik:**
"""
    },
    
    # ---------------------------------------------------------------------
    # Phase 2: Verantwortlichkeiten
    # ---------------------------------------------------------------------
    '2': {
        'system_prompt': """Du bist ein Explosionsschutz-Experte und dokumentierst 
Verantwortlichkeiten gemäß BetrSichV und DGUV Vorschrift 3.

Wichtige Rollen:
- Arbeitgeber/Betreiber (Gesamtverantwortung)
- Verantwortliche Elektrofachkraft (VEFK)
- Befähigte Person für Ex-Prüfungen
- Fachkraft für Explosionsschutz
""",
        'user_prompt': """Erstelle eine Verantwortlichkeits-Matrix für:

**Projekt:** {project_name}

{existing_section}

**Verfügbare Dokumente:**
{document_list}

Erstelle einen Entwurf für die Verantwortlichkeiten im Explosionsschutz.
""",
        'output_format': """## 2 Verantwortlichkeiten

### 2.1 Organisationsstruktur

| Funktion | Name | Qualifikation | Aufgaben |
|----------|------|---------------|----------|
| Betreiber/Arbeitgeber | {name} | [Qualifikation] | Gesamtverantwortung |
| VEFK | [Name eintragen] | [Nachweis] | Ex-Anlagen |
| Befähigte Person | [Name eintragen] | [Nachweis] | Prüfungen nach BetrSichV |
| Fachkraft Ex-Schutz | [Name eintragen] | [Nachweis] | Dokumentation, Beratung |

*Bitte füllen Sie die Tabelle mit den konkreten Verantwortlichen aus.*
""",
        'hints': [
            "Laden Sie Organigramm oder Bestellungsurkunden hoch",
            "Qualifikationsnachweise (Schulungen, Zertifikate) sollten dokumentiert werden",
            "Unterweisungskonzept erstellen: Erstunterweisung + jährliche Wiederholung",
        ]
    },
    
    # ---------------------------------------------------------------------
    # Phase 3: Beschreibung des Verfahrens
    # ---------------------------------------------------------------------
    '3': {
        'system_prompt': """Du bist ein Verfahrenstechnik-Experte und beschreibst 
industrielle Prozesse im Kontext des Explosionsschutzes.

Fokus auf:
- Prozessschritte und Stoffflüsse
- Betriebsparameter (Druck, Temperatur)
- Kritische Verfahrensschritte
- Sicherheitsrelevante Parameter
""",
        'user_prompt': """Beschreibe das Verfahren für:

**Projekt:** {project_name}

{existing_section}

**Verfügbare Dokumente:**
{document_list}

Erstelle eine strukturierte Verfahrensbeschreibung mit Fokus auf explosionsschutzrelevante Aspekte.
""",
        'output_format': """## 3 Beschreibung des Verfahrens

### 3.1 Verfahrensübersicht
{content}

### 3.2 Prozessschritte
1. **Stoffeingabe:**
2. **Verarbeitung:**
3. **Produktaustrag:**

### 3.3 Betriebsparameter
| Parameter | Normalwert | Max. Wert | Sicherheitsgrenze |
|-----------|------------|-----------|-------------------|
| Temperatur | | | |
| Druck | | | |

### 3.4 Sicherheitsrelevante Aspekte
- **Kritische Schritte:**
- **Abweichungen:**
"""
    },
    
    # ---------------------------------------------------------------------
    # Phase 5: Stoffdaten
    # ---------------------------------------------------------------------
    '5': {
        'system_prompt': """Du bist ein Gefahrstoff-Experte und erfasst sicherheitsrelevante 
Stoffdaten für den Explosionsschutz.

Wichtige Parameter:
- Explosionsgrenzen (UEG, OEG)
- Flammpunkt und Zündtemperatur
- Explosionsgruppe und Temperaturklasse
- Dampfdruck und Dichte
- Sicherheitstechnische Kennzahlen (KSt, Pmax)
""",
        'user_prompt': """Erfasse die Stoffdaten für:

**Projekt:** {project_name}

{existing_section}

**Verfügbare Dokumente (z.B. Sicherheitsdatenblätter):**
{document_list}

Extrahiere die relevanten Stoffdaten aus den Dokumenten.
""",
        'output_format': """## 5 Stoffdaten

### 5.1 Stoffübersicht

| Stoff | CAS-Nr. | Formel | Gefahrenhinweise |
|-------|---------|--------|------------------|
| | | | |

### 5.2 Explosionsschutz-relevante Daten

| Stoff | UEG [Vol%] | OEG [Vol%] | Fp [°C] | Tz [°C] | Ex-Gruppe | T-Klasse |
|-------|------------|------------|---------|---------|-----------|----------|
| | | | | | | |

### 5.3 Sicherheitsdatenblätter
| Stoff | SDB-Nr. | Version | Datum |
|-------|---------|---------|-------|
| | | | |

### 5.4 Einstufung
- **Explosionsgruppe:** IIA / IIB / IIC
- **Temperaturklasse:** T1 - T6
"""
    },
    
    # ---------------------------------------------------------------------
    # Phase 6: Gefährdungsbeurteilung
    # ---------------------------------------------------------------------
    '6': {
        'system_prompt': """Du bist ein Explosionsschutz-Experte und führst 
Gefährdungsbeurteilungen gemäß TRGS 720ff durch.

Systematik:
1. Identifikation von Freisetzungsquellen
2. Bewertung von Zündquellen (TRGS 723)
3. Abschätzung der Explosionsauswirkungen
4. Risikobewertung
""",
        'user_prompt': """Erstelle eine Gefährdungsbeurteilung für:

**Projekt:** {project_name}

{existing_section}

**Verfügbare Dokumente:**
{document_list}

**Stoffdaten aus Phase 5:**
{related_stoffdaten}

Führe eine systematische Gefährdungsbeurteilung durch.
""",
        'output_format': """## 6 Gefährdungsbeurteilung

### 6.1 Freisetzungsquellen

| Nr. | Quelle | Stoff | Art | Häufigkeit | Menge |
|-----|--------|-------|-----|------------|-------|
| Q1 | | | | | |

### 6.2 Zündquellenanalyse (nach TRGS 723)

| Zündquelle | Vorhanden | Bewertung | Schutzmaßnahme |
|------------|-----------|-----------|----------------|
| Heiße Oberflächen | | | |
| Flammen | | | |
| Mechanische Funken | | | |
| Elektrische Anlagen | | | |
| Statische Elektrizität | | | |

### 6.3 Explosionsauswirkungen
- **Erwarteter Explosionsdruck:**
- **Gefährdete Bereiche:**
- **Personengefährdung:**

### 6.4 Risikomatrix
| Gefährdung | Eintrittswahrscheinlichkeit | Schadensausmaß | Risiko |
|------------|----------------------------|----------------|--------|
| | | | |
"""
    },
    
    # ---------------------------------------------------------------------
    # Phase 7: Schutzkonzept
    # ---------------------------------------------------------------------
    '7': {
        'system_prompt': """Du bist ein Explosionsschutz-Experte und entwickelst 
Schutzkonzepte gemäß ATEX und BetrSichV.

Schutzebenen:
- Primär: Vermeidung explosionsfähiger Atmosphäre
- Sekundär: Vermeidung wirksamer Zündquellen
- Tertiär: Begrenzung der Explosionsauswirkungen
""",
        'user_prompt': """Entwickle ein Schutzkonzept für:

**Projekt:** {project_name}

{existing_section}

**Verfügbare Dokumente:**
{document_list}

**Gefährdungsbeurteilung aus Phase 6:**
{related_gefaehrdung}

Erstelle ein umfassendes Schutzkonzept.
""",
        'output_format': """## 7 Schutzkonzept

### 7.1 Zoneneinteilung

| Zone | Bereich | Begründung | Ausdehnung |
|------|---------|------------|------------|
| 0/20 | | | |
| 1/21 | | | |
| 2/22 | | | |

### 7.2 Primärer Explosionsschutz
- **Stoffsubstitution:**
- **Inertisierung:**
- **Lüftungstechnik:**

### 7.3 Sekundärer Explosionsschutz
- **Betriebsmittelauswahl:** Geräte EPL {epl}
- **Erdung/Potentialausgleich:**
- **Zündquellenfreie Arbeitsverfahren:**

### 7.4 Tertiärer Explosionsschutz
- **Explosionsdruckentlastung:**
- **Explosionsunterdrückung:**
- **Explosionstechnische Entkopplung:**

### 7.5 Organisatorische Maßnahmen
- Arbeitsfreigabeverfahren
- Schulungen
- Betriebsanweisungen
"""
    },
    
    # ---------------------------------------------------------------------
    # Phase 8: Zoneneinteilung
    # ---------------------------------------------------------------------
    '8': {
        'system_prompt': """Du bist ein Explosionsschutz-Experte und führst 
Zoneneinteilungen gemäß TRGS 721/722 durch.

Zonenarten:
- Zone 0/20: g.A. ständig, langzeitig, häufig
- Zone 1/21: g.A. gelegentlich im Normalbetrieb
- Zone 2/22: g.A. selten, nur kurzzeitig
""",
        'user_prompt': """Führe die Zoneneinteilung durch für:

**Projekt:** {project_name}

{existing_section}

**Verfügbare Dokumente:**
{document_list}

**Zonenberechnungen:**
{related_zonenberechnung}

Dokumentiere die Zoneneinteilung mit Begründung.
""",
        'output_format': """## 8 Zoneneinteilung

### 8.1 Zonenübersicht

| Zone | Bereich/Raum | Ausdehnung | Begründung nach TRGS |
|------|--------------|------------|---------------------|
| | | | |

### 8.2 Zonenplan
Siehe Zeichnung Nr.: ________________

### 8.3 Detailbeschreibung

#### Zone 1 / Zone 21
- **Lage:**
- **Ausdehnung:**
- **Begründung:**

#### Zone 2 / Zone 22
- **Lage:**
- **Ausdehnung:**
- **Begründung:**

### 8.4 Hinweise
- Zonengrenzen sind im Zonenplan maßstäblich dargestellt
- Bei Änderungen ist eine Neubewertung erforderlich
"""
    },
}

# Default-Template für nicht definierte Phasen
DEFAULT_TEMPLATE = {
    'system_prompt': """Du bist ein Explosionsschutz-Experte und erstellst 
Dokumentation gemäß TRGS 720ff und BetrSichV.""",
    'user_prompt': """Erstelle Inhalt für:

**Phase:** {phase_number} {phase_title}
**Beschreibung:** {phase_description}

**Projekt:** {project_name}

{existing_section}

**Verfügbare Dokumente:**
{document_list}

Erstelle einen strukturierten Entwurf für diese Phase.
""",
    'output_format': """## {phase_number} {phase_title}

{phase_description}

### Inhalt
{content}

### Zugeordnete Dokumente
{document_list}

---
*Generiert am {timestamp}*
"""
}


# =============================================================================
# PROMPT RENDERER
# =============================================================================

class PhasePromptRenderer:
    """Rendert Prompts für eine Phase basierend auf dem Kontext."""
    
    def __init__(self, context: PhaseContext):
        self.context = context
        self.template = PHASE_TEMPLATES.get(context.phase_number, DEFAULT_TEMPLATE)
    
    def get_system_prompt(self) -> str:
        """Gibt den System-Prompt zurück."""
        return self.template['system_prompt']
    
    def get_user_prompt(self) -> str:
        """Rendert den User-Prompt mit Kontext."""
        # Existing content section
        if self.context.has_content:
            existing_section = f"""**Bisherige Eingaben des Nutzers:**
```
{self.context.existing_content}
```
Berücksichtige diese Eingaben und erweitere sie."""
        else:
            existing_section = "*Noch keine Eingaben vorhanden.*"
        
        # Related data sections
        related_stoffdaten = self.context.related_data.get('stoffdaten', '[Noch nicht erfasst]')
        related_gefaehrdung = self.context.related_data.get('gefaehrdung', '[Noch nicht erfasst]')
        related_zonenberechnung = self.context.related_data.get('zonenberechnung', '[Noch nicht berechnet]')
        
        return self.template['user_prompt'].format(
            project_name=self.context.project_name or self.context.session_name,
            project_location=self.context.project_location or 'Nicht angegeben',
            phase_number=self.context.phase_number,
            phase_title=self.context.phase_title,
            phase_description=self.context.phase_description,
            existing_section=existing_section,
            document_list=self.context.document_list_md,
            related_stoffdaten=related_stoffdaten,
            related_gefaehrdung=related_gefaehrdung,
            related_zonenberechnung=related_zonenberechnung,
        )
    
    def render_placeholder_output(self) -> Tuple[str, List[str]]:
        """
        Rendert einen Placeholder-Output (ohne echte LLM-Anbindung).
        
        Returns:
            Tuple[str, List[str]]: (Generierter Inhalt, Liste von Hinweisen/Tipps)
        
        WICHTIG: Der Output enthält NUR strukturierten Content.
        Bisherige Eingaben und Dokumente werden NICHT im Content angezeigt,
        sondern als Hinweise in der separaten Tipps-Box.
        """
        hints = []
        
        # Hinweise basierend auf vorhandenem Content
        if not self.context.has_content:
            hints.append("Geben Sie erste Stichpunkte ein, die die KI erweitern soll")
        
        # Hinweise basierend auf Dokumenten
        if self.context.has_documents:
            doc_names = [d.filename for d in self.context.documents]
            hints.append(f"Basiert auf: {', '.join(doc_names[:3])}" + 
                        (f" (+{len(doc_names)-3} weitere)" if len(doc_names) > 3 else ""))
        else:
            hints.append("Laden Sie relevante Dokumente hoch für bessere KI-Ergebnisse")
        
        if self.context.phase_number in ['5', '6', '7']:
            if not self.context.has_documents:
                hints.append("Für diese Phase sind Sicherheitsdatenblätter besonders wichtig")
        
        # Template-spezifische Hints hinzufügen
        template_hints = self.template.get('hints', [])
        hints.extend(template_hints)
        
        # Build output - NUR strukturierter Content, keine Meta-Infos
        output_template = self.template.get('output_format', DEFAULT_TEMPLATE['output_format'])
        
        # Simple placeholder replacement
        output = output_template.format(
            phase_number=self.context.phase_number,
            phase_title=self.context.phase_title,
            phase_description=self.context.phase_description or '',
            project_name=self.context.project_name or self.context.session_name,
            project_location=self.context.project_location or '[Standort]',
            content='[TODO: Basierend auf Dokumenten und Eingaben erstellen]',
            document_list='',  # Nicht im Content anzeigen
            name=self.context.existing_content.split('\n')[0] if self.context.has_content else '[Name]',
            epl='Ga/Gb/Gc',
            timestamp=timezone.now().strftime('%d.%m.%Y %H:%M'),
        )
        
        return output, hints
    
    def get_full_prompt_for_llm(self) -> Dict[str, str]:
        """Gibt System- und User-Prompt für LLM-Aufruf zurück."""
        return {
            'system_prompt': self.get_system_prompt(),
            'user_prompt': self.get_user_prompt(),
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_phase_context(session, phase, phase_status, documents) -> PhaseContext:
    """Erstellt PhaseContext aus Django-Objekten."""
    doc_contexts = [
        DocumentContext(
            filename=doc.original_filename,
            document_type=doc.get_document_type_display(),
            file_size=doc.file_size,
        )
        for doc in documents
    ]
    
    return PhaseContext(
        session_name=session.name,
        project_name=session.project_name or '',
        project_location=session.project_location or '',
        phase_number=phase.number,
        phase_title=phase.title,
        phase_description=phase.description or '',
        existing_content=phase_status.content or '',
        existing_notes=phase_status.notes or '',
        documents=doc_contexts,
    )


def generate_phase_content(session, phase, phase_status, documents, use_llm: bool = False) -> Tuple[str, List[str]]:
    """
    Generiert Inhalt für eine Phase.
    
    Args:
        session: ExAnalysisSession
        phase: ExWorkflowPhase
        phase_status: ExSessionPhaseStatus
        documents: QuerySet of ExSessionDocument
        use_llm: Ob echte LLM-Generierung verwendet werden soll
        
    Returns:
        Tuple[str, List[str]]: (Generierter Markdown-Text, Liste von Hinweisen)
    """
    context = create_phase_context(session, phase, phase_status, documents)
    renderer = PhasePromptRenderer(context)
    
    if use_llm:
        try:
            from apps.expert_hub.services.llm_client import generate_sync
            prompts = renderer.get_full_prompt_for_llm()
            
            success, content, usage = generate_sync(
                prompt=prompts['user_prompt'],
                system_prompt=prompts['system_prompt'],
                max_tokens=2500,
                temperature=0.7,
                response_format="markdown"
            )
            
            if success:
                hints = []
                if usage:
                    hints.append(f"Tokens: {usage.get('tokens_in', 0)} in / {usage.get('tokens_out', 0)} out")
                return content, hints
            else:
                # Fallback auf Placeholder bei Fehler
                placeholder_content, placeholder_hints = renderer.render_placeholder_output()
                return placeholder_content, [f"⚠️ LLM-Fehler: {content}"] + placeholder_hints
                
        except Exception as e:
            # Fallback auf Placeholder
            placeholder_content, placeholder_hints = renderer.render_placeholder_output()
            return placeholder_content, [f"⚠️ Ausnahme: {str(e)}"] + placeholder_hints
    else:
        return renderer.render_placeholder_output()
