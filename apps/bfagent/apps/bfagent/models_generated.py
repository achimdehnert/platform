# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AgentExecutions(models.Model):
    project = models.ForeignKey("BookProjects", models.DO_NOTHING)
    agent = models.ForeignKey("Agents", models.DO_NOTHING)
    status = models.CharField()
    field_name = models.CharField()
    content_preview = models.CharField(blank=True, null=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "agent_executions"


class AgentProjectLinks(models.Model):
    pk = models.CompositePrimaryKey("agent_id", "project_id")
    agent = models.ForeignKey("Agents", models.DO_NOTHING)
    project = models.ForeignKey("BookProjects", models.DO_NOTHING)
    created_at = models.DateTimeField()
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "agent_project_links"


class AgentRecommendations(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    title = models.CharField()
    content = models.CharField()
    recommendation_type = models.CharField()
    priority = models.IntegerField()
    status = models.CharField()
    user_notes = models.CharField(blank=True, null=True)
    implementation_notes = models.CharField(blank=True, null=True)
    agent_used = models.CharField(blank=True, null=True)
    context_data = models.CharField(blank=True, null=True)
    project = models.ForeignKey("BookProjects", models.DO_NOTHING)
    agent = models.ForeignKey("Agents", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "agent_recommendations"


class Agents(models.Model):
    name = models.CharField()
    agent_type = models.CharField()
    status = models.CharField()
    description = models.CharField(blank=True, null=True)
    system_prompt = models.CharField()
    instructions = models.CharField(blank=True, null=True)
    llm_model_id = models.IntegerField(blank=True, null=True)
    creativity_level = models.TextField()  # This field type is a guess.
    consistency_weight = models.TextField()  # This field type is a guess.
    total_requests = models.IntegerField()
    successful_requests = models.IntegerField()
    average_response_time = models.TextField()  # This field type is a guess.
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    last_used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "agents"


class BookChapters(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    title = models.CharField()
    summary = models.CharField(blank=True, null=True)
    content = models.CharField(blank=True, null=True)
    chapter_number = models.IntegerField()
    status = models.CharField()
    word_count = models.IntegerField()
    target_word_count = models.IntegerField(blank=True, null=True)
    notes = models.CharField(blank=True, null=True)
    outline = models.CharField(blank=True, null=True)
    project = models.ForeignKey("BookProjects", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "book_chapters"


class BookCharacters(models.Model):
    book_project = models.ForeignKey("BookProjects", models.DO_NOTHING)
    character = models.ForeignKey("Characters", models.DO_NOTHING)
    role = models.TextField()
    importance_level = models.TextField(blank=True, null=True)
    character_arc = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    updated_at = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = "book_characters"


class BookProjects(models.Model):
    title = models.CharField()
    genre = models.CharField()
    content_rating = models.CharField()
    description = models.TextField(blank=True, null=True)
    tagline = models.CharField(blank=True, null=True)
    target_word_count = models.IntegerField()
    current_word_count = models.IntegerField()
    status = models.CharField()
    deadline = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    story_premise = models.TextField(blank=True, null=True)
    target_audience = models.CharField(blank=True, null=True)
    story_themes = models.CharField(blank=True, null=True)
    setting_time = models.CharField(blank=True, null=True)
    setting_location = models.CharField(blank=True, null=True)
    atmosphere_tone = models.CharField(blank=True, null=True)
    main_conflict = models.TextField(blank=True, null=True)
    stakes = models.CharField(blank=True, null=True)
    protagonist_concept = models.CharField(blank=True, null=True)
    antagonist_concept = models.CharField(blank=True, null=True)
    inspiration_sources = models.CharField(blank=True, null=True)
    unique_elements = models.CharField(blank=True, null=True)
    genre_settings = models.CharField(blank=True, null=True)
    book_type_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "book_projects"


class BookTypes(models.Model):
    name = models.CharField()
    description = models.CharField(blank=True, null=True)
    complexity = models.CharField()
    estimated_duration_hours = models.IntegerField(blank=True, null=True)
    target_word_count_min = models.IntegerField(blank=True, null=True)
    target_word_count_max = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    configuration = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "book_types"


class CharacterProjects(models.Model):
    character_id = models.IntegerField()
    book_project_id = models.IntegerField()
    project_specific_role = models.CharField(blank=True, null=True)
    project_notes = models.CharField(blank=True, null=True)
    importance_level = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "character_projects"


class Characters(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField()
    description = models.CharField(blank=True, null=True)
    role = models.CharField()
    age = models.IntegerField(blank=True, null=True)
    background = models.CharField(blank=True, null=True)
    personality = models.CharField(blank=True, null=True)
    appearance = models.CharField(blank=True, null=True)
    motivation = models.CharField(blank=True, null=True)
    conflict = models.CharField(blank=True, null=True)
    arc = models.CharField(blank=True, null=True)
    project = models.ForeignKey(BookProjects, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "characters"


class EnumTypes(models.Model):
    name = models.CharField(unique=True)
    description = models.CharField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "enum_types"


class EnumValues(models.Model):
    enum_type = models.ForeignKey(EnumTypes, models.DO_NOTHING)
    value = models.CharField()
    label = models.CharField()
    description = models.CharField(blank=True, null=True)
    metadata_json = models.CharField(blank=True, null=True)
    sort_order = models.IntegerField()
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "enum_values"


class FormDrafts(models.Model):
    project_id = models.IntegerField(blank=True, null=True)
    form_type = models.CharField()
    draft_data = models.TextField()  # This field type is a guess.
    session_key = models.CharField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "form_drafts"


class Llms(models.Model):
    name = models.CharField()
    provider = models.CharField()
    llm_name = models.CharField()
    api_key = models.CharField(blank=True, null=True)
    api_endpoint = models.CharField(blank=True, null=True)
    max_tokens = models.IntegerField()
    temperature = models.TextField()  # This field type is a guess.
    top_p = models.TextField()  # This field type is a guess.
    frequency_penalty = models.TextField()  # This field type is a guess.
    presence_penalty = models.TextField()  # This field type is a guess.
    total_tokens_used = models.IntegerField()
    total_requests = models.IntegerField()
    total_cost = models.TextField()  # This field type is a guess.
    cost_per_1k_tokens = models.TextField(blank=True, null=True)  # This field type is a guess.
    description = models.CharField(blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "llms"


class ProjectWorkflowContentCompletion(models.Model):
    project = models.ForeignKey(BookProjects, models.DO_NOTHING)
    workflow_content = models.ForeignKey("WorkflowStepContent", models.DO_NOTHING)
    is_completed = models.BooleanField()
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_by = models.CharField(blank=True, null=True)
    custom_title = models.CharField(blank=True, null=True)
    custom_content = models.CharField(blank=True, null=True)
    custom_notes = models.CharField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "project_workflow_content_completion"


class ProjectWorkflowStatus(models.Model):
    project = models.ForeignKey(BookProjects, models.DO_NOTHING)
    workflow_stage = models.CharField()
    status = models.CharField()
    progress_percentage = models.IntegerField()
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_by = models.CharField(blank=True, null=True)
    notes = models.CharField(blank=True, null=True)
    custom_content = models.CharField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    estimated_hours = models.TextField(blank=True, null=True)  # This field type is a guess.
    actual_hours = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = "project_workflow_status"


class ProjectWorkflows(models.Model):
    project = models.ForeignKey(BookProjects, models.DO_NOTHING)
    current_phase = models.TextField()
    status = models.TextField()
    created_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    started_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    completed_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    updated_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    total_tasks = models.IntegerField(blank=True, null=True)
    completed_tasks = models.IntegerField(blank=True, null=True)
    failed_tasks = models.IntegerField(blank=True, null=True)
    workflow_config = models.TextField(blank=True, null=True)
    completed_phases = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "project_workflows"


class Scenes(models.Model):
    chapter = models.ForeignKey(BookChapters, models.DO_NOTHING)
    book_project = models.ForeignKey(BookProjects, models.DO_NOTHING)
    scene_number = models.IntegerField()
    title = models.CharField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    summary = models.CharField(blank=True, null=True)
    word_count = models.IntegerField()
    setting = models.CharField(blank=True, null=True)
    characters_present = models.CharField(blank=True, null=True)
    purpose = models.CharField(blank=True, null=True)
    conflict = models.CharField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "scenes"


class StoryIdeas(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    title = models.CharField()
    content = models.CharField()
    idea_type = models.CharField()
    rating = models.IntegerField(blank=True, null=True)
    notes = models.CharField(blank=True, null=True)
    agent_used = models.CharField(blank=True, null=True)
    creativity_level = models.TextField(blank=True, null=True)  # This field type is a guess.
    project = models.ForeignKey(BookProjects, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "story_ideas"


class StructuredWorkflowTaskExecutions(models.Model):
    workflow_task = models.ForeignKey("StructuredWorkflowTasks", models.DO_NOTHING)
    project = models.ForeignKey(BookProjects, models.DO_NOTHING)
    agent = models.ForeignKey(Agents, models.DO_NOTHING, blank=True, null=True)
    execution_status = models.CharField()
    input_data = models.CharField(blank=True, null=True)
    output_data = models.CharField(blank=True, null=True)
    error_message = models.CharField(blank=True, null=True)
    tokens_used = models.IntegerField(blank=True, null=True)
    processing_time_seconds = models.TextField(blank=True, null=True)  # This field type is a guess.
    cost_estimate = models.TextField(blank=True, null=True)  # This field type is a guess.
    confidence_score = models.TextField(blank=True, null=True)  # This field type is a guess.
    quality_score = models.TextField(blank=True, null=True)  # This field type is a guess.
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    execution_metadata = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "structured_workflow_task_executions"


class StructuredWorkflowTasks(models.Model):
    workflow_phase = models.ForeignKey("WorkflowPhases", models.DO_NOTHING)
    agent = models.ForeignKey(Agents, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField()
    description = models.CharField()
    task_type = models.CharField()
    priority = models.CharField()
    configuration = models.CharField(blank=True, null=True)
    dependencies = models.CharField(blank=True, null=True)
    is_required = models.BooleanField()
    is_automated = models.BooleanField()
    estimated_duration_minutes = models.IntegerField(blank=True, null=True)
    status = models.CharField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "structured_workflow_tasks"


class Testmodel(models.Model):
    name = models.CharField()

    class Meta:
        managed = False
        db_table = "testmodel"


class UiStates(models.Model):
    session_key = models.CharField()
    state_type = models.CharField()
    state_data = models.TextField(blank=True, null=True)  # This field type is a guess.
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "ui_states"


class WorkflowExecutions(models.Model):
    workflow = models.ForeignKey(ProjectWorkflows, models.DO_NOTHING)
    task = models.ForeignKey("WorkflowTasks", models.DO_NOTHING, blank=True, null=True)
    execution_type = models.TextField()
    message = models.TextField()
    details = models.TextField(blank=True, null=True)
    timestamp = models.TextField(blank=True, null=True)  # This field type is a guess.
    agent_id = models.IntegerField(blank=True, null=True)
    phase = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "workflow_executions"


class WorkflowPhases(models.Model):
    name = models.CharField()
    description = models.CharField(blank=True, null=True)
    phase_type = models.CharField()
    book_type = models.ForeignKey(BookTypes, models.DO_NOTHING)
    order = models.IntegerField()
    is_required = models.BooleanField()
    can_run_parallel = models.BooleanField()
    agent = models.ForeignKey(Agents, models.DO_NOTHING, blank=True, null=True)
    estimated_duration_hours = models.IntegerField(blank=True, null=True)
    estimated_word_output = models.IntegerField(blank=True, null=True)
    configuration = models.CharField(blank=True, null=True)
    prompt_template = models.CharField(blank=True, null=True)
    dependencies = models.CharField(blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "workflow_phases"


class WorkflowPromptTemplates(models.Model):
    workflow_stage = models.CharField()
    template_key = models.CharField()
    template_name = models.CharField()
    prompt_template = models.CharField()
    system_prompt = models.CharField(blank=True, null=True)
    context_variables = models.CharField(blank=True, null=True)
    genre_type = models.CharField(blank=True, null=True)
    agent_type = models.CharField(blank=True, null=True)
    temperature = models.TextField(blank=True, null=True)  # This field type is a guess.
    max_tokens = models.IntegerField(blank=True, null=True)
    language = models.CharField()
    is_active = models.BooleanField()
    priority = models.IntegerField()
    version = models.CharField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    usage_count = models.IntegerField()
    last_used = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "workflow_prompt_templates"


class WorkflowStepConfigurations(models.Model):
    workflow_stage = models.CharField(unique=True)
    tab_configuration = models.CharField(blank=True, null=True)
    interface_type = models.CharField()
    default_agent_types = models.CharField(blank=True, null=True)
    execution_settings = models.CharField(blank=True, null=True)
    estimated_time = models.CharField(blank=True, null=True)
    difficulty_level = models.CharField(blank=True, null=True)
    enable_agent_execution = models.BooleanField()
    enable_prompt_preview = models.BooleanField()
    enable_result_saving = models.BooleanField()
    is_active = models.BooleanField()
    version = models.CharField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "workflow_step_configurations"


class WorkflowStepContent(models.Model):
    workflow_stage = models.CharField()
    content_type = models.CharField()
    content_key = models.CharField()
    title = models.CharField()
    content = models.CharField()
    description = models.CharField(blank=True, null=True)
    language = models.CharField()
    genre_type = models.CharField(blank=True, null=True)
    target_audience = models.CharField(blank=True, null=True)
    priority = models.IntegerField()
    is_active = models.BooleanField()
    version = models.CharField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    created_by = models.CharField(blank=True, null=True)
    updated_by = models.CharField(blank=True, null=True)
    extra_metadata = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "workflow_step_content"


class WorkflowTaskExecutions(models.Model):
    workflow_task = models.ForeignKey("WorkflowTasks", models.DO_NOTHING)
    project = models.ForeignKey(BookProjects, models.DO_NOTHING)
    agent = models.ForeignKey(Agents, models.DO_NOTHING, blank=True, null=True)
    execution_status = models.CharField()
    input_data = models.CharField(blank=True, null=True)
    output_data = models.CharField(blank=True, null=True)
    error_message = models.CharField(blank=True, null=True)
    tokens_used = models.IntegerField(blank=True, null=True)
    processing_time_seconds = models.TextField(blank=True, null=True)  # This field type is a guess.
    cost_estimate = models.TextField(blank=True, null=True)  # This field type is a guess.
    confidence_score = models.TextField(blank=True, null=True)  # This field type is a guess.
    quality_score = models.TextField(blank=True, null=True)  # This field type is a guess.
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    execution_metadata = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "workflow_task_executions"


class WorkflowTasks(models.Model):
    workflow = models.ForeignKey(ProjectWorkflows, models.DO_NOTHING)
    task_id = models.TextField()
    phase = models.TextField()
    agent_type = models.TextField()
    description = models.TextField()
    status = models.TextField()
    priority = models.IntegerField(blank=True, null=True)
    dependencies = models.TextField(blank=True, null=True)
    created_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    started_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    completed_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    result_data = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    execution_time_seconds = models.FloatField(blank=True, null=True)
    retry_count = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "workflow_tasks"


class WorkflowTemplateStageConfigs(models.Model):
    template = models.ForeignKey("WorkflowTemplates", models.DO_NOTHING)
    workflow_stage = models.CharField()
    is_enabled = models.BooleanField()
    is_optional = models.BooleanField()
    is_skippable = models.BooleanField()
    stage_order = models.IntegerField()
    prerequisites = models.CharField(blank=True, null=True)
    custom_title = models.CharField(blank=True, null=True)
    custom_description = models.CharField(blank=True, null=True)
    estimated_hours = models.TextField(blank=True, null=True)  # This field type is a guess.
    interface_type = models.CharField(blank=True, null=True)
    default_agent_types = models.CharField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "workflow_template_stage_configs"


class WorkflowTemplates(models.Model):
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    genre = models.TextField(blank=True, null=True)
    template_config = models.TextField()
    default_agents = models.TextField(blank=True, null=True)
    created_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    updated_at = models.TextField(blank=True, null=True)  # This field type is a guess.
    created_by = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    is_default = models.BooleanField(blank=True, null=True)
    template_name = models.TextField(blank=True, null=True)
    template_type = models.TextField(blank=True, null=True)
    complexity_level = models.TextField(blank=True, null=True)
    target_genres = models.TextField(blank=True, null=True)
    target_word_count_min = models.IntegerField(blank=True, null=True)
    target_word_count_max = models.IntegerField(blank=True, null=True)
    estimated_duration_days = models.IntegerField(blank=True, null=True)
    enabled_stages = models.TextField(blank=True, null=True)
    optional_stages = models.TextField(blank=True, null=True)
    stage_order = models.IntegerField(blank=True, null=True)
    version = models.TextField(blank=True, null=True)
    usage_count = models.IntegerField(blank=True, null=True)
    last_used = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = "workflow_templates"
