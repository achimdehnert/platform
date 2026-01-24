"""
Style System Admin
==================

Admin interface for Style Generation & Adoption System (SGAS).
"""

from django.contrib import admin

from .models_style import (
    AuthorStyleDNA,
    StyleLabSession,
    StyleObservation,
    StyleCandidate,
    StyleFeedback,
    StyleAcceptanceTest,
    StyleAdoption,
    Author,
    WritingStyle,
    ProjectAuthor,
)


# =============================================================================
# AUTHOR STYLE DNA ADMIN
# =============================================================================

class StyleAcceptanceTestInline(admin.TabularInline):
    """Inline für Acceptance Tests"""
    model = StyleAcceptanceTest
    extra = 0
    fields = ['name', 'test_type', 'severity', 'is_active']


class StyleAdoptionInline(admin.TabularInline):
    """Inline für Style Adoptions"""
    model = StyleAdoption
    extra = 0
    fields = ['author', 'project', 'role', 'can_modify', 'is_active']
    readonly_fields = ['adopted_at']


@admin.register(AuthorStyleDNA)
class AuthorStyleDNAAdmin(admin.ModelAdmin):
    """Admin für Author Style DNA"""
    list_display = [
        'name',
        'author',
        'version',
        'is_primary',
        'status',
        'updated_at'
    ]
    list_filter = ['status', 'is_primary', 'author']
    search_fields = ['name', 'author__username']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [StyleAcceptanceTestInline, StyleAdoptionInline]
    
    fieldsets = (
        ('Grundinfo', {
            'fields': ('author', 'name', 'version', 'is_primary', 'status')
        }),
        ('Signature Moves', {
            'fields': ('signature_moves',),
            'classes': ('collapse',)
        }),
        ('Do / Don\'t Listen', {
            'fields': ('do_list', 'dont_list', 'taboo_list'),
            'classes': ('collapse',)
        }),
        ('Rhythm & Lens', {
            'fields': ('rhythm_profile', 'lens_profile'),
            'classes': ('collapse',)
        }),
        ('Dialogue & Imagery', {
            'fields': ('dialogue_profile', 'imagery_profile'),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_production_ready', 'create_new_version']
    
    @admin.action(description="Als produktionsreif markieren")
    def mark_production_ready(self, request, queryset):
        updated = queryset.update(status=AuthorStyleDNA.Status.PRODUCTION_READY)
        self.message_user(request, f"{updated} Stile als produktionsreif markiert.")
    
    @admin.action(description="Neue Version erstellen")
    def create_new_version(self, request, queryset):
        for dna in queryset:
            new_dna = dna.create_new_version()
            self.message_user(request, f"Neue Version {new_dna.version} von '{dna.name}' erstellt.")


# =============================================================================
# STYLE LAB SESSION ADMIN
# =============================================================================

class StyleObservationInline(admin.TabularInline):
    """Inline für Observations"""
    model = StyleObservation
    extra = 0
    fields = ['source_name', 'source_type', 'analyzed_at']
    readonly_fields = ['analyzed_at']


class StyleCandidateInline(admin.TabularInline):
    """Inline für Candidates"""
    model = StyleCandidate
    extra = 0
    fields = ['scene_type', 'generated_at', 'tokens_used']
    readonly_fields = ['generated_at']


@admin.register(StyleLabSession)
class StyleLabSessionAdmin(admin.ModelAdmin):
    """Admin für Style Lab Sessions"""
    list_display = [
        'name',
        'author',
        'purpose',
        'current_phase',
        'target_dna',
        'started_at'
    ]
    list_filter = ['current_phase', 'purpose', 'author']
    search_fields = ['name', 'author__username']
    readonly_fields = ['started_at', 'completed_at']
    autocomplete_fields = ['author', 'target_dna', 'project']
    inlines = [StyleObservationInline, StyleCandidateInline]
    
    fieldsets = (
        ('Session', {
            'fields': ('name', 'author', 'purpose', 'current_phase')
        }),
        ('Ziel', {
            'fields': ('target_dna', 'project', 'target_genres')
        }),
        ('Zeitstempel', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['advance_phase']
    
    @admin.action(description="Zur nächsten Phase")
    def advance_phase(self, request, queryset):
        phase_order = ['init', 'extraction', 'synthesis', 'feedback', 'fixation', 'completed']
        for session in queryset:
            current_idx = phase_order.index(session.current_phase)
            if current_idx < len(phase_order) - 1:
                session.current_phase = phase_order[current_idx + 1]
                session.save()
                self.message_user(request, f"'{session.name}' → {session.current_phase}")


# =============================================================================
# STYLE OBSERVATION ADMIN
# =============================================================================

@admin.register(StyleObservation)
class StyleObservationAdmin(admin.ModelAdmin):
    """Admin für Style Observations"""
    list_display = [
        'source_name',
        'session',
        'source_type',
        'analyzed_at'
    ]
    list_filter = ['source_type', 'session']
    search_fields = ['source_name', 'session__name']
    readonly_fields = ['analyzed_at']
    
    fieldsets = (
        ('Quelle', {
            'fields': ('session', 'source_name', 'source_type')
        }),
        ('Text', {
            'fields': ('source_text',)
        }),
        ('Analyse', {
            'fields': ('observations', 'contradictions', 'metrics'),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': ('analyzed_at', 'llm_used'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# STYLE CANDIDATE ADMIN
# =============================================================================

class StyleFeedbackInline(admin.TabularInline):
    """Inline für Feedback"""
    model = StyleFeedback
    extra = 0
    fields = ['rating', 'given_by', 'given_at']
    readonly_fields = ['given_at']


@admin.register(StyleCandidate)
class StyleCandidateAdmin(admin.ModelAdmin):
    """Admin für Style Candidates"""
    list_display = [
        'scene_type',
        'session',
        'generated_at',
        'tokens_used'
    ]
    list_filter = ['scene_type', 'session']
    search_fields = ['session__name']
    readonly_fields = ['generated_at']
    inlines = [StyleFeedbackInline]
    
    fieldsets = (
        ('Szene', {
            'fields': ('session', 'scene_type', 'scene_prompt')
        }),
        ('Generierter Text', {
            'fields': ('generated_text', 'used_features')
        }),
        ('Metadaten', {
            'fields': ('generated_at', 'llm_used', 'tokens_used'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# STYLE FEEDBACK ADMIN
# =============================================================================

@admin.register(StyleFeedback)
class StyleFeedbackAdmin(admin.ModelAdmin):
    """Admin für Style Feedback"""
    list_display = [
        'candidate',
        'rating',
        'given_by',
        'given_at'
    ]
    list_filter = ['rating', 'given_by']
    search_fields = ['candidate__session__name', 'general_comment']
    readonly_fields = ['given_at']
    
    fieldsets = (
        ('Bewertung', {
            'fields': ('candidate', 'rating', 'given_by')
        }),
        ('Patterns', {
            'fields': ('accepted_patterns', 'rejected_patterns'),
            'classes': ('collapse',)
        }),
        ('Edits & Kommentare', {
            'fields': ('author_edits', 'general_comment'),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': ('given_at',),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# STYLE ACCEPTANCE TEST ADMIN
# =============================================================================

@admin.register(StyleAcceptanceTest)
class StyleAcceptanceTestAdmin(admin.ModelAdmin):
    """Admin für Style Acceptance Tests"""
    list_display = [
        'name',
        'style_dna',
        'test_type',
        'severity',
        'is_active'
    ]
    list_filter = ['test_type', 'severity', 'is_active']
    search_fields = ['name', 'style_dna__name']
    list_editable = ['severity', 'is_active']
    
    fieldsets = (
        ('Test', {
            'fields': ('style_dna', 'name', 'test_type', 'severity', 'is_active')
        }),
        ('Konfiguration', {
            'fields': ('test_config',)
        }),
    )


# =============================================================================
# STYLE ADOPTION ADMIN
# =============================================================================

@admin.register(StyleAdoption)
class StyleAdoptionAdmin(admin.ModelAdmin):
    """Admin für Style Adoptions"""
    list_display = [
        'author',
        'style_dna',
        'project',
        'role',
        'can_modify',
        'is_active'
    ]
    list_filter = ['role', 'is_active', 'can_modify']
    search_fields = ['author__username', 'style_dna__name', 'project__title']
    list_editable = ['role', 'can_modify', 'is_active']
    autocomplete_fields = ['author', 'style_dna', 'project']
    readonly_fields = ['adopted_at']
    
    fieldsets = (
        ('Zuweisung', {
            'fields': ('author', 'style_dna', 'project')
        }),
        ('Optionen', {
            'fields': ('role', 'can_modify', 'is_active')
        }),
        ('Metadaten', {
            'fields': ('adopted_at',),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# AUTHOR & WRITING STYLE ADMIN (für externe Autoren)
# =============================================================================

class WritingStyleInline(admin.TabularInline):
    """Inline für Writing Styles eines Autors"""
    model = WritingStyle
    extra = 1
    fields = ['name', 'is_default', 'default_pov', 'default_tense', 'llm', 'is_active']
    show_change_link = True


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    """Admin für externe Autoren (z.B. Freida McFadden)"""
    list_display = [
        'name',
        'genres_display',
        'styles_count',
        'is_public',
        'is_active',
        'created_by',
        'created_at'
    ]
    list_filter = ['is_public', 'is_active', 'genres']
    search_fields = ['name', 'bio']
    list_editable = ['is_public', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [WritingStyleInline]
    
    fieldsets = (
        ('Autor', {
            'fields': ('name', 'bio', 'genres', 'avatar_url')
        }),
        ('Sichtbarkeit', {
            'fields': ('is_public', 'is_active', 'created_by')
        }),
        ('Metadaten', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def genres_display(self, obj):
        return ", ".join(obj.genres) if obj.genres else "-"
    genres_display.short_description = "Genres"
    
    def styles_count(self, obj):
        return obj.writing_styles.count()
    styles_count.short_description = "Stile"


@admin.register(WritingStyle)
class WritingStyleAdmin(admin.ModelAdmin):
    """Admin für Schreibstile"""
    list_display = [
        'name',
        'author',
        'is_default',
        'default_pov',
        'default_tense',
        'llm',
        'temperature',
        'is_active'
    ]
    list_filter = ['is_default', 'is_active', 'default_pov', 'default_tense', 'author']
    search_fields = ['name', 'author__name', 'description']
    list_editable = ['is_default', 'is_active']
    autocomplete_fields = ['author', 'llm']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Grundlagen', {
            'fields': ('author', 'name', 'description', 'is_default', 'is_active')
        }),
        ('LLM Konfiguration', {
            'fields': ('llm', 'temperature', 'max_tokens')
        }),
        ('Stil-Prompts', {
            'fields': ('system_prompt', 'style_instructions'),
            'classes': ('wide',)
        }),
        ('Do / Don\'t Listen', {
            'fields': ('do_list', 'dont_list', 'taboo_words'),
            'classes': ('collapse',)
        }),
        ('Beispieltexte', {
            'fields': ('example_texts',),
            'classes': ('collapse',)
        }),
        ('POV & Zeitform', {
            'fields': ('default_pov', 'default_tense')
        }),
        ('Metadaten', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProjectAuthor)
class ProjectAuthorAdmin(admin.ModelAdmin):
    """Admin für Projekt-Autor Zuweisungen"""
    list_display = [
        'project',
        'author',
        'writing_style',
        'is_primary',
        'order',
        'created_at'
    ]
    list_filter = ['is_primary', 'author', 'writing_style']
    search_fields = ['project__title', 'author__name']
    list_editable = ['is_primary', 'order']
    autocomplete_fields = ['project', 'author', 'writing_style']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Zuweisung', {
            'fields': ('project', 'author', 'writing_style')
        }),
        ('Optionen', {
            'fields': ('is_primary', 'order')
        }),
        ('Metadaten', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
