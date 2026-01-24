"""
Travel Beat - URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication (django-allauth)
    path('accounts/', include('allauth.urls')),
    
    # Apps
    path('', include('apps.trips.urls', namespace='trips')),
    path('stories/', include('apps.stories.urls', namespace='stories')),
    path('locations/', include('apps.locations.urls', namespace='locations')),
    path('world/', include('apps.worlds.urls', namespace='worlds')),
    path('profile/', include('apps.accounts.urls', namespace='accounts')),
]

# Debug Toolbar
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
