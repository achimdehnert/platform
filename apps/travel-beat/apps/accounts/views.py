from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def profile_view(request):
    """User profile page."""
    return render(request, 'accounts/profile.html')


@login_required
def settings_view(request):
    """User settings page."""
    return render(request, 'accounts/settings.html')
