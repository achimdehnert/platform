"""
Weltenhub Stories API URLs
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    StoryViewSet,
    ChapterViewSet,
    PlotThreadViewSet,
    TimelineEventViewSet,
)

app_name = "stories"

router = DefaultRouter()
router.register("stories", StoryViewSet, basename="story")
router.register("chapters", ChapterViewSet, basename="chapter")
router.register("plot-threads", PlotThreadViewSet, basename="plot-thread")
router.register("timeline", TimelineEventViewSet, basename="timeline-event")

urlpatterns = [
    path("", include(router.urls)),
]
