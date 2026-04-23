"""
Django Management Command: Sphinx to Markdown Export

Konvertiert Sphinx-Dokumentationsprojekte zu einer einzelnen Markdown-Datei.

Usage:
    # Export von Pfad
    python manage.py sphinx_to_markdown --source docs/source -o docs_complete.md
    
    # Mit Titel
    python manage.py sphinx_to_markdown --source docs/ --title "BF Agent Docs"
    
    # Mit API-Referenz
    python manage.py sphinx_to_markdown --source docs/ --python-src apps/bfagent
    
    # Ohne TOC
    python manage.py sphinx_to_markdown --source docs/ --no-toc
    
    # Verbose für Debugging
    python manage.py sphinx_to_markdown --source docs/ -v 2

Author: BF Agent Framework
"""

from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.sphinx_export import SphinxToMarkdownService, ExportConfig


class Command(BaseCommand):
    """Management Command für Sphinx→Markdown Export."""
    
    help = 'Konvertiert Sphinx-Dokumentation zu einer einzelnen Markdown-Datei'
    
    def add_arguments(self, parser):
        """Definiert CLI-Argumente."""
        parser.add_argument(
            '--source', '-s',
            required=True,
            help='Pfad zum Sphinx source-Verzeichnis (mit conf.py)'
        )
        
        parser.add_argument(
            '--output', '-o',
            default='documentation.md',
            help='Ausgabe-Dateiname (default: documentation.md)'
        )
        
        parser.add_argument(
            '--title', '-t',
            help='Dokumenttitel'
        )
        
        parser.add_argument(
            '--no-toc',
            action='store_true',
            help='Kein Inhaltsverzeichnis generieren'
        )
        
        parser.add_argument(
            '--no-meta',
            action='store_true',
            help='Keine Metadaten (Datum, Quelle) im Header'
        )
        
        parser.add_argument(
            '--no-api',
            action='store_true',
            help='Keine API-Referenz aus Python-Sourcen'
        )
        
        parser.add_argument(
            '--python-src',
            action='append',
            default=[],
            metavar='PATH',
            help='Python-Source-Pfade für API-Referenz (kann mehrfach angegeben werden)'
        )
        
        parser.add_argument(
            '--intersphinx',
            action='append',
            default=[],
            metavar='NAME=URL',
            help='Intersphinx-Mapping (z.B. python=https://docs.python.org/3)'
        )
    
    def handle(self, *args, **options):
        """Führt den Export durch."""
        verbosity = options['verbosity']
        
        # Source-Pfad auflösen
        source_path = Path(options['source'])
        if not source_path.is_absolute():
            source_path = Path(settings.BASE_DIR) / source_path
        
        # Validierung
        if not source_path.exists():
            raise CommandError(f"Pfad existiert nicht: {source_path}")
        
        if not (source_path / 'conf.py').exists():
            raise CommandError(f"Keine conf.py gefunden in: {source_path}")
        
        if verbosity >= 1:
            self.stdout.write(f"📚 Exportiere: {source_path}")
        
        # Intersphinx-Mapping parsen
        intersphinx = {}
        for mapping in options['intersphinx']:
            if '=' in mapping:
                name, url = mapping.split('=', 1)
                intersphinx[name.strip()] = url.strip()
        
        # Konfiguration erstellen
        config = ExportConfig(
            title=options['title'],
            include_toc=not options['no_toc'],
            include_metadata=not options['no_meta'],
            include_api_reference=not options['no_api'],
            intersphinx_mapping=intersphinx,
            python_source_paths=options['python_src'],
        )
        
        # Service erstellen und Export durchführen
        service = SphinxToMarkdownService(source_path, config)
        
        output_path = Path(options['output'])
        if not output_path.is_absolute():
            output_path = Path(settings.BASE_DIR) / output_path
        
        success, result_path, metadata = service.export(output_path)
        
        # Warnungen ausgeben
        if verbosity >= 2:
            for warning in metadata.warnings:
                self.stdout.write(self.style.WARNING(f"  ⚠️  {warning}"))
        
        # Fehler
        if not success:
            self.stdout.write(self.style.ERROR("❌ Export fehlgeschlagen:"))
            for error in metadata.errors:
                self.stdout.write(self.style.ERROR(f"   {error}"))
            raise CommandError("Export fehlgeschlagen")
        
        # Erfolg
        if verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Exportiert: {result_path}"))
            self.stdout.write(f"   Seiten:   {metadata.pages_count}")
            self.stdout.write(f"   Wörter:   {metadata.word_count:,}")
            self.stdout.write(f"   Zeichen:  {metadata.char_count:,}")
            self.stdout.write(f"   Dauer:    {metadata.duration_seconds:.1f}s")
            self.stdout.write(f"   Features: {', '.join(metadata.features_used)}")
        
        return str(result_path)
