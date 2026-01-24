"""Beispiele: Research Agent mit Paper Search MCP.

Zeigt verschiedene Research-Workflows:
1. Einfache Paper-Suche
2. Multi-Source Recherche
3. BFA + Research kombiniert
4. Spezialisierte Agents

Voraussetzung:
    pip install paper-search-mcp
    # oder
    uvx paper-search-mcp
"""

import asyncio
from agents import Runner

from bfa_agent.config import setup_openrouter
from bfa_agent.agents_research import (
    research_agent,
    research_triage_agent,
    create_research_agent,
    create_bfa_research_agent,
    create_arxiv_agent,
    create_pubmed_agent,
)


async def example_1_simple_search():
    """Beispiel 1: Einfache Paper-Suche."""
    print("\n" + "="*60)
    print("Beispiel 1: Einfache Paper-Suche")
    print("="*60)
    
    setup_openrouter()
    
    result = await Runner.run(
        research_agent,
        """Suche aktuelle Forschung zu Wasserstoff-Explosionsgrenzen.
        
Fokus auf:
- Experimentelle Daten zu LEL/UEL
- Einfluss von Temperatur und Druck
- Sicherheitsrelevante Erkenntnisse

Maximal 5 relevante Papers."""
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


async def example_2_multi_source():
    """Beispiel 2: Multi-Source Recherche."""
    print("\n" + "="*60)
    print("Beispiel 2: Multi-Source Recherche")
    print("="*60)
    
    setup_openrouter()
    
    # Research Triage routet automatisch
    result = await Runner.run(
        research_triage_agent,
        """Recherchiere zum Thema "Staubexplosionen in der Lebensmittelindustrie":

1. Technische/physikalische Grundlagen (→ arXiv)
2. Gesundheitsauswirkungen und Arbeitsschutz (→ PubMed)
3. Allgemeine Übersichtsartikel (→ Semantic Scholar)

Erstelle eine Zusammenfassung der wichtigsten Erkenntnisse."""
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


async def example_3_bfa_plus_research():
    """Beispiel 3: BFA Tools + Research kombiniert."""
    print("\n" + "="*60)
    print("Beispiel 3: BFA + Research kombiniert")
    print("="*60)
    
    setup_openrouter()
    
    # Kombinierter Agent
    bfa_research = create_bfa_research_agent()
    
    result = await Runner.run(
        bfa_research,
        """Analysiere einen Lackierraum mit Aceton:

1. Hole die Stoffdaten für Aceton (BFA Tool)
2. Recherchiere aktuelle Forschung zu Aceton-Explosionen (Paper Search)
3. Berechne die Zonenausdehnung für:
   - Freisetzungsrate: 0.01 kg/s
   - Luftwechsel: 15/h
   - Raumvolumen: 200 m³

Kombiniere Normbezug (TRGS) mit wissenschaftlicher Literatur."""
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


async def example_4_specialized_agents():
    """Beispiel 4: Spezialisierte Research Agents."""
    print("\n" + "="*60)
    print("Beispiel 4: Spezialisierte Agents")
    print("="*60)
    
    setup_openrouter()
    
    # arXiv für Engineering
    arxiv = create_arxiv_agent()
    
    print("\narXiv Recherche (Engineering):")
    result = await Runner.run(
        arxiv,
        "Suche Papers zu CFD simulation of gas dispersion in ventilated rooms"
    )
    print(f"{str(result.final_output)[:500]}...")
    
    # PubMed für Arbeitsschutz
    pubmed = create_pubmed_agent()
    
    print("\n\nPubMed Recherche (Arbeitsschutz):")
    result = await Runner.run(
        pubmed,
        "Suche Papers zu occupational exposure limits volatile organic compounds"
    )
    print(f"{str(result.final_output)[:500]}...")


async def example_5_literature_review():
    """Beispiel 5: Systematische Literaturübersicht."""
    print("\n" + "="*60)
    print("Beispiel 5: Literaturübersicht")
    print("="*60)
    
    setup_openrouter()
    
    result = await Runner.run(
        research_agent,
        """Erstelle eine kurze Literaturübersicht zum Thema:
"Einfluss der Lüftung auf Ex-Zonen Klassifizierung"

Struktur:
1. Einleitung (Was ist das Problem?)
2. Stand der Forschung (3-5 relevante Papers)
3. Offene Fragen
4. Fazit

Fokus auf Papers der letzten 5 Jahre."""
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


def show_research_capabilities():
    """Zeigt verfügbare Research-Funktionen."""
    print("\n" + "="*60)
    print("BFA Agent Research Capabilities")
    print("="*60)
    
    print("""
## Verfügbare Research Agents

| Agent | Fokus | Quellen |
|-------|-------|---------|
| research_agent | Allgemein | Alle |
| research_triage_agent | Routing | arXiv, PubMed, Semantic |
| arxiv_agent | Physik/Engineering | arXiv |
| pubmed_agent | Biomedizin/Arbeitsschutz | PubMed |
| semantic_agent | Breite Suche | Semantic Scholar |

## Paper Search MCP Tools

### Suche
- search_arxiv(query, max_results)
- search_pubmed(query, max_results)  
- search_biorxiv(query, max_results)
- search_medrxiv(query, max_results)
- search_semantic_scholar(query, max_results)
- search_google_scholar(query, max_results)

### Download
- download_arxiv(paper_id, output_dir)
- download_pubmed(pmid, output_dir)
- download_biorxiv(doi, output_dir)

## Beispiel-Queries für Ex-Schutz

arXiv:
- "explosion limits hydrogen temperature pressure"
- "dust explosion CFD simulation"
- "ventilation effectiveness hazardous areas"

PubMed:
- "solvent exposure workplace safety"
- "occupational health explosion prevention"
- "toxic gas inhalation emergency response"

Semantic Scholar:
- "ATEX directive compliance review"
- "explosion protection standards comparison"
- "hazardous area classification methods"
""")


async def main():
    """Führt alle Beispiele aus."""
    
    show_research_capabilities()
    
    try:
        await example_1_simple_search()
        await example_4_specialized_agents()
        # await example_2_multi_source()  # Dauert länger
        # await example_3_bfa_plus_research()  # Benötigt beide MCP Server
        # await example_5_literature_review()  # Ausführliche Ausgabe
    except ValueError as e:
        print(f"\n⚠️  API-Beispiele übersprungen: {e}")
    except Exception as e:
        print(f"\n⚠️  Fehler: {e}")
        print("Stelle sicher, dass paper-search-mcp installiert ist:")
        print("  pip install paper-search-mcp")


if __name__ == "__main__":
    asyncio.run(main())
