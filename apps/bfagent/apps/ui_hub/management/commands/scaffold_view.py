"""Management command to scaffold views and templates."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.ui_hub.services import ScaffolderService


class Command(BaseCommand):
    """Scaffold views, templates, and HTMX partials."""

    help = "Scaffold Django views and HTMX templates"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("entity", type=str, help="Entity name (e.g., client, invoice)")
        parser.add_argument(
            "action",
            type=str,
            help='Action: list, detail, create, update, delete, or "full" for complete CRUD',
        )
        parser.add_argument("--app", type=str, required=True, help="App name")
        parser.add_argument(
            "--with-htmx", action="store_true", help="Include HTMX support", default=True
        )
        parser.add_argument(
            "--output", type=str, help="Output directory (default: current directory)", default="."
        )
        parser.add_argument(
            "--write",
            action="store_true",
            help="Write files to disk (default: just print to stdout)",
        )

    def handle(self, *args, **options):
        """Execute command."""
        entity = options["entity"]
        action = options["action"]
        app = options["app"]
        with_htmx = options["with_htmx"]
        output_dir = Path(options["output"])
        write_files = options["write"]

        scaffolder = ScaffolderService()

        self.stdout.write(self.style.SUCCESS(f"Scaffolding {entity} {action} view..."))

        # Generate based on action
        if action == "full":
            # Full CRUD scaffold
            results = scaffolder.scaffold_full_crud(entity, app, with_htmx)

            # Display views
            self.stdout.write(self.style.SUCCESS("\n📝 VIEWS:\n"))
            for view in results["views"]:
                self.stdout.write(f"Function: {view['file_name']}")
                self.stdout.write("─" * 70)
                self.stdout.write(view["code"])
                self.stdout.write("─" * 70 + "\n")

            # Display templates
            self.stdout.write(self.style.SUCCESS("\n📄 TEMPLATES:\n"))
            for template in results["templates"]:
                self.stdout.write(f"File: {template['path']}")
                self.stdout.write("─" * 70)
                self.stdout.write(template["code"])
                self.stdout.write("─" * 70 + "\n")

            # Display partials
            if results["partials"]:
                self.stdout.write(self.style.SUCCESS("\n🧩 HTMX PARTIALS:\n"))
                for partial in results["partials"]:
                    self.stdout.write(f"File: {partial['path']}")
                    self.stdout.write("─" * 70)
                    self.stdout.write(partial["code"])
                    self.stdout.write("─" * 70 + "\n")

            # Display URLs
            self.stdout.write(self.style.SUCCESS("\n🔗 URL PATTERNS:\n"))
            self.stdout.write("─" * 70)
            self.stdout.write(results["urls"]["code"])
            self.stdout.write("─" * 70 + "\n")

            # Write files if requested
            if write_files:
                self.write_crud_files(results, output_dir, app, entity)

        else:
            # Single view/template
            view = scaffolder.scaffold_view(entity, action, app, with_htmx)

            self.stdout.write(self.style.SUCCESS("\n📝 VIEW:\n"))
            self.stdout.write("─" * 70)
            self.stdout.write(view["code"])
            self.stdout.write("─" * 70 + "\n")

            # Write file if requested
            if write_files:
                views_file = output_dir / "views.py"
                self.stdout.write(f"Writing to: {views_file}")

                # Append to existing file or create new
                with open(views_file, "a", encoding="utf-8") as f:
                    f.write("\n\n")
                    f.write(view["code"])

                self.stdout.write(self.style.SUCCESS("✅ View written"))

        self.stdout.write(self.style.SUCCESS("\n✅ Scaffolding complete"))

    def write_crud_files(self, results, output_dir, app, entity):
        """Write CRUD files to disk."""
        # Views
        views_file = output_dir / "views.py"
        self.stdout.write(f"\n📝 Writing views to: {views_file}")

        with open(views_file, "a", encoding="utf-8") as f:
            for view in results["views"]:
                f.write("\n\n")
                f.write(view["code"])

        self.stdout.write(self.style.SUCCESS("✅ Views written"))

        # Templates
        templates_dir = output_dir / "templates" / app / entity
        templates_dir.mkdir(parents=True, exist_ok=True)

        for template in results["templates"]:
            template_file = templates_dir / template["file_name"].split("/")[-1]
            self.stdout.write(f"📄 Writing template: {template_file}")

            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template["code"])

        # Partials
        if results["partials"]:
            partials_dir = templates_dir / "partials"
            partials_dir.mkdir(parents=True, exist_ok=True)

            for partial in results["partials"]:
                partial_file = partials_dir / partial["file_name"]
                self.stdout.write(f"🧩 Writing partial: {partial_file}")

                with open(partial_file, "w", encoding="utf-8") as f:
                    f.write(partial["code"])

        # URLs
        urls_file = output_dir / "urls.py"
        self.stdout.write(f"🔗 Appending URLs to: {urls_file}")

        with open(urls_file, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(results["urls"]["code"])

        self.stdout.write(self.style.SUCCESS("✅ All files written"))
