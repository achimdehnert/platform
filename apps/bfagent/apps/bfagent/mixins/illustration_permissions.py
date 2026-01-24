"""
Permission Mixins for Illustration System
Ensures proper user and role-based access control
"""
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


class IllustrationOwnerMixin(UserPassesTestMixin):
    """
    Mixin that ensures user can only access their own illustration resources.
    
    Checks:
    - User is authenticated
    - User owns the resource (via user field)
    - OR User is staff/superuser (admin override)
    
    Usage:
        class MyView(IllustrationOwnerMixin, DetailView):
            model = GeneratedImage
    """
    
    def test_func(self):
        """Check if user has permission to access this resource"""
        # Staff and superusers can access everything
        if self.request.user.is_staff or self.request.user.is_superuser:
            return True
        
        # Get the object being accessed
        obj = self.get_object()
        
        # Check if user owns this resource
        if hasattr(obj, 'user'):
            return obj.user == self.request.user
        
        # Check if resource is linked to a project the user owns
        if hasattr(obj, 'project'):
            return obj.project.user == self.request.user
        
        # Default deny
        return False
    
    def handle_no_permission(self):
        """Custom error message for permission denied"""
        raise PermissionDenied(
            "You don't have permission to access this resource. "
            "You can only access your own illustrations."
        )


class IllustrationProjectAccessMixin(UserPassesTestMixin):
    """
    Mixin for views that access resources through a project.
    
    Checks:
    - User owns the project
    - OR User is team member of the project (if team system exists)
    - OR User is staff/superuser
    
    Usage:
        class MyView(IllustrationProjectAccessMixin, CreateView):
            # Requires 'project_id' in URL or form
    """
    
    def test_func(self):
        """Check if user has access to the project"""
        # Staff and superusers can access everything
        if self.request.user.is_staff or self.request.user.is_superuser:
            return True
        
        # Get project from URL kwargs or form data
        project_id = self.kwargs.get('project_id') or self.request.POST.get('project')
        
        if not project_id:
            # No project specified, can't determine access
            return False
        
        from apps.bfagent.models import BookProjects
        
        try:
            project = BookProjects.objects.get(pk=project_id)
        except BookProjects.DoesNotExist:
            return False
        
        # Check if user owns the project
        if project.user == self.request.user:
            return True
        
        # TODO: Check if user is team member (when team system exists)
        # if hasattr(project, 'team_members'):
        #     return self.request.user in project.team_members.all()
        
        return False
    
    def handle_no_permission(self):
        """Custom error message for permission denied"""
        raise PermissionDenied(
            "You don't have permission to access this project. "
            "You can only work with your own projects."
        )


class IllustrationListOwnerFilterMixin:
    """
    Mixin that automatically filters list views to show only user's resources.
    
    Benefits:
    - Prevents users from seeing other users' data
    - Consistent across all list views
    - Staff can see all resources
    
    Usage:
        class MyListView(IllustrationListOwnerFilterMixin, ListView):
            model = GeneratedImage
    """
    
    def get_queryset(self):
        """Filter queryset to user's resources only"""
        qs = super().get_queryset()
        
        # Staff and superusers see everything
        if self.request.user.is_staff or self.request.user.is_superuser:
            return qs
        
        # Regular users see only their own resources
        if hasattr(qs.model, 'user'):
            return qs.filter(user=self.request.user)
        
        # If model doesn't have 'user' field, try to filter by project
        if hasattr(qs.model, 'project'):
            return qs.filter(project__user=self.request.user)
        
        # Default: return queryset as-is (shouldn't happen)
        return qs
