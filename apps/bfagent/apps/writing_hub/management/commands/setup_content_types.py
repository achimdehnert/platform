"""
Management command to set up content types for Writing Hub
Creates DomainTypes (Roman, Essay, Wissenschaft) with their phases and LLM prompts
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.bfagent.models import DomainArt, DomainType, DomainPhase, WorkflowPhase


class Command(BaseCommand):
    help = "Set up content types (Roman, Essay, Wissenschaft) with phases and LLM prompts"

    # =========================================================================
    # CONTENT TYPE DEFINITIONS
    # =========================================================================
    
    CONTENT_TYPES = {
        "novel": {
            "name": "novel",
            "slug": "novel",
            "display_name": "Roman",
            "description": "Längere Erzählung mit komplexer Handlung, Charakterentwicklung und Weltenbau",
            "icon": "book",
            "color": "primary",
            "sort_order": 1,
            "config": {
                "default_word_count": 80000,
                "min_chapters": 10,
                "max_chapters": 50,
                "has_characters": True,
                "has_world_building": True,
                "has_outline": True,
                "structure_frameworks": ["three_act", "hero_journey", "save_the_cat", "seven_point"],
            }
        },
        "essay": {
            "name": "essay",
            "slug": "essay",
            "display_name": "Essay",
            "description": "Argumentativer oder reflektierender Text zu einem Thema",
            "icon": "file-text",
            "color": "info",
            "sort_order": 2,
            "config": {
                "default_word_count": 3000,
                "min_sections": 3,
                "max_sections": 10,
                "has_characters": False,
                "has_world_building": False,
                "has_outline": True,
                "structure_frameworks": ["five_paragraph", "argumentative", "compare_contrast", "cause_effect"],
            }
        },
        "scientific": {
            "name": "scientific",
            "slug": "scientific",
            "display_name": "Wissenschaftliche Arbeit",
            "description": "Akademische Arbeit mit Forschungsfrage, Methodik und Quellenarbeit",
            "icon": "mortarboard",
            "color": "success",
            "sort_order": 3,
            "config": {
                "default_word_count": 15000,
                "min_sections": 5,
                "max_sections": 15,
                "has_characters": False,
                "has_world_building": False,
                "has_outline": True,
                "has_citations": True,
                "has_abstract": True,
                "structure_frameworks": ["imrad", "thesis", "literature_review"],
            }
        },
    }

    # =========================================================================
    # PHASE DEFINITIONS
    # =========================================================================
    
    PHASES = {
        # Universal phases
        "concept": {
            "name": "concept",
            "description": "Grundidee und Konzept entwickeln",
            "icon": "lightbulb",
            "color": "warning",
        },
        "research": {
            "name": "research",
            "description": "Recherche und Quellensammlung",
            "icon": "search",
            "color": "info",
        },
        "planning": {
            "name": "planning",
            "description": "Planung und Strukturierung",
            "icon": "clipboard",
            "color": "primary",
        },
        "characters": {
            "name": "characters",
            "description": "Charakterentwicklung",
            "icon": "people",
            "color": "success",
        },
        "world_building": {
            "name": "world_building",
            "description": "Weltenbau und Setting",
            "icon": "globe",
            "color": "info",
        },
        "outline": {
            "name": "outline",
            "description": "Struktur und Gliederung",
            "icon": "list-ol",
            "color": "secondary",
        },
        "writing": {
            "name": "writing",
            "description": "Schreiben des Inhalts",
            "icon": "pencil",
            "color": "primary",
        },
        "citations": {
            "name": "citations",
            "description": "Zitate und Referenzen",
            "icon": "quote",
            "color": "dark",
        },
        "abstract": {
            "name": "abstract",
            "description": "Abstract/Zusammenfassung",
            "icon": "file-earmark-text",
            "color": "secondary",
        },
        "review": {
            "name": "review",
            "description": "Überprüfung und Korrektur",
            "icon": "check2-circle",
            "color": "warning",
        },
        "export": {
            "name": "export",
            "description": "Export und Veröffentlichung",
            "icon": "download",
            "color": "success",
        },
    }

    # =========================================================================
    # CONTENT TYPE → PHASE MAPPING WITH LLM PROMPTS
    # =========================================================================
    
    CONTENT_TYPE_PHASES = {
        "novel": [
            {
                "phase": "concept",
                "order": 10,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein erfahrener Romanautor und Lektor.
Hilf beim Entwickeln einer fesselnden Prämisse für einen {genre} Roman.
Berücksichtige: Zielgruppe, Genre-Konventionen, emotionale Resonanz.
Liefere konkrete, umsetzbare Vorschläge.""",
                    "llm_user_template": "Entwickle eine Prämisse für: {title}\nGenre: {genre}\nZielgruppe: {target_audience}\nBisherige Idee: {description}",
                    "fields": ["title", "genre", "target_audience", "description", "themes", "tagline"],
                }
            },
            {
                "phase": "characters",
                "order": 20,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Experte für Charakterentwicklung in der Belletristik.
Erstelle vielschichtige, glaubwürdige Charaktere mit:
- Klarer Motivation und innerem Konflikt
- Stärken und Schwächen
- Charakterbogen und Entwicklungspotential
- Beziehungen zu anderen Charakteren""",
                    "llm_user_template": "Erstelle einen {role} Charakter für: {project_title}\nGenre: {genre}\nName: {name}\nBisherige Beschreibung: {description}",
                    "fields": ["name", "role", "age", "appearance", "personality", "motivation", "conflict", "background", "arc"],
                }
            },
            {
                "phase": "world_building",
                "order": 30,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Weltenbau-Spezialist für Romane.
Entwickle konsistente, immersive Welten mit:
- Geografie und Umgebung
- Gesellschaft und Kultur
- Regeln und Systeme (Magie, Technologie)
- Geschichte und Hintergrund""",
                    "llm_user_template": "Entwickle die Welt '{name}' für: {project_title}\nGenre: {genre}\nTyp: {world_type}",
                    "fields": ["name", "world_type", "setting_details", "geography", "culture", "technology_level", "magic_system", "politics", "history"],
                }
            },
            {
                "phase": "outline",
                "order": 40,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Strukturexperte für Romanhandlungen.
Erstelle einen Kapitel-Outline mit:
- Klarer Drei-Akt-Struktur oder gewähltem Framework
- Spannungsbogen und Wendepunkte
- Charakterentwicklung pro Kapitel
- Scene-Beats und Konflikte""",
                    "llm_user_template": "Erstelle einen Outline für: {project_title}\nFramework: {framework}\nAnzahl Kapitel: {chapter_count}\nPrämisse: {premise}",
                    "fields": ["framework", "acts", "chapters", "beats"],
                }
            },
            {
                "phase": "writing",
                "order": 50,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein erfahrener {genre} Autor.
Schreibe lebendige, fesselnde Prosa mit:
- Show, don't tell
- Lebendigen Dialogen
- Atmosphärischen Beschreibungen
- Konsistentem Erzählton
Zielwortanzahl: {target_words} Wörter.""",
                    "llm_user_template": "Schreibe Kapitel {chapter_number}: {chapter_title}\nOutline: {chapter_outline}\nVorheriges Kapitel: {previous_summary}\nAnwesende Charaktere: {characters}",
                    "fields": ["content", "word_count"],
                }
            },
            {
                "phase": "review",
                "order": 60,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein professioneller Lektor.
Überprüfe auf:
- Konsistenz (Charaktere, Plot, Timeline)
- Pacing und Spannungsbogen
- Dialoge und Erzählstimme
- Grammatik und Stil
Gib konkrete Verbesserungsvorschläge.""",
                    "llm_user_template": "Überprüfe Kapitel {chapter_number}:\n{content}\n\nFokus: {review_focus}",
                    "fields": ["feedback", "suggestions", "score"],
                }
            },
            {
                "phase": "export",
                "order": 70,
                "is_required": True,
                "config": {
                    "export_formats": ["docx", "pdf", "epub", "markdown"],
                }
            },
        ],
        "essay": [
            {
                "phase": "concept",
                "order": 10,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein erfahrener Essay-Autor und Rhetorik-Experte.
Hilf beim Formulieren einer klaren, interessanten These.
Berücksichtige: Aktualität, Kontroverse, Originalität.""",
                    "llm_user_template": "Entwickle eine These zum Thema: {topic}\nPerspektive: {perspective}\nZielgruppe: {target_audience}",
                    "fields": ["topic", "thesis", "perspective", "target_audience"],
                }
            },
            {
                "phase": "research",
                "order": 20,
                "is_required": False,
                "config": {
                    "llm_system_prompt": """Du bist ein Recherche-Assistent.
Identifiziere relevante Quellen, Argumente und Gegenargumente.
Strukturiere die Recherche nach Hauptpunkten.""",
                    "llm_user_template": "Recherchiere zum Thema: {topic}\nThese: {thesis}\nGesuchte Aspekte: {aspects}",
                    "fields": ["sources", "key_points", "counter_arguments"],
                }
            },
            {
                "phase": "outline",
                "order": 30,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Strukturexperte für argumentative Texte.
Erstelle eine klare Gliederung mit:
- Einleitung mit Hook und These
- Hauptargumente mit Belegen
- Gegenargumente und Widerlegung
- Schlussfolgerung""",
                    "llm_user_template": "Erstelle eine Gliederung für Essay: {title}\nThese: {thesis}\nHauptargumente: {main_points}",
                    "fields": ["introduction", "main_arguments", "counter_arguments", "conclusion"],
                }
            },
            {
                "phase": "writing",
                "order": 40,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein versierter Essay-Autor.
Schreibe klar, überzeugend und stilistisch ansprechend.
Verwende rhetorische Mittel, Beispiele und logische Argumentation.
Zielwortanzahl: {target_words} Wörter.""",
                    "llm_user_template": "Schreibe Abschnitt '{section_title}' für Essay: {title}\nInhalt laut Gliederung: {section_outline}\nThese: {thesis}",
                    "fields": ["content", "word_count"],
                }
            },
            {
                "phase": "review",
                "order": 50,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Lektor für argumentative Texte.
Überprüfe auf:
- Argumentationslogik und Konsistenz
- Überzeugungskraft der Belege
- Stilistische Qualität
- Übergänge zwischen Abschnitten""",
                    "llm_user_template": "Überprüfe Essay-Abschnitt:\n{content}\n\nThese: {thesis}",
                    "fields": ["feedback", "suggestions", "logic_score", "style_score"],
                }
            },
            {
                "phase": "export",
                "order": 60,
                "is_required": True,
                "config": {
                    "export_formats": ["docx", "pdf", "markdown"],
                }
            },
        ],
        "scientific": [
            {
                "phase": "concept",
                "order": 10,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein wissenschaftlicher Methodenexperte.
Hilf beim Formulieren einer präzisen Forschungsfrage und Hypothese.
Berücksichtige: Forschungslücke, Machbarkeit, wissenschaftliche Relevanz.""",
                    "llm_user_template": "Entwickle eine Forschungsfrage zum Thema: {topic}\nFachgebiet: {field}\nVorläufige Idee: {description}",
                    "fields": ["topic", "field", "research_question", "hypothesis", "objectives"],
                }
            },
            {
                "phase": "research",
                "order": 20,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein wissenschaftlicher Literaturrecherche-Experte.
Identifiziere relevante Studien, Theorien und Methoden.
Strukturiere nach: Grundlagenwerke, aktuelle Forschung, Methodenpapiere.""",
                    "llm_user_template": "Literaturrecherche für: {research_question}\nFachgebiet: {field}\nSuchbegriffe: {keywords}",
                    "fields": ["literature_review", "key_sources", "research_gap", "theoretical_framework"],
                }
            },
            {
                "phase": "planning",
                "order": 25,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Experte für wissenschaftliche Methodik.
Hilf bei der Planung von:
- Forschungsdesign
- Datenerhebungsmethoden
- Analysemethoden
- Ethische Überlegungen""",
                    "llm_user_template": "Plane Methodik für: {research_question}\nHypothese: {hypothesis}\nVerfügbare Ressourcen: {resources}",
                    "fields": ["methodology", "data_collection", "analysis_methods", "limitations"],
                }
            },
            {
                "phase": "outline",
                "order": 30,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Experte für wissenschaftliche Textstruktur.
Erstelle eine Gliederung nach akademischen Standards:
- IMRaD (Introduction, Methods, Results, Discussion)
- oder angepasst für theoretische Arbeiten""",
                    "llm_user_template": "Erstelle wissenschaftliche Gliederung für: {title}\nTyp: {paper_type}\nForschungsfrage: {research_question}",
                    "fields": ["introduction", "literature_review", "methodology", "results", "discussion", "conclusion"],
                }
            },
            {
                "phase": "writing",
                "order": 40,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein wissenschaftlicher Autor.
Schreibe in akademischem Stil:
- Präzise und objektiv
- Mit korrekter Fachterminologie
- Logisch strukturiert
- Mit Quellenverweisen (Platzhalter: [Quelle])
Zielwortanzahl: {target_words} Wörter.""",
                    "llm_user_template": "Schreibe Abschnitt '{section_title}' für: {title}\nInhalt laut Gliederung: {section_outline}\nRelevante Literatur: {sources}",
                    "fields": ["content", "word_count", "citations_needed"],
                }
            },
            {
                "phase": "citations",
                "order": 50,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Experte für wissenschaftliches Zitieren.
Hilf bei:
- Korrekter Zitierweise (APA, MLA, Chicago, etc.)
- Literaturverzeichnis-Erstellung
- Plagiatsvermeidung""",
                    "llm_user_template": "Formatiere Zitate für Abschnitt:\n{content}\nZitierstil: {citation_style}\nQuellen: {sources}",
                    "fields": ["formatted_citations", "bibliography"],
                }
            },
            {
                "phase": "abstract",
                "order": 55,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein Experte für wissenschaftliche Abstracts.
Erstelle ein prägnantes Abstract mit:
- Hintergrund und Forschungsfrage
- Methodik
- Hauptergebnisse
- Schlussfolgerungen
Max. 250 Wörter.""",
                    "llm_user_template": "Erstelle Abstract für: {title}\nForschungsfrage: {research_question}\nMethodik: {methodology}\nErgebnisse: {results_summary}",
                    "fields": ["abstract", "keywords"],
                }
            },
            {
                "phase": "review",
                "order": 60,
                "is_required": True,
                "config": {
                    "llm_system_prompt": """Du bist ein wissenschaftlicher Gutachter.
Überprüfe auf:
- Wissenschaftliche Stringenz
- Methodische Korrektheit
- Argumentationslogik
- Formale Anforderungen
- Sprachliche Qualität""",
                    "llm_user_template": "Überprüfe wissenschaftlichen Text:\n{content}\n\nPrüfkriterien: {criteria}",
                    "fields": ["feedback", "methodology_score", "argumentation_score", "formal_score"],
                }
            },
            {
                "phase": "export",
                "order": 70,
                "is_required": True,
                "config": {
                    "export_formats": ["docx", "pdf", "latex"],
                }
            },
        ],
    }

    def handle(self, *args, **options):
        self.stdout.write("Setting up Writing Hub content types...")
        
        with transaction.atomic():
            # 1. Get or create DomainArt for writing
            domain_art = self._setup_domain_art()
            
            # 2. Create workflow phases
            phases = self._setup_workflow_phases()
            
            # 3. Create content types (DomainTypes)
            content_types = self._setup_content_types(domain_art)
            
            # 4. Link phases to content types (DomainPhases)
            self._setup_domain_phases(content_types, phases)
        
        self.stdout.write(self.style.SUCCESS("✅ Content types setup complete!"))

    def _setup_domain_art(self):
        """Get or create the writing DomainArt"""
        domain_art, created = DomainArt.objects.update_or_create(
            slug="writing-hub",
            defaults={
                "name": "writing_hub",
                "display_name": "Writing Hub",
                "description": "Schreib-Hub für Romane, Essays, wissenschaftliche Arbeiten und mehr",
                "icon": "pencil-square",
                "color": "primary",
                "is_active": True,
                "is_experimental": False,
            }
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action} DomainArt: {domain_art}")
        return domain_art

    def _setup_workflow_phases(self):
        """Create all workflow phases"""
        phases = {}
        for key, data in self.PHASES.items():
            phase, created = WorkflowPhase.objects.update_or_create(
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "icon": data["icon"],
                    "color": data["color"],
                    "is_active": True,
                }
            )
            phases[key] = phase
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} WorkflowPhase: {phase.name}")
        return phases

    def _setup_content_types(self, domain_art):
        """Create content types as DomainTypes"""
        content_types = {}
        for key, data in self.CONTENT_TYPES.items():
            content_type, created = DomainType.objects.update_or_create(
                domain_art=domain_art,
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "display_name": data["display_name"],
                    "description": data["description"],
                    "icon": data["icon"],
                    "color": data["color"],
                    "sort_order": data["sort_order"],
                    "config": data["config"],
                    "is_active": True,
                }
            )
            content_types[key] = content_type
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} ContentType: {content_type.display_name}")
        return content_types

    def _setup_domain_phases(self, content_types, phases):
        """Link phases to content types with LLM configs"""
        for content_key, phase_configs in self.CONTENT_TYPE_PHASES.items():
            content_type = content_types.get(content_key)
            if not content_type:
                continue
            
            for phase_config in phase_configs:
                phase_key = phase_config["phase"]
                phase = phases.get(phase_key)
                if not phase:
                    continue
                
                domain_phase, created = DomainPhase.objects.update_or_create(
                    domain_type=content_type,
                    workflow_phase=phase,
                    defaults={
                        "sort_order": phase_config["order"],
                        "is_required": phase_config["is_required"],
                        "config": phase_config.get("config", {}),
                        "is_active": True,
                    }
                )
                action = "Created" if created else "Updated"
                self.stdout.write(f"    {action} {content_type.display_name} → {phase.name}")
