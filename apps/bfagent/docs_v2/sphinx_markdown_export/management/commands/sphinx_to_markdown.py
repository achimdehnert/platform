"""
Management Command: sphinx_to_markdown
Exportiert Sphinx-Dokumentation als Single Markdown von der Kommandozeile.

Usage:
    python manage.py sphinx_to_markdown <project_slug> [--output PATH]
    python manage.py sphinx_to_markdown myproject -o docs/complete.md
    python manage.py sphinx_to_markdown --path /path/to/docs --title "My Docs"

Author: BF Agent Framework
License: MIT
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from sphinx_markdown_export.models import DocumentationProject, DocumentationExport
from sphinx_markdown_export.export_service import (
    SphinxToMarkdownService,
    ExportConfig,
    sphinx_to_markdown,
)


class Command(BaseCommand):
    help = 'Exportiert ein Sphinx-Dokumentationsprojekt als Single Markdown'
    
    def add_arguments(self, parser):
        # Projekt-Identifikation (entweder slug/id oder direkter Pfad)
        parser.add_argument(
            'project',
            nargs='?',
            help='Projekt-Slug, ID oder "all" für alle aktiven Projekte'
        )
        
        # Alternative: Direkter Pfad
        parser.add_argument(
            '-p', '--path',
            help='Direkter Pfad zum Sphinx-Projekt (ohne Datenbank)'
        )
        
        # Output
        parser.add_argument(
            '-o', '--output',
            help='Ausgabepfad (default: <slug>_docs.md oder stdout mit --stdout)'
        )
        
        parser.add_argument(
            '--stdout',
            action='store_true',
            help='Ausgabe auf stdout statt in Datei'
        )
        
        # Optionen
        parser.add_argument(
            '-t', '--title',
            help='Dokumenttitel (überschreibt Projekt-Einstellung)'
        )
        
        parser.add_argument(
            '--no-toc',
            action='store_true',
            help='Kein Inhaltsverzeichnis generieren'
        )
        
        parser.add_argument(
            '--no-api',
            action='store_true',
            help='Keine API-Referenz generieren'
        )
        
        parser.add_argument(
            '--python-src',
            action='append',
            default=[],
            help='Python-Source-Pfade für API-Referenz (kann mehrfach angegeben werden)'
        )
        
        parser.add_argument(
            '--save-record',
            action='store_true',
            help='Export-Record in Datenbank speichern'
        )
        
        parser.add_argument(
            '-v', '--verbosity',
            type=int,
            default=1,
            choices=[0, 1, 2, 3],
            help='Verbosity level'
        )
    
    def handle(self, *args, **options):
        verbosity = options['verbosity']
        
        # Direkter Pfad-Modus
        if options['path']:
            return self._handle_direct_path(options, verbosity)
        
        # Datenbank-Modus
        if not options['project']:
            raise CommandError(
                "Entweder Projekt-Slug/ID angeben oder --path für direkten Pfad"
            )
        
        if options['project'] == 'all':
            return self._handle_all_projects(options, verbosity)
        
        return self._handle_single_project(options, verbosity)
    
    def _handle_direct_path(self, options, verbosity):
        """Export direkt von Pfad ohne Datenbank."""
        source_path = Path(options['path'])
        
        if not source_path.exists():
            raise CommandError(f"Pfad existiert nicht: {source_path}")
        
        if not (source_path / 'conf.py').exists():
            raise CommandError(f"Keine conf.py gefunden in: {source_path}")
        
        if verbosity >= 1:
            self.stdout.write(f"📚 Exportiere: {source_path}")
        
        config = ExportConfig(
            title=options['title'],
            include_toc=not options['no_toc'],
            include_api_reference=not options['no_api'],
            python_source_paths=options['python_src'],
        )
        
        service = SphinxToMarkdownService(source_path, config)
        output_path = Path(options['output']) if options['output'] else None
        
        success, result_path, metadata = service.export(output_path)
        
        if not success:
            raise CommandError(f"Export fehlgeschlagen: {', '.join(metadata.errors)}")
        
        # Warnungen ausgeben
        if verbosity >= 2:
            for warning in metadata.warnings:
                self.stdout.write(self.style.WARNING(f"  ⚠️  {warning}"))
        
        # Output
        if options['stdout']:
            self.stdout.write(result_path.read_text(encoding='utf-8'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Exportiert: {result_path}\n"
                f"   Seiten: {metadata.pages_count}\n"
                f"   Wörter: {metadata.word_count:,}\n"
                f"   Dauer:  {metadata.duration_seconds:.1f}s\n"
                f"   Features: {', '.join(metadata.features_used)}"
            ))
    
    def _handle_single_project(self, options, verbosity):
        """Export eines einzelnen Projekts aus der Datenbank."""
        project_ref = options['project']
        
        # Projekt finden
        try:
            if project_ref.isdigit():
                project = DocumentationProject.objects.get(pk=int(project_ref))
            else:
                project = DocumentationProject.objects.get(slug=project_ref)
        except DocumentationProject.DoesNotExist:
            raise CommandError(f"Projekt nicht gefunden: {project_ref}")
        
        if not project.has_valid_sphinx_project():
            raise CommandError(
                f"Ungültiges Sphinx-Projekt: {project.get_full_source_path()}"
            )
        
        if verbosity >= 1:
            self.stdout.write(f"📚 Exportiere: {project.name}")
        
        # Konfiguration
        config = ExportConfig(
            title=options['title'] or project.get_export_title(),
            include_toc=not options['no_toc'] and project.include_toc,
            include_api_reference=not options['no_api'] and project.include_api_reference,
            intersphinx_mapping=project.intersphinx_mapping or {},
            python_source_paths=options['python_src'] or project.python_source_paths or [],
        )
        
        # Export
        service = SphinxToMarkdownService(project.get_full_source_path(), config)
        output_path = Path(options['output']) if options['output'] else None
        
        success, result_path, metadata = service.export(output_path)
        
        # Export-Record speichern
        if options['save_record']:
            export_record = DocumentationExport.objects.create(
                project=project,
                format=DocumentationExport.Format.MARKDOWN,
                pages_count=metadata.pages_count,
                word_count=metadata.word_count,
                char_count=metadata.char_count,
                success=success,
                error_message='\n'.join(metadata.errors),
                warnings=metadata.warnings,
                features_used=metadata.features_used,
                duration_seconds=metadata.duration_seconds
            )
            
            if success:
                content = result_path.read_text(encoding='utf-8')
                export_record.file_size = len(content.encode('utf-8'))
                export_record.save(update_fields=['file_size'])
                
                project.last_export_at = timezone.now()
                project.save(update_fields=['last_export_at'])
        
        if not success:
            raise CommandError(f"Export fehlgeschlagen: {', '.join(metadata.errors)}")
        
        # Warnungen ausgeben
        if verbosity >= 2:
            for warning in metadata.warnings:
                self.stdout.write(self.style.WARNING(f"  ⚠️  {warning}"))
        
        # Output
        if options['stdout']:
            self.stdout.write(result_path.read_text(encoding='utf-8'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Exportiert: {result_path}\n"
                f"   Seiten: {metadata.pages_count}\n"
                f"   Wörter: {metadata.word_count:,}\n"
                f"   Dauer:  {metadata.duration_seconds:.1f}s\n"
                f"   Features: {', '.join(metadata.features_used)}"
            ))
    
    def _handle_all_projects(self, options, verbosity):
        """Export aller aktiven Projekte."""
        projects = DocumentationProject.objects.filter(
            status=DocumentationProject.Status.ACTIVE
        )
        
        if not projects.exists():
            raise CommandError("Keine aktiven Projekte gefunden")
        
        success_count = 0
        error_count = 0
        
        for project in projects:
            if verbosity >= 1:
                self.stdout.write(f"\n📚 Exportiere: {project.name}")
            
            if not project.has_valid_sphinx_project():
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️  Übersprungen (ungültiges Projekt)"
                ))
                error_count += 1
                continue
            
            config = ExportConfig(
                title=project.get_export_title(),
                include_toc=project.include_toc,
                include_api_reference=project.include_api_reference,
                intersphinx_mapping=project.intersphinx_mapping or {},
                python_source_paths=project.python_source_paths or [],
            )
            
            service = SphinxToMarkdownService(project.get_full_source_path(), config)
            
            # Output-Pfad generieren
            if options['output']:
                output_dir = Path(options['output'])
                output_path = output_dir / f"{project.slug}_docs.md"
            else:
                output_path = None
            
            success, result_path, metadata = service.export(output_path)
            
            # Export-Record speichern
            if options['save_record']:
                export_record = DocumentationExport.objects.create(
                    project=project,
                    format=DocumentationExport.Format.MARKDOWN,
                    pages_count=metadata.pages_count,
                    word_count=metadata.word_count,
                    char_count=metadata.char_count,
                    success=success,
                    error_message='\n'.join(metadata.errors),
                    warnings=metadata.warnings,
                    features_used=metadata.features_used,
                    duration_seconds=metadata.duration_seconds
                )
                
                if success:
                    project.last_export_at = timezone.now()
                    project.save(update_fields=['last_export_at'])
            
            if success:
                success_count += 1
                if verbosity >= 1:
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✅ {result_path} ({metadata.pages_count} Seiten)"
                    ))
            else:
                error_count += 1
                if verbosity >= 1:
                    self.stdout.write(self.style.ERROR(
                        f"  ❌ Fehler: {', '.join(metadata.errors)}"
                    ))
        
        # Zusammenfassung
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(self.style.SUCCESS(
            f"✅ {success_count} Projekt(e) erfolgreich exportiert"
        ))
        if error_count > 0:
            self.stdout.write(self.style.WARNING(
                f"⚠️  {error_count} Projekt(e) mit Fehlern"
            ))
