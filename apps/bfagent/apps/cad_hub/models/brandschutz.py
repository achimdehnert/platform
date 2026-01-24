"""
Brandschutz Datenbank-Models.

Models für die Verwaltung von Brandschutz-Prüfungen, Symbolen und Nachweisen.
"""
import uuid
from django.db import models
from django.utils import timezone


class BrandschutzKategorie(models.TextChoices):
    """Kategorien für Brandschutz-Elemente."""
    FLUCHTWEG = "fluchtweg", "Fluchtweg"
    NOTAUSGANG = "notausgang", "Notausgang"
    BRANDABSCHNITT = "brandabschnitt", "Brandabschnitt"
    FEUERLOESCHER = "feuerloescher", "Feuerlöscher"
    RAUCHMELDER = "rauchmelder", "Rauchmelder"
    SPRINKLER = "sprinkler", "Sprinkler"
    RWA = "rwa", "RWA"
    EX_ZONE = "ex_zone", "Ex-Zone"
    BRANDMELDER = "brandmelder", "Brandmelder"
    HYDRANT = "hydrant", "Hydrant"


class Feuerwiderstandsklasse(models.TextChoices):
    """Feuerwiderstandsklassen nach DIN 4102 / EN 13501."""
    F30 = "F30", "F30 (30 min)"
    F60 = "F60", "F60 (60 min)"
    F90 = "F90", "F90 (90 min)"
    F120 = "F120", "F120 (120 min)"
    F180 = "F180", "F180 (180 min)"


class ExZoneTyp(models.TextChoices):
    """Explosionsgefährdete Bereiche nach ATEX."""
    ZONE_0 = "zone_0", "Zone 0 (Gas, ständig)"
    ZONE_1 = "zone_1", "Zone 1 (Gas, gelegentlich)"
    ZONE_2 = "zone_2", "Zone 2 (Gas, selten)"
    ZONE_20 = "zone_20", "Zone 20 (Staub, ständig)"
    ZONE_21 = "zone_21", "Zone 21 (Staub, gelegentlich)"
    ZONE_22 = "zone_22", "Zone 22 (Staub, selten)"


class PruefStatus(models.TextChoices):
    """Status einer Brandschutz-Prüfung."""
    ENTWURF = "entwurf", "Entwurf"
    IN_PRUEFUNG = "in_pruefung", "In Prüfung"
    ABGESCHLOSSEN = "abgeschlossen", "Abgeschlossen"
    MAENGEL = "maengel", "Mängel festgestellt"
    FREIGEGEBEN = "freigegeben", "Freigegeben"


class BrandschutzSymbol(models.Model):
    """
    Brandschutz-Symbol nach DIN EN ISO 7010.
    
    Speichert Symbol-Definitionen mit DXF-Block-Daten.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, help_text="Name des Symbols")
    din_nummer = models.CharField(max_length=20, help_text="z.B. F001, E001")
    kategorie = models.CharField(
        max_length=50,
        choices=BrandschutzKategorie.choices,
        default=BrandschutzKategorie.FEUERLOESCHER,
    )
    
    beschreibung = models.TextField(blank=True)
    
    # DXF-Block als Datei oder JSON
    block_dxf = models.FileField(upload_to="brandschutz/symbole/", blank=True, null=True)
    block_json = models.JSONField(blank=True, null=True, help_text="Block-Definition als JSON")
    
    # Darstellung
    farbe = models.CharField(max_length=20, default="rot", help_text="rot, grün, gelb, blau")
    groesse_mm = models.FloatField(default=200, help_text="Standard-Größe in mm")
    
    # Regelwerk
    regelwerk = models.CharField(max_length=100, blank=True, help_text="z.B. ASR A2.2")
    
    aktiv = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "cad_hub_brandschutz_symbol"
        verbose_name = "Brandschutz-Symbol"
        verbose_name_plural = "Brandschutz-Symbole"
        ordering = ["kategorie", "din_nummer"]
    
    def __str__(self):
        return f"{self.din_nummer} - {self.name}"


class BrandschutzPruefung(models.Model):
    """
    Brandschutz-Prüfung für ein Projekt/Plan.
    
    Dokumentiert die Analyse, Mängel und Maßnahmen.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basis-Info
    titel = models.CharField(max_length=200, help_text="Titel der Prüfung")
    projekt_name = models.CharField(max_length=200)
    projekt_id = models.UUIDField(blank=True, null=True)
    
    # Gebäude-Info
    gebaeude_typ = models.CharField(max_length=50, blank=True)
    etage = models.CharField(max_length=50, blank=True, default="EG")
    flaeche_qm = models.FloatField(blank=True, null=True, help_text="Geprüfte Fläche in m²")
    beschreibung = models.TextField(blank=True)
    
    # Dateien
    quelldatei = models.FileField(upload_to="brandschutz/plaene/", blank=True, null=True)
    report_pdf = models.FileField(upload_to="brandschutz/reports/", blank=True, null=True)
    
    # Status
    status = models.CharField(
        max_length=50,
        choices=PruefStatus.choices,
        default=PruefStatus.ENTWURF,
    )
    
    # Analyseergebnisse (JSON)
    analyse_ergebnis = models.JSONField(blank=True, null=True)
    
    # Prüfer & Termine
    pruefer = models.CharField(max_length=200, blank=True)
    pruef_datum = models.DateField(blank=True, null=True)
    naechste_pruefung = models.DateField(blank=True, null=True)
    
    # Timestamps
    erstellt_am = models.DateTimeField(auto_now_add=True)
    aktualisiert_am = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = "cad_hub"
        db_table = "cad_hub_brandschutz_pruefung"
        verbose_name = "Brandschutz-Prüfung"
        verbose_name_plural = "Brandschutz-Prüfungen"
        ordering = ["-pruef_datum", "-erstellt_am"]
    
    def __str__(self):
        return f"{self.titel} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if not self.titel:
            self.titel = f"Prüfung {self.projekt_name}"
        if not self.pruef_datum:
            self.pruef_datum = timezone.now().date()
        super().save(*args, **kwargs)


class BrandschutzMangel(models.Model):
    """
    Einzelner Mangel aus einer Brandschutz-Prüfung.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    pruefung = models.ForeignKey(
        BrandschutzPruefung,
        on_delete=models.CASCADE,
        related_name="maengel",
    )
    
    # Mangel-Details
    kategorie = models.CharField(
        max_length=50,
        choices=BrandschutzKategorie.choices,
        default=BrandschutzKategorie.FLUCHTWEG,
    )
    beschreibung = models.TextField()
    schweregrad = models.CharField(
        max_length=20, 
        choices=[
            ("kritisch", "Kritisch"),
            ("hoch", "Hoch"),
            ("mittel", "Mittel"),
            ("gering", "Gering"),
        ],
        default="mittel"
    )
    
    # Regelwerk-Referenz
    regelwerk_referenz = models.CharField(max_length=100, blank=True, help_text="z.B. ASR A2.3 §5")
    
    # Position im Plan
    position_x = models.FloatField(blank=True, null=True)
    position_y = models.FloatField(blank=True, null=True)
    
    # Status
    behoben = models.BooleanField(default=False)
    behoben_am = models.DateTimeField(blank=True, null=True)
    behoben_kommentar = models.TextField(blank=True)
    
    # Anhänge
    foto = models.ImageField(upload_to="brandschutz/maengel/", blank=True, null=True)
    notizen = models.TextField(blank=True)
    
    # Timestamps
    erstellt_am = models.DateTimeField(auto_now_add=True)
    aktualisiert_am = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = "cad_hub"
        db_table = "cad_hub_brandschutz_mangel"
        verbose_name = "Brandschutz-Mangel"
        verbose_name_plural = "Brandschutz-Mängel"
        ordering = ["-schweregrad", "-erstellt_am"]
    
    def __str__(self):
        return f"{self.get_kategorie_display()}: {self.beschreibung[:50]}"


class BrandschutzSymbolVorschlag(models.Model):
    """
    Vorgeschlagenes Symbol für eine Prüfung.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    pruefung = models.ForeignKey(
        BrandschutzPruefung,
        on_delete=models.CASCADE,
        related_name="symbole",
    )
    
    symbol_typ = models.CharField(max_length=50, help_text="z.B. F001, RM, E001")
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    raum_referenz = models.CharField(max_length=100, blank=True)
    
    begruendung = models.TextField(blank=True)
    regelwerk_basis = models.CharField(max_length=100, blank=True)
    prioritaet = models.IntegerField(default=2, help_text="1=hoch, 2=mittel, 3=niedrig")
    
    status = models.CharField(
        max_length=20,
        choices=[
            ("vorgeschlagen", "Vorgeschlagen"),
            ("genehmigt", "Genehmigt"),
            ("abgelehnt", "Abgelehnt"),
            ("eingefuegt", "Eingefügt"),
        ],
        default="vorgeschlagen"
    )
    
    erstellt_am = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = "cad_hub"
        db_table = "cad_hub_brandschutz_symbol_vorschlag"
        verbose_name = "Symbol-Vorschlag"
        verbose_name_plural = "Symbol-Vorschläge"
        ordering = ["prioritaet", "-erstellt_am"]
    
    def __str__(self):
        return f"{self.symbol_typ} @ ({self.position_x:.0f}, {self.position_y:.0f})"


class BrandschutzRegelwerk(models.Model):
    """
    Regelwerk-Referenz für Brandschutz-Prüfungen.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    kuerzel = models.CharField(max_length=50, unique=True, help_text="z.B. ASR_A2_2")
    name = models.CharField(max_length=200, help_text="z.B. ASR A2.2 - Feuerlöscher")
    
    # Typ
    TYP_CHOICES = [
        ("asr", "Arbeitsstättenregel"),
        ("din", "DIN-Norm"),
        ("lbo", "Landesbauordnung"),
        ("mbo", "Musterbauordnung"),
        ("vstaettvo", "Versammlungsstättenverordnung"),
        ("indbauril", "Industriebaurichtlinie"),
        ("sonstige", "Sonstige"),
    ]
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default="din")
    
    # Anwendungsbereich
    kategorien = models.JSONField(default=list, help_text="Anwendbare Kategorien")
    
    # Regeln als JSON
    regeln = models.JSONField(default=dict, help_text="Prüfregeln als JSON")
    
    # Referenz
    url = models.URLField(blank=True)
    version = models.CharField(max_length=50, blank=True)
    gueltig_ab = models.DateField(blank=True, null=True)
    
    aktiv = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "cad_hub_brandschutz_regelwerk"
        verbose_name = "Brandschutz-Regelwerk"
        verbose_name_plural = "Brandschutz-Regelwerke"
        ordering = ["typ", "kuerzel"]
    
    def __str__(self):
        return f"{self.kuerzel} - {self.name}"
