"""Abstract Django models for concept-template integration (ADR-147 Phase B).

Consumer apps inherit these and override PK/tenant_id types as needed.
Requires the [django] extra: pip install iil-concept-templates[django]
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class AbstractConceptDocument(models.Model):
    """Abstract base for documents linked to a concept.

    Consumer apps MUST override:
    - ``id`` if not using BigAutoField (e.g. UUIDField for risk-hub)
    - ``tenant_id`` if not using BigIntegerField (e.g. UUIDField for risk-hub)
    - Add a ForeignKey to the app-specific concept model
    """

    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )
    title = models.CharField(
        max_length=240,
        verbose_name=_("Titel"),
    )
    scope = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name=_("Fachbereich"),
        help_text=_("brandschutz, explosionsschutz, ausschreibung"),
    )
    source_filename = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Originaldateiname"),
    )
    content_type = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name=_("MIME-Typ"),
    )
    extracted_text = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Extrahierter Text"),
        help_text=_("Volltext aus PDF-Extraktion"),
    )
    extraction_warnings = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Extraktions-Warnungen"),
        help_text=_("JSON-Liste von Warnungen aus der Extraktion"),
    )
    page_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Seitenanzahl"),
    )
    template_json = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Template JSON"),
        help_text=_("Serialisiertes ConceptTemplate nach LLM-Analyse"),
    )
    analysis_confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("Analyse-Konfidenz"),
        help_text=_("0.0-1.0, Konfidenz der LLM-Strukturanalyse"),
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("uploaded", _("Hochgeladen")),
            ("extracting", _("Wird extrahiert")),
            ("extracted", _("Text extrahiert")),
            ("analyzing", _("Wird analysiert")),
            ("analyzed", _("Analysiert")),
            ("failed", _("Fehlgeschlagen")),
        ],
        default="uploaded",
        verbose_name=_("Status"),
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Fehlermeldung"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Erstellt am"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Aktualisiert am"),
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Gelöscht am"),
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.scope})"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def has_extracted_text(self) -> bool:
        return bool(self.extracted_text)

    @property
    def has_template(self) -> bool:
        return bool(self.template_json)


class AbstractConceptTemplate(models.Model):
    """Abstract base for persisted concept templates.

    Stores the master or customer-specific template as serialized JSON.
    Consumer apps override PK/tenant_id as needed.
    """

    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Template-Name"),
    )
    scope = models.CharField(
        max_length=30,
        verbose_name=_("Fachbereich"),
    )
    version = models.CharField(
        max_length=20,
        default="1.0",
        verbose_name=_("Version"),
    )
    is_master = models.BooleanField(
        default=False,
        verbose_name=_("Master-Template"),
    )
    framework = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Framework"),
    )
    template_json = models.TextField(
        verbose_name=_("Template JSON"),
        help_text=_("Serialisiertes ConceptTemplate (Pydantic)"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Erstellt am"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Aktualisiert am"),
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Gelöscht am"),
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.scope})"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class AbstractFilledTemplate(models.Model):
    """Abstract base for filled-out concept templates (ADR-147 Phase E).

    Stores the values entered by users for a specific ConceptTemplate.
    Consumer apps MUST add:
    - ForeignKey to the app-specific ConceptTemplate model
    - ForeignKey to the app-specific concept model (optional)
    - Override tenant_id type if needed
    """

    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )
    name = models.CharField(
        max_length=240,
        verbose_name=_("Dokumentname"),
        help_text=_("Name des ausgefüllten Dokuments"),
    )
    values_json = models.TextField(
        verbose_name=_("Ausgefüllte Werte"),
        help_text=_("JSON: {section_name: {field_name: value}}"),
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", _("Entwurf")),
            ("review", _("In Prüfung")),
            ("approved", _("Freigegeben")),
            ("exported", _("Exportiert")),
        ],
        default="draft",
        verbose_name=_("Status"),
    )
    generated_pdf_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name=_("PDF S3-Key"),
        help_text=_("S3-Pfad des generierten PDFs"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Erstellt am"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Aktualisiert am"),
    )

    class Meta:
        abstract = True
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"
