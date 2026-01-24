# apps/cad_hub/admin_brandschutz.py
"""
Admin-Konfiguration für Brandschutz-System.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q

from .models import (
    BrandschutzPruefung,
    BrandschutzMangel,
    BrandschutzSymbol,
    BrandschutzSymbolVorschlag,
    BrandschutzRegelwerk,
    PruefStatus,
)


class BrandschutzMangelInline(admin.TabularInline):
    """Inline für Mängel in Prüfung."""
    model = BrandschutzMangel
    extra = 0
    fields = ["kategorie", "schweregrad", "beschreibung", "regelwerk_referenz", "behoben"]
    readonly_fields = ["erstellt_am"]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("pruefung")


class BrandschutzSymbolInline(admin.TabularInline):
    """Inline für Symbole in Prüfung."""
    model = BrandschutzSymbolVorschlag
    extra = 0
    fields = ["symbol_typ", "position_x", "position_y", "status", "begruendung"]
    readonly_fields = ["erstellt_am"]


@admin.register(BrandschutzPruefung)
class BrandschutzPruefungAdmin(admin.ModelAdmin):
    """Admin für Brandschutz-Prüfungen."""
    
    list_display = [
        "titel",
        "projekt_name",
        "status_badge",
        "mangel_count",
        "symbol_count",
        "pruefer",
        "pruef_datum",
        "actions_column",
    ]
    list_filter = ["status", "pruef_datum", "pruefer", "gebaeude_typ"]
    search_fields = ["titel", "projekt_name", "pruefer", "beschreibung"]
    date_hierarchy = "pruef_datum"
    ordering = ["-pruef_datum"]
    
    readonly_fields = [
        "id", 
        "erstellt_am", 
        "aktualisiert_am",
        "analyse_ergebnis_display",
        "mangel_statistik",
    ]
    
    fieldsets = (
        (None, {
            "fields": ("titel", "projekt_name", "status")
        }),
        ("Gebäude-Information", {
            "fields": ("gebaeude_typ", "etage", "flaeche_qm", "beschreibung")
        }),
        ("Prüfung", {
            "fields": ("pruefer", "pruef_datum", "naechste_pruefung")
        }),
        ("Dateien", {
            "fields": ("quelldatei", "report_pdf"),
            "classes": ("collapse",)
        }),
        ("Analyse-Ergebnis", {
            "fields": ("analyse_ergebnis_display", "mangel_statistik"),
            "classes": ("collapse",)
        }),
        ("Metadaten", {
            "fields": ("id", "erstellt_am", "aktualisiert_am"),
            "classes": ("collapse",)
        }),
    )
    
    inlines = [BrandschutzMangelInline, BrandschutzSymbolInline]
    
    def status_badge(self, obj):
        colors = {
            PruefStatus.ENTWURF: "#6c757d",
            PruefStatus.IN_PRUEFUNG: "#0d6efd",
            PruefStatus.ABGESCHLOSSEN: "#198754",
            PruefStatus.MAENGEL: "#dc3545",
            PruefStatus.FREIGEGEBEN: "#20c997",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:10px; font-size:0.85em;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"
    
    def mangel_count(self, obj):
        count = obj.maengel.count()
        offen = obj.maengel.filter(behoben=False).count()
        if offen > 0:
            return format_html(
                '<span style="color:#dc3545; font-weight:bold;">{} ({} offen)</span>',
                count, offen
            )
        return count
    mangel_count.short_description = "Mängel"
    
    def symbol_count(self, obj):
        return obj.symbole.count()
    symbol_count.short_description = "Symbole"
    
    def actions_column(self, obj):
        return format_html(
            '<a class="button" href="{}">📊 Report</a> '
            '<a class="button" href="{}">📥 PDF</a>',
            reverse("admin:cad_hub_brandschutzpruefung_change", args=[obj.pk]),
            reverse("brandschutz:report_pdf", args=[obj.pk]) if obj.pk else "#"
        )
    actions_column.short_description = "Aktionen"
    
    def analyse_ergebnis_display(self, obj):
        if not obj.analyse_ergebnis:
            return "-"
        import json
        return format_html(
            '<pre style="background:#f8f9fa; padding:10px; border-radius:5px; '
            'max-height:300px; overflow:auto;">{}</pre>',
            json.dumps(obj.analyse_ergebnis, indent=2, ensure_ascii=False)
        )
    analyse_ergebnis_display.short_description = "Analyse-Ergebnis (JSON)"
    
    def mangel_statistik(self, obj):
        stats = obj.maengel.values("schweregrad").annotate(count=Count("id"))
        if not stats:
            return "Keine Mängel"
        
        html = "<ul>"
        for stat in stats:
            html += f"<li><strong>{stat['schweregrad']}</strong>: {stat['count']}</li>"
        html += "</ul>"
        return format_html(html)
    mangel_statistik.short_description = "Mängel nach Schweregrad"
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("maengel", "symbole")


@admin.register(BrandschutzMangel)
class BrandschutzMangelAdmin(admin.ModelAdmin):
    """Admin für einzelne Mängel."""
    
    list_display = [
        "kurz_beschreibung",
        "pruefung_link",
        "kategorie",
        "schweregrad_badge",
        "regelwerk_referenz",
        "behoben",
        "behoben_status",
        "erstellt_am",
    ]
    list_filter = ["kategorie", "schweregrad", "behoben", "pruefung__status"]
    search_fields = ["beschreibung", "regelwerk_referenz", "pruefung__titel"]
    list_editable = ["behoben"]
    ordering = ["-erstellt_am"]
    
    fieldsets = (
        (None, {
            "fields": ("pruefung", "kategorie", "schweregrad")
        }),
        ("Details", {
            "fields": ("beschreibung", "regelwerk_referenz", "position_x", "position_y")
        }),
        ("Status", {
            "fields": ("behoben", "behoben_am", "behoben_kommentar")
        }),
        ("Anhänge", {
            "fields": ("foto", "notizen"),
            "classes": ("collapse",)
        }),
    )
    
    def kurz_beschreibung(self, obj):
        return obj.beschreibung[:50] + "..." if len(obj.beschreibung) > 50 else obj.beschreibung
    kurz_beschreibung.short_description = "Beschreibung"
    
    def pruefung_link(self, obj):
        url = reverse("admin:cad_hub_brandschutzpruefung_change", args=[obj.pruefung.pk])
        return format_html('<a href="{}">{}</a>', url, obj.pruefung.titel)
    pruefung_link.short_description = "Prüfung"
    
    def schweregrad_badge(self, obj):
        colors = {
            "kritisch": "#dc3545",
            "hoch": "#fd7e14",
            "mittel": "#ffc107",
            "gering": "#28a745",
        }
        color = colors.get(obj.schweregrad, "#6c757d")
        text_color = "white" if obj.schweregrad in ["kritisch", "hoch"] else "#333"
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 10px; '
            'border-radius:10px; font-size:0.85em;">{}</span>',
            color, text_color, obj.schweregrad.upper()
        )
    schweregrad_badge.short_description = "Schweregrad"
    schweregrad_badge.admin_order_field = "schweregrad"
    
    def behoben_status(self, obj):
        if obj.behoben:
            return format_html('<span style="color:#28a745;">✅ Behoben</span>')
        return format_html('<span style="color:#dc3545;">❌ Offen</span>')
    behoben_status.short_description = "Status"
    behoben_status.admin_order_field = "behoben"


@admin.register(BrandschutzSymbolVorschlag)
class BrandschutzSymbolVorschlagAdmin(admin.ModelAdmin):
    """Admin für Brandschutz-Symbol-Vorschläge."""
    
    list_display = [
        "symbol_typ",
        "pruefung_link",
        "position_display",
        "status_badge",
        "prioritaet",
        "erstellt_am",
    ]
    list_filter = ["symbol_typ", "status", "prioritaet", "pruefung__status"]
    search_fields = ["symbol_typ", "begruendung", "pruefung__titel"]
    ordering = ["prioritaet", "-erstellt_am"]
    
    fieldsets = (
        (None, {
            "fields": ("pruefung", "symbol_typ", "status")
        }),
        ("Position", {
            "fields": ("position_x", "position_y", "raum_referenz")
        }),
        ("Details", {
            "fields": ("begruendung", "prioritaet", "regelwerk_basis")
        }),
    )
    
    def pruefung_link(self, obj):
        url = reverse("admin:cad_hub_brandschutzpruefung_change", args=[obj.pruefung.pk])
        return format_html('<a href="{}">{}</a>', url, obj.pruefung.titel)
    pruefung_link.short_description = "Prüfung"
    
    def position_display(self, obj):
        return f"({obj.position_x:.0f}, {obj.position_y:.0f})"
    position_display.short_description = "Position"
    
    def status_badge(self, obj):
        colors = {
            "vorgeschlagen": "#0d6efd",
            "genehmigt": "#198754",
            "abgelehnt": "#dc3545",
            "eingefuegt": "#20c997",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:10px; font-size:0.85em;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = "Status"


@admin.register(BrandschutzSymbol)
class BrandschutzSymbolAdmin(admin.ModelAdmin):
    """Admin für Brandschutz-Symbole (Bibliothek)."""
    
    list_display = ["din_nummer", "name", "kategorie", "groesse_mm", "aktiv"]
    list_filter = ["kategorie", "aktiv"]
    search_fields = ["din_nummer", "name", "beschreibung"]
    ordering = ["kategorie", "din_nummer"]


@admin.register(BrandschutzRegelwerk)
class BrandschutzRegelwerkAdmin(admin.ModelAdmin):
    """Admin für Regelwerke."""
    
    list_display = [
        "kuerzel",
        "name",
        "version",
        "kategorie_count",
        "aktiv_badge",
        "gueltig_ab",
    ]
    list_filter = ["aktiv", "gueltig_ab"]
    search_fields = ["kuerzel", "name", "beschreibung"]
    ordering = ["kuerzel"]
    
    fieldsets = (
        (None, {
            "fields": ("kuerzel", "name", "version", "aktiv")
        }),
        ("Details", {
            "fields": ("beschreibung", "quelle_url")
        }),
        ("Gültigkeit", {
            "fields": ("gueltig_ab", "gueltig_bis")
        }),
        ("Regeln", {
            "fields": ("regeln",),
            "classes": ("collapse",)
        }),
    )
    
    def kategorie_count(self, obj):
        if obj.regeln and "kategorien" in obj.regeln:
            return len(obj.regeln["kategorien"])
        return 0
    kategorie_count.short_description = "Kategorien"
    
    def aktiv_badge(self, obj):
        if obj.aktiv:
            return format_html('<span style="color:#28a745;">✅ Aktiv</span>')
        return format_html('<span style="color:#6c757d;">⏸️ Inaktiv</span>')
    aktiv_badge.short_description = "Status"
