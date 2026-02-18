# ============================================================================
# DOMAIN DEVELOPMENT LIFECYCLE - WEB VIEWS & TEMPLATES
# Step 5: Django Views + HTMX Templates for Web UI
# ============================================================================
#
# Part of: Domain Development Lifecycle System
# Compatible with: ADR-015 Platform Governance System
# Location: platform/governance/views/domain_views.py
#
# ============================================================================

"""
Django Views für das Domain Development Lifecycle Web UI.

Diese Views ermöglichen:
- Dashboard mit Statusübersicht
- Business Case Liste und Detail
- Use Case Liste und Detail
- ADR Liste und Detail
- Review/Approval Workflow

Verwendet HTMX für interaktive Updates ohne Full Page Reload.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

if TYPE_CHECKING:
    from governance.models import BusinessCase, UseCase, ADR


# ============================================================================
# SECTION 1: DASHBOARD VIEW
# ============================================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard mit Statusübersicht aller Entitäten.
    """
    template_name = "governance/dashboard.html"
    
    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        
        from governance.models import BusinessCase, UseCase, ADR
        from governance.services import BusinessCaseService
        
        # Statistiken
        context['bc_stats'] = BusinessCaseService.get_statistics()
        
        # Neueste Einträge
        context['recent_business_cases'] = BusinessCase.objects.select_related(
            'status', 'category', 'owner'
        ).order_by('-created_at')[:5]
        
        context['recent_use_cases'] = UseCase.objects.select_related(
            'status', 'priority', 'business_case'
        ).order_by('-created_at')[:5]
        
        context['pending_reviews'] = BusinessCase.objects.filter(
            status__code='submitted'
        ).count()
        
        # Meine Business Cases
        if self.request.user.is_authenticated:
            context['my_business_cases'] = BusinessCase.objects.filter(
                owner=self.request.user
            ).select_related('status', 'category')[:5]
        
        return context


# ============================================================================
# SECTION 2: BUSINESS CASE VIEWS
# ============================================================================

class BusinessCaseListView(LoginRequiredMixin, ListView):
    """
    Liste aller Business Cases mit Filtern.
    """
    model = None  # Wird in get_queryset gesetzt
    template_name = "governance/business_case/list.html"
    context_object_name = "business_cases"
    paginate_by = 20
    
    def get_queryset(self):
        from governance.models import BusinessCase
        
        qs = BusinessCase.objects.select_related(
            'status', 'category', 'owner'
        ).annotate(
            use_case_count=Count('use_cases'),
            adr_count=Count('adrs'),
        ).order_by('-created_at')
        
        # Filter
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status__code=status)
        
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category__code=category)
        
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(code__icontains=search) |
                Q(title__icontains=search) |
                Q(problem_statement__icontains=search)
            )
        
        return qs
    
    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        
        from governance.services import LookupService
        
        context['statuses'] = LookupService.get_choices('bc_status')
        context['categories'] = LookupService.get_choices('bc_category')
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'category': self.request.GET.get('category', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        return context


class BusinessCaseDetailView(LoginRequiredMixin, DetailView):
    """
    Detail-Ansicht eines Business Cases.
    """
    template_name = "governance/business_case/detail.html"
    context_object_name = "bc"
    slug_field = "code"
    slug_url_kwarg = "code"
    
    def get_queryset(self):
        from governance.models import BusinessCase
        return BusinessCase.objects.select_related(
            'status', 'category', 'owner'
        ).prefetch_related(
            'use_cases__status',
            'use_cases__priority',
            'adrs__status',
            'conversations__role',
        )
    
    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        
        bc = self.object
        
        # Use Cases sortiert
        context['use_cases'] = bc.use_cases.select_related(
            'status', 'priority', 'complexity'
        ).order_by('sort_order')
        
        # ADRs
        context['adrs'] = bc.adrs.select_related('status')
        
        # Conversations (für Inception History)
        context['conversations'] = bc.conversations.select_related(
            'role'
        ).order_by('turn_number')
        
        # Status Transitions
        context['allowed_transitions'] = bc.allowed_transitions
        
        # Reviews
        from governance.models import Review
        context['reviews'] = Review.objects.filter(
            entity_type='business_case',
            entity_id=bc.id,
        ).select_related('reviewer').order_by('-created_at')
        
        return context


class BusinessCaseCreateView(LoginRequiredMixin, CreateView):
    """
    Erstellt einen neuen Business Case (Simple Form, nicht Inception).
    """
    template_name = "governance/business_case/form.html"
    fields = ['title', 'problem_statement', 'target_audience', 'expected_benefits']
    
    def get_form(self, form_class=None):
        from django import forms
        from governance.models import BusinessCase
        from governance.services import LookupService
        
        class BusinessCaseForm(forms.ModelForm):
            category = forms.ChoiceField(
                choices=[
                    (c['code'], c['name'])
                    for c in LookupService.get_choices('bc_category')
                ],
                label="Kategorie",
            )
            
            class Meta:
                model = BusinessCase
                fields = ['title', 'problem_statement', 'target_audience', 'expected_benefits']
                widgets = {
                    'problem_statement': forms.Textarea(attrs={'rows': 4}),
                    'target_audience': forms.Textarea(attrs={'rows': 2}),
                    'expected_benefits': forms.Textarea(attrs={'rows': 3}),
                }
        
        return BusinessCaseForm(**self.get_form_kwargs())
    
    def form_valid(self, form):
        from governance.services import BusinessCaseService
        
        bc = BusinessCaseService.create(
            title=form.cleaned_data['title'],
            problem_statement=form.cleaned_data['problem_statement'],
            category_code=form.cleaned_data['category'],
            owner=self.request.user,
            target_audience=form.cleaned_data.get('target_audience', ''),
            expected_benefits=form.cleaned_data.get('expected_benefits', ''),
        )
        
        messages.success(self.request, f"Business Case {bc.code} erstellt.")
        return redirect('governance:business_case_detail', code=bc.code)


# ============================================================================
# SECTION 3: HTMX PARTIAL VIEWS
# ============================================================================

@login_required
def htmx_business_case_status_change(request: HttpRequest, code: str) -> HttpResponse:
    """
    HTMX: Ändert den Status eines Business Cases.
    
    POST /governance/business-cases/{code}/status/
    """
    from governance.models import BusinessCase
    
    bc = get_object_or_404(BusinessCase, code=code)
    new_status = request.POST.get('status')
    reason = request.POST.get('reason', '')
    
    try:
        bc.transition_to(new_status, user=request.user, reason=reason)
        messages.success(request, f"Status geändert zu: {bc.status.name}")
    except ValueError as e:
        messages.error(request, str(e))
    
    # Partial für HTMX zurückgeben
    return render(request, "governance/business_case/_status_badge.html", {
        'bc': bc,
    })


@login_required
def htmx_business_case_list_partial(request: HttpRequest) -> HttpResponse:
    """
    HTMX: Gibt gefilterte Business Case Liste zurück.
    
    GET /governance/business-cases/list-partial/
    """
    from governance.models import BusinessCase
    
    qs = BusinessCase.objects.select_related('status', 'category').annotate(
        use_case_count=Count('use_cases'),
    ).order_by('-created_at')
    
    # Filter aus Query-Params
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status__code=status)
    
    category = request.GET.get('category')
    if category:
        qs = qs.filter(category__code=category)
    
    search = request.GET.get('search')
    if search:
        qs = qs.filter(
            Q(code__icontains=search) |
            Q(title__icontains=search)
        )
    
    return render(request, "governance/business_case/_list_table.html", {
        'business_cases': qs[:50],
    })


@login_required
def htmx_use_case_flow_editor(request: HttpRequest, code: str) -> HttpResponse:
    """
    HTMX: Editor für Use Case Flows.
    
    GET/POST /governance/use-cases/{code}/flow-editor/
    """
    from governance.models import UseCase
    from governance.services import UseCaseService
    
    uc = get_object_or_404(UseCase, code=code)
    
    if request.method == 'POST':
        # Flow speichern
        main_flow = json.loads(request.POST.get('main_flow', '[]'))
        
        UseCaseService.update_flow(uc, main_flow=main_flow)
        messages.success(request, "Flow gespeichert.")
        
        return render(request, "governance/use_case/_flow_display.html", {
            'uc': uc,
        })
    
    # GET: Editor anzeigen
    return render(request, "governance/use_case/_flow_editor.html", {
        'uc': uc,
        'step_types': [
            {'code': 'user_action', 'name': 'Benutzeraktion', 'icon': 'user'},
            {'code': 'system_action', 'name': 'Systemaktion', 'icon': 'cog'},
            {'code': 'validation', 'name': 'Validierung', 'icon': 'shield-check'},
            {'code': 'decision', 'name': 'Entscheidung', 'icon': 'question-mark-circle'},
            {'code': 'external_call', 'name': 'Externer Aufruf', 'icon': 'globe'},
            {'code': 'data_operation', 'name': 'Datenoperation', 'icon': 'database'},
        ],
    })


@login_required
def htmx_review_form(request: HttpRequest, entity_type: str, entity_id: int) -> HttpResponse:
    """
    HTMX: Review-Formular.
    
    GET/POST /governance/review/{entity_type}/{entity_id}/
    """
    from governance.models import Review, BusinessCase, UseCase, ADR
    
    # Entity laden
    if entity_type == 'business_case':
        entity = get_object_or_404(BusinessCase, id=entity_id)
    elif entity_type == 'use_case':
        entity = get_object_or_404(UseCase, id=entity_id)
    elif entity_type == 'adr':
        entity = get_object_or_404(ADR, id=entity_id)
    else:
        return HttpResponse("Invalid entity type", status=400)
    
    if request.method == 'POST':
        decision = request.POST.get('decision')
        comments = request.POST.get('comments', '')
        
        Review.objects.create(
            entity_type=entity_type,
            entity_id=entity_id,
            reviewer=request.user,
            decision=decision,
            comments=comments,
        )
        
        # Bei Approval: Status ändern
        if decision == 'approved' and entity_type == 'business_case':
            from governance.services import BusinessCaseService
            BusinessCaseService.approve(entity, request.user, comments)
        
        messages.success(request, f"Review gespeichert: {decision}")
        
        return render(request, "governance/_review_success.html", {
            'entity': entity,
            'decision': decision,
        })
    
    return render(request, "governance/_review_form.html", {
        'entity': entity,
        'entity_type': entity_type,
    })


# ============================================================================
# SECTION 4: USE CASE VIEWS
# ============================================================================

class UseCaseListView(LoginRequiredMixin, ListView):
    """
    Liste aller Use Cases.
    """
    template_name = "governance/use_case/list.html"
    context_object_name = "use_cases"
    paginate_by = 30
    
    def get_queryset(self):
        from governance.models import UseCase
        
        qs = UseCase.objects.select_related(
            'status', 'priority', 'complexity', 'business_case'
        ).order_by('-created_at')
        
        # Filter
        bc_code = self.request.GET.get('business_case')
        if bc_code:
            qs = qs.filter(business_case__code=bc_code)
        
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status__code=status)
        
        priority = self.request.GET.get('priority')
        if priority:
            qs = qs.filter(priority__code=priority)
        
        return qs


class UseCaseDetailView(LoginRequiredMixin, DetailView):
    """
    Detail-Ansicht eines Use Cases.
    """
    template_name = "governance/use_case/detail.html"
    context_object_name = "uc"
    slug_field = "code"
    slug_url_kwarg = "code"
    
    def get_queryset(self):
        from governance.models import UseCase
        return UseCase.objects.select_related(
            'status', 'priority', 'complexity', 'business_case__status'
        )


# ============================================================================
# SECTION 5: ADR VIEWS
# ============================================================================

class ADRListView(LoginRequiredMixin, ListView):
    """
    Liste aller ADRs.
    """
    template_name = "governance/adr/list.html"
    context_object_name = "adrs"
    paginate_by = 20
    
    def get_queryset(self):
        from governance.models import ADR
        return ADR.objects.select_related(
            'status', 'business_case', 'supersedes'
        ).order_by('-created_at')


class ADRDetailView(LoginRequiredMixin, DetailView):
    """
    Detail-Ansicht eines ADRs.
    """
    template_name = "governance/adr/detail.html"
    context_object_name = "adr"
    slug_field = "code"
    slug_url_kwarg = "code"
    
    def get_queryset(self):
        from governance.models import ADR
        return ADR.objects.select_related(
            'status', 'business_case', 'supersedes'
        ).prefetch_related(
            'use_case_links__use_case'
        )


# ============================================================================
# SECTION 6: URL PATTERNS
# ============================================================================

# governance/urls.py

"""
from django.urls import path
from governance.views import domain_views as views

app_name = 'governance'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Business Cases
    path('business-cases/', views.BusinessCaseListView.as_view(), name='business_case_list'),
    path('business-cases/create/', views.BusinessCaseCreateView.as_view(), name='business_case_create'),
    path('business-cases/<str:code>/', views.BusinessCaseDetailView.as_view(), name='business_case_detail'),
    
    # HTMX Partials
    path('business-cases/<str:code>/status/', views.htmx_business_case_status_change, name='htmx_bc_status'),
    path('business-cases/list-partial/', views.htmx_business_case_list_partial, name='htmx_bc_list'),
    
    # Use Cases
    path('use-cases/', views.UseCaseListView.as_view(), name='use_case_list'),
    path('use-cases/<str:code>/', views.UseCaseDetailView.as_view(), name='use_case_detail'),
    path('use-cases/<str:code>/flow-editor/', views.htmx_use_case_flow_editor, name='htmx_uc_flow'),
    
    # ADRs
    path('adrs/', views.ADRListView.as_view(), name='adr_list'),
    path('adrs/<str:code>/', views.ADRDetailView.as_view(), name='adr_detail'),
    
    # Reviews
    path('review/<str:entity_type>/<int:entity_id>/', views.htmx_review_form, name='htmx_review'),
]
"""


# ============================================================================
# SECTION 7: TEMPLATES
# ============================================================================

# Die Templates werden als separate Dateien erstellt.
# Hier die Template-Struktur:

TEMPLATE_STRUCTURE = """
templates/governance/
├── base.html                    # Base Template mit Navigation
├── dashboard.html               # Dashboard
├── _review_form.html            # HTMX Review Form
├── _review_success.html         # HTMX Review Success
│
├── business_case/
│   ├── list.html               # BC Liste
│   ├── detail.html             # BC Detail
│   ├── form.html               # BC Create/Edit Form
│   ├── _list_table.html        # HTMX Partial: Table
│   └── _status_badge.html      # HTMX Partial: Status Badge
│
├── use_case/
│   ├── list.html               # UC Liste
│   ├── detail.html             # UC Detail
│   ├── _flow_display.html      # Flow Anzeige
│   └── _flow_editor.html       # HTMX Flow Editor
│
└── adr/
    ├── list.html               # ADR Liste
    └── detail.html             # ADR Detail
"""
