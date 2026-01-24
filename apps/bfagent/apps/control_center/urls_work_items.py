# -*- coding: utf-8 -*-
"""
URL patterns for Unified Work Items

Consolidated URLs replacing fragmented test-studio and feature-planning URLs.
"""

from django.urls import path
from . import views_work_items

urlpatterns = [
    # Dashboard
    path(
        '',
        views_work_items.work_items_dashboard,
        name='work-items-dashboard',
    ),
    
    # List Views
    path(
        'list/',
        views_work_items.work_items_list,
        name='work-items-list',
    ),
    path(
        'bugs/',
        views_work_items.work_items_list,
        {'item_type': 'bug'},
        name='work-items-bugs',
    ),
    path(
        'features/',
        views_work_items.work_items_list,
        {'item_type': 'feature'},
        name='work-items-features',
    ),
    path(
        'tasks/',
        views_work_items.work_items_list,
        {'item_type': 'task'},
        name='work-items-tasks',
    ),
    
    # Kanban
    path(
        'kanban/',
        views_work_items.work_items_kanban,
        name='work-items-kanban',
    ),
    
    # CRUD
    path(
        'create/',
        views_work_items.work_item_create,
        name='work-item-create',
    ),
    path(
        '<uuid:pk>/',
        views_work_items.work_item_detail,
        name='work-item-detail',
    ),
    
    # API Endpoints (HTMX)
    path(
        '<uuid:pk>/status/',
        views_work_items.work_item_update_status,
        name='work-item-update-status',
    ),
    path(
        '<uuid:pk>/priority/',
        views_work_items.work_item_update_priority,
        name='work-item-update-priority',
    ),
    path(
        '<uuid:pk>/comment/',
        views_work_items.work_item_add_comment,
        name='work-item-add-comment',
    ),
    path(
        '<uuid:pk>/assign-llm/',
        views_work_items.work_item_assign_llm,
        name='work-item-assign-llm',
    ),
    path(
        '<uuid:pk>/cascade-context/',
        views_work_items.work_item_cascade_context,
        name='work-item-cascade-context',
    ),
]
