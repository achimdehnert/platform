"""
Enhanced Workflow Domain and Project Type Management
Dynamic, AI-optimized domain and project type system
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class WorkflowDomain(models.Model):
    """
    Dynamic Domain Management (Projektart)
    Replaces hardcoded DOMAIN_CHOICES with manageable entities
    """

    # Basic Information
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique domain code (e.g., 'bookwriting', 'medtrans', 'genagent')",
    )
    name = models.CharField(
        max_length=100,
        help_text="Human-readable domain name (e.g., 'Book Writing', 'Medical Translation')",
    )
    # display_name = models.CharField(
    #     max_length=100,
    #     blank=True,
    #     null=True,
    #     help_text="Display name for UI (e.g., 'Bücher-Hub', 'Control-Hub')",
    # )

    # AI Context Enhancement
    description = models.TextField(
        help_text="Detailed description of this domain and its characteristics"
    )
    characteristics = models.TextField(
        help_text="Key characteristics, workflows, and industry-specific requirements for AI context"
    )
    typical_phases = models.TextField(
        blank=True, help_text="Common phases typically found in this domain (for AI reference)"
    )

    # Visual & UX
    icon = models.CharField(
        max_length=50,
        default="bi-folder",
        help_text="Bootstrap icon class (e.g., 'bi-book', 'bi-translate', 'bi-robot')",
    )
    color = models.CharField(
        max_length=20,
        default="primary",
        help_text="Bootstrap color class (primary, success, warning, info, etc.)",
    )

    # Metadata
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Statistics
    project_count = models.IntegerField(default=0, help_text="Number of projects using this domain")

    class Meta:
        db_table = "workflow_domains"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def display_name(self):
        """
        Get display name from database or generate from name
        """
        # Try to get display_name from database (raw SQL)
        from django.db import connection

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT display_name FROM workflow_domains WHERE id = %s", [self.id])
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
        except:
            pass

        # Fallback to name
        return self.name

    @property
    def ai_context(self):
        """Generate rich AI context for LLM prompts"""
        return {
            "domain_code": self.code,
            "domain_name": self.name,
            "description": self.description,
            "characteristics": self.characteristics,
            "typical_phases": self.typical_phases,
        }


class ProjectType(models.Model):
    """
    Enhanced Project Type Management (Projekttyp)
    Rich descriptions and AI context for better workflow generation
    """

    # Basic Information
    domain = models.ForeignKey(
        WorkflowDomain, on_delete=models.CASCADE, related_name="project_types"
    )
    code = models.CharField(
        max_length=100,
        help_text="Unique project type code within domain (e.g., 'novel', 'medical_report')",
    )
    name = models.CharField(max_length=150, help_text="Human-readable project type name")

    # AI Context Enhancement
    description = models.TextField(
        help_text="Detailed description of this project type and its specific requirements"
    )
    characteristics = models.TextField(
        help_text="Key characteristics, deliverables, and specific workflows for this project type"
    )
    typical_duration_days = models.IntegerField(
        null=True, blank=True, help_text="Typical project duration in days (for AI estimation)"
    )
    complexity_level = models.CharField(
        max_length=20,
        choices=[
            ("simple", "Simple (1-2 weeks)"),
            ("moderate", "Moderate (1-2 months)"),
            ("complex", "Complex (3-6 months)"),
            ("enterprise", "Enterprise (6+ months)"),
        ],
        default="moderate",
        help_text="Complexity level for AI phase estimation",
    )

    # Industry Context
    industry_standards = models.TextField(
        blank=True,
        help_text="Industry standards, regulations, or best practices relevant to this project type",
    )
    common_deliverables = models.TextField(
        blank=True, help_text="Common deliverables and outputs for this project type"
    )
    stakeholder_types = models.TextField(
        blank=True, help_text="Typical stakeholders involved in this project type"
    )

    # AI Prompt Enhancement
    phase_generation_hints = models.TextField(
        blank=True,
        help_text="Specific hints for AI phase generation (e.g., 'Include regulatory review', 'Emphasize testing')",
    )

    # Metadata
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Statistics
    usage_count = models.IntegerField(
        default=0, help_text="Number of times this project type has been used"
    )

    class Meta:
        db_table = "project_types"
        unique_together = ["domain", "code"]
        ordering = ["domain__name", "name"]

    def __str__(self):
        return f"{self.domain.name}: {self.name}"

    @property
    def full_code(self):
        """Generate full code: domain.project_type"""
        return f"{self.domain.code}.{self.code}"

    @property
    def ai_context(self):
        """Generate comprehensive AI context for LLM prompts"""
        return {
            "domain": self.domain.ai_context,
            "project_type_code": self.code,
            "project_type_name": self.name,
            "description": self.description,
            "characteristics": self.characteristics,
            "complexity_level": self.complexity_level,
            "typical_duration_days": self.typical_duration_days,
            "industry_standards": self.industry_standards,
            "common_deliverables": self.common_deliverables,
            "stakeholder_types": self.stakeholder_types,
            "phase_generation_hints": self.phase_generation_hints,
        }


class WorkflowTemplate(models.Model):
    """
    Pre-defined workflow templates for common project types
    Can be used as starting points or references for AI generation
    """

    project_type = models.ForeignKey(
        ProjectType, on_delete=models.CASCADE, related_name="workflow_templates"
    )
    name = models.CharField(max_length=200)
    description = models.TextField()

    # Template Data
    phases_json = models.JSONField(
        help_text="JSON array of phase definitions with name, description, estimated_days, required, order"
    )

    # Template Metadata
    is_default = models.BooleanField(
        default=False, help_text="Whether this is the default template for the project type"
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Usage Statistics
    usage_count = models.IntegerField(default=0)

    class Meta:
        db_table = "workflow_templates_v2"  # Revert: Conflicts with bfagent.WorkflowTemplate, keep separate
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.project_type}: {self.name}"

    @property
    def phase_count(self):
        """Get number of phases in this template"""
        return len(self.phases_json) if self.phases_json else 0

    @property
    def total_estimated_days(self):
        """Calculate total estimated days for all phases"""
        if not self.phases_json:
            return 0
        return sum(phase.get("estimated_days", 0) for phase in self.phases_json)
