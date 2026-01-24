"""Tests for view generation tools."""

import pytest


class TestGenerateCBV:
    """Tests for generate_cbv tool."""

    def test_list_view(self):
        """Test ListView generation."""
        from django_htmx_mcp.tools.views import generate_cbv
        
        code = generate_cbv(
            view_name="TaskListView",
            view_type="ListView",
            model="Task",
            app_name="tasks",
            htmx_enabled=True,
            paginate_by=25,
        )
        
        assert "class TaskListView(ListView):" in code
        assert "model = Task" in code
        assert "paginate_by = 25" in code
        assert "def get_template_names(self):" in code
        assert 'if self.request.headers.get("HX-Request"):' in code

    def test_create_view(self):
        """Test CreateView generation."""
        from django_htmx_mcp.tools.views import generate_cbv
        
        code = generate_cbv(
            view_name="TaskCreateView",
            view_type="CreateView",
            model="Task",
            app_name="tasks",
            htmx_enabled=True,
            fields=["title", "description"],
        )
        
        assert "class TaskCreateView(CreateView):" in code
        assert "def form_valid(self, form):" in code
        assert "def form_invalid(self, form):" in code
        assert 'response["HX-Trigger"] = "taskChanged"' in code

    def test_delete_view(self):
        """Test DeleteView generation."""
        from django_htmx_mcp.tools.views import generate_cbv
        
        code = generate_cbv(
            view_name="TaskDeleteView",
            view_type="DeleteView",
            model="Task",
            app_name="tasks",
            htmx_enabled=True,
        )
        
        assert "class TaskDeleteView(DeleteView):" in code
        assert "def delete(self, request, *args, **kwargs):" in code
        assert 'response["HX-Trigger"] = "taskDeleted"' in code

    def test_view_with_login_required(self):
        """Test view with LoginRequiredMixin."""
        from django_htmx_mcp.tools.views import generate_cbv
        
        code = generate_cbv(
            view_name="TaskListView",
            view_type="ListView",
            model="Task",
            app_name="tasks",
            login_required=True,
        )
        
        assert "LoginRequiredMixin" in code
        assert "class TaskListView(LoginRequiredMixin, ListView):" in code

    def test_view_with_permission(self):
        """Test view with PermissionRequiredMixin."""
        from django_htmx_mcp.tools.views import generate_cbv
        
        code = generate_cbv(
            view_name="TaskUpdateView",
            view_type="UpdateView",
            model="Task",
            app_name="tasks",
            permission_required="tasks.change_task",
        )
        
        assert "PermissionRequiredMixin" in code
        assert 'permission_required = "tasks.change_task"' in code


class TestGenerateHTMXActionView:
    """Tests for generate_htmx_action_view tool."""

    def test_toggle_view(self):
        """Test toggle action view."""
        from django_htmx_mcp.tools.views import generate_htmx_action_view
        
        code = generate_htmx_action_view(
            view_name="TaskToggleView",
            model="Task",
            action="toggle",
            field="completed",
        )
        
        assert "class TaskToggleView(" in code
        assert "def post(self, request, pk):" in code
        assert "obj.completed = not obj.completed" in code

    def test_inline_edit_view(self):
        """Test inline edit view."""
        from django_htmx_mcp.tools.views import generate_htmx_action_view
        
        code = generate_htmx_action_view(
            view_name="TaskInlineEditView",
            model="Task",
            action="inline_edit",
            field="title",
        )
        
        assert "def get(self, request, pk):" in code
        assert "def post(self, request, pk):" in code

    def test_bulk_action_view(self):
        """Test bulk action view."""
        from django_htmx_mcp.tools.views import generate_htmx_action_view
        
        code = generate_htmx_action_view(
            view_name="TaskBulkActionView",
            model="Task",
            action="bulk_action",
        )
        
        assert 'ids = request.POST.getlist(\'ids\')' in code
        assert 'action = request.POST.get(\'action\')' in code


class TestGenerateHTMXSearchView:
    """Tests for generate_htmx_search_view tool."""

    def test_search_view(self):
        """Test search view generation."""
        from django_htmx_mcp.tools.views import generate_htmx_search_view
        
        code = generate_htmx_search_view(
            view_name="TaskSearchView",
            model="Task",
            search_fields=["title", "description"],
            app_name="tasks",
        )
        
        assert "class TaskSearchView(View):" in code
        assert "Q(title__icontains=query)" in code
        assert "Q(description__icontains=query)" in code
        assert "min_chars = 2" in code
