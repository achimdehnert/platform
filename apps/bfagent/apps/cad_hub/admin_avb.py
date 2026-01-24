# apps/cad_hub/admin_avb.py
"""
Admin-Konfiguration für AVB-Module (Ausschreibung, Vergabe, Bauausführung)
"""

from django.contrib import admin
from django.utils.html import format_html

from .models_avb import (
    Award,
    Bid,
    Bidder,
    BidPosition,
    ConstructionProject,
    CostEstimate,
    ProjectMilestone,
    Tender,
    TenderGroup,
    TenderPosition,
)


# =============================================================================
# Inlines
# =============================================================================

class ProjectMilestoneInline(admin.TabularInline):
    model = ProjectMilestone
    extra = 0
    fields = ["name", "phase", "due_date", "completed_at", "order"]
    ordering = ["order", "due_date"]


class CostEstimateInline(admin.TabularInline):
    model = CostEstimate
    extra = 0
    fields = ["cost_group", "description", "quantity", "unit", "unit_price", "total"]
    readonly_fields = ["total"]
    ordering = ["cost_group"]


class TenderPositionInline(admin.TabularInline):
    model = TenderPosition
    extra = 0
    fields = ["oz", "short_text", "quantity", "unit", "stlb_code", "order"]
    ordering = ["order", "oz"]


class BidPositionInline(admin.TabularInline):
    model = BidPosition
    extra = 0
    fields = ["tender_position", "unit_price", "total_price", "notes"]
    readonly_fields = ["total_price"]


class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    fields = ["bidder", "status", "total_price", "received_at"]
    readonly_fields = ["received_at"]
    show_change_link = True


# =============================================================================
# Projektplanung
# =============================================================================

@admin.register(ConstructionProject)
class ConstructionProjectAdmin(admin.ModelAdmin):
    list_display = [
        "project_number", "ifc_project", "client", "current_phase",
        "budget_display", "cost_estimate_display", "tenders_count"
    ]
    list_filter = ["current_phase", "created_at"]
    search_fields = ["project_number", "client", "ifc_project__name"]
    readonly_fields = ["created_at", "updated_at"]
    
    fieldsets = [
        ("Projekt", {
            "fields": ["ifc_project", "project_number", "client", "client_contact"]
        }),
        ("Adresse", {
            "fields": ["street", "zip_code", "city"],
            "classes": ["collapse"]
        }),
        ("Planung", {
            "fields": ["current_phase", "planning_start", "construction_start", "construction_end"]
        }),
        ("Kosten", {
            "fields": ["budget_total", "cost_estimate"]
        }),
        ("Meta", {
            "fields": ["created_by", "created_at", "updated_at"],
            "classes": ["collapse"]
        }),
    ]
    
    inlines = [ProjectMilestoneInline, CostEstimateInline]
    
    def budget_display(self, obj):
        return f"{obj.budget_total:,.2f} €"
    budget_display.short_description = "Budget"
    
    def cost_estimate_display(self, obj):
        return f"{obj.cost_estimate:,.2f} €"
    cost_estimate_display.short_description = "Kostenschätzung"
    
    def tenders_count(self, obj):
        return obj.tenders.count()
    tenders_count.short_description = "Ausschreibungen"


# =============================================================================
# Ausschreibung
# =============================================================================

@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = [
        "tender_number", "title", "project", "trade", "status_badge",
        "estimated_value_display", "positions_count", "bids_count", "submission_deadline"
    ]
    list_filter = ["status", "cost_group", "project", "created_at"]
    search_fields = ["tender_number", "title", "trade", "project__ifc_project__name"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    
    fieldsets = [
        ("Identifikation", {
            "fields": ["project", "tender_number", "title", "description"]
        }),
        ("Klassifikation", {
            "fields": ["cost_group", "trade"]
        }),
        ("Status & Termine", {
            "fields": ["status", "publication_date", "submission_deadline", "opening_date"]
        }),
        ("Werte", {
            "fields": ["estimated_value"]
        }),
        ("Dateien", {
            "fields": ["gaeb_file"],
            "classes": ["collapse"]
        }),
        ("Meta", {
            "fields": ["created_by", "created_at", "updated_at"],
            "classes": ["collapse"]
        }),
    ]
    
    inlines = [TenderPositionInline, BidInline]
    
    def status_badge(self, obj):
        colors = {
            "draft": "#6c757d",
            "published": "#007bff",
            "submission": "#17a2b8",
            "evaluation": "#ffc107",
            "awarded": "#28a745",
            "cancelled": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def estimated_value_display(self, obj):
        return f"{obj.estimated_value:,.2f} €"
    estimated_value_display.short_description = "Schätzwert"
    
    def positions_count(self, obj):
        return obj.positions.count()
    positions_count.short_description = "Positionen"
    
    def bids_count(self, obj):
        return obj.bids.count()
    bids_count.short_description = "Angebote"


@admin.register(TenderPosition)
class TenderPositionAdmin(admin.ModelAdmin):
    list_display = ["oz", "short_text", "tender", "quantity", "unit", "stlb_code"]
    list_filter = ["tender", "unit"]
    search_fields = ["oz", "short_text", "long_text", "stlb_code"]
    ordering = ["tender", "order", "oz"]


@admin.register(TenderGroup)
class TenderGroupAdmin(admin.ModelAdmin):
    list_display = ["oz", "title", "tender", "parent"]
    list_filter = ["tender"]
    search_fields = ["oz", "title"]


# =============================================================================
# Bieter & Angebote
# =============================================================================

@admin.register(Bidder)
class BidderAdmin(admin.ModelAdmin):
    list_display = [
        "company_name", "contact_person", "city", "email",
        "rating_display", "is_preferred", "is_active", "bids_count"
    ]
    list_filter = ["is_active", "is_preferred", "city"]
    search_fields = ["company_name", "contact_person", "email", "city"]
    readonly_fields = ["created_at", "updated_at"]
    
    fieldsets = [
        ("Firma", {
            "fields": ["company_name", "contact_person"]
        }),
        ("Adresse", {
            "fields": ["street", "zip_code", "city", "country"]
        }),
        ("Kontakt", {
            "fields": ["email", "phone", "website"]
        }),
        ("Qualifikation", {
            "fields": ["trades", "certifications"],
            "classes": ["collapse"]
        }),
        ("Bewertung", {
            "fields": ["rating", "is_preferred", "is_active", "notes"]
        }),
    ]
    
    def rating_display(self, obj):
        if obj.rating:
            stars = "★" * int(obj.rating) + "☆" * (5 - int(obj.rating))
            return f"{stars} ({obj.rating})"
        return "-"
    rating_display.short_description = "Bewertung"
    
    def bids_count(self, obj):
        return obj.bids.count()
    bids_count.short_description = "Angebote"


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = [
        "bidder", "tender", "status_badge", "total_price_display",
        "discount_display", "final_price_display", "rank_display", "received_at"
    ]
    list_filter = ["status", "tender", "tender__project"]
    search_fields = ["bidder__company_name", "tender__title"]
    readonly_fields = ["created_at", "updated_at", "final_price_display", "rank_display"]
    date_hierarchy = "received_at"
    
    fieldsets = [
        ("Grunddaten", {
            "fields": ["tender", "bidder", "status"]
        }),
        ("Termine", {
            "fields": ["invited_at", "received_at", "valid_until"]
        }),
        ("Preise", {
            "fields": ["total_price", "total_price_gross", "discount_percent", "discount_absolute"]
        }),
        ("Bewertung", {
            "fields": ["technical_score", "price_score", "total_score"]
        }),
        ("Dateien", {
            "fields": ["gaeb_file"],
            "classes": ["collapse"]
        }),
        ("Notizen", {
            "fields": ["notes"],
            "classes": ["collapse"]
        }),
    ]
    
    inlines = [BidPositionInline]
    
    def status_badge(self, obj):
        colors = {
            "invited": "#6c757d",
            "received": "#17a2b8",
            "evaluated": "#007bff",
            "negotiation": "#ffc107",
            "awarded": "#28a745",
            "rejected": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def total_price_display(self, obj):
        return f"{obj.total_price:,.2f} €"
    total_price_display.short_description = "Netto"
    
    def discount_display(self, obj):
        parts = []
        if obj.discount_percent > 0:
            parts.append(f"{obj.discount_percent}%")
        if obj.discount_absolute > 0:
            parts.append(f"{obj.discount_absolute:,.2f} €")
        return " + ".join(parts) if parts else "-"
    discount_display.short_description = "Nachlass"
    
    def final_price_display(self, obj):
        return f"{obj.final_price:,.2f} €"
    final_price_display.short_description = "Endpreis"
    
    def rank_display(self, obj):
        rank = obj.rank
        if rank == 1:
            return format_html('<span style="color:#28a745; font-weight:bold;">🥇 1.</span>')
        elif rank == 2:
            return format_html('<span style="color:#6c757d;">🥈 2.</span>')
        elif rank == 3:
            return format_html('<span style="color:#cd7f32;">🥉 3.</span>')
        return f"{rank}."
    rank_display.short_description = "Rang"


# =============================================================================
# Vergabe
# =============================================================================

@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = [
        "tender", "bidder_display", "award_date",
        "contract_value_display", "contract_number"
    ]
    list_filter = ["award_date", "tender__project"]
    search_fields = ["tender__title", "bid__bidder__company_name", "contract_number"]
    readonly_fields = ["created_at"]
    date_hierarchy = "award_date"
    
    fieldsets = [
        ("Vergabe", {
            "fields": ["tender", "bid", "award_date"]
        }),
        ("Vertrag", {
            "fields": ["contract_value", "contract_number", "contract_file"]
        }),
        ("GAEB", {
            "fields": ["gaeb_file"]
        }),
        ("Notizen", {
            "fields": ["notes"],
            "classes": ["collapse"]
        }),
    ]
    
    def bidder_display(self, obj):
        return obj.bid.bidder.company_name
    bidder_display.short_description = "Auftragnehmer"
    
    def contract_value_display(self, obj):
        return f"{obj.contract_value:,.2f} €"
    contract_value_display.short_description = "Auftragssumme"
