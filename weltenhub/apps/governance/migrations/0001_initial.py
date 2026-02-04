# Generated manually for ADR-017 DDL Governance
# Creates all DDL models in the 'platform' schema

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # =======================================================================
        # LOOKUP TABLES
        # =======================================================================
        migrations.CreateModel(
            name='LookupDomain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text="Machine-readable code (e.g., 'bc_status')", max_length=50, unique=True)),
                ('name', models.CharField(help_text='English display name', max_length=100)),
                ('name_de', models.CharField(blank=True, help_text='German display name', max_length=100)),
                ('description', models.TextField(blank=True, help_text='Description of this domain')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Lookup Domain',
                'verbose_name_plural': 'Lookup Domains',
                'db_table': 'platform"."lkp_domain',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='LookupChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text="Machine-readable code (e.g., 'draft')", max_length=50)),
                ('name', models.CharField(help_text='English display name', max_length=100)),
                ('name_de', models.CharField(blank=True, help_text='German display name', max_length=100)),
                ('description', models.TextField(blank=True)),
                ('sort_order', models.IntegerField(db_index=True, default=0)),
                ('color', models.CharField(default='#3498db', help_text='Color for UI (hex)', max_length=7)),
                ('icon', models.CharField(blank=True, help_text="Icon class (e.g., 'bi-check')", max_length=50)),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata as JSON')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('domain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='choices', to='governance.lookupdomain', verbose_name='Domain')),
            ],
            options={
                'verbose_name': 'Lookup Choice',
                'verbose_name_plural': 'Lookup Choices',
                'db_table': 'platform"."lkp_choice',
                'ordering': ['domain', 'sort_order', 'code'],
            },
        ),
        migrations.AddConstraint(
            model_name='lookupchoice',
            constraint=models.UniqueConstraint(fields=('domain', 'code'), name='governance_lookupchoice_domain_code_unique'),
        ),
        migrations.AddIndex(
            model_name='lookupchoice',
            index=models.Index(fields=['domain', 'is_active'], name='governance_lkpchoice_domain_active_idx'),
        ),

        # =======================================================================
        # BUSINESS CASE
        # =======================================================================
        migrations.CreateModel(
            name='BusinessCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(help_text="Unique code (e.g., 'BC-042')", max_length=20, unique=True)),
                ('title', models.CharField(help_text='Short descriptive title', max_length=200)),
                ('problem_statement', models.TextField(help_text='What problem does this solve?')),
                ('target_audience', models.TextField(blank=True, help_text='Who benefits from this?')),
                ('expected_benefits', models.JSONField(blank=True, default=list, help_text='List of expected benefits')),
                ('scope', models.TextField(blank=True, help_text="What's included?")),
                ('out_of_scope', models.JSONField(blank=True, default=list, help_text="What's explicitly excluded?")),
                ('success_criteria', models.JSONField(blank=True, default=list, help_text='Measurable success criteria')),
                ('assumptions', models.JSONField(blank=True, default=list)),
                ('risks', models.JSONField(blank=True, default=list, help_text='List of risk objects with description, probability, impact')),
                ('requires_adr', models.BooleanField(default=False, help_text='Does this require an ADR?')),
                ('adr_reason', models.TextField(blank=True, help_text='Why is an ADR required?')),
                ('category', models.ForeignKey(limit_choices_to={'domain__code': 'bc_category'}, on_delete=django.db.models.deletion.PROTECT, related_name='business_cases_by_category', to='governance.lookupchoice', verbose_name='Category')),
                ('priority', models.ForeignKey(blank=True, limit_choices_to={'domain__code': 'bc_priority'}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='business_cases_by_priority', to='governance.lookupchoice', verbose_name='Priority')),
                ('status', models.ForeignKey(limit_choices_to={'domain__code': 'bc_status'}, on_delete=django.db.models.deletion.PROTECT, related_name='business_cases_by_status', to='governance.lookupchoice', verbose_name='Status')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_business_cases', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Business Case',
                'verbose_name_plural': 'Business Cases',
                'db_table': 'platform"."dom_business_case',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='businesscase',
            index=models.Index(fields=['status'], name='governance_bc_status_idx'),
        ),
        migrations.AddIndex(
            model_name='businesscase',
            index=models.Index(fields=['category'], name='governance_bc_category_idx'),
        ),
        migrations.AddIndex(
            model_name='businesscase',
            index=models.Index(fields=['code'], name='governance_bc_code_idx'),
        ),

        # =======================================================================
        # USE CASE
        # =======================================================================
        migrations.CreateModel(
            name='UseCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(help_text="Unique code (e.g., 'UC-042-01')", max_length=20, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('actor', models.CharField(help_text="Primary actor (e.g., 'Registered User')", max_length=100)),
                ('preconditions', models.JSONField(blank=True, default=list)),
                ('postconditions', models.JSONField(blank=True, default=list)),
                ('main_flow', models.JSONField(blank=True, default=list, help_text='Main success scenario steps')),
                ('alternative_flows', models.JSONField(blank=True, default=list)),
                ('exception_flows', models.JSONField(blank=True, default=list)),
                ('estimated_effort', models.CharField(blank=True, help_text="e.g., '3-5 days'", max_length=50)),
                ('business_case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='use_cases', to='governance.businesscase')),
                ('complexity', models.ForeignKey(blank=True, limit_choices_to={'domain__code': 'uc_complexity'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='use_cases_by_complexity', to='governance.lookupchoice')),
                ('priority', models.ForeignKey(blank=True, limit_choices_to={'domain__code': 'uc_priority'}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='use_cases_by_priority', to='governance.lookupchoice')),
                ('status', models.ForeignKey(limit_choices_to={'domain__code': 'uc_status'}, on_delete=django.db.models.deletion.PROTECT, related_name='use_cases_by_status', to='governance.lookupchoice')),
            ],
            options={
                'verbose_name': 'Use Case',
                'verbose_name_plural': 'Use Cases',
                'db_table': 'platform"."dom_use_case',
                'ordering': ['business_case', 'code'],
            },
        ),
        migrations.AddIndex(
            model_name='usecase',
            index=models.Index(fields=['business_case'], name='governance_uc_bc_idx'),
        ),
        migrations.AddIndex(
            model_name='usecase',
            index=models.Index(fields=['status'], name='governance_uc_status_idx'),
        ),

        # =======================================================================
        # ADR
        # =======================================================================
        migrations.CreateModel(
            name='ADR',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(help_text="e.g., 'ADR-017'", max_length=20, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('context', models.TextField(help_text='What is the context and problem?')),
                ('decision', models.TextField(help_text='What is the decision?')),
                ('consequences', models.TextField(blank=True, help_text='What are the consequences?')),
                ('alternatives', models.JSONField(blank=True, default=list, help_text='Considered alternatives')),
                ('file_path', models.CharField(blank=True, help_text='Path to ADR markdown file', max_length=500)),
                ('status', models.ForeignKey(limit_choices_to={'domain__code': 'adr_status'}, on_delete=django.db.models.deletion.PROTECT, related_name='adrs_by_status', to='governance.lookupchoice')),
                ('supersedes', models.ForeignKey(blank=True, help_text='Previous ADR this supersedes', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='superseded_by', to='governance.adr')),
            ],
            options={
                'verbose_name': 'ADR',
                'verbose_name_plural': 'ADRs',
                'db_table': 'platform"."dom_adr',
                'ordering': ['code'],
            },
        ),
        migrations.AddIndex(
            model_name='adr',
            index=models.Index(fields=['status'], name='governance_adr_status_idx'),
        ),

        # =======================================================================
        # ADR-USE CASE LINK
        # =======================================================================
        migrations.CreateModel(
            name='ADRUseCaseLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notes', models.TextField(blank=True)),
                ('adr', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='use_case_links', to='governance.adr')),
                ('use_case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='adr_links', to='governance.usecase')),
                ('relationship_type', models.ForeignKey(help_text='implements, affects, or references', limit_choices_to={'domain__code': 'adr_uc_relationship'}, on_delete=django.db.models.deletion.PROTECT, related_name='adr_use_case_links', to='governance.lookupchoice')),
            ],
            options={
                'verbose_name': 'ADR-Use Case Link',
                'verbose_name_plural': 'ADR-Use Case Links',
                'db_table': 'platform"."dom_adr_use_case',
            },
        ),
        migrations.AddConstraint(
            model_name='adrusecaselink',
            constraint=models.UniqueConstraint(fields=('adr', 'use_case'), name='governance_adruclink_adr_uc_unique'),
        ),

        # =======================================================================
        # CONVERSATION
        # =======================================================================
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session_id', models.CharField(help_text='Unique session identifier', max_length=100, unique=True)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('business_case', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='governance.businesscase')),
                ('started_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('status', models.ForeignKey(limit_choices_to={'domain__code': 'conversation_status'}, on_delete=django.db.models.deletion.PROTECT, related_name='conversations_by_status', to='governance.lookupchoice')),
            ],
            options={
                'verbose_name': 'Conversation',
                'verbose_name_plural': 'Conversations',
                'db_table': 'platform"."dom_conversation',
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='ConversationTurn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('turn_number', models.PositiveIntegerField()),
                ('content', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Token usage, model info, etc.')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='turns', to='governance.conversation')),
                ('role', models.ForeignKey(help_text='user, assistant, or system', limit_choices_to={'domain__code': 'conversation_role'}, on_delete=django.db.models.deletion.PROTECT, related_name='conversation_turns_by_role', to='governance.lookupchoice')),
            ],
            options={
                'verbose_name': 'Conversation Turn',
                'verbose_name_plural': 'Conversation Turns',
                'db_table': 'platform"."dom_conversation_turn',
                'ordering': ['conversation', 'turn_number'],
            },
        ),
        migrations.AddConstraint(
            model_name='conversationturn',
            constraint=models.UniqueConstraint(fields=('conversation', 'turn_number'), name='governance_convturn_conv_num_unique'),
        ),

        # =======================================================================
        # REVIEW
        # =======================================================================
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('entity_id', models.BigIntegerField(help_text='ID of the reviewed entity')),
                ('comments', models.TextField(blank=True)),
                ('requested_changes', models.JSONField(blank=True, default=list)),
                ('decision', models.ForeignKey(help_text='approved, rejected, or changes_requested', limit_choices_to={'domain__code': 'review_decision'}, on_delete=django.db.models.deletion.PROTECT, related_name='reviews_by_decision', to='governance.lookupchoice')),
                ('entity_type', models.ForeignKey(help_text='business_case, use_case, or adr', limit_choices_to={'domain__code': 'review_entity_type'}, on_delete=django.db.models.deletion.PROTECT, related_name='reviews_by_entity_type', to='governance.lookupchoice')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Review',
                'verbose_name_plural': 'Reviews',
                'db_table': 'platform"."dom_review',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='review',
            index=models.Index(fields=['entity_type', 'entity_id'], name='governance_review_entity_idx'),
        ),
        migrations.AddIndex(
            model_name='review',
            index=models.Index(fields=['reviewer'], name='governance_review_reviewer_idx'),
        ),

        # =======================================================================
        # STATUS HISTORY (Audit Trail)
        # =======================================================================
        migrations.CreateModel(
            name='StatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('entity_id', models.BigIntegerField()),
                ('reason', models.TextField(blank=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='status_changes', to=settings.AUTH_USER_MODEL)),
                ('entity_type', models.ForeignKey(limit_choices_to={'domain__code': 'review_entity_type'}, on_delete=django.db.models.deletion.PROTECT, related_name='status_history_by_entity_type', to='governance.lookupchoice')),
                ('new_status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='status_history_new', to='governance.lookupchoice')),
                ('old_status', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='status_history_old', to='governance.lookupchoice')),
            ],
            options={
                'verbose_name': 'Status History',
                'verbose_name_plural': 'Status Histories',
                'db_table': 'platform"."dom_status_history',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='statushistory',
            index=models.Index(fields=['entity_type', 'entity_id'], name='governance_statushist_entity_idx'),
        ),
        migrations.AddIndex(
            model_name='statushistory',
            index=models.Index(fields=['created_at'], name='governance_statushist_created_idx'),
        ),
    ]
