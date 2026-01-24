"""
Django Admin Konfiguration für Dokumentations-Management
Enthält Admin-Actions für Sphinx→Markdown Export.

Author: BF Agent Framework
License: MIT
"""

from datetime import datetime
from pathlib import Path

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.core.files.base import ContentFile

from .models import DocumentationProject, DocumentationExport
from .export_service import SphinxToMarkdownService, ExportConfig


# =============================================================================
# Admin Actions
# =============================================================================

@admin.action(description="📄 Exportiere als Single Markdown")
def export_as_markdown(modeladmin, request, queryset):
    """
    Admin-Action: Exportiert ausgewählte Dokumentationsprojekte als Markdown.
    
    - Validiert das Sphinx-Projekt
    - Führt den Export durch
    - Erstellt einen Export-Record
    - Gibt die Datei als Download zurück
    """
    if queryset.count() > 1:
        messages.warning(
            request,
            _("Bitte nur ein Projekt zur Zeit exportieren für direkten Download.")
        )
        return
    
    project = queryset.first()
    
    # Validierung
    if not project.has_valid_sphinx_project():
        messages.error(
            request,
            _("Kein gültiges Sphinx-Projekt gefunden in: %(path)s") % {
                'path': project.source_path
            }
        )
        return
    
    # Export-Konfiguration erstellen
    config = ExportConfig(
        title=project.get_export_title(),
        include_toc=project.include_toc,
        include_api_reference=project.include_api_reference,
        intersphinx_mapping=project.intersphinx_mapping or {},
        python_source_paths=project.python_source_paths or [],
    )
    
    # Export durchführen
    service = SphinxToMarkdownService(
        source_path=project.get_full_source_path(),
        config=config
    )
    
    success, output_path, metadata = service.export()
    
    # Export-Record erstellen
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
    
    if not success:
        messages.error(
            request,
            _("Export fehlgeschlagen: %(errors)s") % {
                'errors': ', '.join(metadata.errors)
            }
        )
        return
    
    # Warnungen anzeigen
    for warning in metadata.warnings[:3]:  # Max 3 Warnungen
        messages.warning(request, warning)
    
    if len(metadata.warnings) > 3:
        messages.warning(
            request,
            _("... und %(count)d weitere Warnungen") % {
                'count': len(metadata.warnings) - 3
            }
        )
    
    # Datei lesen
    content = output_path.read_text(encoding='utf-8')
    content_bytes = content.encode('utf-8')
    
    # Export-Record aktualisieren
    export_record.file_size = len(content_bytes)
    export_record.save(update_fields=['file_size'])
    
    # Optional: Datei im Export-Record speichern
    # export_record.file.save(
    #     f"{project.slug}_{datetime.now():%Y%m%d_%H%M%S}.md",
    #     ContentFile(content_bytes)
    # )
    
    # Projekt-Timestamp aktualisieren
    project.last_export_at = datetime.now()
    project.save(update_fields=['last_export_at'])
    
    # Erfolgs-Message
    messages.success(
        request,
        _("✅ Export erfolgreich: %(pages)d Seiten, %(words)s Wörter in %(duration)s") % {
            'pages': metadata.pages_count,
            'words': f"{metadata.word_count:,}".replace(',', '.'),
            'duration': f"{metadata.duration_seconds:.1f}s"
        }
    )
    
    # Datei als Download zurückgeben
    filename = f"{project.slug}_documentation_{datetime.now():%Y%m%d}.md"
    
    response = HttpResponse(content, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = len(content_bytes)
    
    return response


@admin.action(description="📄 Exportiere alle als Markdown (ohne Download)")
def export_all_markdown_save(modeladmin, request, queryset):
    """
    Admin-Action: Exportiert alle ausgewählten Projekte und speichert sie.
    
    Nützlich für Batch-Exporte ohne direkten Download.
    """
    success_count = 0
    error_count = 0
    
    for project in queryset:
        if not project.has_valid_sphinx_project():
            messages.warning(
                request,
                _("Übersprungen (ungültig): %(name)s") % {'name': project.name}
            )
            error_count += 1
            continue
        
        config = ExportConfig(
            title=project.get_export_title(),
            include_toc=project.include_toc,
            include_api_reference=project.include_api_reference,
            intersphinx_mapping=project.intersphinx_mapping or {},
            python_source_paths=project.python_source_paths or [],
        )
        
        service = SphinxToMarkdownService(
            source_path=project.get_full_source_path(),
            config=config
        )
        
        success, output_path, metadata = service.export()
        
        # Export-Record erstellen
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
            # Datei speichern
            content = output_path.read_text(encoding='utf-8')
            export_record.file.save(
                f"{project.slug}_{datetime.now():%Y%m%d_%H%M%S}.md",
                ContentFile(content.encode('utf-8'))
            )
            export_record.file_size = len(content.encode('utf-8'))
            export_record.save(update_fields=['file_size'])
            
            project.last_export_at = datetime.now()
            project.save(update_fields=['last_export_at'])
            
            success_count += 1
        else:
            error_count += 1
    
    if success_count > 0:
        messages.success(
            request,
            _("%(count)d Projekt(e) erfolgreich exportiert") % {'count': success_count}
        )
    
    if error_count > 0:
        messages.warning(
            request,
            _("%(count)d Projekt(e) mit Fehlern") % {'count': error_count}
        )


@admin.action(description="🔍 Validiere Sphinx-Projekt(e)")
def validate_sphinx_project(modeladmin, request, queryset):
    """
    Admin-Action: Validiert ausgewählte Sphinx-Projekte.
    
    Prüft:
    - Pfad existiert
    - conf.py vorhanden
    - index.rst/md vorhanden
    - Extensions konfiguriert
    """
    for project in queryset:
        source = project.get_full_source_path()
        issues = []
        warnings = []
        
        # Pfad-Prüfung
        if not source.exists():
            issues.append(_("Pfad existiert nicht: %(path)s") % {'path': source})
        elif not (source / 'conf.py').exists():
            issues.append(_("conf.py fehlt"))
        else:
            # Erweiterte Validierung
            conf_content = (source / 'conf.py').read_text(encoding='utf-8')
            
            if 'extensions' not in conf_content:
                warnings.append(_("Keine extensions definiert"))
            
            # Index-Datei
            has_index = any(
                (source / f).exists()
                for f in ['index.rst', 'index.md', 'contents.rst']
            )
            if not has_index:
                warnings.append(_("index.rst/md fehlt"))
            
            # Autodoc
            if project.include_api_reference:
                if 'autodoc' not in conf_content and 'autodoc2' not in conf_content:
                    warnings.append(_("autodoc nicht in extensions (API-Referenz aktiviert)"))
        
        # Feedback
        if issues:
            messages.error(
                request,
                format_html(
                    "❌ <strong>{}</strong>: {}",
                    project.name,
                    ', '.join(str(i) for i in issues)
                )
            )
        elif warnings:
            messages.warning(
                request,
                format_html(
                    "⚠️ <strong>{}</strong>: {}",
                    project.name,
                    ', '.join(str(w) for w in warnings)
                )
            )
        else:
            messages.success(
                request,
                format_html("✅ <strong>{}</strong>: Sphinx-Projekt valide", project.name)
            )


# =============================================================================
# Admin Configuration
# =============================================================================

@admin.register(DocumentationProject)
class DocumentationProjectAdmin(admin.ModelAdmin):
    """Admin für Dokumentationsprojekte."""
    
    list_display = [
        'name',
        'status',
        'source_path_display',
        'last_export_at',
        'export_count_display',
        'quick_actions',
    ]
    list_filter = ['status', 'include_toc', 'include_api_reference']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'last_export_at']
    
    actions = [
        export_as_markdown,
        export_all_markdown_save,
        validate_sphinx_project,
    ]
    
    fieldsets = (
        (_('Allgemein'), {
            'fields': ('name', 'slug', 'description', 'status')
        }),
        (_('Pfade'), {
            'fields': ('source_path', 'python_source_paths'),
            'description': _('Pfade relativ zu BASE_DIR angeben')
        }),
        (_('Export-Einstellungen'), {
            'fields': (
                'custom_title',
                'include_toc',
                'include_api_reference',
                'intersphinx_mapping',
            ),
            'classes': ('collapse',)
        }),
        (_('Metadaten'), {
            'fields': ('created_at', 'updated_at', 'last_export_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description=_("Source-Pfad"))
    def source_path_display(self, obj):
        """Zeigt Pfad mit Validierungsstatus."""
        valid = obj.has_valid_sphinx_project()
        icon = '✅' if valid else '❌'
        return format_html(
            '{} <code style="background:#f5f5f5;padding:2px 6px;border-radius:3px">{}</code>',
            icon,
            obj.source_path
        )
    
    @admin.display(description=_("Exporte"))
    def export_count_display(self, obj):
        """Anzahl der Exporte mit Link."""
        count = obj.export_count
        if count > 0:
            return format_html(
                '<a href="{}?project__id__exact={}">{} Export{}</a>',
                '/admin/documentation/documentationexport/',
                obj.pk,
                count,
                'e' if count != 1 else ''
            )
        return format_html('<span style="color:#999">Keine</span>')
    
    @admin.display(description=_("Aktionen"))
    def quick_actions(self, obj):
        """Quick-Actions Spalte."""
        if obj.has_valid_sphinx_project():
            return format_html(
                '<a class="button" style="padding:3px 8px;font-size:11px" '
                'title="Export starten">📄 Export</a>'
            )
        return format_html(
            '<span style="color:#c00" title="Ungültiges Projekt">⚠️ Ungültig</span>'
        )


@admin.register(DocumentationExport)
class DocumentationExportAdmin(admin.ModelAdmin):
    """Admin für Export-Historie."""
    
    list_display = [
        'project',
        'format',
        'success_display',
        'pages_count',
        'word_count',
        'file_size_display',
        'duration_display',
        'created_at',
    ]
    list_filter = ['format', 'success', 'project', 'created_at']
    search_fields = ['project__name']
    readonly_fields = [
        'project',
        'format',
        'file',
        'file_size',
        'pages_count',
        'word_count',
        'char_count',
        'success',
        'error_message',
        'warnings',
        'features_used',
        'created_at',
        'duration_seconds',
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('Allgemein'), {
            'fields': ('project', 'format', 'success', 'created_at')
        }),
        (_('Datei'), {
            'fields': ('file', 'file_size')
        }),
        (_('Statistiken'), {
            'fields': ('pages_count', 'word_count', 'char_count', 'duration_seconds')
        }),
        (_('Details'), {
            'fields': ('features_used', 'warnings', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description=_("Status"))
    def success_display(self, obj):
        if obj.success:
            return format_html('<span style="color:green">✅ OK</span>')
        return format_html('<span style="color:red">❌ Fehler</span>')
    
    @admin.display(description=_("Größe"))
    def file_size_display(self, obj):
        return obj.file_size_display
    
    @admin.display(description=_("Dauer"))
    def duration_display(self, obj):
        return obj.duration_display
    
    def has_add_permission(self, request):
        """Exporte nur durch Action erstellen."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Exporte nicht editierbar."""
        return False
