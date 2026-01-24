"""
MCP Dashboard Views - Option B: Full BF Agent Pattern
======================================================

Class-Based Views mit:
- HTMX-native Interaktionen
- Celery für Async-Tasks
- SSE für Real-time Updates
- Proper Error Handling
- BF Agent Mixins

Author: BF Agent Team
Created: 2025-12
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any, Optional

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q, Prefetch
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    TemplateView,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MIXINS - Reusable Patterns
# =============================================================================

class HTMXResponseMixin:
    """
    Mixin für HTMX-native Responses.
    
    Automatisch:
    - Erkennt HTMX Requests
    - Rendert Partials statt Full Pages
    - Setzt OOB Swaps für Toasts
    - Handles Retargeting bei Errors
    """
    
    partial_template_name: Optional[str] = None
    toast_template = 'control_center/partials/toast.html'
    
    def is_htmx_request(self) -> bool:
        """Check if this is an HTMX request."""
        return self.request.headers.get('HX-Request', 'false') == 'true'
    
    def get_htmx_trigger(self) -> Optional[str]:
        """Get the element that triggered the request."""
        return self.request.headers.get('HX-Trigger')
    
    def get_htmx_target(self) -> Optional[str]:
        """Get the target element for the response."""
        return self.request.headers.get('HX-Target')
    
    def render_partial(self, template_name: str, context: dict) -> HttpResponse:
        """Render a partial template for HTMX."""
        html = render_to_string(template_name, context, request=self.request)
        return HttpResponse(html)
    
    def render_with_toast(
        self,
        template_name: str,
        context: dict,
        message: str,
        level: str = 'success'
    ) -> HttpResponse:
        """
        Render template with OOB toast notification.
        
        Uses HTMX OOB swap to inject toast into #toast-container
        """
        # Main content
        main_html = render_to_string(template_name, context, request=self.request)
        
        # Toast OOB
        toast_context = {
            'message': message,
            'level': level,
            'icon': self._get_toast_icon(level),
        }
        toast_html = render_to_string(self.toast_template, toast_context)
        
        # Combine with OOB swap
        combined_html = f'{main_html}\n{toast_html}'
        
        response = HttpResponse(combined_html)
        response['HX-Trigger'] = json.dumps({'showToast': {'message': message, 'level': level}})
        return response
    
    def htmx_redirect(self, url: str) -> HttpResponse:
        """Redirect via HTMX (client-side navigation)."""
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
    
    def htmx_refresh(self) -> HttpResponse:
        """Trigger a full page refresh."""
        response = HttpResponse(status=204)
        response['HX-Refresh'] = 'true'
        return response
    
    def htmx_error_response(self, message: str, target: str = '#modal-container') -> HttpResponse:
        """Return an error response for HTMX."""
        html = f'''
        <div class="alert alert-danger" role="alert">
            <i class="bi bi-exclamation-triangle"></i> {message}
        </div>
        '''
        response = HttpResponse(html)
        response['HX-Retarget'] = target
        response['HX-Reswap'] = 'innerHTML'
        return response
    
    def _get_toast_icon(self, level: str) -> str:
        """Get icon for toast level."""
        icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
        }
        return icons.get(level, 'ℹ️')


class MCPDashboardMixin(LoginRequiredMixin, HTMXResponseMixin):
    """
    Base Mixin für alle MCP Dashboard Views.
    
    Provides:
    - Common queryset optimizations
    - Stats calculation
    - Navigation context
    """
    
    login_url = 'accounts:login'
    
    def get_mcp_stats(self) -> dict:
        """Calculate common MCP statistics."""
        from bfagent_mcp.models_mcp import (
            MCPDomainConfig,
            MCPProtectedPath,
            MCPRefactorSession,
        )
        
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        
        return {
            'total_domains': MCPDomainConfig.objects.filter(is_active=True).count(),
            'ready_domains': MCPDomainConfig.objects.filter(
                is_active=True,
                is_refactor_ready=True
            ).count(),
            'protected_paths': MCPProtectedPath.objects.filter(is_active=True).count(),
            'total_sessions': MCPRefactorSession.objects.count(),
            'active_sessions': MCPRefactorSession.objects.filter(
                status='in_progress'
            ).count(),
            'sessions_24h': MCPRefactorSession.objects.filter(
                started_at__gte=last_24h
            ).count(),
            'last_session': MCPRefactorSession.objects.order_by('-started_at').first(),
        }
    
    def get_navigation_context(self) -> dict:
        """Get navigation context for sidebar."""
        return {
            'nav_items': [
                {'name': 'Dashboard', 'url': 'control_center:mcp-dashboard', 'icon': '🎯'},
                {'name': 'Domains', 'url': 'control_center:mcp-domains', 'icon': '📊'},
                {'name': 'Protected Paths', 'url': 'control_center:mcp-protected-paths', 'icon': '🔒'},
                {'name': 'Sessions', 'url': 'control_center:mcp-sessions', 'icon': '📝'},
                {'name': 'Conventions', 'url': 'control_center:mcp-conventions', 'icon': '📋'},
            ],
            'current_view': self.__class__.__name__,
        }


# =============================================================================
# MAIN DASHBOARD VIEW
# =============================================================================

class MCPDashboardView(MCPDashboardMixin, TemplateView):
    """
    MCP Dashboard - Hauptübersicht
    
    Features:
    - Stats Cards mit Live-Updates
    - Refactor Queue sortiert nach Risk
    - Recent Sessions Timeline
    - Quick Actions
    """
    
    template_name = 'control_center/mcp/dashboard.html'
    partial_template_name = 'control_center/mcp/partials/dashboard_content.html'
    
    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        
        from bfagent_mcp.models_mcp import MCPDomainConfig, MCPRefactorSession
        
        # Stats
        context['stats'] = self.get_mcp_stats()
        
        # Refactor Queue - optimized query
        context['refactor_queue'] = MCPDomainConfig.objects.filter(
            is_active=True,
            is_refactor_ready=True
        ).select_related(
            'domain',
            'risk_level'
        ).prefetch_related(
            Prefetch(
                'components',
                queryset=MCPDomainConfig.components.through.objects.select_related(
                    'component_type'
                ).filter(is_active=True)
            )
        ).annotate(
            component_count=Count('components', filter=Q(components__is_active=True))
        ).order_by(
            '-risk_level__severity_score',
            'refactor_order',
            'domain__name'
        )[:10]
        
        # Recent Sessions
        context['recent_sessions'] = MCPRefactorSession.objects.select_related(
            'domain_config__domain',
            'triggered_by_user'
        ).order_by('-started_at')[:10]
        
        # Navigation
        context.update(self.get_navigation_context())
        
        return context
    
    def get(self, request, *args, **kwargs):
        """Handle GET - HTMX or Full Page."""
        context = self.get_context_data(**kwargs)
        
        if self.is_htmx_request():
            # Partial update
            target = self.get_htmx_target()
            
            if target == '#stats-container':
                return self.render_partial(
                    'control_center/mcp/partials/stats_cards.html',
                    {'stats': context['stats']}
                )
            elif target == '#queue-container':
                return self.render_partial(
                    'control_center/mcp/partials/refactor_queue.html',
                    {'refactor_queue': context['refactor_queue']}
                )
            elif target == '#sessions-container':
                return self.render_partial(
                    'control_center/mcp/partials/recent_sessions.html',
                    {'recent_sessions': context['recent_sessions']}
                )
            else:
                # Full dashboard partial
                return self.render_partial(self.partial_template_name, context)
        
        return self.render_to_response(context)


# =============================================================================
# DOMAIN VIEWS
# =============================================================================

class MCPDomainListView(MCPDashboardMixin, ListView):
    """
    Domain List - Alle konfigurierten Domains
    """
    
    template_name = 'control_center/mcp/domain_list.html'
    partial_template_name = 'control_center/mcp/partials/domain_list_table.html'
    context_object_name = 'domains'
    paginate_by = 20
    
    def get_queryset(self):
        from bfagent_mcp.models_mcp import MCPDomainConfig
        
        queryset = MCPDomainConfig.objects.filter(
            is_active=True
        ).select_related(
            'domain',
            'risk_level'
        ).prefetch_related(
            'components__component_type',
            'depends_on'
        ).annotate(
            component_count=Count('components', filter=Q(components__is_active=True)),
            session_count=Count('refactor_sessions')
        ).order_by('refactor_order', 'domain__name')
        
        # Filter by risk level
        risk_filter = self.request.GET.get('risk')
        if risk_filter:
            queryset = queryset.filter(risk_level__name=risk_filter)
        
        # Search
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(domain__name__icontains=search) |
                Q(domain__display_name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = self.get_mcp_stats()
        context.update(self.get_navigation_context())
        
        # Filter options
        from bfagent_mcp.models_mcp import MCPRiskLevel
        context['risk_levels'] = MCPRiskLevel.objects.filter(is_active=True)
        context['current_risk'] = self.request.GET.get('risk', '')
        context['search_query'] = self.request.GET.get('q', '')
        
        return context
    
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        
        if self.is_htmx_request():
            return self.render_partial(self.partial_template_name, context)
        
        return self.render_to_response(context)


class MCPDomainDetailView(MCPDashboardMixin, DetailView):
    """
    Domain Detail - Komponenten, Dependencies, Sessions
    """
    
    template_name = 'control_center/mcp/domain_detail.html'
    context_object_name = 'config'
    
    def get_object(self):
        from bfagent_mcp.models_mcp import MCPDomainConfig
        
        domain_id = self.kwargs.get('domain_id')
        
        return get_object_or_404(
            MCPDomainConfig.objects.select_related(
                'domain',
                'risk_level'
            ).prefetch_related(
                'components__component_type',
                'depends_on__domain',
                'refactor_sessions'
            ),
            domain_id=domain_id
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.object
        
        from bfagent_mcp.models_mcp import MCPProtectedPath
        
        # Protected paths for this domain
        if config.base_path:
            context['protected_paths'] = MCPProtectedPath.objects.filter(
                is_active=True,
                path_pattern__startswith=config.base_path
            ).select_related('protection_level', 'category')[:20]
        else:
            context['protected_paths'] = []
        
        # Recent sessions
        context['recent_sessions'] = config.refactor_sessions.order_by(
            '-started_at'
        )[:5]
        
        # Components grouped by type
        components = config.components.filter(is_active=True).select_related('component_type')
        context['components_by_type'] = {}
        for comp in components:
            type_name = comp.component_type.name
            if type_name not in context['components_by_type']:
                context['components_by_type'][type_name] = []
            context['components_by_type'][type_name].append(comp)
        
        context.update(self.get_navigation_context())
        return context


# =============================================================================
# PROTECTED PATHS VIEWS
# =============================================================================

class MCPProtectedPathsView(MCPDashboardMixin, ListView):
    """
    Protected Paths - Übersicht und Management
    """
    
    template_name = 'control_center/mcp/protected_paths.html'
    partial_template_name = 'control_center/mcp/partials/protected_paths_list.html'
    context_object_name = 'paths'
    paginate_by = 50
    
    def get_queryset(self):
        from bfagent_mcp.models_mcp import MCPProtectedPath
        
        queryset = MCPProtectedPath.objects.filter(
            is_active=True
        ).select_related(
            'protection_level',
            'category'
        ).order_by('category__order', 'path_pattern')
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__name=category)
        
        # Filter by protection level
        level = self.request.GET.get('level')
        if level:
            queryset = queryset.filter(protection_level__name=level)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from bfagent_mcp.models_mcp import MCPProtectionLevel, MCPPathCategory
        
        # Group paths by category
        paths = list(self.object_list)
        categories = {}
        for path in paths:
            cat_name = path.category.name if path.category else 'Uncategorized'
            if cat_name not in categories:
                categories[cat_name] = {
                    'category': path.category,
                    'paths': [],
                    'count': 0
                }
            categories[cat_name]['paths'].append(path)
            categories[cat_name]['count'] += 1
        
        context['categories'] = categories
        context['total_paths'] = len(paths)
        
        # Filter options
        context['protection_levels'] = MCPProtectionLevel.objects.filter(is_active=True)
        context['path_categories'] = MCPPathCategory.objects.filter(is_active=True)
        
        context.update(self.get_navigation_context())
        return context


# =============================================================================
# SESSION VIEWS
# =============================================================================

class MCPSessionListView(MCPDashboardMixin, ListView):
    """
    Sessions - History und Status
    """
    
    template_name = 'control_center/mcp/sessions.html'
    partial_template_name = 'control_center/mcp/partials/sessions_table.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        from bfagent_mcp.models_mcp import MCPRefactorSession
        
        queryset = MCPRefactorSession.objects.select_related(
            'domain_config__domain',
            'domain_config__risk_level',
            'triggered_by_user'
        ).order_by('-started_at')
        
        # Status filter
        status = self.request.GET.get('status')
        if status and status != 'all':
            queryset = queryset.filter(status=status)
        
        # Domain filter
        domain = self.request.GET.get('domain')
        if domain and domain != 'all':
            queryset = queryset.filter(domain_config__domain__domain_id=domain)
        
        # Date range
        days = self.request.GET.get('days')
        if days:
            try:
                days = int(days)
                since = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(started_at__gte=since)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from bfagent_mcp.models_mcp import MCPRefactorSession, MCPDomainConfig
        
        # Stats
        context['session_stats'] = {
            'total': MCPRefactorSession.objects.count(),
            'completed': MCPRefactorSession.objects.filter(status='completed').count(),
            'in_progress': MCPRefactorSession.objects.filter(status='in_progress').count(),
            'failed': MCPRefactorSession.objects.filter(status='failed').count(),
        }
        
        # Filter options
        context['status_choices'] = MCPRefactorSession.STATUS_CHOICES
        context['domains'] = MCPDomainConfig.objects.filter(
            is_active=True
        ).select_related('domain')
        
        # Current filters
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_domain'] = self.request.GET.get('domain', 'all')
        context['current_days'] = self.request.GET.get('days', '')
        
        context.update(self.get_navigation_context())
        return context
    
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        
        if self.is_htmx_request():
            return self.render_partial(self.partial_template_name, context)
        
        return self.render_to_response(context)


class MCPSessionDetailView(MCPDashboardMixin, DetailView):
    """
    Session Detail - File Changes, Stats, Timeline
    """
    
    template_name = 'control_center/mcp/session_detail.html'
    context_object_name = 'session'
    
    def get_object(self):
        from bfagent_mcp.models_mcp import MCPRefactorSession
        
        session_id = self.kwargs.get('session_id')
        
        return get_object_or_404(
            MCPRefactorSession.objects.select_related(
                'domain_config__domain',
                'domain_config__risk_level',
                'triggered_by_user'
            ).prefetch_related(
                'file_changes'
            ),
            id=session_id
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        
        # File changes grouped by type
        file_changes = session.file_changes.all().order_by('file_path')
        context['file_changes'] = file_changes
        
        # Stats
        context['session_stats'] = {
            'files_changed': session.files_changed,
            'lines_added': session.lines_added,
            'lines_removed': session.lines_removed,
            'duration': (
                session.ended_at - session.started_at
            ) if session.ended_at else None,
        }
        
        # Timeline events (if available)
        if hasattr(session, 'events'):
            context['timeline_events'] = session.events.order_by('timestamp')
        
        context.update(self.get_navigation_context())
        return context


# =============================================================================
# CONVENTIONS VIEW
# =============================================================================

class MCPConventionsView(MCPDashboardMixin, ListView):
    """
    Naming Conventions - Übersicht
    """
    
    template_name = 'control_center/mcp/conventions.html'
    context_object_name = 'conventions'
    
    def get_queryset(self):
        from bfagent_mcp.models_naming import TableNamingConvention
        
        return TableNamingConvention.objects.filter(
            is_active=True
        ).order_by('app_label')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        conventions = list(self.object_list)
        
        # Group by enforcement
        context['strict_conventions'] = [
            c for c in conventions if c.enforce_convention
        ]
        context['flexible_conventions'] = [
            c for c in conventions if not c.enforce_convention
        ]
        context['total'] = len(conventions)
        
        context.update(self.get_navigation_context())
        return context


# =============================================================================
# ACTION VIEWS (HTMX Actions)
# =============================================================================

class MCPSyncDataView(MCPDashboardMixin, View):
    """
    Sync Data Action - Triggered via HTMX
    
    Triggers a Celery task to sync MCP data.
    """
    
    def post(self, request, *args, **kwargs):
        from apps.control_center.tasks import sync_mcp_data_task
        
        try:
            # Trigger Celery task
            task = sync_mcp_data_task.delay(
                triggered_by=request.user.id
            )
            
            logger.info(f"MCP sync task started: {task.id}")
            
            if self.is_htmx_request():
                return self.render_with_toast(
                    'control_center/mcp/partials/sync_status.html',
                    {'task_id': task.id, 'status': 'started'},
                    message='Data sync started!',
                    level='success'
                )
            
            return JsonResponse({
                'status': 'success',
                'task_id': task.id,
                'message': 'Sync started'
            })
            
        except Exception as e:
            logger.error(f"MCP sync failed: {e}")
            
            if self.is_htmx_request():
                return self.htmx_error_response(f'Sync failed: {str(e)}')
            
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class MCPStartSessionView(MCPDashboardMixin, View):
    """
    Start Refactor Session - Triggered via HTMX
    
    Creates a new refactor session and triggers Celery task.
    """
    
    def post(self, request, *args, **kwargs):
        from bfagent_mcp.models_mcp import MCPDomainConfig, MCPRefactorSession
        from apps.control_center.tasks import start_refactor_session_task
        
        # Get domain from request
        domain_id = request.POST.get('domain_id')
        components = request.POST.getlist('components', ['handler', 'service', 'model'])
        
        if not domain_id:
            if self.is_htmx_request():
                return self.htmx_error_response('Domain ID required')
            return JsonResponse({'error': 'Domain ID required'}, status=400)
        
        try:
            # Get domain config
            config = get_object_or_404(MCPDomainConfig, domain__domain_id=domain_id)
            
            if not config.is_refactor_ready:
                if self.is_htmx_request():
                    return self.htmx_error_response(
                        f'Domain {domain_id} is protected and cannot be refactored'
                    )
                return JsonResponse({
                    'error': 'Domain is protected'
                }, status=403)
            
            # Create session record
            session = MCPRefactorSession.objects.create(
                domain_config=config,
                status='pending',
                triggered_by='web_dashboard',
                triggered_by_user=request.user,
                components_selected=components,
            )
            
            # Trigger Celery task
            task = start_refactor_session_task.delay(
                session_id=session.id,
                user_id=request.user.id
            )
            
            # Update session with task ID
            session.celery_task_id = task.id
            session.save(update_fields=['celery_task_id'])
            
            logger.info(f"Refactor session {session.id} started for {domain_id}")
            
            if self.is_htmx_request():
                return self.render_with_toast(
                    'control_center/mcp/partials/session_started.html',
                    {'session': session, 'task_id': task.id},
                    message=f'Session #{session.id} started for {domain_id}!',
                    level='success'
                )
            
            return JsonResponse({
                'status': 'success',
                'session_id': session.id,
                'task_id': task.id
            })
            
        except MCPDomainConfig.DoesNotExist:
            if self.is_htmx_request():
                return self.htmx_error_response(f'Domain {domain_id} not found')
            return JsonResponse({'error': 'Domain not found'}, status=404)
            
        except Exception as e:
            logger.error(f"Start session failed: {e}")
            
            if self.is_htmx_request():
                return self.htmx_error_response(f'Failed: {str(e)}')
            
            return JsonResponse({'error': str(e)}, status=500)


class MCPCancelSessionView(MCPDashboardMixin, View):
    """
    Cancel Refactor Session - Triggered via HTMX
    """
    
    def post(self, request, *args, **kwargs):
        from bfagent_mcp.models_mcp import MCPRefactorSession
        from celery.result import AsyncResult
        
        session_id = kwargs.get('session_id')
        
        try:
            session = get_object_or_404(MCPRefactorSession, id=session_id)
            
            if session.status not in ['pending', 'in_progress']:
                if self.is_htmx_request():
                    return self.htmx_error_response(
                        f'Session cannot be cancelled (status: {session.status})'
                    )
                return JsonResponse({
                    'error': 'Session cannot be cancelled'
                }, status=400)
            
            # Cancel Celery task if running
            if session.celery_task_id:
                result = AsyncResult(session.celery_task_id)
                result.revoke(terminate=True)
            
            # Update session
            session.status = 'cancelled'
            session.ended_at = timezone.now()
            session.save(update_fields=['status', 'ended_at'])
            
            logger.info(f"Session {session_id} cancelled by {request.user}")
            
            if self.is_htmx_request():
                return self.render_with_toast(
                    'control_center/mcp/partials/session_row.html',
                    {'session': session},
                    message=f'Session #{session_id} cancelled',
                    level='warning'
                )
            
            return JsonResponse({'status': 'cancelled', 'session_id': session_id})
            
        except Exception as e:
            logger.error(f"Cancel session failed: {e}")
            
            if self.is_htmx_request():
                return self.htmx_error_response(f'Cancel failed: {str(e)}')
            
            return JsonResponse({'error': str(e)}, status=500)


# =============================================================================
# SSE (Server-Sent Events) VIEW for Real-time Updates
# =============================================================================

class MCPSessionSSEView(MCPDashboardMixin, View):
    """
    Server-Sent Events for real-time session updates.
    
    Client connects via:
    <div hx-ext="sse" sse-connect="/control-center/mcp/sse/sessions/">
    
    Updates are pushed when session status changes.
    """
    
    def get(self, request, *args, **kwargs):
        def event_stream():
            import time
            from bfagent_mcp.models_mcp import MCPRefactorSession
            
            last_check = timezone.now()
            
            while True:
                # Check for active sessions with updates
                active_sessions = MCPRefactorSession.objects.filter(
                    status='in_progress',
                    updated_at__gt=last_check
                ).select_related('domain_config__domain')
                
                for session in active_sessions:
                    # Render partial
                    html = render_to_string(
                        'control_center/mcp/partials/session_row.html',
                        {'session': session},
                        request=request
                    )
                    
                    # SSE format
                    yield f"event: session-update\n"
                    yield f"data: {json.dumps({'session_id': session.id, 'html': html})}\n\n"
                
                last_check = timezone.now()
                time.sleep(2)  # Poll every 2 seconds
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class MCPStatsSSEView(MCPDashboardMixin, View):
    """
    Server-Sent Events for real-time stats updates.
    """
    
    def get(self, request, *args, **kwargs):
        def event_stream():
            import time
            
            while True:
                stats = self.get_mcp_stats()
                
                # Render stats partial
                html = render_to_string(
                    'control_center/mcp/partials/stats_cards.html',
                    {'stats': stats},
                    request=request
                )
                
                yield f"event: stats-update\n"
                yield f"data: {json.dumps({'html': html})}\n\n"
                
                time.sleep(10)  # Update every 10 seconds
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
