"""
Graph Core Models - Universal Workflow Orchestration Platform

Models for:
1. Framework System (DB-driven story/software frameworks)
2. Graph System (nodes and edges for complex relationships)
3. Project Integration (links to existing BookProjects)
"""

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


# =============================================================================
# FRAMEWORK SYSTEM - DB-Driven Story/Software Frameworks
# =============================================================================

class Framework(models.Model):
    """
    A story or workflow framework (e.g., Save the Cat, Hero's Journey, C4 Model)
    
    Replaces hardcoded frameworks in story_frameworks.py with DB-driven config.
    """
    
    class DomainType(models.TextChoices):
        STORY = 'story', 'Story/Narrative'
        SOFTWARE = 'software', 'Software Architecture'
        BUSINESS = 'business', 'Business Process'
        RESEARCH = 'research', 'Research/Academic'
        LEGAL = 'legal', 'Legal/Compliance'
        CUSTOM = 'custom', 'Custom Domain'
    
    # === Identity ===
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Framework name (e.g., 'Save the Cat')"
    )
    slug = models.SlugField(
        unique=True,
        help_text="URL-friendly identifier"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Human-readable name"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the framework"
    )
    
    # === Classification ===
    domain = models.CharField(
        max_length=20,
        choices=DomainType.choices,
        default=DomainType.STORY,
        help_text="Domain this framework applies to"
    )
    
    # === Visual ===
    icon = models.CharField(
        max_length=50,
        default='diagram-3',
        help_text="Bootstrap icon name"
    )
    color = models.CharField(
        max_length=20,
        default='primary',
        help_text="Bootstrap color class"
    )
    
    # === Configuration ===
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Framework-specific configuration"
    )
    
    # === Status ===
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Default framework for this domain"
    )
    sort_order = models.IntegerField(default=0)
    
    # === Metadata ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_frameworks'
    )
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_frameworks'
        ordering = ['domain', 'sort_order', 'name']
        verbose_name = 'Framework'
        verbose_name_plural = 'Frameworks'
    
    def __str__(self):
        return f"{self.display_name} ({self.get_domain_display()})"
    
    @property
    def phase_count(self):
        return FrameworkPhase.objects.filter(framework=self).count()
    
    @property
    def step_count(self):
        return FrameworkStep.objects.filter(phase__framework=self).count()


class FrameworkPhase(models.Model):
    """
    A phase within a framework (e.g., "Act 1", "Opening Image", "Context")
    """
    
    framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        related_name='phases'
    )
    
    # === Identity ===
    name = models.CharField(
        max_length=100,
        help_text="Phase name (e.g., 'Act 1', 'Opening Image')"
    )
    slug = models.SlugField(
        help_text="URL-friendly identifier"
    )
    description = models.TextField(
        blank=True,
        help_text="What happens in this phase"
    )
    
    # === Position ===
    order = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Order within the framework"
    )
    position_start = models.FloatField(
        default=0.0,
        help_text="Start position in story (0.0 to 1.0)"
    )
    position_end = models.FloatField(
        default=1.0,
        help_text="End position in story (0.0 to 1.0)"
    )
    
    # === Visual ===
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text="Hex color for UI"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Bootstrap icon"
    )
    
    # === Guidance ===
    guidance = models.TextField(
        blank=True,
        help_text="Writing/implementation guidance for this phase"
    )
    emotional_arc = models.CharField(
        max_length=200,
        blank=True,
        help_text="Emotional tone/arc for this phase"
    )
    
    # === Status ===
    is_required = models.BooleanField(
        default=True,
        help_text="Is this phase required?"
    )
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_framework_phases'
        ordering = ['framework', 'order']
        unique_together = [['framework', 'slug']]
        verbose_name = 'Framework Phase'
        verbose_name_plural = 'Framework Phases'
    
    def __str__(self):
        return f"{self.framework.name} - {self.name}"
    
    @property
    def step_count(self):
        return self.steps.count()


class FrameworkStep(models.Model):
    """
    A step/beat within a phase (e.g., "Opening Image", "Theme Stated")
    
    This is the most granular level - individual beats or steps.
    """
    
    phase = models.ForeignKey(
        FrameworkPhase,
        on_delete=models.CASCADE,
        related_name='steps'
    )
    
    # === Identity ===
    name = models.CharField(
        max_length=100,
        help_text="Step/beat name"
    )
    slug = models.SlugField(
        help_text="URL-friendly identifier"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description"
    )
    
    # === Position ===
    order = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    typical_position = models.FloatField(
        default=0.0,
        help_text="Typical position in story (0.0 to 1.0)"
    )
    
    # === Guidance ===
    chapter_guidance = models.TextField(
        blank=True,
        help_text="How to write this in a chapter"
    )
    example = models.TextField(
        blank=True,
        help_text="Example from famous works"
    )
    common_mistakes = models.TextField(
        blank=True,
        help_text="Common mistakes to avoid"
    )
    
    # === Duration/Length ===
    estimated_word_count = models.IntegerField(
        default=0,
        help_text="Estimated words for this step"
    )
    estimated_chapters = models.IntegerField(
        default=1,
        help_text="Estimated chapters for this step"
    )
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_framework_steps'
        ordering = ['phase', 'order']
        unique_together = [['phase', 'slug']]
        verbose_name = 'Framework Step'
        verbose_name_plural = 'Framework Steps'
    
    def __str__(self):
        return f"{self.phase.framework.name} - {self.phase.name} - {self.name}"


# =============================================================================
# GRAPH SYSTEM - Nodes and Edges for Complex Relationships
# =============================================================================

class NodeType(models.Model):
    """
    Type of node (e.g., Character, Location, Event, Component, Container)
    
    Domain-specific node types for different frameworks.
    """
    
    # === Identity ===
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Type name (e.g., 'character', 'location')"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Human-readable name"
    )
    description = models.TextField(
        blank=True
    )
    
    # === Classification ===
    domain = models.CharField(
        max_length=20,
        choices=Framework.DomainType.choices,
        default=Framework.DomainType.STORY,
        help_text="Domain this type belongs to"
    )
    
    # === Visual ===
    icon = models.CharField(
        max_length=50,
        default='circle',
        help_text="Bootstrap icon"
    )
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text="Default hex color"
    )
    shape = models.CharField(
        max_length=20,
        default='ellipse',
        choices=[
            ('ellipse', 'Ellipse'),
            ('rectangle', 'Rectangle'),
            ('round-rectangle', 'Rounded Rectangle'),
            ('diamond', 'Diamond'),
            ('hexagon', 'Hexagon'),
            ('octagon', 'Octagon'),
            ('star', 'Star'),
        ],
        help_text="Cytoscape.js shape"
    )
    
    # === Schema ===
    schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON schema for node properties"
    )
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_node_types'
        ordering = ['domain', 'name']
        verbose_name = 'Node Type'
        verbose_name_plural = 'Node Types'
    
    def __str__(self):
        return f"{self.display_name} ({self.get_domain_display()})"


class EdgeType(models.Model):
    """
    Type of edge/relationship (e.g., loves, hates, contains, depends_on)
    """
    
    # === Identity ===
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Type name (e.g., 'loves', 'contains')"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Human-readable name"
    )
    description = models.TextField(
        blank=True
    )
    
    # === Classification ===
    domain = models.CharField(
        max_length=20,
        choices=Framework.DomainType.choices,
        default=Framework.DomainType.STORY,
        help_text="Domain this type belongs to"
    )
    
    # === Constraints ===
    source_types = models.ManyToManyField(
        NodeType,
        related_name='outgoing_edge_types',
        blank=True,
        help_text="Valid source node types"
    )
    target_types = models.ManyToManyField(
        NodeType,
        related_name='incoming_edge_types',
        blank=True,
        help_text="Valid target node types"
    )
    
    # === Visual ===
    color = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Line color"
    )
    line_style = models.CharField(
        max_length=20,
        default='solid',
        choices=[
            ('solid', 'Solid'),
            ('dashed', 'Dashed'),
            ('dotted', 'Dotted'),
        ]
    )
    arrow_shape = models.CharField(
        max_length=20,
        default='triangle',
        choices=[
            ('triangle', 'Triangle'),
            ('circle', 'Circle'),
            ('square', 'Square'),
            ('diamond', 'Diamond'),
            ('none', 'None'),
        ]
    )
    
    # === Directionality ===
    is_directed = models.BooleanField(
        default=True,
        help_text="Is this a directed relationship?"
    )
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_edge_types'
        ordering = ['domain', 'name']
        verbose_name = 'Edge Type'
        verbose_name_plural = 'Edge Types'
    
    def __str__(self):
        return f"{self.display_name} ({self.get_domain_display()})"


class GraphNode(models.Model):
    """
    A node in the project graph (e.g., a character, location, event)
    
    Links to BookProjects for story domains.
    """
    
    # === Project Link ===
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='graph_nodes',
        help_text="Project this node belongs to"
    )
    
    # === Type ===
    node_type = models.ForeignKey(
        NodeType,
        on_delete=models.PROTECT,
        related_name='nodes'
    )
    
    # === Identity ===
    name = models.CharField(
        max_length=200,
        help_text="Node name/label"
    )
    description = models.TextField(
        blank=True
    )
    
    # === Properties ===
    properties = models.JSONField(
        default=dict,
        blank=True,
        help_text="Type-specific properties"
    )
    
    # === Visual Position ===
    position_x = models.FloatField(
        default=0,
        help_text="X position in graph"
    )
    position_y = models.FloatField(
        default=0,
        help_text="Y position in graph"
    )
    
    # === Visual Override ===
    custom_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Override type color"
    )
    custom_icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Override type icon"
    )
    
    # === Status ===
    is_active = models.BooleanField(default=True)
    
    # === Metadata ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_graph_nodes'
    )
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_nodes'
        ordering = ['project', 'node_type', 'name']
        verbose_name = 'Graph Node'
        verbose_name_plural = 'Graph Nodes'
    
    def __str__(self):
        return f"{self.name} ({self.node_type.display_name})"
    
    @property
    def color(self):
        return self.custom_color or self.node_type.color
    
    @property
    def icon(self):
        return self.custom_icon or self.node_type.icon
    
    def to_cytoscape(self):
        """Convert to Cytoscape.js node format"""
        return {
            'data': {
                'id': f'n{self.id}',
                'label': self.name,
                'type': self.node_type.name,
                'description': self.description,
                'properties': self.properties,
            },
            'position': {
                'x': self.position_x,
                'y': self.position_y,
            },
            'classes': self.node_type.name,
        }


class GraphEdge(models.Model):
    """
    An edge/relationship between two nodes
    """
    
    # === Project Link ===
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='graph_edges',
        help_text="Project this edge belongs to"
    )
    
    # === Type ===
    edge_type = models.ForeignKey(
        EdgeType,
        on_delete=models.PROTECT,
        related_name='edges'
    )
    
    # === Connection ===
    source = models.ForeignKey(
        GraphNode,
        on_delete=models.CASCADE,
        related_name='outgoing_edges'
    )
    target = models.ForeignKey(
        GraphNode,
        on_delete=models.CASCADE,
        related_name='incoming_edges'
    )
    
    # === Properties ===
    label = models.CharField(
        max_length=200,
        blank=True,
        help_text="Edge label (optional)"
    )
    weight = models.FloatField(
        default=1.0,
        help_text="Edge weight/strength"
    )
    properties = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional properties"
    )
    
    # === Visual Override ===
    custom_color = models.CharField(
        max_length=7,
        blank=True
    )
    
    # === Status ===
    is_active = models.BooleanField(default=True)
    
    # === Metadata ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_edges'
        ordering = ['project', 'edge_type', 'source']
        verbose_name = 'Graph Edge'
        verbose_name_plural = 'Graph Edges'
    
    def __str__(self):
        return f"{self.source.name} --[{self.edge_type.display_name}]--> {self.target.name}"
    
    @property
    def color(self):
        return self.custom_color or self.edge_type.color
    
    def to_cytoscape(self):
        """Convert to Cytoscape.js edge format"""
        return {
            'data': {
                'id': f'e{self.id}',
                'source': f'n{self.source_id}',
                'target': f'n{self.target_id}',
                'label': self.label or self.edge_type.display_name,
                'type': self.edge_type.name,
                'weight': self.weight,
            },
            'classes': self.edge_type.name,
        }


# =============================================================================
# PROJECT FRAMEWORK ASSIGNMENT
# =============================================================================

class ProjectFramework(models.Model):
    """
    Links a project to a framework with project-specific progress tracking
    """
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='assigned_frameworks'
    )
    framework = models.ForeignKey(
        Framework,
        on_delete=models.PROTECT,
        related_name='projects'
    )
    
    # === Progress ===
    current_phase = models.ForeignKey(
        FrameworkPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    current_step = models.ForeignKey(
        FrameworkStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    progress_percent = models.FloatField(
        default=0.0,
        help_text="Overall progress (0-100)"
    )
    
    # === Configuration ===
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Project-specific framework config"
    )
    
    # === Status ===
    is_primary = models.BooleanField(
        default=True,
        help_text="Primary framework for this project"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    # === Metadata ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_project_frameworks'
        unique_together = [['project', 'framework']]
        ordering = ['-is_primary', 'created_at']
        verbose_name = 'Project Framework'
        verbose_name_plural = 'Project Frameworks'
    
    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return f"{self.project.title} - {self.framework.name}{primary}"
    
    def start(self):
        """Start working with this framework"""
        if not self.started_at:
            self.started_at = timezone.now()
            first_phase = self.framework.phases.first()
            if first_phase:
                self.current_phase = first_phase
                first_step = first_phase.steps.first()
                if first_step:
                    self.current_step = first_step
            self.save()
    
    def complete(self):
        """Mark framework as completed"""
        self.completed_at = timezone.now()
        self.progress_percent = 100.0
        self.save()
    
    def get_phase_progress(self):
        """Get progress for all phases"""
        phases = FrameworkPhase.objects.filter(framework=self.framework).order_by('order')
        progress_map = {
            pp.phase_id: pp 
            for pp in PhaseProgress.objects.filter(project_framework=self)
        }
        
        result = []
        for phase in phases:
            pp = progress_map.get(phase.id)
            result.append({
                'phase': phase,
                'is_complete': pp.is_complete if pp else False,
                'completed_at': pp.completed_at if pp else None,
                'notes': pp.notes if pp else '',
                'steps': self._get_step_progress(phase)
            })
        return result
    
    def _get_step_progress(self, phase):
        """Get progress for steps in a phase"""
        steps = FrameworkStep.objects.filter(phase=phase).order_by('order')
        progress_map = {
            sp.step_id: sp
            for sp in StepProgress.objects.filter(
                project_framework=self,
                step__phase=phase
            )
        }
        
        result = []
        for step in steps:
            sp = progress_map.get(step.id)
            result.append({
                'step': step,
                'is_complete': sp.is_complete if sp else False,
                'completed_at': sp.completed_at if sp else None,
                'notes': sp.notes if sp else '',
            })
        return result
    
    def update_progress(self):
        """Recalculate progress percentage"""
        total_steps = FrameworkStep.objects.filter(
            phase__framework=self.framework
        ).count()
        
        if total_steps == 0:
            self.progress_percent = 0
        else:
            completed = StepProgress.objects.filter(
                project_framework=self,
                is_complete=True
            ).count()
            self.progress_percent = (completed / total_steps) * 100
        
        self.save(update_fields=['progress_percent', 'updated_at'])


class PhaseProgress(models.Model):
    """Tracks completion of a phase for a specific project"""
    
    project_framework = models.ForeignKey(
        ProjectFramework,
        on_delete=models.CASCADE,
        related_name='phase_progress'
    )
    phase = models.ForeignKey(
        FrameworkPhase,
        on_delete=models.CASCADE
    )
    
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_phase_progress'
        unique_together = [['project_framework', 'phase']]
        verbose_name = 'Phase Progress'
        verbose_name_plural = 'Phase Progress'


class StepProgress(models.Model):
    """Tracks completion of a step for a specific project"""
    
    project_framework = models.ForeignKey(
        ProjectFramework,
        on_delete=models.CASCADE,
        related_name='step_progress'
    )
    step = models.ForeignKey(
        FrameworkStep,
        on_delete=models.CASCADE
    )
    
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    chapter_link = models.ForeignKey(
        'writing_hub.Chapter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to chapter implementing this step"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'graph_core'
        db_table = 'graph_core_step_progress'
        unique_together = [['project_framework', 'step']]
        verbose_name = 'Step Progress'
        verbose_name_plural = 'Step Progress'
