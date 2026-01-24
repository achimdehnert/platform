"""
Custom decorators for app-level permissions
"""

from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import render


def group_required(*group_names):
    """
    Decorator to check if user belongs to at least one of the specified groups
    
    Usage:
        @login_required
        @group_required('BookWriting')
        def my_view(request):
            ...
    """
    def check_groups(user):
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=group_names).exists()
    
    return user_passes_test(check_groups)


def bookwriting_required(view_func):
    """
    Decorator to ensure user has access to Book Writing app
    
    Usage:
        @login_required
        @bookwriting_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if not request.user.groups.filter(name='BookWriting').exists():
            return render(request, 'errors/403_app_access.html', {
                'app_name': 'Book Writing',
                'required_group': 'BookWriting'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def medtrans_required(view_func):
    """
    Decorator to ensure user has access to Medical Translation app
    
    Usage:
        @login_required
        @medtrans_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if not request.user.groups.filter(name='MedicalTranslation').exists():
            return render(request, 'errors/403_app_access.html', {
                'app_name': 'Medical Translation',
                'required_group': 'MedicalTranslation'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def genagent_required(view_func):
    """
    Decorator to ensure user has access to GenAgent Framework
    
    Usage:
        @login_required
        @genagent_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if not request.user.groups.filter(name='GenAgent').exists():
            return render(request, 'errors/403_app_access.html', {
                'app_name': 'GenAgent Framework',
                'required_group': 'GenAgent'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
