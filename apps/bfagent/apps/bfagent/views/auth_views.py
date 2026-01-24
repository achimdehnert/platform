"""
Authentication Views - User Registration and Profile
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse


def register(request: HttpRequest) -> HttpResponse:
    """
    User registration view
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Automatically log in the user after registration
            login(request, user)
            return redirect('bfagent:project-list')  # Redirect to projects after registration
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def custom_logout(request: HttpRequest) -> HttpResponse:
    """
    Custom logout view that redirects to landing page
    """
    logout(request)
    return redirect('hub:landing')


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """
    User profile view
    """
    return render(request, 'registration/profile.html', {
        'user': request.user
    })
