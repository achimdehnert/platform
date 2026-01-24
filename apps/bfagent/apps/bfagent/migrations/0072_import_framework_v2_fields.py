# Generated manually for Import Framework V2
# Migration adds new fields to BookProjects and Characters models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bfagent', '0071_book_series_models'),
    ]

    operations = [
        # BookProjects - Agent-Ready Project Definition
        migrations.AddField(
            model_name='bookprojects',
            name='project_definition_xml',
            field=models.TextField(blank=True, help_text='Agent-Ready Project Definition XML für LangGraph etc.', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='outline_template_code',
            field=models.CharField(blank=True, help_text='Code des verwendeten Outline-Templates', max_length=100, null=True),
        ),
        
        # BookProjects - Extended Story Metadata
        migrations.AddField(
            model_name='bookprojects',
            name='logline',
            field=models.TextField(blank=True, help_text='Ein-Satz-Zusammenfassung der Geschichte', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='central_question',
            field=models.TextField(blank=True, help_text='Die thematische Kernfrage des Werks', null=True),
        ),
        
        # BookProjects - Style Metadata
        migrations.AddField(
            model_name='bookprojects',
            name='narrative_voice',
            field=models.TextField(blank=True, help_text='Beschreibung der Erzählstimme', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='prose_style',
            field=models.TextField(blank=True, help_text='Beschreibung des Prosa-Stils', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='pacing_style',
            field=models.TextField(blank=True, help_text='Pacing/Tempo-Stil (straff, gemächlich, etc.)', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='dialogue_style',
            field=models.TextField(blank=True, help_text='Beschreibung des Dialog-Stils', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='comparable_titles',
            field=models.TextField(blank=True, help_text='Vergleichbare Bücher/Autoren (JSON oder kommasepariert)', null=True),
        ),
        
        # BookProjects - Genre-specific
        migrations.AddField(
            model_name='bookprojects',
            name='spice_level',
            field=models.CharField(blank=True, help_text='Explizitäts-Level für Romance (none, low, medium, high)', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='content_warnings',
            field=models.TextField(blank=True, help_text='Content Warnings/Trigger Warnings', null=True),
        ),
        
        # BookProjects - Series Context
        migrations.AddField(
            model_name='bookprojects',
            name='series_arc',
            field=models.TextField(blank=True, help_text='Übergreifender Serien-Arc (für mehrbändige Werke)', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='threads_to_continue',
            field=models.TextField(blank=True, help_text='Offene Handlungsstränge für Folgebände (JSON)', null=True),
        ),
        
        # BookProjects - Consistency Rules
        migrations.AddField(
            model_name='bookprojects',
            name='consistency_rules',
            field=models.TextField(blank=True, help_text='Projekt-spezifische Konsistenz-Regeln (JSON)', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='forbidden_elements',
            field=models.TextField(blank=True, help_text='Was NICHT im Buch vorkommen darf (JSON)', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='required_elements',
            field=models.TextField(blank=True, help_text='Was im Buch vorkommen MUSS (JSON)', null=True),
        ),
        migrations.AddField(
            model_name='bookprojects',
            name='agent_instructions',
            field=models.TextField(blank=True, help_text='Spezifische Anweisungen für Writing-Agents', null=True),
        ),
        
        # Characters - Psychological Depth
        migrations.AddField(
            model_name='characters',
            name='wound',
            field=models.TextField(blank=True, help_text='Innere Verletzung/Trauma des Charakters', null=True),
        ),
        migrations.AddField(
            model_name='characters',
            name='secret',
            field=models.TextField(blank=True, help_text='Verborgenes Geheimnis des Charakters', null=True),
        ),
        migrations.AddField(
            model_name='characters',
            name='dark_trait',
            field=models.TextField(blank=True, help_text='Dunkle Seite/Schattenseite (für Dark Romance etc.)', null=True),
        ),
        
        # Characters - Strengths & Weaknesses
        migrations.AddField(
            model_name='characters',
            name='strengths',
            field=models.TextField(blank=True, help_text='Hauptstärken des Charakters (JSON oder kommasepariert)', null=True),
        ),
        migrations.AddField(
            model_name='characters',
            name='weaknesses',
            field=models.TextField(blank=True, help_text='Hauptschwächen des Charakters (JSON oder kommasepariert)', null=True),
        ),
        
        # Characters - Voice & Expression
        migrations.AddField(
            model_name='characters',
            name='voice_sample',
            field=models.TextField(blank=True, help_text='Beispiel-Dialog, der die Stimme des Charakters zeigt', null=True),
        ),
        migrations.AddField(
            model_name='characters',
            name='speech_patterns',
            field=models.TextField(blank=True, help_text='Sprachmuster, typische Ausdrücke, Dialekt', null=True),
        ),
        
        # Characters - Occupation & Status
        migrations.AddField(
            model_name='characters',
            name='occupation',
            field=models.CharField(blank=True, help_text='Beruf/Tätigkeit des Charakters', max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='characters',
            name='organization',
            field=models.CharField(blank=True, help_text='Organisation/Firma des Charakters', max_length=200, null=True),
        ),
        
        # Characters - Structured Relationships
        migrations.AddField(
            model_name='characters',
            name='relationships_json',
            field=models.JSONField(blank=True, help_text="Strukturierte Beziehungen: [{to: 'Name', type: 'love_interest'}]", null=True),
        ),
        
        # Characters - Importance
        migrations.AddField(
            model_name='characters',
            name='importance',
            field=models.PositiveIntegerField(default=3, help_text='Wichtigkeit 1-5 (1=Protagonist, 5=Minor)'),
        ),
        
        # Characters - Origin
        migrations.AddField(
            model_name='characters',
            name='nationality',
            field=models.CharField(blank=True, help_text='Nationalität des Charakters', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='characters',
            name='ethnicity',
            field=models.CharField(blank=True, help_text='Ethnische Herkunft des Charakters', max_length=100, null=True),
        ),
    ]
