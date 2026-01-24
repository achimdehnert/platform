"""
Django Models für Dokumentations-Management
Verwaltet Sphinx-Projekte und Export-Historie.

Author: BF Agent Framework
License: MIT
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from pathlib import Path


class DocumentationProject(models.Model):
    """
    Sphinx-Dokumentationsprojekt.
    
    Repräsentiert ein Sphinx-Projekt mit allen Einstellungen
    für den Markdown-Export.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Entwurf')
        ACTIVE = 'active', _('Aktiv')
        ARCHIVED = 'archived', _('Archiviert')
    
    # Identifikation
    name = models.CharField(
        max_length=200,
        verbose_name=_("Projektname"),
        help_text=_("Name des Dokumentationsprojekts")
    )
    slug = models.SlugField(
        unique=True,
        help_text=_("URL-freundlicher Bezeichner")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Beschreibung"),
        help_text=_("Optionale Beschreibung des Projekts")
    )
    
    # Pfade
    source_path = models.CharField(
        max_length=500,
        verbose_name=_("Sphinx Source-Pfad"),
        help_text=_("Relativer Pfad zum docs/ Verzeichnis (von BASE_DIR)")
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Status")
    )
    
    # Intersphinx-Konfiguration
    intersphinx_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Intersphinx Mapping"),
        help_text=_('Format: {"python": "https://docs.python.org/3", ...}')
    )
    
    # Python-Sourcen für Autodoc
    python_source_paths = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Python Source-Pfade"),
        help_text=_('Liste von Pfaden für API-Referenz: ["src/mymodule", ...]')
    )
    
    # Export-Einstellungen
    include_toc = models.BooleanField(
        default=True,
        verbose_name=_("Inhaltsverzeichnis")
    )
    include_api_reference = models.BooleanField(
        default=True,
        verbose_name=_("API-Referenz einbeziehen"),
        help_text=_("Docstrings aus Python-Sourcen extrahieren")
    )
    custom_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Custom Titel"),
        help_text=_("Überschreibt den Projektnamen im Export")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Erstellt"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Aktualisiert"))
    last_export_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Letzter Export")
    )
    
    class Meta:
        verbose_name = _("Dokumentationsprojekt")
        verbose_name_plural = _("Dokumentationsprojekte")
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def get_full_source_path(self) -> Path:
        """Gibt den vollständigen Pfad zum Source-Verzeichnis zurück."""
        base = Path(settings.BASE_DIR)
        return base / self.source_path
    
    def has_valid_sphinx_project(self) -> bool:
        """Prüft ob ein gültiges Sphinx-Projekt existiert."""
        source = self.get_full_source_path()
        return source.exists() and (source / 'conf.py').exists()
    
    def get_export_title(self) -> str:
        """Gibt den Titel für Exporte zurück."""
        return self.custom_title or self.name
    
    @property
    def export_count(self) -> int:
        """Anzahl der Exporte."""
        return self.exports.count()


class DocumentationExport(models.Model):
    """
    Export-Historie für Dokumentationsprojekte.
    
    Speichert Metadaten und optional die exportierte Datei.
    """
    
    class Format(models.TextChoices):
        MARKDOWN = 'md', _('Markdown')
        HTML = 'html', _('HTML')
        PDF = 'pdf', _('PDF')
    
    # Beziehung
    project = models.ForeignKey(
        DocumentationProject,
        on_delete=models.CASCADE,
        related_name='exports',
        verbose_name=_("Projekt")
    )
    
    # Format
    format = models.CharField(
        max_length=10,
        choices=Format.choices,
        default=Format.MARKDOWN,
        verbose_name=_("Format")
    )
    
    # Export-Datei (optional)
    file = models.FileField(
        upload_to='documentation/exports/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_("Datei")
    )
    file_size = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Dateigröße"),
        help_text=_("In Bytes")
    )
    
    # Metadaten
    pages_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Seiten")
    )
    word_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Wörter")
    )
    char_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Zeichen")
    )
    
    # Status
    success = models.BooleanField(
        default=False,
        verbose_name=_("Erfolgreich")
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Fehlermeldung")
    )
    warnings = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Warnungen")
    )
    features_used = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Verwendete Features")
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Erstellt")
    )
    duration_seconds = models.FloatField(
        default=0,
        verbose_name=_("Dauer (Sekunden)")
    )
    
    class Meta:
        verbose_name = _("Dokumentations-Export")
        verbose_name_plural = _("Dokumentations-Exporte")
        ordering = ['-created_at']
    
    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"{status} {self.project.name} - {self.format} ({self.created_at:%Y-%m-%d %H:%M})"
    
    @property
    def duration_display(self) -> str:
        """Formatierte Dauer."""
        if self.duration_seconds < 1:
            return f"{self.duration_seconds * 1000:.0f}ms"
        elif self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        else:
            minutes = int(self.duration_seconds // 60)
            seconds = self.duration_seconds % 60
            return f"{minutes}m {seconds:.0f}s"
    
    @property
    def file_size_display(self) -> str:
        """Formatierte Dateigröße."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
