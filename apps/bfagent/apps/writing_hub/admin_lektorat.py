"""
Lektorats-Framework Admin
=========================

Admin-Konfiguration für Lektorats-Models.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models_lektorat import (
    LektoratsSession,
    LektoratsFehler,
    FigurenRegister,
    ZeitlinienEintrag,
    StilProfil,
    WiederholungsAnalyse,
    GenreStyleProfile,
    CorrectionSuggestion,
)


@admin.register(LektoratsSession)
class LektoratsSessionAdmin(admin.ModelAdmin):
    list_display = ['project', 'version_name', 'status', 'total_fehler', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['project__title', 'version_name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    
    fieldsets = (
        (None, {
            'fields': ('project', 'version_name', 'status', 'created_by')
        }),
        ('Statistiken', {
            'fields': ('total_fehler', 'fehler_kritisch', 'fehler_schwer', 
                      'fehler_mittel', 'fehler_leicht', 'fehler_marginal')
        }),
        ('Modul-Status', {
            'fields': ('modul_status',),
            'classes': ('collapse',)
        }),
        ('Zeitstempel', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LektoratsFehler)
class LektoratsFehlerAdmin(admin.ModelAdmin):
    list_display = ['severity_badge', 'modul', 'beschreibung_short', 'chapter', 'status', 'correction_status', 'created_at']
    list_filter = ['severity', 'modul', 'status', 'correction_status', 'is_intentional', 'ai_erkannt']
    search_fields = ['beschreibung', 'originaltext']
    raw_id_fields = ['session', 'chapter', 'querverweis_kapitel']
    
    fieldsets = (
        (None, {
            'fields': ('session', 'chapter', 'modul', 'severity', 'fehler_typ')
        }),
        ('Details', {
            'fields': ('beschreibung', 'originaltext', 'korrekturvorschlag', 'erklaerung')
        }),
        ('Querverweis', {
            'fields': ('querverweis_kapitel', 'querverweis_text'),
            'classes': ('collapse',)
        }),
        ('Position', {
            'fields': ('position_zeile', 'position_start', 'position_end'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'korrektur_notiz', 'korrigiert_at')
        }),
        ('Korrektur-Workflow', {
            'fields': ('correction_status', 'is_intentional'),
        }),
        ('AI-Info', {
            'fields': ('ai_erkannt', 'ai_konfidenz'),
            'classes': ('collapse',)
        }),
    )
    
    def severity_badge(self, obj):
        colors = {
            'A': '#dc3545',
            'B': '#fd7e14',
            'C': '#ffc107',
            'D': '#28a745',
            'E': '#6c757d',
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color, obj.severity
        )
    severity_badge.short_description = 'Severity'
    severity_badge.admin_order_field = 'severity'
    
    def beschreibung_short(self, obj):
        return obj.beschreibung[:60] + '...' if len(obj.beschreibung) > 60 else obj.beschreibung
    beschreibung_short.short_description = 'Beschreibung'


@admin.register(FigurenRegister)
class FigurenRegisterAdmin(admin.ModelAdmin):
    list_display = ['name', 'rolle', 'session', 'erste_erwaehnung_kapitel', 'ai_extrahiert']
    list_filter = ['rolle', 'ai_extrahiert', 'session']
    search_fields = ['name', 'name_varianten']
    raw_id_fields = ['session']
    
    fieldsets = (
        (None, {
            'fields': ('session', 'name', 'name_varianten', 'rolle')
        }),
        ('Erwähnungen', {
            'fields': ('erste_erwaehnung_kapitel', 'letzte_erwaehnung_kapitel')
        }),
        ('Physische Merkmale', {
            'fields': ('alter', 'geschlecht', 'haarfarbe', 'augenfarbe', 'groesse', 'besondere_merkmale'),
            'classes': ('collapse',)
        }),
        ('Hintergrund', {
            'fields': ('herkunft', 'beruf', 'familie'),
            'classes': ('collapse',)
        }),
        ('Persönlichkeit', {
            'fields': ('charakterzuege', 'sprechweise', 'gewohnheiten', 'motivation'),
            'classes': ('collapse',)
        }),
        ('Beziehungen & Referenzen', {
            'fields': ('beziehungen', 'kapitel_referenzen'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ZeitlinienEintrag)
class ZeitlinienEintragAdmin(admin.ModelAdmin):
    list_display = ['beschreibung_short', 'zeit_typ', 'chapter', 'tag_nummer', 'reihenfolge']
    list_filter = ['zeit_typ', 'ai_extrahiert']
    search_fields = ['beschreibung', 'originaltext']
    raw_id_fields = ['session', 'chapter']
    
    def beschreibung_short(self, obj):
        return obj.beschreibung[:50] + '...' if len(obj.beschreibung) > 50 else obj.beschreibung
    beschreibung_short.short_description = 'Beschreibung'


@admin.register(StilProfil)
class StilProfilAdmin(admin.ModelAdmin):
    list_display = ['session', 'perspektive', 'tempus', 'grundton', 'ai_analysiert']
    list_filter = ['perspektive', 'tempus', 'ai_analysiert']
    raw_id_fields = ['session']


@admin.register(WiederholungsAnalyse)
class WiederholungsAnalyseAdmin(admin.ModelAdmin):
    list_display = ['text_short', 'typ', 'anzahl', 'bewertung', 'session']
    list_filter = ['typ', 'bewertung', 'ai_erkannt']
    search_fields = ['text']
    raw_id_fields = ['session']
    
    def text_short(self, obj):
        return obj.text[:40] + '...' if len(obj.text) > 40 else obj.text
    text_short.short_description = 'Text'


# =============================================================================
# Korrektur-System Admin
# =============================================================================

@admin.register(GenreStyleProfile)
class GenreStyleProfileAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'genre', 'repetition_tolerance', 'preferred_sentence_length', 'updated_at']
    list_filter = ['repetition_tolerance', 'preferred_sentence_length']
    search_fields = ['genre', 'display_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('genre', 'display_name', 'repetition_tolerance', 'preferred_sentence_length')
        }),
        ('Phrasen-Regeln', {
            'fields': ('acceptable_phrases', 'avoid_phrases'),
            'classes': ('collapse',)
        }),
        ('Synonyme & Stil', {
            'fields': ('synonym_preferences', 'style_instructions'),
            'classes': ('collapse',)
        }),
        ('Zeitstempel', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CorrectionSuggestion)
class CorrectionSuggestionAdmin(admin.ModelAdmin):
    list_display = ['original_short', 'strategy', 'confidence_badge', 'status', 'fehler', 'created_at']
    list_filter = ['strategy', 'status', 'created_at']
    search_fields = ['original_text', 'suggested_text']
    raw_id_fields = ['fehler']
    readonly_fields = ['created_at', 'reviewed_at']
    
    fieldsets = (
        (None, {
            'fields': ('fehler', 'strategy', 'status')
        }),
        ('Korrektur', {
            'fields': ('original_text', 'suggested_text', 'alternatives', 'confidence')
        }),
        ('Kontext', {
            'fields': ('context_before', 'context_after'),
            'classes': ('collapse',)
        }),
        ('Position', {
            'fields': ('chapter_id', 'position_start', 'position_end'),
            'classes': ('collapse',)
        }),
        ('User-Feedback', {
            'fields': ('user_note', 'final_text'),
            'classes': ('collapse',)
        }),
        ('Zeitstempel', {
            'fields': ('created_at', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def original_short(self, obj):
        return obj.original_text[:40] + '...' if len(obj.original_text) > 40 else obj.original_text
    original_short.short_description = 'Original'
    
    def confidence_badge(self, obj):
        if obj.confidence >= 0.9:
            color = '#28a745'
        elif obj.confidence >= 0.7:
            color = '#ffc107'
        else:
            color = '#dc3545'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{:.0%}</span>',
            color, obj.confidence
        )
    confidence_badge.short_description = 'Konfidenz'
