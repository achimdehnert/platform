"""
Management command to add Groq LLMs to the database.

Groq provides fast inference on open-source models via their API.
API Endpoint: https://api.groq.com/openai/v1/chat/completions

Current Models from Groq API (January 2026):
- llama-3.1-8b-instant (Meta, 131K context) - Fast, cheap
- llama-3.3-70b-versatile (Meta, 131K context) - Powerful reasoning
- meta-llama/llama-4-scout-17b-16e-instruct (Meta, 131K context) - Latest Llama 4
- meta-llama/llama-4-maverick-17b-128e-instruct (Meta, 131K context) - Latest Llama 4
- qwen/qwen3-32b (Alibaba, 131K context) - Strong multilingual
- moonshotai/kimi-k2-instruct (Moonshot, 131K context) - Good reasoning
- groq/compound (Groq, 131K context) - Groq's own model
- meta-llama/llama-guard-4-12b (Meta, 131K context) - Safety model

DEPRECATED (removed):
- gemma2-9b-it, llama3-8b-8192, llama3-70b-8192, llama-guard-3-8b

Usage:
    python manage.py add_groq_llms
    python manage.py add_groq_llms --api-key YOUR_GROQ_API_KEY
    python manage.py add_groq_llms --clean  # Remove old, add new
"""

import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.bfagent.models import Llms


class Command(BaseCommand):
    help = "Add Groq LLMs to the database (current models only, January 2026)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--api-key",
            type=str,
            default="",
            help="Groq API Key (or set GROQ_API_KEY env var)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing LLMs instead of skipping",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Remove all existing Groq LLMs before adding new ones",
        )

    def handle(self, *args, **options):
        api_key = options["api_key"] or os.environ.get("GROQ_API_KEY", "")
        update_existing = options["update"]
        clean_first = options["clean"]

        # Clean old Groq LLMs if requested
        if clean_first:
            deleted = Llms.objects.filter(provider="groq").delete()
            self.stdout.write(self.style.WARNING(f"🗑️  Cleaned old Groq LLMs: {deleted}"))

        # Current Groq LLM configurations (January 2026)
        # Source: https://api.groq.com/openai/v1/models
        # Pricing: https://groq.com/pricing/
        groq_llms = [
            # ═══════════════════════════════════════════════════════════════
            # Tier 1: Fast & Cheap (Simple bugs, quick tasks)
            # ═══════════════════════════════════════════════════════════════
            {
                "name": "Groq Llama 3.1 8B Instant",
                "provider": "groq",
                "llm_name": "llama-3.1-8b-instant",
                "max_tokens": 8192,
                "context_window": 131072,
                "temperature": 0.3,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00005,  # $0.05 per 1M input
                "description": (
                    "🚀 TIER 1 - SCHNELL | Context: 131K | Max: 131K | Owner: Meta\n\n"
                    "EINSATZZWECK:\n"
                    "• Einfache Bugs (Typos, Syntax-Fehler)\n"
                    "• Kleine Refactorings\n"
                    "• Code-Formatierung\n"
                    "• Kurze Erklärungen\n"
                    "• Docstrings generieren\n\n"
                    "STÄRKEN: Extrem schnell (<100ms), riesiger Context, sehr günstig\n"
                    "SCHWÄCHEN: Weniger Reasoning-Tiefe als größere Modelle"
                ),
                "tier": "tier_1",
            },
            {
                "name": "Groq Compound Mini",
                "provider": "groq",
                "llm_name": "groq/compound-mini",
                "max_tokens": 8192,
                "context_window": 131072,
                "temperature": 0.3,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00008,
                "description": (
                    "🚀 TIER 1 - SCHNELL | Context: 131K | Max: 8K | Owner: Groq\n\n"
                    "EINSATZZWECK:\n"
                    "• Schnelle Code-Completion\n"
                    "• Einfache Transformationen\n"
                    "• Unit-Test Generierung\n"
                    "• API Response Parsing\n\n"
                    "STÄRKEN: Groqs eigenes optimiertes Modell, sehr schnell\n"
                    "SCHWÄCHEN: Kleineres Completion-Limit"
                ),
                "tier": "tier_1",
            },
            # ═══════════════════════════════════════════════════════════════
            # Tier 2: Balanced (Moderate bugs, analysis)
            # ═══════════════════════════════════════════════════════════════
            {
                "name": "Groq Qwen3 32B",
                "provider": "groq",
                "llm_name": "qwen/qwen3-32b",
                "max_tokens": 8192,
                "context_window": 131072,
                "temperature": 0.5,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00015,
                "description": (
                    "⚡ TIER 2 - BALANCED | Context: 131K | Max: 40K | Owner: Alibaba\n\n"
                    "EINSATZZWECK:\n"
                    "• Moderate Bugs (Logic-Fehler)\n"
                    "• Code-Analyse\n"
                    "• API-Integration\n"
                    "• Multi-File Debugging\n"
                    "• Code Review\n\n"
                    "STÄRKEN: Starkes multilinguales Verständnis, gute Code-Qualität\n"
                    "SCHWÄCHEN: Etwas langsamer als Tier 1"
                ),
                "tier": "tier_2",
            },
            {
                "name": "Groq Kimi K2 Instruct",
                "provider": "groq",
                "llm_name": "moonshotai/kimi-k2-instruct",
                "max_tokens": 8192,
                "context_window": 131072,
                "temperature": 0.5,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00012,
                "description": (
                    "⚡ TIER 2 - BALANCED | Context: 131K | Max: 16K | Owner: Moonshot AI\n\n"
                    "EINSATZZWECK:\n"
                    "• Code-Refactoring\n"
                    "• Design Pattern Implementation\n"
                    "• Test-Coverage Analyse\n"
                    "• Documentation\n\n"
                    "STÄRKEN: Gutes Reasoning, lange Outputs möglich\n"
                    "SCHWÄCHEN: Weniger bekannt, evtl. Edge-Cases"
                ),
                "tier": "tier_2",
            },
            {
                "name": "Groq Compound",
                "provider": "groq",
                "llm_name": "groq/compound",
                "max_tokens": 8192,
                "context_window": 131072,
                "temperature": 0.5,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00010,
                "description": (
                    "⚡ TIER 2 - BALANCED | Context: 131K | Max: 8K | Owner: Groq\n\n"
                    "EINSATZZWECK:\n"
                    "• Allgemeine Code-Aufgaben\n"
                    "• Bug-Fixing mittlerer Komplexität\n"
                    "• Code-Erklärungen\n"
                    "• Optimierungsvorschläge\n\n"
                    "STÄRKEN: Groqs Flagship-Modell, optimiert für Speed\n"
                    "SCHWÄCHEN: Noch relativ neu"
                ),
                "tier": "tier_2",
            },
            # ═══════════════════════════════════════════════════════════════
            # Tier 3: Powerful (Complex bugs, architecture)
            # ═══════════════════════════════════════════════════════════════
            {
                "name": "Groq Llama 3.3 70B Versatile",
                "provider": "groq",
                "llm_name": "llama-3.3-70b-versatile",
                "max_tokens": 8192,
                "context_window": 131072,
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00059,
                "description": (
                    "🔥 TIER 3 - POWERFUL | Context: 131K | Max: 32K | Owner: Meta\n\n"
                    "EINSATZZWECK:\n"
                    "• Komplexe Multi-File Bugs\n"
                    "• Architektur-Probleme\n"
                    "• Performance-Optimierung\n"
                    "• Security-Audits\n"
                    "• System Design\n\n"
                    "STÄRKEN: Höchste Reasoning-Qualität, beste Code-Generierung\n"
                    "SCHWÄCHEN: Teurer, etwas langsamer"
                ),
                "tier": "tier_3",
            },
            {
                "name": "Groq Llama 4 Scout",
                "provider": "groq",
                "llm_name": "meta-llama/llama-4-scout-17b-16e-instruct",
                "max_tokens": 8192,
                "context_window": 131072,
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00025,
                "description": (
                    "🔥 TIER 3 - POWERFUL | Context: 131K | Max: 8K | Owner: Meta\n\n"
                    "EINSATZZWECK:\n"
                    "• Neueste Llama 4 Generation\n"
                    "• Komplexe Reasoning-Aufgaben\n"
                    "• Code-Architektur Analyse\n"
                    "• Technische Dokumentation\n\n"
                    "STÄRKEN: Llama 4 - State of the Art, 16 Experten MoE\n"
                    "SCHWÄCHEN: Noch sehr neu, evtl. Bugs"
                ),
                "tier": "tier_3",
            },
            {
                "name": "Groq Llama 4 Maverick",
                "provider": "groq",
                "llm_name": "meta-llama/llama-4-maverick-17b-128e-instruct",
                "max_tokens": 8192,
                "context_window": 131072,
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00030,
                "description": (
                    "🔥 TIER 3 - POWERFUL | Context: 131K | Max: 8K | Owner: Meta\n\n"
                    "EINSATZZWECK:\n"
                    "• Größtes Llama 4 Modell (128 Experten)\n"
                    "• Komplexeste Aufgaben\n"
                    "• Multi-Repo Refactoring\n"
                    "• Framework-Migration\n\n"
                    "STÄRKEN: Llama 4 Maverick - höchste Kapazität, 128 Experten MoE\n"
                    "SCHWÄCHEN: Am teuersten, noch sehr neu"
                ),
                "tier": "tier_3",
            },
            # ═══════════════════════════════════════════════════════════════
            # Special: Safety Models (Content Moderation)
            # ═══════════════════════════════════════════════════════════════
            {
                "name": "Groq Llama Guard 4 12B",
                "provider": "groq",
                "llm_name": "meta-llama/llama-guard-4-12b",
                "max_tokens": 1024,
                "context_window": 131072,
                "temperature": 0.1,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "cost_per_1k_tokens": 0.00005,
                "description": (
                    "🛡️ SAFETY MODEL | Context: 131K | Max: 1K | Owner: Meta\n\n"
                    "EINSATZZWECK:\n"
                    "• Content-Moderation\n"
                    "• Safety-Checks\n"
                    "• Input/Output-Validierung\n"
                    "• Code-Injection Erkennung\n\n"
                    "STÄRKEN: Spezialisiert auf Sicherheit, aktuellste Version\n"
                    "SCHWÄCHEN: Nicht für Code-Generierung geeignet"
                ),
                "tier": "safety",
            },
        ]

        api_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        created_count = 0
        updated_count = 0
        skipped_count = 0

        self.stdout.write(self.style.MIGRATE_HEADING("Adding official Groq LLMs..."))
        self.stdout.write("")

        for llm_config in groq_llms:
            tier = llm_config.pop("tier")  # Remove tier from config
            context_window = llm_config.pop("context_window", None)  # Remove, not in DB model
            
            existing = Llms.objects.filter(
                provider="groq",
                llm_name=llm_config["llm_name"]
            ).first()

            if existing:
                if update_existing:
                    for key, value in llm_config.items():
                        setattr(existing, key, value)
                    existing.api_endpoint = api_endpoint
                    if api_key:
                        existing.api_key = api_key
                    existing.updated_at = timezone.now()
                    existing.save()
                    self.stdout.write(
                        f"  ✏️  Updated: {llm_config['name']} ({tier})"
                    )
                    updated_count += 1
                else:
                    self.stdout.write(
                        f"  ⏭️  Skipped: {llm_config['name']} (already exists)"
                    )
                    skipped_count += 1
            else:
                Llms.objects.create(
                    **llm_config,
                    api_key=api_key,
                    api_endpoint=api_endpoint,
                    total_tokens_used=0,
                    total_requests=0,
                    total_cost=0.0,
                    is_active=True,
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Created: {llm_config['name']} ({tier})")
                )
                created_count += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Updated: {updated_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if not api_key:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  No API key set! Add your Groq API key via:"
                )
            )
            self.stdout.write("   1. Admin UI: http://localhost:8000/control-center/ai-config/llms/")
            self.stdout.write("   2. Or re-run: python manage.py add_groq_llms --api-key YOUR_KEY")
            self.stdout.write("")
            self.stdout.write("   Get your free API key at: https://console.groq.com/keys")

        # Show tier summary with context windows
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Groq Models - Tier Summary (January 2026):"))
        self.stdout.write("")
        self.stdout.write("  💚 TIER 1 - Schnell & Günstig:")
        self.stdout.write("     • llama-3.1-8b-instant    (131K) - Einfache Bugs, Typos")
        self.stdout.write("     • groq/compound-mini      (131K) - Code-Completion")
        self.stdout.write("")
        self.stdout.write("  💛 TIER 2 - Balanced:")
        self.stdout.write("     • qwen/qwen3-32b          (131K) - Code-Analyse, Multi-File")
        self.stdout.write("     • moonshotai/kimi-k2      (131K) - Refactoring, Docs")
        self.stdout.write("     • groq/compound           (131K) - Allgemeine Aufgaben")
        self.stdout.write("")
        self.stdout.write("  🔴 TIER 3 - Powerful:")
        self.stdout.write("     • llama-3.3-70b-versatile (131K) - Komplexe Bugs, Architektur")
        self.stdout.write("     • llama-4-scout           (131K) - State of the Art (16 MoE)")
        self.stdout.write("     • llama-4-maverick        (131K) - Höchste Kapazität (128 MoE)")
        self.stdout.write("")
        self.stdout.write("  🛡️  SAFETY:")
        self.stdout.write("     • llama-guard-4-12b       (131K) - Content-Moderation")
