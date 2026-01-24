"""Create DLM Hub domain + navigation (idempotent)."""

from django.core.management.base import BaseCommand

from apps.bfagent.models_domains import DomainArt
from apps.control_center.models_navigation import NavigationItem, NavigationSection


class Command(BaseCommand):
    help = "Create DLM Hub domain and navigation sections/items"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        domain_slug = "dlm-hub"
        domain_name = "dlm_hub"

        self.stdout.write(self.style.SUCCESS("\n📋 Creating DLM Hub Navigation\n"))
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be saved\n"))

        domain = DomainArt.objects.filter(slug=domain_slug).first()
        if domain:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  DomainArt already exists: {domain.display_name} (slug={domain.slug})"
                )
            )
        else:
            if dry_run:
                self.stdout.write(f"[DRY RUN] Would create DomainArt: {domain_slug}")
                domain = DomainArt(slug=domain_slug)
            else:
                domain = DomainArt.objects.create(
                    name=domain_name,
                    slug=domain_slug,
                    display_name="DLM Hub",
                    description="Documentation Lifecycle Management",
                    icon="bi-journal-text",
                    color="secondary",
                    is_active=True,
                    is_experimental=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Created DomainArt: {domain.display_name}")
                )

        # Sections + Items
        sections = [
            {
                "code": "dlm_overview",
                "name": "Overview",
                "description": "DLM dashboard and health overview",
                "icon": "bi-speedometer2",
                "color": "secondary",
                "order": 10,
                "slug": "overview",
                "items": [
                    {
                        "code": "dlm_dashboard",
                        "name": "Dashboard",
                        "description": "Documentation status overview",
                        "item_type": "link",
                        "url_name": "dlm_hub:dashboard",
                        "icon": "bi-graph-up",
                        "order": 10,
                        "badge_text": "NEW",
                        "badge_color": "warning",
                    },
                ],
            },
        ]

        for sec in sections:
            section = NavigationSection.objects.filter(code=sec["code"]).first()
            if section:
                if not dry_run and section.domain_id_id != getattr(domain, "id", None):
                    section.domain_id = domain
                    section.save(update_fields=["domain_id"])
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Section already exists: {section.name} (code={section.code})"
                    )
                )
            else:
                if dry_run:
                    self.stdout.write(f"[DRY RUN] Would create section: {sec['name']}")
                    section = None
                else:
                    section = NavigationSection.objects.create(
                        code=sec["code"],
                        name=sec["name"],
                        description=sec["description"],
                        icon=sec["icon"],
                        color=sec["color"],
                        order=sec["order"],
                        slug=sec["slug"],
                        is_active=True,
                        is_collapsible=True,
                        is_collapsed_default=False,
                        domain_id=domain,
                    )
                    self.stdout.write(self.style.SUCCESS(f"✅ Created section: {section.name}"))

            if section and not dry_run:
                for item in sec["items"]:
                    nav_item = NavigationItem.objects.filter(
                        section=section, code=item["code"]
                    ).first()
                    if nav_item:
                        self.stdout.write(f"  ⏭️  Item already exists: {nav_item.name}")
                    else:
                        NavigationItem.objects.create(section=section, **item)
                        self.stdout.write(self.style.SUCCESS(f"  ✅ Created item: {item['name']}"))

        self.stdout.write(self.style.SUCCESS("\n✅ DLM Hub navigation setup complete\n"))
