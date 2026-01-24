"""Tests for model generation tools."""

import pytest


class TestGenerateDjangoModel:
    """Tests for generate_django_model tool."""

    def test_basic_model(self):
        """Test basic model generation."""
        from django_htmx_mcp.tools.models import generate_django_model
        
        code = generate_django_model(
            model_name="Task",
            fields=[
                {"name": "title", "type": "CharField", "max_length": 200},
                {"name": "completed", "type": "BooleanField", "default": False},
            ],
            app_name="tasks",
        )
        
        assert "class Task(models.Model):" in code
        assert "title = models.CharField(max_length=200)" in code
        assert "completed = models.BooleanField(default=False)" in code
        assert "created_at = models.DateTimeField(auto_now_add=True)" in code
        assert "updated_at = models.DateTimeField(auto_now=True)" in code
        assert "def __str__(self):" in code
        assert "def get_absolute_url(self):" in code

    def test_model_with_uuid(self):
        """Test model with UUID primary key."""
        from django_htmx_mcp.tools.models import generate_django_model
        
        code = generate_django_model(
            model_name="Item",
            fields=[{"name": "name", "type": "CharField", "max_length": 100}],
            app_name="app",
            with_uuid_pk=True,
        )
        
        assert "import uuid" in code
        assert "id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)" in code

    def test_model_with_soft_delete(self):
        """Test model with soft delete."""
        from django_htmx_mcp.tools.models import generate_django_model
        
        code = generate_django_model(
            model_name="Item",
            fields=[{"name": "name", "type": "CharField", "max_length": 100}],
            app_name="app",
            with_soft_delete=True,
        )
        
        assert "is_deleted = models.BooleanField(default=False)" in code
        assert "deleted_at = models.DateTimeField(null=True, blank=True)" in code
        assert "def soft_delete(self):" in code
        assert "def restore(self):" in code

    def test_model_with_foreign_key(self):
        """Test model with ForeignKey."""
        from django_htmx_mcp.tools.models import generate_django_model
        
        code = generate_django_model(
            model_name="Task",
            fields=[
                {"name": "assignee", "type": "ForeignKey", "to": "User", "on_delete": "CASCADE", "null": True},
            ],
            app_name="tasks",
        )
        
        assert 'assignee = models.ForeignKey("User", on_delete=models.CASCADE, null=True)' in code

    def test_model_with_choices(self):
        """Test model with choices field."""
        from django_htmx_mcp.tools.models import generate_django_model
        
        code = generate_django_model(
            model_name="Task",
            fields=[
                {
                    "name": "status",
                    "type": "CharField",
                    "max_length": 20,
                    "choices": [("pending", "Pending"), ("done", "Done")],
                },
            ],
            app_name="tasks",
        )
        
        assert 'choices=[("pending", "Pending"), ("done", "Done")]' in code


class TestGenerateChoicesClass:
    """Tests for generate_choices_class tool."""

    def test_text_choices(self):
        """Test TextChoices generation."""
        from django_htmx_mcp.tools.models import generate_choices_class
        
        code = generate_choices_class(
            name="TaskStatus",
            choices=[("PENDING", "Pending"), ("DONE", "Done")],
        )
        
        assert "class TaskStatus(models.TextChoices):" in code
        assert 'PENDING = "pending", "Pending"' in code
        assert 'DONE = "done", "Done"' in code

    def test_integer_choices(self):
        """Test IntegerChoices generation."""
        from django_htmx_mcp.tools.models import generate_choices_class
        
        code = generate_choices_class(
            name="Priority",
            choices=[("LOW", "Low"), ("HIGH", "High")],
            use_text_choices=False,
        )
        
        assert "class Priority(models.IntegerChoices):" in code
        assert 'LOW = 1, "Low"' in code
        assert 'HIGH = 2, "High"' in code


class TestGenerateModelManager:
    """Tests for generate_model_manager tool."""

    def test_manager_with_soft_delete(self):
        """Test manager with soft delete methods."""
        from django_htmx_mcp.tools.models import generate_model_manager
        
        code = generate_model_manager(
            model_name="Task",
            with_soft_delete=True,
        )
        
        assert "class TaskQuerySet(models.QuerySet):" in code
        assert "class TaskManager(models.Manager):" in code
        assert "def active(self):" in code
        assert "def deleted(self):" in code
        assert "return self.filter(is_deleted=False)" in code

    def test_manager_with_custom_methods(self):
        """Test manager with custom methods."""
        from django_htmx_mcp.tools.models import generate_model_manager
        
        code = generate_model_manager(
            model_name="Task",
            with_soft_delete=False,
            custom_methods=[
                {"name": "pending", "filter": {"status": "pending"}, "description": "Get pending tasks"},
            ],
        )
        
        assert "def pending(self):" in code
        assert '"Get pending tasks"' in code
