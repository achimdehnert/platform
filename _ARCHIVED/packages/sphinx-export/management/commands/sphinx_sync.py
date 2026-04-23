"""
Sphinx Sync Management Command
==============================

Prüft und synchronisiert Sphinx-Dokumentation mit dem Quellcode.

Usage:
    # Nur prüfen
    python manage.py sphinx_sync
    
    # Mit Bericht
    python manage.py sphinx_sync --report
    
    # Fehlende Stubs generieren
    python manage.py sphinx_sync --generate-stubs
    
    # Dokumentation neu bauen
    python manage.py sphinx_sync --rebuild
    
    # Alles (prüfen + generieren + bauen)
    python manage.py sphinx_sync --full-sync
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pathlib import Path

from ...sync_service import SphinxSyncService, get_sphinx_sync_service


class Command(BaseCommand):
    help = 'Prüft und synchronisiert Sphinx-Dokumentation mit dem Quellcode'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--docs-path',
            type=str,
            default='docs/source',
            help='Pfad zur Sphinx-Dokumentation (default: docs/source)'
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generiert detaillierten Markdown-Bericht'
        )
        parser.add_argument(
            '--report-file',
            type=str,
            help='Speichert Bericht in Datei'
        )
        parser.add_argument(
            '--generate-stubs',
            action='store_true',
            help='Generiert fehlende autodoc-Stubs'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Zeigt nur an, was getan würde (kein Schreiben)'
        )
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Baut Sphinx-Dokumentation neu'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Clean vor Rebuild'
        )
        parser.add_argument(
            '--full-sync',
            action='store_true',
            help='Führt vollständige Synchronisation durch'
        )
        parser.add_argument(
            '--check-docstrings',
            action='store_true',
            default=True,
            help='Prüft auch auf fehlende Docstrings'
        )
        parser.add_argument(
            '--no-docstrings',
            action='store_true',
            help='Überspringt Docstring-Prüfung'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Ausgabe als JSON'
        )
    
    def handle(self, *args, **options):
        docs_path = Path(settings.BASE_DIR) / options['docs_path']
        
        if not docs_path.exists():
            raise CommandError(f"Dokumentationspfad existiert nicht: {docs_path}")
        
        # Service initialisieren
        service = SphinxSyncService(
            project_root=settings.BASE_DIR,
            docs_path=docs_path,
        )
        
        # Full Sync
        if options['full_sync']:
            self._full_sync(service, options)
            return
        
        # Nur Rebuild
        if options['rebuild']:
            self._rebuild(service, options)
            return
        
        # Nur Stubs generieren
        if options['generate_stubs']:
            self._generate_stubs(service, options)
            return
        
        # Standard: Prüfen und Bericht
        self._check_and_report(service, options)
    
    def _check_and_report(self, service: SphinxSyncService, options: dict):
        """Prüft auf Änderungen und erstellt Bericht."""
        self.stdout.write("🔍 Prüfe Sphinx-Dokumentation...\n")
        
        check_docstrings = not options['no_docstrings']
        report = service.check_changes(check_docstrings=check_docstrings)
        
        if options['json']:
            import json
            self.stdout.write(json.dumps(report.to_dict(), indent=2))
            return
        
        if options['report'] or options['report_file']:
            markdown = report.to_markdown()
            
            if options['report_file']:
                Path(options['report_file']).write_text(markdown, encoding='utf-8')
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Bericht gespeichert: {options['report_file']}")
                )
            else:
                self.stdout.write(markdown)
            return
        
        # Kompakte Ausgabe
        self._print_summary(report)
    
    def _print_summary(self, report):
        """Gibt kompakte Zusammenfassung aus."""
        if report.has_changes:
            self.stdout.write(self.style.WARNING("⚠️  Änderungen gefunden:\n"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Dokumentation ist aktuell\n"))
        
        if report.python_changes:
            self.stdout.write(f"   🐍 Python-Änderungen: {len(report.python_changes)}")
            for change in report.python_changes[:5]:
                self.stdout.write(f"      - {change.path}")
            if len(report.python_changes) > 5:
                self.stdout.write(f"      ... und {len(report.python_changes) - 5} weitere")
        
        if report.doc_changes:
            self.stdout.write(f"   📄 Dok-Änderungen: {len(report.doc_changes)}")
        
        if report.missing_docs:
            self.stdout.write(f"   ❌ Fehlende Doku: {len(report.missing_docs)}")
            for doc in report.missing_docs[:3]:
                self.stdout.write(f"      - {doc}")
        
        if report.outdated_docs:
            self.stdout.write(f"   ⏰ Veraltet: {len(report.outdated_docs)}")
        
        if report.undocumented_items:
            self.stdout.write(f"   📝 Ohne Docstring: {len(report.undocumented_items)}")
        
        self.stdout.write("")
        
        if report.suggestions:
            self.stdout.write("💡 Vorschläge:")
            for suggestion in report.suggestions:
                self.stdout.write(f"   {suggestion}")
        
        self.stdout.write("")
        self.stdout.write(f"📊 Gesamt-Issues: {report.total_issues}")
    
    def _generate_stubs(self, service: SphinxSyncService, options: dict):
        """Generiert fehlende autodoc-Stubs."""
        dry_run = options['dry_run']
        
        self.stdout.write("📝 Generiere autodoc-Stubs...\n")
        
        generated = service.generate_missing_stubs(dry_run=dry_run)
        
        if generated:
            for path in generated:
                self.stdout.write(f"   {'[DRY-RUN] ' if dry_run else '✅ '}{path}")
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(f"{'Würde generieren' if dry_run else 'Generiert'}: {len(generated)} Stubs")
            )
        else:
            self.stdout.write(self.style.SUCCESS("✅ Keine fehlenden Stubs gefunden"))
    
    def _rebuild(self, service: SphinxSyncService, options: dict):
        """Baut Sphinx-Dokumentation neu."""
        clean = options['clean']
        
        self.stdout.write(f"🔨 Baue Sphinx-Dokumentation{' (clean)' if clean else ''}...\n")
        
        success, output = service.rebuild_docs(clean=clean)
        
        if success:
            self.stdout.write(self.style.SUCCESS("✅ Build erfolgreich"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Build fehlgeschlagen:\n{output}"))
    
    def _full_sync(self, service: SphinxSyncService, options: dict):
        """Führt vollständige Synchronisation durch."""
        self.stdout.write(self.style.HTTP_INFO("🔄 Vollständige Sphinx-Synchronisation\n"))
        self.stdout.write("=" * 50 + "\n")
        
        # 1. Prüfen
        self.stdout.write("\n📋 Schritt 1/3: Prüfe Änderungen...")
        report = service.check_changes()
        self._print_summary(report)
        
        # 2. Stubs generieren
        if report.missing_docs or options['generate_stubs']:
            self.stdout.write("\n📝 Schritt 2/3: Generiere Stubs...")
            dry_run = options['dry_run']
            generated = service.generate_missing_stubs(dry_run=dry_run)
            if generated:
                self.stdout.write(f"   {'Würde generieren' if dry_run else 'Generiert'}: {len(generated)} Stubs")
            else:
                self.stdout.write("   Keine fehlenden Stubs")
        else:
            self.stdout.write("\n📝 Schritt 2/3: Keine Stubs nötig")
        
        # 3. Rebuild
        if not options['dry_run']:
            self.stdout.write("\n🔨 Schritt 3/3: Rebuild Dokumentation...")
            success, output = service.rebuild_docs(clean=options['clean'])
            if success:
                self.stdout.write(self.style.SUCCESS("   ✅ Build erfolgreich"))
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️ Build-Probleme: {output[:200]}"))
        else:
            self.stdout.write("\n🔨 Schritt 3/3: [DRY-RUN] Rebuild übersprungen")
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("\n✅ Synchronisation abgeschlossen\n"))
