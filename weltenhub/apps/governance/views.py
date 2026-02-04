"""
Governance App Views
====================
Web UI views for DDL Business Cases, Use Cases, and ADRs.
Uses Django Class-Based Views with HTMX integration.
"""

from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone

from .models import BusinessCase, UseCase, ADR, LookupChoice, LookupDomain


class DashboardView(TemplateView):
    """Main governance dashboard with statistics."""
    template_name = "governance/dashboard.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # BC statistics
        context["bc_total"] = BusinessCase.objects.count()
        context["bc_draft"] = BusinessCase.objects.filter(
            status__code="draft"
        ).count()
        context["bc_in_review"] = BusinessCase.objects.filter(
            status__code__in=["submitted", "in_review"]
        ).count()
        context["bc_approved"] = BusinessCase.objects.filter(
            status__code="approved"
        ).count()
        
        # UC statistics
        context["uc_total"] = UseCase.objects.count()
        
        # Recent items
        context["recent_bcs"] = BusinessCase.objects.select_related(
            "status", "category"
        ).order_by("-created_at")[:5]
        
        context["recent_ucs"] = UseCase.objects.select_related(
            "status", "business_case"
        ).order_by("-created_at")[:5]
        
        # Pending reviews
        context["pending_reviews"] = BusinessCase.objects.filter(
            status__code="submitted"
        ).select_related("category")[:5]
        
        return context


class BusinessCaseListView(ListView):
    """List all Business Cases with filtering."""
    model = BusinessCase
    template_name = "governance/bc_list.html"
    context_object_name = "business_cases"
    paginate_by = 20
    
    def get_queryset(self):
        qs = BusinessCase.objects.select_related(
            "status", "category", "priority"
        ).order_by("-created_at")
        
        # Filter by status
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status__code=status)
        
        # Filter by category
        category = self.request.GET.get("category")
        if category:
            qs = qs.filter(category__code=category)
        
        # Search
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(problem_statement__icontains=search) |
                Q(code__icontains=search)
            )
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        bc_status_domain = LookupDomain.objects.filter(code="bc_status").first()
        bc_category_domain = LookupDomain.objects.filter(code="bc_category").first()
        
        if bc_status_domain:
            context["status_choices"] = LookupChoice.objects.filter(
                domain=bc_status_domain, is_active=True
            ).order_by("sort_order")
        
        if bc_category_domain:
            context["category_choices"] = LookupChoice.objects.filter(
                domain=bc_category_domain, is_active=True
            ).order_by("sort_order")
        
        # Current filters
        context["current_status"] = self.request.GET.get("status", "")
        context["current_category"] = self.request.GET.get("category", "")
        context["current_search"] = self.request.GET.get("q", "")
        
        return context


class BusinessCaseDetailView(DetailView):
    """Detail view for a single Business Case."""
    model = BusinessCase
    template_name = "governance/bc_detail.html"
    context_object_name = "bc"
    slug_field = "code"
    slug_url_kwarg = "code"
    
    def get_queryset(self):
        return BusinessCase.objects.select_related(
            "status", "category", "priority"
        ).prefetch_related("use_cases", "use_cases__status")


class BusinessCaseCreateView(CreateView):
    """Simple form to create a Business Case (non-inception)."""
    model = BusinessCase
    template_name = "governance/bc_create.html"
    fields = ["title", "category", "problem_statement", "target_audience", "scope"]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bc_category_domain = LookupDomain.objects.filter(code="bc_category").first()
        if bc_category_domain:
            context["categories"] = LookupChoice.objects.filter(
                domain=bc_category_domain, is_active=True
            ).order_by("sort_order")
        return context


class UseCaseListView(ListView):
    """List all Use Cases."""
    model = UseCase
    template_name = "governance/uc_list.html"
    context_object_name = "use_cases"
    paginate_by = 20
    
    def get_queryset(self):
        qs = UseCase.objects.select_related(
            "status", "business_case", "priority"
        ).order_by("-created_at")
        
        # Filter by business case
        bc = self.request.GET.get("bc")
        if bc:
            qs = qs.filter(business_case__code=bc)
        
        return qs


class UseCaseDetailView(DetailView):
    """Detail view for a single Use Case."""
    model = UseCase
    template_name = "governance/uc_detail.html"
    context_object_name = "uc"
    slug_field = "code"
    slug_url_kwarg = "code"


# =============================================================================
# HTMX PARTIALS
# =============================================================================

def bc_list_partial(request):
    """HTMX partial for filtered BC list."""
    qs = BusinessCase.objects.select_related("status", "category").order_by("-created_at")
    
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status__code=status)
    
    category = request.GET.get("category")
    if category:
        qs = qs.filter(category__code=category)
    
    search = request.GET.get("q")
    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(code__icontains=search)
        )
    
    return render(request, "governance/partials/bc_list_rows.html", {
        "business_cases": qs[:20]
    })


def bc_stats_partial(request):
    """HTMX partial for dashboard statistics."""
    context = {
        "bc_total": BusinessCase.objects.count(),
        "bc_draft": BusinessCase.objects.filter(status__code="draft").count(),
        "bc_in_review": BusinessCase.objects.filter(
            status__code__in=["submitted", "in_review"]
        ).count(),
        "bc_approved": BusinessCase.objects.filter(status__code="approved").count(),
    }
    return render(request, "governance/partials/bc_stats.html", context)


def bc_status_partial(request, code):
    """HTMX partial for updating BC status badge."""
    bc = get_object_or_404(BusinessCase.objects.select_related("status"), code=code)
    return render(request, "governance/partials/bc_status_badge.html", {"bc": bc})
