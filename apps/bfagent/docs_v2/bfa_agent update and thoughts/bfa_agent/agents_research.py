"""Research Agent für wissenschaftliche Literaturrecherche.

Nutzt paper-search-mcp für:
- arXiv (Physik, Engineering, CS)
- PubMed (Biomedizin, Toxikologie, Arbeitsschutz)
- bioRxiv/medRxiv (Preprints)
- Semantic Scholar (Breite Suche)
- Google Scholar
- IACR ePrint (Kryptographie)

Installation:
    pip install paper-search-mcp
    # oder
    uvx paper-search-mcp
"""

from agents import Agent, handoff
from .config import Models
from .mcp_integration import MCPServers
from .presets import get_preset_model


# ============================================================
# Research Agent Instructions
# ============================================================

RESEARCH_INSTRUCTIONS = """Du bist ein Experte für wissenschaftliche Literaturrecherche im Bereich Explosionsschutz und Sicherheitstechnik.

## Deine Aufgaben

1. **Stand der Technik recherchieren**
   - Aktuelle Forschung zu Explosionsschutz
   - Neue Entwicklungen in der Sicherheitstechnik
   - Wissenschaftliche Grundlagen hinter Normen

2. **Stoffdaten validieren**
   - Forschung zu Explosionsgrenzen (LEL/UEL)
   - Zündtemperaturen und Flammpunkte
   - Toxikologische Daten

3. **Normen-Hintergrund liefern**
   - Wissenschaftliche Basis für TRGS, ATEX, IECEx
   - Begründung für Grenzwerte
   - Historische Entwicklung

## Verfügbare Tools (via paper-search-mcp)

### Suche
- `search_arxiv` - Physik, Engineering, Informatik
- `search_pubmed` - Biomedizin, Toxikologie, Arbeitsschutz  
- `search_biorxiv` - Biologie Preprints
- `search_medrxiv` - Medizin Preprints
- `search_semantic_scholar` - Breite akademische Suche
- `search_google_scholar` - Umfassende Suche

### Download
- `download_arxiv` - PDF von arXiv
- `download_pubmed` - Volltext wenn verfügbar
- `download_biorxiv` - PDF von bioRxiv

## Suchstrategie

1. **Starte breit** mit Semantic Scholar
2. **Spezialisiere** mit arXiv (Engineering) oder PubMed (Gesundheit)
3. **Prüfe Preprints** auf bioRxiv/medRxiv für neueste Forschung
4. **Lade PDFs** für wichtige Papers

## Ausgabeformat

Für jedes relevante Paper:
- **Titel** (mit Link wenn verfügbar)
- **Autoren** und Jahr
- **Kernaussage** (1-2 Sätze)
- **Relevanz** für die Anfrage

Am Ende: Zusammenfassung der wichtigsten Erkenntnisse.

## Beispiel-Suchen für Ex-Schutz

- "hydrogen explosion limits ventilation" (arXiv)
- "solvent vapor explosion workplace" (PubMed)
- "dust explosion prevention" (Semantic Scholar)
- "ATEX zone classification" (Google Scholar)
"""

RESEARCH_INSTRUCTIONS_SHORT = """Recherchiere wissenschaftliche Literatur für Explosionsschutz.

Tools:
- search_arxiv: Physik, Engineering
- search_pubmed: Toxikologie, Arbeitsschutz
- search_semantic_scholar: Breite Suche
- download_*: PDFs laden

Fokus: Stand der Technik, Stoffdaten, Normen-Hintergrund.
Ausgabe: Titel, Autoren, Kernaussage, Relevanz."""


# ============================================================
# Research Agent Definitionen
# ============================================================

def create_research_agent(
    use_preset: bool = False,
    detailed_instructions: bool = True
) -> Agent:
    """Erstellt Research Agent mit Paper Search MCP.
    
    Args:
        use_preset: True für @preset/bfa-research
        detailed_instructions: True für ausführliche Anweisungen
        
    Returns:
        Konfigurierter Research Agent
    """
    model = get_preset_model("bfa-substances") if use_preset else Models.PRECISE
    instructions = RESEARCH_INSTRUCTIONS if detailed_instructions else RESEARCH_INSTRUCTIONS_SHORT
    
    return Agent(
        name="Research Expert",
        instructions=instructions,
        model=model,
        mcp_servers=[MCPServers.paper_search()]
    )


# Vorkonfigurierte Agents
research_agent = create_research_agent(use_preset=False, detailed_instructions=True)
research_agent_preset = create_research_agent(use_preset=True, detailed_instructions=True)


# ============================================================
# Spezialisierte Research Agents
# ============================================================

def create_arxiv_agent() -> Agent:
    """Agent spezialisiert auf arXiv (Physik, Engineering)."""
    return Agent(
        name="arXiv Researcher",
        instructions="""Du recherchierst auf arXiv nach Physik und Engineering Papers.

Fokus für Ex-Schutz:
- Combustion science
- Explosion dynamics
- Ventilation engineering
- Dust explosion physics
- Gas dispersion modeling

Nutze search_arxiv und download_arxiv.
Bevorzuge Papers mit experimentellen Daten.""",
        model=Models.FAST,
        mcp_servers=[MCPServers.paper_search()]
    )


def create_pubmed_agent() -> Agent:
    """Agent spezialisiert auf PubMed (Biomedizin, Arbeitsschutz)."""
    return Agent(
        name="PubMed Researcher",
        instructions="""Du recherchierst auf PubMed nach biomedizinischer Literatur.

Fokus für Ex-Schutz:
- Occupational health and safety
- Toxicology of solvents/gases
- Workplace exposure limits
- Industrial hygiene
- Accident case studies

Nutze search_pubmed und download_pubmed.
Achte auf peer-reviewed Journals.""",
        model=Models.FAST,
        mcp_servers=[MCPServers.paper_search()]
    )


def create_semantic_scholar_agent() -> Agent:
    """Agent für breite akademische Suche."""
    return Agent(
        name="Semantic Scholar Researcher",
        instructions="""Du führst breite akademische Recherchen durch.

Nutze search_semantic_scholar für:
- Übersichtsartikel (Reviews)
- Interdisziplinäre Themen
- Zitationsanalyse
- Neueste Publikationen

Filtere nach Relevanz und Zitationszahl.""",
        model=Models.FAST,
        mcp_servers=[MCPServers.paper_search()]
    )


# ============================================================
# Research Triage Agent
# ============================================================

arxiv_agent = create_arxiv_agent()
pubmed_agent = create_pubmed_agent()
semantic_agent = create_semantic_scholar_agent()

research_triage_agent = Agent(
    name="Research Triage",
    instructions="""Du leitest Recherche-Anfragen an spezialisierte Agents weiter.

Routing:
- Physik, Engineering, Modeling → arXiv Researcher
- Gesundheit, Toxikologie, Arbeitsschutz → PubMed Researcher  
- Breite Suche, Reviews, Unklares Thema → Semantic Scholar

Bei komplexen Anfragen: Mehrere Agents nacheinander nutzen.
Am Ende: Ergebnisse zusammenfassen.""",
    model=Models.FAST,
    handoffs=[
        handoff(arxiv_agent, "Physik/Engineering auf arXiv"),
        handoff(pubmed_agent, "Biomedizin/Arbeitsschutz auf PubMed"),
        handoff(semantic_agent, "Breite akademische Suche"),
    ]
)


# ============================================================
# Combined BFA + Research Agent
# ============================================================

def create_bfa_research_agent() -> Agent:
    """Kombinierter Agent: BFA Tools + Paper Search.
    
    Hat Zugriff auf:
    - BFA CAD Tools (Zonen, Equipment, Stoffe)
    - Paper Search (arXiv, PubMed, etc.)
    """
    from .mcp_integration import MCPServerSets
    
    return Agent(
        name="BFA Research Expert",
        instructions="""Du bist ein Explosionsschutz-Experte mit Zugang zu:

## BFA Tools
- read_cad_file: CAD-Dateien lesen
- calculate_zone_extent: Zonen berechnen
- check_equipment_for_zone: Equipment prüfen
- get_substance_data: Stoffdaten abrufen
- analyze_ventilation: Lüftung bewerten

## Research Tools
- search_arxiv: Physik, Engineering Papers
- search_pubmed: Biomedizin, Arbeitsschutz
- search_semantic_scholar: Breite Suche
- download_*: PDFs laden

## Workflow
1. Analysiere die Anfrage
2. Nutze BFA Tools für konkrete Berechnungen
3. Recherchiere Hintergrund mit Paper Search
4. Kombiniere beides zur fundierten Antwort

Begründe mit Normbezug UND wissenschaftlicher Literatur.""",
        model=Models.PRECISE,
        mcp_servers=MCPServerSets.bfa_full()
    )


# ============================================================
# Exports
# ============================================================

__all__ = [
    # Instructions
    "RESEARCH_INSTRUCTIONS",
    "RESEARCH_INSTRUCTIONS_SHORT",
    # Factory
    "create_research_agent",
    "create_arxiv_agent",
    "create_pubmed_agent",
    "create_semantic_scholar_agent",
    "create_bfa_research_agent",
    # Pre-built Agents
    "research_agent",
    "research_agent_preset",
    "arxiv_agent",
    "pubmed_agent",
    "semantic_agent",
    "research_triage_agent",
]
