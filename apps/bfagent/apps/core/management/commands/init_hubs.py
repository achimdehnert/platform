"""
Initialize Hub data in database with NavigationSection links.

Usage:
    python manage.py init_hubs

Idempotent - safe to run multiple times.
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Initialize Hub records with NavigationSection links"

    # Hub → NavigationSection mapping (section.code)
    HUB_SECTION_MAP = {
        "writing_hub": "WRITING",
        "cad_hub": "CAD", 
        "control_center": "CONTROL_CENTER",
        "expert_hub": "EXPERT",
        "research": "RESEARCH",
        "mcp_hub": "MCP",
        "media_hub": "MEDIA",
        "dlm_hub": "DLM",
    }

    DEFAULT_HUBS = [
        {
            "hub_id": "writing_hub",
            "name": "Writing Hub",
            "version": "2.0.0",
            "description": "AI-gestützte Bucherstellung mit Kapitel-, Charakter- und Outline-Generierung",
            "status": "production",
            "category": "content",
            "icon": "bi-book",
            "provides": ["views", "models", "handlers", "api"],
            "config": {"default_llm": "gpt-4o", "max_chapters": 50},
        },
        {
            "hub_id": "cad_hub",
            "name": "CAD Hub",
            "version": "1.5.0",
            "description": "Bauzeichnungs-Analyse und GAEB Export für Bauprojekte",
            "status": "production",
            "category": "engineering",
            "icon": "bi-building",
            "provides": ["views", "models", "handlers"],
        },
        {
            "hub_id": "control_center",
            "name": "Control Center",
            "version": "1.0.0",
            "description": "System-Administration, AI-Konfiguration und Hub-Verwaltung",
            "status": "production",
            "category": "system",
            "icon": "bi-gear",
            "provides": ["views", "models"],
        },
        {
            "hub_id": "expert_hub",
            "name": "Expert Hub",
            "version": "1.0.0",
            "description": "Explosionsschutz-Dokumentation und Zonen-Analyse",
            "status": "production",
            "category": "engineering",
            "icon": "bi-shield-exclamation",
            "provides": ["views", "models", "handlers"],
        },
        {
            "hub_id": "research",
            "name": "Research Hub",
            "version": "1.0.0",
            "description": "Deep Research mit Quellenanalyse und Synthese",
            "status": "production",
            "category": "research",
            "icon": "bi-search",
            "provides": ["views", "models", "api"],
        },
        {
            "hub_id": "mcp_hub",
            "name": "MCP Hub",
            "version": "1.0.0",
            "description": "MCP-Server Verwaltung und Tool-Integration",
            "status": "production",
            "category": "system",
            "icon": "bi-plug",
            "provides": ["views", "models"],
        },
        {
            "hub_id": "media_hub",
            "name": "Media Hub",
            "version": "1.0.0",
            "description": "Medien-Pipeline für Illustration und Audio",
            "status": "production",
            "category": "content",
            "icon": "bi-image",
            "provides": ["views", "models", "handlers"],
        },
        {
            "hub_id": "dlm_hub",
            "name": "DLM Hub",
            "version": "0.5.0",
            "description": "Document Lifecycle Management",
            "status": "beta",
            "category": "research",
            "icon": "bi-file-earmark-text",
            "provides": ["views", "models"],
        },
    ]

    def handle(self, *args, **options):
        from apps.core.models.hub import Hub
        from apps.control_center.models_navigation import NavigationSection

        self.stdout.write("Initializing Hubs...")
        
        created = 0
        updated = 0
        linked = 0

        with transaction.atomic():
            for hub_data in self.DEFAULT_HUBS:
                hub_id = hub_data["hub_id"]
                
                # Find matching NavigationSection
                section_code = self.HUB_SECTION_MAP.get(hub_id)
                nav_section = None
                if section_code:
                    nav_section = NavigationSection.objects.filter(code=section_code).first()
                
                # Create or update Hub
                hub, was_created = Hub.objects.update_or_create(
                    hub_id=hub_id,
                    defaults={
                        "name": hub_data["name"],
                        "version": hub_data["version"],
                        "description": hub_data["description"],
                        "status": hub_data["status"],
                        "category": hub_data["category"],
                        "icon": hub_data["icon"],
                        "provides": hub_data.get("provides", ["views", "models"]),
                        "config": hub_data.get("config", {}),
                        "navigation_section": nav_section,
                    }
                )
                
                if was_created:
                    created += 1
                    self.stdout.write(f"  ✅ Created: {hub.name}")
                else:
                    updated += 1
                    self.stdout.write(f"  🔄 Updated: {hub.name}")
                
                if nav_section:
                    linked += 1
                    self.stdout.write(f"     → Linked to NavigationSection: {section_code}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created}, Updated: {updated}, Linked: {linked}"
        ))
        
        # Summary
        self.stdout.write("\n=== Hub Summary ===")
        for hub in Hub.objects.all():
            status = "✅" if hub.is_active else "⚪"
            nav = f"→ {hub.navigation_section.code}" if hub.navigation_section else "⚠️ No section"
            self.stdout.write(f"  {status} {hub.name} ({hub.hub_id}) {nav}")
