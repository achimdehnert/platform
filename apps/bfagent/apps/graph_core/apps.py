"""
Graph Core App Configuration
"""

from django.apps import AppConfig


class GraphCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.graph_core'
    label = 'graph_core'
    verbose_name = 'Graph Core - Workflow Orchestration'
    
    def ready(self):
        """Initialize app when Django starts"""
        pass
