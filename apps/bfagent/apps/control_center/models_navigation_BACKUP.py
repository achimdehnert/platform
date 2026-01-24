"""
Dynamic Navigation System
Domain-aware, permission-based, configurable navigation
"""

from django.contrib.auth.models import Group, Permission, User
from django.db import models
from django.utils import timezone

from .models_workflow_domains import WorkflowDomain


class NavigationSection(models.Model):
    """
    Navigation sections (e.g., "WORKFLOW ENGINE", "CONTENT MANAGEMENT")
    """

    # Basic Information
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique section code (e.g., 'workflow_engine', 'content_management')",
    )
    name = models.CharField(max_length=100, help_text="Display name for the section")
    description = models.TextField(blank=True, help_text="Description of this navigation section")

    # Visual & UX
    icon = models.CharField(
        max_length=50, default="bi-folder", help_text="Bootstrap icon class for the section"
    )
    color = models.CharField(max_length=20, default="primary", help_text="Bootstrap color class")

    # Ordering & Visibility
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    is_active = models.BooleanField(default=True)
    is_collapsible = models.BooleanField(
        default=True, help_text="Whether this section can be collapsed"
    )
    is_collapsed_default = models.BooleanField(
        default=False, help_text="Whether this section is collapsed by default"
    )

    # NEW SCHEMA (Phase 1+): Domain FK and Slug
    domain_id = models.ForeignKey(
        'core.DomainArt',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column='domain_id',
        related_name='navigation_sections_new',
        help_text="Domain this section belongs to (Phase 1+: FK to DomainArt)"
    )
    slug = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="URL-safe identifier (Phase 1+: for new schema)"
    )
    
    # OLD SCHEMA (Legacy): M2M Domain filtering
    domains = models.ManyToManyField(
        "WorkflowDomain",
        blank=True,
        help_text="Domains where this section is visible (empty = all domains)",
    )
    required_permissions = models.ManyToManyField(
        Permission, blank=True, help_text="Permissions required to see this section"
    )
    required_groups = models.ManyToManyField(
        Group, blank=True, help_text="Groups required to see this section"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "navigation_sections"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def is_visible_for_user(self, user, domain=None):
        """Check if this section should be visible for the given user and domain"""
        if not self.is_active:
            return False

        # Domain filtering disabled for now
        # if domain and self.domains.exists():
        #     if not self.domains.filter(code=domain).exists():
        #         return False

        # Check permissions
        if self.required_permissions.exists():
            if not user.has_perms(self.required_permissions.values_list("codename", flat=True)):
                return False

        # Check groups
        if self.required_groups.exists():
            user_groups = user.groups.all()
            if not self.required_groups.filter(id__in=user_groups).exists():
                return False

        return True


class NavigationItem(models.Model):
    """
    Individual navigation items within sections
    """

    ITEM_TYPES = [
        ("link", "Link"),
        ("dropdown", "Dropdown"),
        ("separator", "Separator"),
        ("header", "Header"),
    ]

    # Basic Information
    section = models.ForeignKey(
        NavigationSection, on_delete=models.CASCADE, related_name="navigation_items"
    )
    code = models.CharField(max_length=50, help_text="Unique item code within section")
    name = models.CharField(max_length=100, help_text="Display name for the navigation item")
    description = models.TextField(blank=True, help_text="Tooltip or description text")

    # Navigation Properties
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default="link")
    url_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Django URL name (e.g., 'control_center:workflow-v2-dashboard')",
    )
    url_params = models.JSONField(
        default=dict,
        blank=True,
        help_text="URL parameters as JSON (e.g., {'domain': 'bookwriting'})",
    )
    external_url = models.URLField(
        blank=True, help_text="External URL (if not using Django URL name)"
    )

    # Visual & UX
    icon = models.CharField(max_length=50, default="bi-circle", help_text="Bootstrap icon class")
    badge_text = models.CharField(
        max_length=20, blank=True, help_text="Badge text (e.g., 'V2', 'NEW', 'BETA')"
    )
    badge_color = models.CharField(max_length=20, default="primary", help_text="Badge color class")

    # Ordering & Visibility
    order = models.IntegerField(default=0, help_text="Display order within section")
    is_active = models.BooleanField(default=True)
    opens_in_new_tab = models.BooleanField(default=False, help_text="Whether link opens in new tab")

    # Domain & Permission Filtering - now active for Phase 2
    domains = models.ManyToManyField(
        "WorkflowDomain",
        blank=True,
        help_text="Limit this item to specific domains (empty = all domains)",
    )
    required_permissions = models.ManyToManyField(
        Permission, blank=True, help_text="Permissions required to see this item"
    )
    required_groups = models.ManyToManyField(
        Group, blank=True, help_text="Groups required to see this item"
    )

    # Parent-Child Relationships (for dropdowns)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "navigation_items"
        unique_together = ["section", "code"]
        ordering = ["section__order", "order", "name"]

    def __str__(self):
        return f"{self.section.name}: {self.name}"

    def is_visible_for_user(self, user, domain=None):
        """Check if this item should be visible for the given user and domain"""
        if not self.is_active:
            return False

        # Check if user is authenticated
        if not user.is_authenticated:
            return False

        # Domain filtering disabled for now
        # if domain and self.domains.exists():
        #     if not self.domains.filter(code=domain).exists():
        #         return False

        # Check required permissions
        if self.required_permissions.exists():
            for permission in self.required_permissions.all():
                if not user.has_perm(permission.codename):
                    return False

        # Check required groups
        if self.required_groups.exists():
            user_groups = set(user.groups.values_list("name", flat=True))
            required_groups = set(self.required_groups.values_list("name", flat=True))
            if not user_groups.intersection(required_groups):
                return False

        return True

    def get_url(self, request=None):
        """Generate the URL for this navigation item.

        This method must never raise NoReverseMatch. It prefers external_url,
        then tries to reverse url_name (with optional url_params). If reversing
        fails and url_name looks like a literal path, that path is used. As a
        last resort, it falls back to the navigation-url-missing view or '#'.
        """
        # 1. External URLs have highest priority
        if self.external_url:
            return self.external_url

        # 2. No url_name configured -> dummy link
        if not self.url_name:
            return "#"

        from django.urls import NoReverseMatch, reverse
        import json

        # 3. Try to resolve url_name as a regular Django view name
        try:
            # Handle url_params being a string (e.g., "{}") or dict
            params_dict = {}
            if self.url_params:
                if isinstance(self.url_params, str):
                    # Parse string as JSON
                    try:
                        params_dict = json.loads(self.url_params) if self.url_params.strip() else {}
                    except json.JSONDecodeError:
                        params_dict = {}
                elif isinstance(self.url_params, dict):
                    params_dict = self.url_params
            
            if params_dict:
                params = {}
                for key, value in params_dict.items():
                    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                        # Dynamic parameter - e.g. {current_project_id}
                        param_name = value[1:-1]
                        if request is not None and hasattr(request, param_name):
                            params[key] = getattr(request, param_name)
                        else:
                            # Keep placeholder if we can't resolve it dynamically
                            params[key] = value
                    else:
                        params[key] = value
                return reverse(self.url_name, kwargs=params)
            else:
                return reverse(self.url_name)
        except NoReverseMatch:
            # 4. url_name might actually already be a literal path like '/control-center/'
            if isinstance(self.url_name, str) and self.url_name.startswith("/"):
                return self.url_name

            # 5. As a last resort, point to the URL-missing diagnostic page
            try:
                return reverse("control_center:navigation-url-missing", args=[self.id])
            except NoReverseMatch:
                # Even the diagnostic view is not available -> safe fallback
                return "#"
        except Exception:
            # Any other unexpected error should not bubble up into templates
            return "#"

    @property
    def has_children(self):
        """Check if this item has child items (for dropdowns)"""
        return self.children.filter(is_active=True).exists()


class UserNavigationPreference(models.Model):
    """
    User-specific navigation preferences
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    section = models.ForeignKey(NavigationSection, on_delete=models.CASCADE)

    # Preferences
    is_collapsed = models.BooleanField(
        default=False, help_text="Whether user has collapsed this section"
    )
    is_hidden = models.BooleanField(default=False, help_text="Whether user has hidden this section")
    custom_order = models.IntegerField(
        null=True, blank=True, help_text="User's custom ordering preference"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_navigation_preferences"
        unique_together = ["user", "section"]

    def __str__(self):
        return f"{self.user.username}: {self.section.name}"
