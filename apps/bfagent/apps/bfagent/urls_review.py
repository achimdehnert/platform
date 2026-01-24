"""
URL Configuration for Review System
"""
from django.urls import path

from .views.review_views import (
    ReviewRoundListView,
    ReviewRoundDetailView,
    ReviewRoundCreateView,
    ReviewRoundUpdateView,
    ReviewRoundDeleteView,
    review_round_start,
    review_round_complete,
    review_round_stats,
    participant_add,
    participant_remove,
)

# Note: No app_name here because we're already under bfagent namespace
# URLs will be: bfagent:review-round-list, etc.

urlpatterns = [
    # Review Round CRUD
    path('rounds/', ReviewRoundListView.as_view(), name='review-round-list'),
    path('rounds/create/', ReviewRoundCreateView.as_view(), name='review-round-create'),
    path('rounds/<int:pk>/', ReviewRoundDetailView.as_view(), name='review-round-detail'),
    path('rounds/<int:pk>/edit/', ReviewRoundUpdateView.as_view(), name='review-round-update'),
    path('rounds/<int:pk>/delete/', ReviewRoundDeleteView.as_view(), name='review-round-delete'),

    # Round Actions
    path('rounds/<int:pk>/start/', review_round_start, name='review-round-start'),
    path('rounds/<int:pk>/complete/', review_round_complete, name='review-round-complete'),
    path('rounds/<int:pk>/stats/', review_round_stats, name='review-round-stats'),

    # Participant Management
    path('rounds/<int:pk>/participants/add/', participant_add, name='review-participant-add'),
    path('rounds/<int:pk>/participants/<int:participant_id>/remove/',
         participant_remove, name='review-participant-remove'),
]
