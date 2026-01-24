"""
Setup Scientific Writing Configuration
Creates LLMs, Agents, and Templates for scientific paper writing.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.bfagent.models import Llms, Agents, AgentAction


class Command(BaseCommand):
    help = "Setup LLMs, Agents, and configurations for scientific writing"

    # ==========================================================================
    # SCIENTIFIC LLM CONFIGURATIONS
    # ==========================================================================
    SCIENTIFIC_LLMS = [
        {
            "name": "Scientific Writer (Precise)",
            "provider": "anthropic",
            "llm_name": "claude-3-5-sonnet-20241022",
            "description": "Optimiert für wissenschaftliches Schreiben: niedrige Temperature für faktische, konsistente Ausgabe",
            "max_tokens": 4000,
            "temperature": 0.3,  # Low for factual content
            "top_p": 0.85,
            "frequency_penalty": 0.5,  # Avoid repetition
            "presence_penalty": 0.3,
        },
        {
            "name": "Research Assistant",
            "provider": "anthropic", 
            "llm_name": "claude-3-5-sonnet-20241022",
            "description": "Für Literaturanalyse und Forschungsfragen - etwas kreativer",
            "max_tokens": 3000,
            "temperature": 0.5,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.2,
        },
        {
            "name": "Academic Reviewer",
            "provider": "anthropic",
            "llm_name": "claude-3-5-sonnet-20241022", 
            "description": "Für kritische Analyse und Review - analytisch und präzise",
            "max_tokens": 2500,
            "temperature": 0.2,  # Very low for analytical work
            "top_p": 0.8,
            "frequency_penalty": 0.4,
            "presence_penalty": 0.2,
        },
    ]

    # ==========================================================================
    # SCIENTIFIC AGENTS
    # ==========================================================================
    SCIENTIFIC_AGENTS = [
        {
            "name": "Forschungsfragen-Assistent",
            "agent_type": "research_question",
            "description": """Hilft bei der Formulierung präziser Forschungsfragen und Hypothesen.
            
Fähigkeiten:
- Analysiert Thema und identifiziert Forschungslücken
- Formuliert präzise, beantwortbare Forschungsfragen
- Leitet passende Hypothesen ab
- Schlägt geeignete Methodik vor""",
            "system_prompt": """Du bist ein erfahrener Forschungsmethodiker. Deine Aufgabe ist es, 
Forschenden bei der Formulierung präziser, wissenschaftlich valider Forschungsfragen zu helfen.

REGELN:
1. Forschungsfragen müssen spezifisch, messbar und beantwortbar sein
2. Unterscheide zwischen explorativen, deskriptiven und explanativen Fragen
3. Formuliere Hypothesen nur bei quantitativen/experimentellen Designs
4. Berücksichtige ethische Aspekte
5. Schlage passende Methodik vor (qualitativ/quantitativ/mixed)

AUSGABEFORMAT:
- Hauptforschungsfrage (1 Satz, klar formuliert)
- Unterforschungsfragen (2-4, nummeriert)
- Hypothesen (falls anwendbar, H1, H2, ...)
- Empfohlene Methodik (kurze Begründung)""",
            "capabilities": ["research_question", "hypothesis", "methodology_suggestion"],
        },
        {
            "name": "Literatur-Analyst",
            "agent_type": "literature_review",
            "description": """Analysiert und strukturiert wissenschaftliche Literatur.
            
Fähigkeiten:
- Identifiziert Schlüsselkonzepte und Theorien
- Erstellt thematische Strukturierung
- Findet Forschungslücken
- Generiert Zitationsvorschläge""",
            "system_prompt": """Du bist ein Experte für systematische Literaturarbeit. Deine Aufgabe ist es,
wissenschaftliche Quellen zu analysieren und für den Forschungsstand aufzubereiten.

REGELN:
1. Strukturiere Literatur thematisch, nicht chronologisch
2. Identifiziere Konsens und Kontroversen
3. Benenne explizit Forschungslücken
4. Zitiere korrekt im angegebenen Stil (Standard: APA)
5. Paraphrasiere statt wörtlich zu zitieren

AUSGABEFORMAT:
- Thematische Gliederung des Forschungsstands
- Zentrale Theorien und Modelle
- Empirische Befunde (tabellarisch wenn möglich)
- Identifizierte Forschungslücken
- Überleitung zur eigenen Forschung""",
            "capabilities": ["literature_analysis", "citation", "gap_identification"],
        },
        {
            "name": "Methodik-Berater",
            "agent_type": "methodology",
            "description": """Berät bei der Wahl und Beschreibung der Forschungsmethodik.
            
Fähigkeiten:
- Empfiehlt passende Forschungsdesigns
- Beschreibt Datenerhebungsmethoden
- Erklärt Analyseverfahren
- Diskutiert Gütekriterien""",
            "system_prompt": """Du bist ein Methodenexperte für empirische Sozialforschung. 
Deine Aufgabe ist es, bei der Auswahl und Beschreibung geeigneter Forschungsmethoden zu beraten.

REGELN:
1. Methodik muss zur Forschungsfrage passen
2. Beschreibe so detailliert, dass Replikation möglich ist
3. Begründe methodische Entscheidungen
4. Benenne Limitationen proaktiv
5. Berücksichtige Gütekriterien (Validität, Reliabilität, Objektivität)

BEI QUANTITATIVEN STUDIEN:
- Stichprobengröße und -auswahl
- Erhebungsinstrumente (Fragebogen, etc.)
- Statistische Analyseverfahren
- Signifikanzniveau

BEI QUALITATIVEN STUDIEN:
- Sampling-Strategie
- Erhebungsmethode (Interview, Beobachtung, etc.)
- Auswertungsmethode (Inhaltsanalyse, Grounded Theory, etc.)
- Gütekriterien nach Lincoln & Guba""",
            "capabilities": ["methodology_design", "sampling", "analysis_methods"],
        },
        {
            "name": "Wissenschaftlicher Schreibcoach",
            "agent_type": "academic_writing",
            "description": """Unterstützt beim wissenschaftlichen Schreiben.
            
Fähigkeiten:
- Verbessert akademischen Schreibstil
- Strukturiert Argumentation
- Prüft Kohärenz und Logik
- Korrigiert Zitationen""",
            "system_prompt": """Du bist ein erfahrener akademischer Schreibcoach. 
Deine Aufgabe ist es, wissenschaftliche Texte zu verbessern und beim Schreiben zu unterstützen.

STILREGELN:
1. Verwende Passiv oder unpersönliche Formulierungen
2. Vermeide umgangssprachliche Ausdrücke
3. Definiere Fachbegriffe bei Erstnennung
4. Verwende Signalwörter für Übergänge (jedoch, darüber hinaus, folglich)
5. Belege Behauptungen mit Quellen
6. Formuliere präzise und sachlich
7. Vermeide Redundanzen und Füllwörter

STRUKTUR:
- Jeder Absatz: Ein Hauptgedanke
- Klare Topic Sentences
- Logische Argumentation (These → Begründung → Beleg → Schlussfolgerung)
- Roter Faden zwischen Abschnitten""",
            "capabilities": ["style_improvement", "argumentation", "coherence_check"],
        },
    ]

    # ==========================================================================
    # SCIENTIFIC AGENT ACTIONS
    # ==========================================================================
    SCIENTIFIC_ACTIONS = [
        {
            "name": "Forschungsfrage formulieren",
            "action_type": "research_question",
            "description": "Hilft bei der Formulierung einer präzisen Forschungsfrage",
            "prompt_template": """Analysiere folgendes Thema und formuliere eine wissenschaftliche Forschungsfrage:

THEMA: {topic}
FACHGEBIET: {field}
ARBEITSTYP: {paper_type}

Erstelle:
1. Eine Hauptforschungsfrage
2. 2-3 Unterforschungsfragen
3. Passende Hypothesen (falls quantitativ)
4. Methodenempfehlung""",
        },
        {
            "name": "IMRaD-Gliederung erstellen",
            "action_type": "imrad_outline",
            "description": "Erstellt eine wissenschaftliche Gliederung nach IMRaD-Struktur",
            "prompt_template": """Erstelle eine wissenschaftliche Gliederung für folgende Arbeit:

TITEL: {title}
FORSCHUNGSFRAGE: {research_question}
FACHGEBIET: {field}
ARBEITSTYP: {paper_type}

Struktur nach IMRaD:
1. Abstract (Zusammenfassung)
2. Einleitung (Problemstellung, Forschungslücke, Zielsetzung)
3. Theoretischer Hintergrund / Forschungsstand
4. Methodik (Design, Datenerhebung, Analyse)
5. Ergebnisse
6. Diskussion (Interpretation, Limitationen)
7. Fazit
8. Literaturverzeichnis

Erstelle für jeden Abschnitt:
- Unterüberschriften
- Leitfragen (was soll beantwortet werden)
- Geschätzte Wortanzahl""",
        },
        {
            "name": "Abschnitt schreiben",
            "action_type": "write_section",
            "description": "Schreibt einen wissenschaftlichen Abschnitt",
            "prompt_template": """Schreibe folgenden Abschnitt einer wissenschaftlichen Arbeit:

ABSCHNITT: {section_title}
ABSCHNITTSTYP: {section_type}
FORSCHUNGSFRAGE: {research_question}

KONTEXT:
{context}

GLIEDERUNG FÜR DIESEN ABSCHNITT:
{section_outline}

ZIEL-WORTANZAHL: {target_words}
ZITATIONSSTIL: {citation_style}

Schreibe in wissenschaftlichem Stil mit korrekten Zitationen.""",
        },
        {
            "name": "Literatur analysieren",
            "action_type": "analyze_literature",
            "description": "Analysiert Quellen für den Forschungsstand",
            "prompt_template": """Analysiere folgende Literaturquellen für den Forschungsstand:

FORSCHUNGSFRAGE: {research_question}
THEMENGEBIET: {topic}

QUELLEN:
{sources}

Erstelle:
1. Thematische Strukturierung der Literatur
2. Zentrale Theorien und Modelle
3. Wichtige empirische Befunde
4. Identifizierte Forschungslücken
5. Überleitung zur eigenen Forschung""",
        },
    ]

    # ==========================================================================
    # IMRAD SECTION TEMPLATES
    # ==========================================================================
    IMRAD_TEMPLATES = {
        "empirical": {
            "name": "Empirische Studie (IMRaD)",
            "sections": [
                {"title": "Abstract", "type": "abstract", "target_words": 250,
                 "guidance": "Zusammenfassung: Hintergrund, Methodik, Ergebnisse, Schlussfolgerung"},
                {"title": "1. Einleitung", "type": "introduction", "target_words": 1500,
                 "guidance": "Problemhintergrund, Forschungslücke, Forschungsfrage, Aufbau"},
                {"title": "2. Theoretischer Hintergrund", "type": "literature_review", "target_words": 3000,
                 "guidance": "Stand der Forschung, zentrale Theorien, Forschungslücke"},
                {"title": "3. Methodik", "type": "methodology", "target_words": 2000,
                 "subsections": ["3.1 Forschungsdesign", "3.2 Stichprobe", "3.3 Datenerhebung", "3.4 Datenanalyse"],
                 "guidance": "Detailliert genug für Replikation"},
                {"title": "4. Ergebnisse", "type": "results", "target_words": 2500,
                 "guidance": "Objektive Darstellung ohne Interpretation"},
                {"title": "5. Diskussion", "type": "discussion", "target_words": 2500,
                 "subsections": ["5.1 Interpretation", "5.2 Einordnung in Literatur", "5.3 Limitationen", "5.4 Implikationen"],
                 "guidance": "Interpretation, Vergleich mit Literatur, Limitationen"},
                {"title": "6. Fazit", "type": "conclusion", "target_words": 800,
                 "guidance": "Beantwortung der Forschungsfrage, Ausblick"},
                {"title": "Literaturverzeichnis", "type": "references", "target_words": 500,
                 "guidance": "Vollständiges Quellenverzeichnis im gewählten Zitationsstil"},
            ]
        },
        "literature_review": {
            "name": "Literaturarbeit",
            "sections": [
                {"title": "Abstract", "type": "abstract", "target_words": 200},
                {"title": "1. Einleitung", "type": "introduction", "target_words": 1000,
                 "guidance": "Relevanz, Fragestellung, Aufbau"},
                {"title": "2. Methodik der Literaturrecherche", "type": "methodology", "target_words": 800,
                 "guidance": "Suchstrategie, Datenbanken, Ein-/Ausschlusskriterien"},
                {"title": "3. Forschungsstand", "type": "literature_review", "target_words": 6000,
                 "guidance": "Thematisch strukturierte Aufarbeitung"},
                {"title": "4. Diskussion", "type": "discussion", "target_words": 2000,
                 "guidance": "Synthese, Forschungslücken, kritische Würdigung"},
                {"title": "5. Fazit", "type": "conclusion", "target_words": 600},
                {"title": "Literaturverzeichnis", "type": "references", "target_words": 800},
            ]
        },
        "thesis": {
            "name": "Abschlussarbeit (Bachelor/Master)",
            "sections": [
                {"title": "Abstract", "type": "abstract", "target_words": 300},
                {"title": "1. Einleitung", "type": "introduction", "target_words": 2000,
                 "subsections": ["1.1 Problemstellung", "1.2 Zielsetzung", "1.3 Aufbau der Arbeit"]},
                {"title": "2. Theoretische Grundlagen", "type": "literature_review", "target_words": 4000,
                 "guidance": "Begriffe, Theorien, Modelle"},
                {"title": "3. Stand der Forschung", "type": "literature_review", "target_words": 3000,
                 "guidance": "Empirische Befunde, Forschungslücke"},
                {"title": "4. Methodik", "type": "methodology", "target_words": 3000},
                {"title": "5. Ergebnisse", "type": "results", "target_words": 4000},
                {"title": "6. Diskussion", "type": "discussion", "target_words": 3000},
                {"title": "7. Fazit und Ausblick", "type": "conclusion", "target_words": 1500},
                {"title": "Literaturverzeichnis", "type": "references", "target_words": 1000},
                {"title": "Anhang", "type": "appendix", "target_words": 0},
            ]
        },
    }

    def handle(self, *args, **options):
        self.stdout.write("Setting up Scientific Writing configuration...")
        
        # Create LLMs
        llm_count = self._create_llms()
        self.stdout.write(f"  ✓ Created/updated {llm_count} LLM configurations")
        
        # Create Agents
        agent_count = self._create_agents()
        self.stdout.write(f"  ✓ Created/updated {agent_count} Agents")
        
        # Create Agent Actions
        action_count = self._create_actions()
        self.stdout.write(f"  ✓ Created/updated {action_count} Agent Actions")
        
        self.stdout.write(self.style.SUCCESS("\n✅ Scientific Writing setup complete!"))
        self.stdout.write("\nVerfügbare Templates:")
        for key, template in self.IMRAD_TEMPLATES.items():
            self.stdout.write(f"  - {template['name']} ({len(template['sections'])} Abschnitte)")

    def _create_llms(self):
        """Create or update scientific LLM configurations"""
        count = 0
        for llm_data in self.SCIENTIFIC_LLMS:
            llm, created = Llms.objects.update_or_create(
                name=llm_data["name"],
                defaults={
                    "provider": llm_data["provider"],
                    "llm_name": llm_data["llm_name"],
                    "description": llm_data["description"],
                    "max_tokens": llm_data["max_tokens"],
                    "temperature": llm_data["temperature"],
                    "top_p": llm_data["top_p"],
                    "frequency_penalty": llm_data["frequency_penalty"],
                    "presence_penalty": llm_data["presence_penalty"],
                    "api_key": "",  # Set via env
                    "api_endpoint": "",
                    "total_tokens_used": 0,
                    "total_requests": 0,
                    "total_cost": 0.0,
                    "cost_per_1k_tokens": 0.003,  # Claude pricing
                    "is_active": True,
                    "created_at": timezone.now(),
                    "updated_at": timezone.now(),
                }
            )
            count += 1
        return count

    def _create_agents(self):
        """Create or update scientific agents"""
        count = 0
        for agent_data in self.SCIENTIFIC_AGENTS:
            agent, created = Agents.objects.update_or_create(
                name=agent_data["name"],
                defaults={
                    "agent_type": agent_data["agent_type"],
                    "description": agent_data["description"],
                    "system_prompt": agent_data["system_prompt"],
                    "status": "active",
                    "created_at": timezone.now(),
                    "updated_at": timezone.now(),
                }
            )
            count += 1
        return count

    def _create_actions(self):
        """Create or update scientific agent actions"""
        count = 0
        for action_data in self.SCIENTIFIC_ACTIONS:
            action, created = AgentAction.objects.update_or_create(
                name=action_data["name"],
                defaults={
                    "action_type": action_data["action_type"],
                    "description": action_data["description"],
                    "prompt_template": action_data["prompt_template"],
                    "is_active": True,
                }
            )
            count += 1
        return count
