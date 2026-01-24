"""
Visual Workflow Builder Views
Django views for the workflow builder UI
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class WorkflowBuilderView(LoginRequiredMixin, TemplateView):
    """
    Main view for the Visual Workflow Builder
    
    Renders the React-based workflow builder interface with
    Visual Workflow Builder view with Handler Management.
    """
    template_name = 'workflow_builder/builder_v2.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Visual Workflow Builder'
        return context
