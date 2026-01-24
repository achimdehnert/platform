from django.contrib import admin
from .models import Initiative, Requirement, Feedback


class FeedbackInline(admin.TabularInline):
    model = Feedback
    extra = 0
    readonly_fields = ['created_by', 'created_at']


class RequirementInline(admin.TabularInline):
    model = Requirement
    extra = 0
    fields = ['title', 'status', 'category', 'priority']
    show_change_link = True


@admin.register(Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    list_display = ['title', 'domain', 'status', 'priority', 'created_at']
    list_filter = ['status', 'domain', 'priority']
    search_fields = ['title', 'description']
    inlines = [RequirementInline]


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ['title', 'initiative', 'status', 'category', 'priority', 'created_at']
    list_filter = ['status', 'category', 'priority']
    search_fields = ['title', 'description']
    inlines = [FeedbackInline]
    raw_id_fields = ['initiative', 'created_by', 'assigned_to']
