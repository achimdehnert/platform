#!/usr/bin/env python
"""Create Workflow Dashboard URL Routing"""
import os
from pathlib import Path

# Create URL configuration
urls_file = Path('apps/bfagent/urls_workflow.py')

urls_content = '''"""
Workflow Dashboard URLs
URL routing for Multi-Hub Framework workflow views
"""

from django.urls import path
from apps.bfagent.views import workflow_dashboard as views

app_name = 'workflow'

urlpatterns = [
    # Main dashboard
    path(
        '',
        views.workflow_dashboard,
        name='dashboard'
    ),
    
    # Workflow builder
    path(
        'builder/<str:domain_art>/<str:domain_type>/',
        views.workflow_builder,
        name='builder'
    ),
    
    # Workflow visualizer
    path(
        'visualizer/<str:domain_art>/<str:domain_type>/',
        views.workflow_visualizer,
        name='visualizer'
    ),
    
    # Phase detail
    path(
        'phase/<int:phase_id>/',
        views.workflow_phase_detail,
        name='phase_detail'
    ),
    
    # API endpoints
    path(
        'api/execute/',
        views.workflow_execute,
        name='execute'
    ),
    path(
        'api/info/',
        views.workflow_api_info,
        name='api_info'
    ),
]
'''

# Write file
print(f'📝 Creating {urls_file}...')
with open(urls_file, 'w', encoding='utf-8') as f:
    f.write(urls_content)

print(f'✅ Created: {urls_file}')
print(f'📊 Size: {os.path.getsize(urls_file)} bytes')

# Now update main urls.py to include workflow URLs
print('\n📝 Update instructions for main urls.py:')
print('   Add to apps/bfagent/urls.py:')
print('   ')
print('   from django.urls import path, include')
print('   ')
print('   urlpatterns = [')
print('       ...')
print("       path('workflow/', include('apps.bfagent.urls_workflow')),")
print('       ...')
print('   ]')

print('\n✅ URL routing created!')
print('\n📋 Available URLs:')
print('   • /workflow/ - Main dashboard')
print('   • /workflow/builder/<domain>/<type>/ - Workflow builder')
print('   • /workflow/visualizer/<domain>/<type>/ - Workflow visualizer')
print('   • /workflow/phase/<id>/ - Phase details')
print('   • /workflow/api/execute/ - Execute workflow (POST)')
print('   • /workflow/api/info/ - Workflow information (GET)')