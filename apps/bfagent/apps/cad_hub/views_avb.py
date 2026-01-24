# apps/cad_hub/views_avb.py
"""
Views für AVB-Module (Ausschreibung, Vergabe, Bauausführung)
============================================================

Komplettes Planungs-, Ausschreibungs- und Angebotstool.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .models import (
    Award,
    Bid,
    Bidder,
    BidPosition,
    ConstructionProject,
    CostEstimate,
    IFCModel,
    ProjectMilestone,
    Tender,
    TenderPosition,
)


# =============================================================================
# Projekt-Planung
# =============================================================================

class ConstructionProjectListView(LoginRequiredMixin, ListView):
    """Liste aller Bauprojekte"""
    model = ConstructionProject
    template_name = "cad_hub/avb/project_list.html"
    context_object_name = "projects"
    paginate_by = 20


class ConstructionProjectDetailView(LoginRequiredMixin, DetailView):
    """Bauprojekt-Detail mit Übersicht"""
    model = ConstructionProject
    template_name = "cad_hub/avb/project_detail.html"
    context_object_name = "project"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object
        
        # Statistiken
        ctx["stats"] = {
            "tenders_count": project.tenders.count(),
            "tenders_draft": project.tenders.filter(status="draft").count(),
            "tenders_published": project.tenders.filter(status="published").count(),
            "tenders_awarded": project.tenders.filter(status="awarded").count(),
            "total_value": project.total_tender_value,
            "milestones_total": project.milestones.count(),
            "milestones_completed": project.milestones.filter(completed_at__isnull=False).count(),
        }
        
        # Aktuelle Meilensteine
        ctx["upcoming_milestones"] = project.milestones.filter(
            completed_at__isnull=True
        ).order_by("due_date")[:5]
        
        # Kostenschätzung nach KG
        ctx["cost_by_group"] = project.cost_estimates.values(
            "cost_group"
        ).annotate(
            total=models.Sum("total")
        ).order_by("cost_group")
        
        return ctx


class ConstructionProjectCreateView(LoginRequiredMixin, CreateView):
    """Neues Bauprojekt erstellen"""
    model = ConstructionProject
    template_name = "cad_hub/avb/project_form.html"
    fields = [
        "ifc_project", "project_number", "client", "client_contact",
        "street", "zip_code", "city",
        "current_phase", "planning_start", "construction_start", "construction_end",
        "budget_total",
    ]
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Bauprojekt erfolgreich erstellt.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse("cad_hub:avb_project_detail", kwargs={"pk": self.object.pk})


class ConstructionProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Bauprojekt bearbeiten"""
    model = ConstructionProject
    template_name = "cad_hub/avb/project_form.html"
    fields = [
        "project_number", "client", "client_contact",
        "street", "zip_code", "city",
        "current_phase", "planning_start", "construction_start", "construction_end",
        "budget_total", "cost_estimate",
    ]
    
    def get_success_url(self):
        return reverse("cad_hub:avb_project_detail", kwargs={"pk": self.object.pk})


# =============================================================================
# Ausschreibungen
# =============================================================================

class TenderListView(LoginRequiredMixin, ListView):
    """Liste aller Ausschreibungen"""
    model = Tender
    template_name = "cad_hub/avb/tender_list.html"
    context_object_name = "tenders"
    paginate_by = 20
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filter nach Projekt
        project_id = self.request.GET.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        
        # Filter nach Status
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        
        return qs.select_related("project", "project__ifc_project")


class TenderDetailView(LoginRequiredMixin, DetailView):
    """Ausschreibungs-Detail"""
    model = Tender
    template_name = "cad_hub/avb/tender_detail.html"
    context_object_name = "tender"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tender = self.object
        
        # Positionen
        ctx["positions"] = tender.positions.all()
        ctx["positions_count"] = tender.positions.count()
        
        # Angebote
        ctx["bids"] = tender.bids.select_related("bidder").order_by("total_price")
        ctx["bids_count"] = tender.bids.count()
        
        # Statistik
        if tender.bids.exists():
            from django.db.models import Avg, Max, Min
            ctx["bid_stats"] = tender.bids.aggregate(
                min_price=Min("total_price"),
                max_price=Max("total_price"),
                avg_price=Avg("total_price"),
            )
        
        return ctx


class TenderCreateView(LoginRequiredMixin, CreateView):
    """Neue Ausschreibung erstellen"""
    model = Tender
    template_name = "cad_hub/avb/tender_form.html"
    fields = [
        "project", "tender_number", "title", "description",
        "cost_group", "trade", "estimated_value",
        "publication_date", "submission_deadline", "opening_date",
    ]
    
    def get_initial(self):
        initial = super().get_initial()
        project_id = self.request.GET.get("project")
        if project_id:
            initial["project"] = project_id
        return initial
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Ausschreibung erfolgreich erstellt.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse("cad_hub:tender_detail", kwargs={"pk": self.object.pk})


class TenderFromIFCView(LoginRequiredMixin, View):
    """Ausschreibung aus IFC-Modell erstellen"""
    
    def post(self, request, model_id):
        ifc_model = get_object_or_404(IFCModel, pk=model_id)
        
        trade = request.POST.get("trade", "Allgemein")
        cost_group = request.POST.get("cost_group", "")
        title = request.POST.get("title", "")
        gewerke = request.POST.getlist("gewerke")
        
        from .services import get_avb_service
        service = get_avb_service()
        
        try:
            tender = service.create_tender_from_ifc(
                ifc_model=ifc_model,
                trade=trade,
                cost_group=cost_group,
                title=title,
                gewerke=gewerke or None,
            )
            messages.success(
                request,
                f"Ausschreibung '{tender.tender_number}' mit {tender.positions.count()} Positionen erstellt."
            )
            return redirect("cad_hub:tender_detail", pk=tender.pk)
        except Exception as e:
            messages.error(request, f"Fehler: {e}")
            return redirect("cad_hub:model_detail", pk=model_id)


class TenderPublishView(LoginRequiredMixin, View):
    """Ausschreibung veröffentlichen"""
    
    def post(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk)
        
        if tender.status != "draft":
            messages.error(request, "Nur Entwürfe können veröffentlicht werden.")
        else:
            from django.utils import timezone
            tender.status = "published"
            tender.publication_date = timezone.now().date()
            tender.save()
            messages.success(request, "Ausschreibung veröffentlicht.")
        
        return redirect("cad_hub:tender_detail", pk=pk)


# =============================================================================
# Bieter
# =============================================================================

class BidderListView(LoginRequiredMixin, ListView):
    """Bieter-Verzeichnis"""
    model = Bidder
    template_name = "cad_hub/avb/bidder_list.html"
    context_object_name = "bidders"
    paginate_by = 30
    
    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(company_name__icontains=search)
        
        return qs


class BidderDetailView(LoginRequiredMixin, DetailView):
    """Bieter-Detail"""
    model = Bidder
    template_name = "cad_hub/avb/bidder_detail.html"
    context_object_name = "bidder"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["recent_bids"] = self.object.bids.select_related(
            "tender", "tender__project"
        ).order_by("-created_at")[:10]
        return ctx


class BidderCreateView(LoginRequiredMixin, CreateView):
    """Neuen Bieter anlegen"""
    model = Bidder
    template_name = "cad_hub/avb/bidder_form.html"
    fields = [
        "company_name", "contact_person",
        "street", "zip_code", "city", "country",
        "email", "phone", "website",
        "trades", "certifications",
        "is_preferred", "notes",
    ]
    
    def get_success_url(self):
        return reverse("cad_hub:bidder_detail", kwargs={"pk": self.object.pk})


# =============================================================================
# Angebote
# =============================================================================

class BidListView(LoginRequiredMixin, ListView):
    """Liste aller Angebote einer Ausschreibung"""
    model = Bid
    template_name = "cad_hub/avb/bid_list.html"
    context_object_name = "bids"
    
    def get_queryset(self):
        tender_id = self.kwargs.get("tender_id")
        return Bid.objects.filter(tender_id=tender_id).select_related("bidder")
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tender"] = get_object_or_404(Tender, pk=self.kwargs["tender_id"])
        return ctx


class BidDetailView(LoginRequiredMixin, DetailView):
    """Angebots-Detail"""
    model = Bid
    template_name = "cad_hub/avb/bid_detail.html"
    context_object_name = "bid"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["positions"] = self.object.positions.select_related("tender_position")
        return ctx


class BidCreateView(LoginRequiredMixin, CreateView):
    """Bieter zu Ausschreibung einladen"""
    model = Bid
    template_name = "cad_hub/avb/bid_form.html"
    fields = ["bidder"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tender"] = get_object_or_404(Tender, pk=self.kwargs["tender_id"])
        return ctx
    
    def form_valid(self, form):
        from django.utils import timezone
        form.instance.tender_id = self.kwargs["tender_id"]
        form.instance.status = "invited"
        form.instance.invited_at = timezone.now()
        messages.success(self.request, "Bieter eingeladen.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse("cad_hub:tender_detail", kwargs={"pk": self.kwargs["tender_id"]})


class BidReceiveView(LoginRequiredMixin, UpdateView):
    """Angebot erfassen"""
    model = Bid
    template_name = "cad_hub/avb/bid_receive.html"
    fields = [
        "total_price", "total_price_gross",
        "discount_percent", "discount_absolute",
        "valid_until", "notes",
    ]
    
    def form_valid(self, form):
        from django.utils import timezone
        form.instance.status = "received"
        form.instance.received_at = timezone.now()
        messages.success(self.request, "Angebot erfasst.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse("cad_hub:bid_detail", kwargs={"pk": self.object.pk})


# =============================================================================
# Preisspiegel & Vergabe
# =============================================================================

class PriceComparisonView(LoginRequiredMixin, TemplateView):
    """Preisspiegel / Angebotsvergleich"""
    template_name = "cad_hub/avb/price_comparison.html"
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tender = get_object_or_404(Tender, pk=self.kwargs["pk"])
        
        from .services import get_avb_service
        service = get_avb_service()
        
        ctx["tender"] = tender
        ctx["comparisons"] = service.compare_bids(tender)
        ctx["rankings"] = service.calculate_price_ranking(tender)
        ctx["suggestion"] = service.suggest_award(tender)
        
        return ctx


class ExportPriceComparisonView(LoginRequiredMixin, View):
    """Preisspiegel als Excel exportieren"""
    
    def get(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk)
        
        from .services import get_avb_service
        service = get_avb_service()
        
        output = service.export_price_comparison_excel(tender)
        
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="Preisspiegel_{tender.tender_number}.xlsx"'
        return response


class ExportTenderGAEBView(LoginRequiredMixin, View):
    """Ausschreibung als GAEB exportieren"""
    
    def get(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk)
        phase = request.GET.get("phase", "X81")
        
        from .services import get_avb_service
        service = get_avb_service()
        
        output = service.export_tender_gaeb(tender, phase=phase)
        
        response = HttpResponse(output.read(), content_type="application/xml")
        response["Content-Disposition"] = f'attachment; filename="{tender.tender_number}.{phase.lower()}"'
        return response


class AwardCreateView(LoginRequiredMixin, CreateView):
    """Zuschlag erteilen"""
    model = Award
    template_name = "cad_hub/avb/award_form.html"
    fields = ["award_date", "contract_value", "contract_number", "notes"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tender"] = get_object_or_404(Tender, pk=self.kwargs["tender_id"])
        ctx["bid"] = get_object_or_404(Bid, pk=self.kwargs["bid_id"])
        return ctx
    
    def form_valid(self, form):
        tender = get_object_or_404(Tender, pk=self.kwargs["tender_id"])
        bid = get_object_or_404(Bid, pk=self.kwargs["bid_id"])
        
        form.instance.tender = tender
        form.instance.bid = bid
        form.instance.created_by = self.request.user
        
        # Status aktualisieren
        tender.status = "awarded"
        tender.save()
        
        bid.status = "awarded"
        bid.save()
        
        # Andere Angebote ablehnen
        tender.bids.exclude(pk=bid.pk).update(status="rejected")
        
        messages.success(
            self.request,
            f"Zuschlag an {bid.bidder.company_name} erteilt."
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse("cad_hub:tender_detail", kwargs={"pk": self.kwargs["tender_id"]})


# =============================================================================
# API Endpoints (JSON)
# =============================================================================

class TenderStatsAPIView(LoginRequiredMixin, View):
    """API: Ausschreibungs-Statistiken"""
    
    def get(self, request, pk):
        tender = get_object_or_404(Tender, pk=pk)
        
        from django.db.models import Avg, Max, Min
        stats = tender.bids.filter(status__in=["received", "evaluated"]).aggregate(
            count=models.Count("id"),
            min_price=Min("total_price"),
            max_price=Max("total_price"),
            avg_price=Avg("total_price"),
        )
        
        return JsonResponse({
            "tender_number": tender.tender_number,
            "title": tender.title,
            "status": tender.status,
            "estimated_value": float(tender.estimated_value),
            "positions_count": tender.positions.count(),
            "bids": stats,
        })


# Import models für Aggregation
from django.db import models
