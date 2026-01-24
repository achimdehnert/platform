"""
Django Models für Expert Hub - Explosionsschutz Analysen

Persistenz für:
- Analyse-Sessions
- Analyseergebnisse (Zonen, Equipment, Lüftung)
- Stoffdaten (erweiterbar)
"""

import uuid
from django.db import models
from django.contrib.auth.models import User


class ExAnalysisSession(models.Model):
    """Analyse-Session für Explosionsschutz."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basis-Info
    name = models.CharField(max_length=200, help_text="Name der Analyse")
    description = models.TextField(blank=True)
    
    # Projekt-Referenz (optional)
    project_name = models.CharField(max_length=200, blank=True)
    project_location = models.CharField(max_length=300, blank=True)
    
    # Benutzer
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ex_analysis_sessions'
    )
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Entwurf'),
        ('in_progress', 'In Bearbeitung'),
        ('review', 'In Prüfung'),
        ('completed', 'Abgeschlossen'),
        ('archived', 'Archiviert'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Corporate Design Template (Word-Vorlage)
    template_file = models.FileField(
        upload_to='expert_hub/templates/',
        null=True,
        blank=True,
        help_text="Word-Vorlage (.docx) für Corporate Design"
    )
    company_logo = models.ImageField(
        upload_to='expert_hub/logos/',
        null=True,
        blank=True,
        help_text="Firmenlogo für Deckblatt"
    )
    
    # Metadaten
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'expert_hub_analysis_session'
        ordering = ['-created_at']
        verbose_name = 'Ex-Analyse Session'
        verbose_name_plural = 'Ex-Analyse Sessions'
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class ExZoneResult(models.Model):
    """Ergebnis einer Ex-Zonen Klassifizierung."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ExAnalysisSession,
        on_delete=models.CASCADE,
        related_name='zone_results'
    )
    
    # Raum-Info
    room_name = models.CharField(max_length=200)
    room_volume_m3 = models.FloatField(null=True, blank=True)
    
    # Klassifizierung
    ZONE_CHOICES = [
        ('zone_0', 'Zone 0'),
        ('zone_1', 'Zone 1'),
        ('zone_2', 'Zone 2'),
        ('zone_20', 'Zone 20'),
        ('zone_21', 'Zone 21'),
        ('zone_22', 'Zone 22'),
        ('none', 'Keine Ex-Zone'),
    ]
    zone_type = models.CharField(max_length=20, choices=ZONE_CHOICES)
    zone_category = models.CharField(max_length=10, choices=[('gas', 'Gas'), ('dust', 'Staub')])
    
    # Berechnung
    zone_extent_m = models.FloatField(null=True, blank=True, help_text="Zonenausdehnung in m")
    zone_volume_m3 = models.FloatField(null=True, blank=True, help_text="Zonenvolumen in m³")
    
    # Risiko
    RISK_CHOICES = [
        ('low', 'Gering'),
        ('medium', 'Mittel'),
        ('high', 'Hoch'),
        ('critical', 'Kritisch'),
    ]
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default='medium')
    
    # Begründung
    justification = models.TextField(help_text="Begründung mit Normbezug")
    recommendations = models.JSONField(default=list, blank=True)
    
    # Input-Parameter (für Nachvollziehbarkeit)
    input_parameters = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'expert_hub_zone_result'
        ordering = ['room_name']
        verbose_name = 'Zonen-Ergebnis'
        verbose_name_plural = 'Zonen-Ergebnisse'
    
    def __str__(self):
        return f"{self.room_name}: {self.get_zone_type_display()}"


class ExEquipmentCheck(models.Model):
    """Equipment-Prüfungsergebnis."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ExAnalysisSession,
        on_delete=models.CASCADE,
        related_name='equipment_checks'
    )
    
    # Equipment-Info
    equipment_name = models.CharField(max_length=200)
    equipment_type = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    
    # Ex-Kennzeichnung
    ex_marking = models.CharField(max_length=100, blank=True)
    detected_category = models.CharField(max_length=10, blank=True)
    detected_temp_class = models.CharField(max_length=5, blank=True)
    detected_exp_group = models.CharField(max_length=5, blank=True)
    
    # Zone
    target_zone = models.CharField(max_length=20)
    required_category = models.CharField(max_length=10)
    
    # Ergebnis
    is_suitable = models.BooleanField(default=False)
    issues = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'expert_hub_equipment_check'
        ordering = ['equipment_name']
        verbose_name = 'Equipment-Prüfung'
        verbose_name_plural = 'Equipment-Prüfungen'
    
    def __str__(self):
        status = "✓" if self.is_suitable else "✗"
        return f"{self.equipment_name} [{status}]"


class ExSubstance(models.Model):
    """Stoffdatenbank für Explosionsschutz (erweiterbar)."""
    
    id = models.AutoField(primary_key=True)
    
    # Basis
    name = models.CharField(max_length=200, unique=True)
    name_en = models.CharField(max_length=200, blank=True)
    cas_number = models.CharField(max_length=20, blank=True, db_index=True)
    
    # Explosionsgrenzen
    lower_explosion_limit = models.FloatField(help_text="UEG in Vol-%")
    upper_explosion_limit = models.FloatField(help_text="OEG in Vol-%")
    
    # Physikalische Eigenschaften
    flash_point_c = models.FloatField(null=True, blank=True, help_text="Flammpunkt in °C")
    ignition_temperature_c = models.FloatField(null=True, blank=True, help_text="Zündtemperatur in °C")
    vapor_density = models.FloatField(null=True, blank=True, help_text="Dampfdichte rel. zu Luft")
    molar_mass = models.FloatField(null=True, blank=True, help_text="Molare Masse in g/mol")
    
    # Ex-Klassifizierung
    TEMP_CLASS_CHOICES = [
        ('T1', 'T1 (>450°C)'),
        ('T2', 'T2 (300-450°C)'),
        ('T3', 'T3 (200-300°C)'),
        ('T4', 'T4 (135-200°C)'),
        ('T5', 'T5 (100-135°C)'),
        ('T6', 'T6 (85-100°C)'),
    ]
    temperature_class = models.CharField(max_length=5, choices=TEMP_CLASS_CHOICES, blank=True)
    
    EXP_GROUP_CHOICES = [
        ('IIA', 'IIA'),
        ('IIB', 'IIB'),
        ('IIC', 'IIC'),
    ]
    explosion_group = models.CharField(max_length=5, choices=EXP_GROUP_CHOICES, blank=True)
    
    # Quelle
    data_source = models.CharField(max_length=100, default='GESTIS')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'expert_hub_substance'
        ordering = ['name']
        verbose_name = 'Gefahrstoff'
        verbose_name_plural = 'Gefahrstoffe'
    
    def __str__(self):
        return f"{self.name} (UEG: {self.lower_explosion_limit}%)"


class ExWorkflowPhase(models.Model):
    """Workflow-Phasen für Explosionsschutzdokument nach TRGS 720ff."""
    
    id = models.AutoField(primary_key=True)
    
    # Basis
    number = models.CharField(max_length=10, help_text="z.B. '1', '6.2.1'")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Hierarchie
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    order = models.IntegerField(default=0)
    
    # Typ und Verhalten
    PHASE_TYPE_CHOICES = [
        ('info', 'Informationssammlung'),
        ('analysis', 'Analyse'),
        ('calculation', 'Berechnung'),
        ('assessment', 'Bewertung'),
        ('documentation', 'Dokumentation'),
        ('approval', 'Freigabe'),
    ]
    phase_type = models.CharField(max_length=20, choices=PHASE_TYPE_CHOICES, default='info')
    
    # Verknüpfung zu Tools/Views
    tool_name = models.CharField(max_length=100, blank=True, help_text="z.B. 'zone_analysis'")
    help_text = models.TextField(blank=True, help_text="Hilfetext für diese Phase")
    
    # Status
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'expert_hub_workflow_phase'
        ordering = ['order', 'number']
        verbose_name = 'Workflow-Phase'
        verbose_name_plural = 'Workflow-Phasen'
    
    def __str__(self):
        return f"{self.number} {self.title}"


class ExSessionPhaseStatus(models.Model):
    """Status einer Phase innerhalb einer Session."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ExAnalysisSession,
        on_delete=models.CASCADE,
        related_name='phase_statuses'
    )
    phase = models.ForeignKey(
        ExWorkflowPhase,
        on_delete=models.CASCADE,
        related_name='session_statuses'
    )
    
    # Status
    STATUS_CHOICES = [
        ('not_started', 'Nicht begonnen'),
        ('in_progress', 'In Bearbeitung'),
        ('completed', 'Abgeschlossen'),
        ('skipped', 'Übersprungen'),
        ('not_applicable', 'Nicht zutreffend'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    # Fortschritt
    progress_percent = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    
    # Inhalte
    content = models.TextField(blank=True, help_text="Textinhalt dieser Phase")
    ai_generated_content = models.TextField(blank=True, help_text="KI-generierter Inhalt")
    
    # Daten
    data = models.JSONField(default=dict, blank=True, help_text="Phasen-spezifische Daten")
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'expert_hub_session_phase_status'
        unique_together = ['session', 'phase']
        ordering = ['phase__order']
        verbose_name = 'Session-Phasenstatus'
        verbose_name_plural = 'Session-Phasenstatus'
    
    def __str__(self):
        return f"{self.session.name} - {self.phase.number}: {self.get_status_display()}"


class ExSessionDocument(models.Model):
    """Hochgeladene Dokumente zu einer Analyse-Session."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ExAnalysisSession,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    # Optional: Dokument einer Phase zuordnen
    phase = models.ForeignKey(
        ExWorkflowPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    
    # Datei
    file = models.FileField(upload_to='expert_hub/documents/%Y/%m/')
    original_filename = models.CharField(max_length=255, default='')
    file_size = models.IntegerField(help_text="Dateigröße in Bytes", default=0)
    file_type = models.CharField(max_length=100, blank=True, help_text="MIME-Type")
    
    # Kategorisierung
    DOC_TYPE_CHOICES = [
        ('plan', 'Lageplan/Grundriss'),
        ('piid', 'P&ID / R&I-Schema'),
        ('datasheet', 'Datenblatt'),
        ('certificate', 'Zertifikat/Prüfbericht'),
        ('report', 'Gutachten/Bericht'),
        ('photo', 'Foto'),
        ('cad', 'CAD-Datei'),
        ('other', 'Sonstiges'),
    ]
    document_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default='other')
    description = models.TextField(blank=True)
    
    # Analyse-Status
    ANALYSIS_STATUS_CHOICES = [
        ('pending', 'Ausstehend'),
        ('processing', 'Wird analysiert'),
        ('completed', 'Analysiert'),
        ('failed', 'Fehler'),
        ('skipped', 'Übersprungen'),
    ]
    analysis_status = models.CharField(max_length=20, choices=ANALYSIS_STATUS_CHOICES, default='pending')
    analysis_result = models.JSONField(default=dict, blank=True, help_text="Extrahierte Daten")
    analysis_notes = models.TextField(blank=True)
    
    # Benutzer
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ex_uploaded_documents'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'expert_hub_session_document'
        ordering = ['-created_at']
        verbose_name = 'Session-Dokument'
        verbose_name_plural = 'Session-Dokumente'
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_document_type_display()})"
    
    @property
    def file_size_display(self):
        """Dateigröße formatiert anzeigen."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
    
    @property
    def file_extension(self):
        """Dateiendung extrahieren."""
        if '.' in self.original_filename:
            return self.original_filename.rsplit('.', 1)[-1].lower()
        return ''
