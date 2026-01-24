"""
Setup Universal Agent Roles and LLM Tiers
Creates the core agent roles, specialized writers, and LLM tier configurations.
"""

from django.core.management.base import BaseCommand
from apps.writing_hub.models import (
    AgentRole, LlmTier, AgentPipelineTemplate,
)


class Command(BaseCommand):
    help = "Setup universal agent roles, LLM tiers, and pipeline templates"

    # ==========================================================================
    # LLM TIERS
    # ==========================================================================
    LLM_TIERS = [
        {
            "code": "bulk",
            "name": "Bulk",
            "name_de": "Masse",
            "description": "Kostengünstige LLMs für Recherche, Brainstorming, erste Entwürfe. Lokale oder günstige Cloud-Modelle.",
            "cost_factor": 0.1,
            "priority": 1,
            "default_temperature": 0.8,
            "default_max_tokens": 2000,
            "icon": "bi-lightning",
            "color": "#22c55e",
            "badge_class": "bg-success",
            "sort_order": 1,
        },
        {
            "code": "standard",
            "name": "Standard",
            "name_de": "Standard",
            "description": "Ausgewogene LLMs für normale Arbeit. Gutes Preis-Leistungs-Verhältnis.",
            "cost_factor": 1.0,
            "priority": 2,
            "default_temperature": 0.7,
            "default_max_tokens": 3000,
            "icon": "bi-cpu",
            "color": "#3b82f6",
            "badge_class": "bg-primary",
            "sort_order": 2,
        },
        {
            "code": "premium",
            "name": "Premium",
            "name_de": "Premium",
            "description": "Beste LLMs für finale Texte, kritische Abschnitte, höchste Qualität.",
            "cost_factor": 3.0,
            "priority": 3,
            "default_temperature": 0.5,
            "default_max_tokens": 4000,
            "icon": "bi-gem",
            "color": "#f59e0b",
            "badge_class": "bg-warning",
            "sort_order": 3,
        },
    ]

    # ==========================================================================
    # CORE AGENT ROLES
    # ==========================================================================
    CORE_ROLES = [
        {
            "code": "researcher",
            "name": "Researcher",
            "name_de": "Rechercheur",
            "category": "core",
            "description": "Collects and analyzes information, builds context, finds sources and references.",
            "description_de": "Sammelt und analysiert Informationen, baut Kontext auf, findet Quellen und Referenzen.",
            "icon": "bi-search",
            "color": "#8b5cf6",
            "sort_order": 1,
            "base_system_prompt": """Du bist ein gründlicher Researcher. Deine Aufgaben:

RECHERCHE:
- Sammle alle relevanten Informationen zum Thema
- Identifiziere Schlüsselkonzepte und Zusammenhänge
- Finde Lücken im vorhandenen Material

ANALYSE:
- Strukturiere Erkenntnisse logisch
- Priorisiere nach Relevanz
- Erstelle Zusammenfassungen

OUTPUT:
- Klare, strukturierte Informationssammlung
- Quellenangaben wo möglich
- Offene Fragen und Empfehlungen für weitere Recherche""",
        },
        {
            "code": "writer",
            "name": "Writer",
            "name_de": "Autor",
            "category": "core",
            "description": "Creates content - creative or formal, adapts to style requirements.",
            "description_de": "Erstellt Inhalte - kreativ oder formal, passt sich Stil-Anforderungen an.",
            "icon": "bi-pencil",
            "color": "#ec4899",
            "sort_order": 2,
            "base_system_prompt": """Du bist ein erfahrener Autor. Deine Aufgaben:

SCHREIBEN:
- Erstelle qualitativ hochwertigen Content
- Halte dich an Vorgaben (Outline, Struktur, Stil)
- Erreiche die Ziel-Wortanzahl

STIL:
- Passe den Ton an Zielgruppe und Genre an
- Achte auf Konsistenz mit vorherigem Content
- Verwende lebendige, präzise Sprache

QUALITÄT:
- Vermeide Wiederholungen und Füllwörter
- Baue logische Übergänge ein
- Schreibe abgeschlossene, runde Texte""",
        },
        {
            "code": "reviewer",
            "name": "Reviewer",
            "name_de": "Reviewer",
            "category": "core",
            "description": "Provides constructive feedback and improvement suggestions.",
            "description_de": "Gibt konstruktives Feedback und Verbesserungsvorschläge.",
            "icon": "bi-chat-left-text",
            "color": "#06b6d4",
            "sort_order": 3,
            "base_system_prompt": """Du bist ein erfahrener Editor und Reviewer. Deine Aufgaben:

ANALYSE:
- Lies den Content sorgfältig und vollständig
- Identifiziere Stärken und Schwächen
- Bewerte Struktur, Stil und Inhalt

FEEDBACK:
- Gib konkretes, umsetzbares Feedback
- Benenne spezifische Textstellen
- Schlage konkrete Verbesserungen vor

STIL:
- Sei konstruktiv und ermutigend
- Priorisiere wichtiges Feedback
- Erkläre das "Warum" hinter Kritik""",
        },
        {
            "code": "critic",
            "name": "Critic",
            "name_de": "Kritiker",
            "category": "core",
            "description": "Critical analysis, finds weaknesses, questions assumptions.",
            "description_de": "Kritische Analyse, findet Schwachstellen, hinterfragt Annahmen.",
            "icon": "bi-eye",
            "color": "#ef4444",
            "sort_order": 4,
            "base_system_prompt": """Du bist ein kritischer Analyst. Deine Aufgaben:

KRITISCHE PRÜFUNG:
- Suche aktiv nach Schwachstellen
- Hinterfrage Annahmen und Logik
- Identifiziere Inkonsistenzen

ANALYSE:
- Prüfe auf logische Fehler
- Bewerte Glaubwürdigkeit und Plausibilität
- Finde fehlende Informationen

OUTPUT:
- Benenne Probleme konkret und direkt
- Priorisiere nach Schweregrad
- Biete Lösungsansätze an

Sei ehrlich und direkt, aber fair.""",
        },
        {
            "code": "quality_manager",
            "name": "Quality Manager",
            "name_de": "Qualitätsmanager",
            "category": "core",
            "description": "Ensures consistency, standards compliance, final quality checks.",
            "description_de": "Stellt Konsistenz sicher, prüft Standards, finale Qualitätskontrolle.",
            "icon": "bi-check2-circle",
            "color": "#10b981",
            "sort_order": 5,
            "base_system_prompt": """Du bist ein Quality Manager. Deine Aufgaben:

KONSISTENZ:
- Prüfe Konsistenz im gesamten Dokument
- Achte auf Namen, Daten, Fakten
- Stelle einheitliche Terminologie sicher

STANDARDS:
- Prüfe Einhaltung von Formatvorgaben
- Kontrolliere Zitationen und Referenzen
- Verifiziere Vollständigkeit

QUALITÄTSBERICHT:
- Erstelle strukturierte Checkliste
- Markiere kritische Probleme
- Gib Freigabe-Empfehlung

Sei gründlich und systematisch.""",
        },
    ]

    # ==========================================================================
    # SPECIALIZED WRITERS
    # ==========================================================================
    SPECIALIZED_WRITERS = [
        {
            "code": "writer_character",
            "name": "Character Writer",
            "name_de": "Charakter-Autor",
            "category": "writer_specialized",
            "parent_code": "writer",
            "description": "Specialized in character development, dialogue, and character-driven scenes.",
            "description_de": "Spezialisiert auf Charakterentwicklung, Dialoge und charaktergetriebene Szenen.",
            "icon": "bi-person",
            "color": "#f472b6",
            "sort_order": 10,
            "base_system_prompt": """Du bist ein Autor spezialisiert auf Charakterentwicklung.

CHARAKTERE:
- Erschaffe authentische, dreidimensionale Charaktere
- Zeige Persönlichkeit durch Handlung und Dialog
- Entwickle konsistente Charakterstimmen

DIALOG:
- Schreibe natürliche, charakterspezifische Dialoge
- Nutze Subtext und unausgesprochene Bedeutung
- Vermeide Exposition-Dumps

ENTWICKLUNG:
- Zeige Charakterwachstum durch Handlung
- Baue innere Konflikte ein
- Halte Motivationen konsistent""",
        },
        {
            "code": "writer_pov",
            "name": "POV Writer",
            "name_de": "Perspektiv-Autor",
            "category": "writer_specialized",
            "parent_code": "writer",
            "description": "Specialized in specific narrative perspectives (1st person, 3rd limited, omniscient).",
            "description_de": "Spezialisiert auf bestimmte Erzählperspektiven (Ich-Perspektive, personaler Erzähler, auktorial).",
            "icon": "bi-eye",
            "color": "#a855f7",
            "sort_order": 11,
            "base_system_prompt": """Du bist ein Autor spezialisiert auf Erzählperspektiven.

PERSPEKTIVE:
- Halte die gewählte Perspektive konsequent ein
- Beschränke Wissen auf das, was der POV-Charakter weiß
- Filtere alle Beschreibungen durch die POV-Linse

ICH-PERSPEKTIVE:
- Authentische innere Stimme
- Persönliche Färbung aller Beobachtungen
- Unmittelbare emotionale Reaktionen

PERSONALER ERZÄHLER:
- Enge Bindung an POV-Charakter
- Gedanken und Gefühle nur des POV-Charakters
- "Kameraposition" nahe am Charakter""",
        },
        {
            "code": "writer_dialog",
            "name": "Dialog Writer",
            "name_de": "Dialog-Autor",
            "category": "writer_specialized",
            "parent_code": "writer",
            "description": "Specialized in realistic, engaging dialogue.",
            "description_de": "Spezialisiert auf realistische, fesselnde Dialoge.",
            "icon": "bi-chat-quote",
            "color": "#14b8a6",
            "sort_order": 12,
            "base_system_prompt": """Du bist ein Autor spezialisiert auf Dialoge.

NATÜRLICHKEIT:
- Schreibe wie Menschen wirklich sprechen
- Nutze Unterbrechungen, unvollständige Sätze
- Vermeide perfekte Grammatik in Dialogen

SUBTEXT:
- Was wird NICHT gesagt ist oft wichtiger
- Baue Spannung durch das Unausgesprochene
- Zeige Konflikte subtil

CHARAKTERSTIMMEN:
- Jeder Charakter hat eigene Sprachmuster
- Vokabular passt zu Bildung/Herkunft
- Sprechrhythmus charakterisiert""",
        },
        {
            "code": "writer_action",
            "name": "Action Writer",
            "name_de": "Action-Autor",
            "category": "writer_specialized",
            "parent_code": "writer",
            "description": "Specialized in action sequences, pacing, and tension.",
            "description_de": "Spezialisiert auf Action-Sequenzen, Pacing und Spannung.",
            "icon": "bi-lightning-charge",
            "color": "#f97316",
            "sort_order": 13,
            "base_system_prompt": """Du bist ein Autor spezialisiert auf Action und Spannung.

PACING:
- Kurze Sätze für schnelle Action
- Variiere Tempo für Spannung
- Baue zu Höhepunkten auf

ACTION:
- Klare, präzise Bewegungen beschreiben
- Räumliche Orientierung behalten
- Physische Konsequenzen zeigen

SPANNUNG:
- Nutze Cliffhanger und Wendungen
- Halte Stakes hoch
- Baue Unsicherheit ein""",
        },
        {
            "code": "writer_description",
            "name": "Description Writer",
            "name_de": "Beschreibungs-Autor",
            "category": "writer_specialized",
            "parent_code": "writer",
            "description": "Specialized in vivid descriptions, worldbuilding, and atmosphere.",
            "description_de": "Spezialisiert auf lebendige Beschreibungen, Weltenbau und Atmosphäre.",
            "icon": "bi-image",
            "color": "#84cc16",
            "sort_order": 14,
            "base_system_prompt": """Du bist ein Autor spezialisiert auf Beschreibungen und Atmosphäre.

SENSORIK:
- Nutze alle fünf Sinne
- Zeige, statt zu erzählen
- Wähle spezifische, konkrete Details

ATMOSPHÄRE:
- Stimmung durch Setting vermitteln
- Wetter und Umgebung als emotionale Spiegel
- Subtile Vorahnungen einbauen

WELTENBAU:
- Details organisch einweben
- Konsistenz mit etabliertem Setting
- Lebendige, glaubwürdige Orte""",
        },
        {
            "code": "writer_scientific",
            "name": "Scientific Writer",
            "name_de": "Wissenschaftlicher Autor",
            "category": "writer_specialized",
            "parent_code": "writer",
            "description": "Specialized in academic/scientific writing style.",
            "description_de": "Spezialisiert auf akademischen/wissenschaftlichen Schreibstil.",
            "icon": "bi-mortarboard",
            "color": "#6366f1",
            "sort_order": 15,
            "base_system_prompt": """Du bist ein Autor spezialisiert auf wissenschaftliches Schreiben.

STIL:
- Formal und sachlich
- Passiv oder unpersönliche Formulierungen
- Präzise Fachterminologie

STRUKTUR:
- Klare Argumentationslinien
- Logische Absatzübergänge
- These → Begründung → Beleg → Schlussfolgerung

ZITATION:
- Alle Behauptungen belegen
- Korrekter Zitationsstil (APA, etc.)
- Paraphrasieren statt wörtlich zitieren""",
        },
    ]

    # ==========================================================================
    # PIPELINE TEMPLATES
    # ==========================================================================
    PIPELINE_TEMPLATES = [
        {
            "code": "write_chapter",
            "name": "Write Chapter",
            "name_de": "Kapitel schreiben",
            "description": "Full pipeline for writing a chapter with research, drafting, review, and quality check.",
            "pipeline_config": [
                {"agent_role": "researcher", "tier": "bulk", "order": 1},
                {"agent_role": "writer", "tier": "standard", "order": 2},
                {"agent_role": "reviewer", "tier": "standard", "order": 3},
                {"agent_role": "critic", "tier": "standard", "order": 4},
                {"agent_role": "writer", "tier": "premium", "order": 5, "label": "Revision"},
                {"agent_role": "quality_manager", "tier": "standard", "order": 6},
            ],
            "estimated_duration_seconds": 180,
            "estimated_cost_factor": 2.5,
            "sort_order": 1,
        },
        {
            "code": "quick_draft",
            "name": "Quick Draft",
            "name_de": "Schneller Entwurf",
            "description": "Fast draft without full review cycle.",
            "pipeline_config": [
                {"agent_role": "researcher", "tier": "bulk", "order": 1},
                {"agent_role": "writer", "tier": "standard", "order": 2},
            ],
            "estimated_duration_seconds": 60,
            "estimated_cost_factor": 0.8,
            "sort_order": 2,
        },
        {
            "code": "review_only",
            "name": "Review & Improve",
            "name_de": "Review & Verbessern",
            "description": "Review and improve existing content.",
            "pipeline_config": [
                {"agent_role": "reviewer", "tier": "standard", "order": 1},
                {"agent_role": "critic", "tier": "standard", "order": 2},
                {"agent_role": "writer", "tier": "premium", "order": 3, "label": "Revision"},
            ],
            "estimated_duration_seconds": 120,
            "estimated_cost_factor": 1.5,
            "sort_order": 3,
        },
        {
            "code": "quality_check",
            "name": "Quality Check",
            "name_de": "Qualitätsprüfung",
            "description": "Final quality check and consistency review.",
            "pipeline_config": [
                {"agent_role": "quality_manager", "tier": "standard", "order": 1},
                {"agent_role": "critic", "tier": "premium", "order": 2},
            ],
            "estimated_duration_seconds": 90,
            "estimated_cost_factor": 1.0,
            "sort_order": 4,
        },
        {
            "code": "character_scene",
            "name": "Character Scene",
            "name_de": "Charakter-Szene",
            "description": "Character-focused scene with specialized writer.",
            "pipeline_config": [
                {"agent_role": "researcher", "tier": "bulk", "order": 1},
                {"agent_role": "writer_character", "tier": "standard", "order": 2},
                {"agent_role": "reviewer", "tier": "standard", "order": 3},
                {"agent_role": "writer_character", "tier": "premium", "order": 4, "label": "Polish"},
            ],
            "estimated_duration_seconds": 150,
            "estimated_cost_factor": 2.0,
            "sort_order": 5,
        },
        {
            "code": "scientific_section",
            "name": "Scientific Section",
            "name_de": "Wissenschaftlicher Abschnitt",
            "description": "Academic writing pipeline with research and formal review.",
            "pipeline_config": [
                {"agent_role": "researcher", "tier": "standard", "order": 1},
                {"agent_role": "writer_scientific", "tier": "standard", "order": 2},
                {"agent_role": "critic", "tier": "standard", "order": 3},
                {"agent_role": "writer_scientific", "tier": "premium", "order": 4, "label": "Revision"},
                {"agent_role": "quality_manager", "tier": "premium", "order": 5},
            ],
            "estimated_duration_seconds": 200,
            "estimated_cost_factor": 3.0,
            "sort_order": 6,
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write("Setting up Universal Agent Architecture...")
        
        # Create LLM Tiers
        tier_count = self._create_llm_tiers()
        self.stdout.write(f"  ✓ Created/updated {tier_count} LLM Tiers")
        
        # Create Core Roles
        core_count = self._create_roles(self.CORE_ROLES)
        self.stdout.write(f"  ✓ Created/updated {core_count} Core Agent Roles")
        
        # Create Specialized Writers
        writer_count = self._create_roles(self.SPECIALIZED_WRITERS, with_parent=True)
        self.stdout.write(f"  ✓ Created/updated {writer_count} Specialized Writers")
        
        # Create Pipeline Templates
        pipeline_count = self._create_pipelines()
        self.stdout.write(f"  ✓ Created/updated {pipeline_count} Pipeline Templates")
        
        self.stdout.write(self.style.SUCCESS("\n✅ Universal Agent Architecture setup complete!"))
        
        # Summary
        self.stdout.write("\n📊 Summary:")
        self.stdout.write(f"   LLM Tiers: {LlmTier.objects.count()}")
        self.stdout.write(f"   Agent Roles: {AgentRole.objects.count()}")
        self.stdout.write(f"   - Core: {AgentRole.objects.filter(category='core').count()}")
        self.stdout.write(f"   - Specialized Writers: {AgentRole.objects.filter(category='writer_specialized').count()}")
        self.stdout.write(f"   Pipeline Templates: {AgentPipelineTemplate.objects.count()}")

    def _create_llm_tiers(self):
        count = 0
        for tier_data in self.LLM_TIERS:
            tier, created = LlmTier.objects.update_or_create(
                code=tier_data["code"],
                defaults={
                    "name": tier_data["name"],
                    "name_de": tier_data["name_de"],
                    "description": tier_data["description"],
                    "cost_factor": tier_data["cost_factor"],
                    "priority": tier_data["priority"],
                    "default_temperature": tier_data["default_temperature"],
                    "default_max_tokens": tier_data["default_max_tokens"],
                    "icon": tier_data["icon"],
                    "color": tier_data["color"],
                    "badge_class": tier_data["badge_class"],
                    "sort_order": tier_data["sort_order"],
                    "is_active": True,
                }
            )
            count += 1
        return count

    def _create_roles(self, roles_data, with_parent=False):
        count = 0
        for role_data in roles_data:
            parent = None
            if with_parent and role_data.get("parent_code"):
                parent = AgentRole.objects.filter(code=role_data["parent_code"]).first()
            
            role, created = AgentRole.objects.update_or_create(
                code=role_data["code"],
                defaults={
                    "name": role_data["name"],
                    "name_de": role_data["name_de"],
                    "category": role_data["category"],
                    "description": role_data["description"],
                    "description_de": role_data.get("description_de", ""),
                    "base_system_prompt": role_data["base_system_prompt"],
                    "icon": role_data["icon"],
                    "color": role_data["color"],
                    "sort_order": role_data["sort_order"],
                    "parent_role": parent,
                    "is_active": True,
                }
            )
            count += 1
        return count

    def _create_pipelines(self):
        count = 0
        for pipeline_data in self.PIPELINE_TEMPLATES:
            pipeline, created = AgentPipelineTemplate.objects.update_or_create(
                code=pipeline_data["code"],
                defaults={
                    "name": pipeline_data["name"],
                    "name_de": pipeline_data["name_de"],
                    "description": pipeline_data["description"],
                    "pipeline_config": pipeline_data["pipeline_config"],
                    "estimated_duration_seconds": pipeline_data["estimated_duration_seconds"],
                    "estimated_cost_factor": pipeline_data["estimated_cost_factor"],
                    "sort_order": pipeline_data["sort_order"],
                    "is_active": True,
                }
            )
            count += 1
        return count
