"""
Documentation System Models - DB-Driven Documentation

Hybrid-Ansatz:
- DB für strukturierte Dokumentation (durchsuchbar, verknüpfbar, versioniert)
- MD-Export für essentielle Dateien (README, Guides)
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class SystemDocumentation(models.Model):
    """
    Technische Dokumentation des Gesamtsystems.
    Ersetzt lose MD-Dateien durch strukturierte DB-Einträge.
    """
    
    DOC_TYPE_CHOICES = [
        ('architecture', 'Architektur'),
        ('deployment', 'Deployment'),
        ('security', 'Sicherheit'),
        ('performance', 'Performance'),
        ('integration', 'Integration'),
        ('api_overview', 'API Übersicht'),
        ('concept', 'Konzept'),
        ('guide', 'Anleitung'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    doc_type = models.CharField(max_length=50, choices=DOC_TYPE_CHOICES)
    
    summary = models.TextField(blank=True, help_text="Kurzzusammenfassung (1-2 Sätze)")
    content = models.TextField(help_text="Markdown-Inhalt")
    
    # Versionierung
    version = models.CharField(max_length=20, default="1.0")
    is_current = models.BooleanField(default=True, help_text="Ist dies die aktuelle Version?")
    previous_version = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='newer_versions'
    )
    
    # Metadaten
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='docs_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='docs_updated'
    )
    
    # Ursprung (falls aus MD importiert)
    source_file = models.CharField(
        max_length=500, blank=True,
        help_text="Ursprünglicher MD-Dateipfad (falls importiert)"
    )
    
    class Meta:
        db_table = 'documentation_system'
        ordering = ['doc_type', 'title']
        verbose_name = 'System-Dokumentation'
        verbose_name_plural = 'System-Dokumentationen'
    
    def __str__(self):
        return f"{self.get_doc_type_display()}: {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class DomainDocumentation(models.Model):
    """
    Dokumentation einer spezifischen Domain (Writing Hub, Control Center, etc.).
    """
    
    SECTION_CHOICES = [
        ('overview', 'Übersicht'),
        ('features', 'Features'),
        ('api', 'API'),
        ('models', 'Datenmodelle'),
        ('handlers', 'Handlers'),
        ('views', 'Views/URLs'),
        ('templates', 'Templates'),
        ('changelog', 'Änderungshistorie'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    domain = models.ForeignKey(
        'bfagent.DomainArt', on_delete=models.CASCADE,
        related_name='documentation'
    )
    
    section = models.CharField(max_length=50, choices=SECTION_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Markdown-Inhalt")
    
    order = models.IntegerField(default=0, help_text="Sortierung innerhalb der Domain")
    is_published = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documentation_domain'
        unique_together = ['domain', 'section']
        ordering = ['domain', 'order', 'section']
        verbose_name = 'Domain-Dokumentation'
        verbose_name_plural = 'Domain-Dokumentationen'
    
    def __str__(self):
        return f"{self.domain.display_name}: {self.get_section_display()}"


class ChangelogEntry(models.Model):
    """
    Changelog-Eintrag, automatisch aus geschlossenen Bugs/Features generiert.
    Basis für automatische CHANGELOG.md Generierung.
    """
    
    CHANGE_TYPE_CHOICES = [
        ('feature', '✨ Feature'),
        ('bugfix', '🐛 Bugfix'),
        ('enhancement', '💡 Enhancement'),
        ('breaking', '⚠️ Breaking Change'),
        ('security', '🔒 Security'),
        ('performance', '⚡ Performance'),
        ('docs', '📚 Documentation'),
        ('refactor', '♻️ Refactoring'),
        ('deprecation', '🗑️ Deprecation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Verknüpfung zum Requirement (Bug/Feature)
    requirement = models.OneToOneField(
        'bfagent.TestRequirement', on_delete=models.CASCADE,
        related_name='changelog_entry', null=True, blank=True
    )
    
    # Changelog-Daten
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Kategorisierung
    domain = models.ForeignKey(
        'bfagent.DomainArt', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='changelog_entries'
    )
    
    # Release-Zuordnung
    version = models.CharField(max_length=20, blank=True, help_text="z.B. 2.1.0")
    release_date = models.DateField(null=True, blank=True)
    
    # Sichtbarkeit
    is_public = models.BooleanField(default=True, help_text="In öffentlichen Release Notes zeigen?")
    is_breaking = models.BooleanField(default=False, help_text="Breaking Change?")
    
    # Metadaten
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    
    class Meta:
        db_table = 'documentation_changelog'
        ordering = ['-created_at']
        verbose_name = 'Changelog-Eintrag'
        verbose_name_plural = 'Changelog-Einträge'
    
    def __str__(self):
        return f"{self.get_change_type_display()} {self.title}"
    
    @classmethod
    def create_from_requirement(cls, requirement, change_type=None):
        """Erstellt einen Changelog-Eintrag aus einem TestRequirement."""
        from apps.bfagent.models_domains import DomainArt
        
        # Change-Type aus Requirement-Category ableiten
        if not change_type:
            type_mapping = {
                'bug_fix': 'bugfix',
                'feature': 'feature',
                'enhancement': 'enhancement',
                'performance': 'performance',
                'security': 'security',
            }
            change_type = type_mapping.get(requirement.category, 'feature')
        
        # Domain finden
        domain = None
        if requirement.domain:
            domain = DomainArt.objects.filter(
                models.Q(slug=requirement.domain) |
                models.Q(name=requirement.domain)
            ).first()
        
        return cls.objects.create(
            requirement=requirement,
            change_type=change_type,
            title=requirement.name,
            description=requirement.description or '',
            domain=domain,
            created_by=requirement.created_by,
        )


class GlossaryTerm(models.Model):
    """
    Zentrale Begriffsdefinitionen für das System.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    term = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, max_length=100)
    definition = models.TextField()
    
    # Kategorisierung
    category = models.CharField(max_length=50, blank=True, help_text="z.B. 'Handler', 'Model', 'API'")
    
    # Verknüpfungen
    related_terms = models.ManyToManyField('self', blank=True, symmetrical=True)
    domains = models.ManyToManyField('bfagent.DomainArt', blank=True, related_name='glossary_terms')
    
    # Beispiele und Kontext
    examples = models.TextField(blank=True, help_text="Code-Beispiele oder Anwendungsfälle")
    see_also = models.TextField(blank=True, help_text="Externe Links oder Referenzen")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documentation_glossary'
        ordering = ['term']
        verbose_name = 'Glossar-Begriff'
        verbose_name_plural = 'Glossar-Begriffe'
    
    def __str__(self):
        return self.term
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.term)
        super().save(*args, **kwargs)


class DocumentationLink(models.Model):
    """
    Verknüpft TestRequirements mit relevanter Dokumentation.
    Ermöglicht Tracking welche Doku bei Bug/Feature relevant ist.
    """
    
    LINK_TYPE_CHOICES = [
        ('affected', 'Betroffen'),
        ('updated', 'Aktualisiert'),
        ('created', 'Neu erstellt'),
        ('reference', 'Referenz'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    requirement = models.ForeignKey(
        'bfagent.TestRequirement', on_delete=models.CASCADE,
        related_name='documentation_links'
    )
    
    # Kann auf verschiedene Doku-Typen verweisen
    system_doc = models.ForeignKey(
        SystemDocumentation, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='requirement_links'
    )
    domain_doc = models.ForeignKey(
        DomainDocumentation, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='requirement_links'
    )
    external_file = models.CharField(
        max_length=500, blank=True,
        help_text="Pfad zu externer MD-Datei (falls nicht in DB)"
    )
    
    link_type = models.CharField(max_length=20, choices=LINK_TYPE_CHOICES, default='reference')
    notes = models.TextField(blank=True, help_text="Was wurde geändert/ist relevant?")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documentation_links'
        verbose_name = 'Dokumentations-Verknüpfung'
        verbose_name_plural = 'Dokumentations-Verknüpfungen'
    
    def __str__(self):
        doc_name = (
            self.system_doc.title if self.system_doc else
            self.domain_doc.title if self.domain_doc else
            self.external_file
        )
        return f"{self.requirement.name} → {doc_name}"
