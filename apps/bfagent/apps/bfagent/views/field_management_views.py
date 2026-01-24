"""
User-facing views for managing custom fields
Allows users to create/edit/view custom field definitions
"""

from django.contrib import messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..models import (
    FieldDefinition,
    FieldGroup,
    ProjectFieldValue,
    BookProjects,
    FieldTemplate,
)


# ============================================================================
# FIELD DEFINITION MANAGEMENT
# ============================================================================


def field_definition_list(request):
    """List all field definitions grouped by target model"""
    
    # Get filter parameters
    target_model = request.GET.get("target_model", "all")
    group_id = request.GET.get("group", "all")
    search = request.GET.get("search", "")
    
    # Base queryset
    fields = FieldDefinition.objects.filter(is_active=True).select_related("group")
    
    # Apply filters
    if target_model != "all":
        fields = fields.filter(target_model=target_model)
    
    if group_id != "all":
        fields = fields.filter(group_id=group_id)
    
    if search:
        fields = fields.filter(
            models.Q(name__icontains=search) |
            models.Q(display_name__icontains=search) |
            models.Q(description__icontains=search)
        )
    
    # Group by target model
    grouped_fields = {}
    for field in fields:
        if field.target_model not in grouped_fields:
            grouped_fields[field.target_model] = []
        grouped_fields[field.target_model].append(field)
    
    # Get all groups for filter
    groups = FieldGroup.objects.filter(is_active=True).order_by("order")
    
    context = {
        "grouped_fields": grouped_fields,
        "groups": groups,
        "target_model": target_model,
        "group_id": group_id,
        "search": search,
    }
    
    return render(request, "bfagent/field_management/field_list.html", context)


def field_definition_create(request):
    """Create a new field definition"""
    
    if request.method == "POST":
        try:
            field = FieldDefinition.objects.create(
                name=request.POST["name"],
                display_name=request.POST["display_name"],
                description=request.POST.get("description", ""),
                field_type=request.POST["field_type"],
                target_model=request.POST["target_model"],
                group_id=request.POST.get("group") if request.POST.get("group") else None,
                placeholder=request.POST.get("placeholder", ""),
                help_text=request.POST.get("help_text", ""),
                is_ai_enrichable=request.POST.get("is_ai_enrichable") == "on",
                ai_prompt_template=request.POST.get("ai_prompt_template", ""),
                is_required=request.POST.get("is_required") == "on",
                created_by=request.user if request.user.is_authenticated else None,
            )
            
            messages.success(request, f"✅ Field '{field.display_name}' created successfully!")
            return redirect("bfagent:field-definition-list")
            
        except Exception as e:
            messages.error(request, f"❌ Error creating field: {str(e)}")
    
    # GET: Show form
    groups = FieldGroup.objects.filter(is_active=True).order_by("order")
    
    context = {
        "groups": groups,
        "field_types": FieldDefinition.FIELD_TYPE_CHOICES,
        "target_models": FieldDefinition.TARGET_MODEL_CHOICES,
    }
    
    return render(request, "bfagent/field_management/field_form.html", context)


def field_definition_edit(request, pk):
    """Edit an existing field definition"""
    
    field = get_object_or_404(FieldDefinition, pk=pk)
    
    if request.method == "POST":
        try:
            field.display_name = request.POST["display_name"]
            field.description = request.POST.get("description", "")
            field.field_type = request.POST["field_type"]
            field.target_model = request.POST["target_model"]
            field.group_id = request.POST.get("group") if request.POST.get("group") else None
            field.placeholder = request.POST.get("placeholder", "")
            field.help_text = request.POST.get("help_text", "")
            field.is_ai_enrichable = request.POST.get("is_ai_enrichable") == "on"
            field.ai_prompt_template = request.POST.get("ai_prompt_template", "")
            field.is_required = request.POST.get("is_required") == "on"
            field.is_active = request.POST.get("is_active") == "on"
            field.save()
            
            messages.success(request, f"✅ Field '{field.display_name}' updated successfully!")
            return redirect("bfagent:field-definition-list")
            
        except Exception as e:
            messages.error(request, f"❌ Error updating field: {str(e)}")
    
    # GET: Show form
    groups = FieldGroup.objects.filter(is_active=True).order_by("order")
    
    context = {
        "field": field,
        "groups": groups,
        "field_types": FieldDefinition.FIELD_TYPE_CHOICES,
        "target_models": FieldDefinition.TARGET_MODEL_CHOICES,
    }
    
    return render(request, "bfagent/field_management/field_form.html", context)


def field_definition_delete(request, pk):
    """Soft delete a field definition"""
    
    if request.method == "POST":
        field = get_object_or_404(FieldDefinition, pk=pk)
        field.is_active = False
        field.save()
        
        messages.success(request, f"✅ Field '{field.display_name}' deactivated")
        return redirect("bfagent:field-definition-list")
    
    return redirect("bfagent:field-definition-list")


# ============================================================================
# PROJECT FIELD VALUES (User's actual data)
# ============================================================================


def project_field_values(request, pk):
    """View and edit custom field values for a project"""
    
    project = get_object_or_404(BookProjects, pk=pk)
    
    # Get all active field definitions for projects
    field_definitions = FieldDefinition.objects.filter(
        target_model="project",
        is_active=True
    ).select_related("group").order_by("group__order", "order")
    
    # Get existing values
    existing_values = {
        fv.field_definition_id: fv
        for fv in ProjectFieldValue.objects.filter(project=project).select_related("field_definition")
    }
    
    # Organize fields by group
    grouped_fields = {}
    for field_def in field_definitions:
        group_name = field_def.group.display_name if field_def.group else "Other"
        if group_name not in grouped_fields:
            grouped_fields[group_name] = []
        
        field_value = existing_values.get(field_def.id)
        grouped_fields[group_name].append({
            "definition": field_def,
            "value": field_value.get_value() if field_value else None,
            "value_obj": field_value,
        })
    
    context = {
        "project": project,
        "grouped_fields": grouped_fields,
    }
    
    return render(request, "bfagent/field_management/project_fields.html", context)


@require_http_methods(["POST"])
def project_field_value_save(request, pk, field_id):
    """Save a custom field value for a project"""
    
    project = get_object_or_404(BookProjects, pk=pk)
    field_definition = get_object_or_404(FieldDefinition, pk=field_id)
    
    # Get or create field value
    field_value, created = ProjectFieldValue.objects.get_or_create(
        project=project,
        field_definition=field_definition
    )
    
    # Get submitted value
    value = request.POST.get("value", "")
    
    # Save value
    field_value.set_value(value, user=request.user if request.user.is_authenticated else None)
    
    if request.headers.get("HX-Request"):
        # HTMX request - return partial
        return render(request, "bfagent/field_management/partials/field_saved.html", {
            "field": field_definition,
            "value": value,
        })
    
    messages.success(request, f"✅ Saved {field_definition.display_name}")
    return redirect("bfagent:project-field-values", pk=pk)


# ============================================================================
# FIELD GROUP MANAGEMENT
# ============================================================================


def field_group_list(request):
    """List all field groups"""
    
    groups = FieldGroup.objects.filter(is_active=True).prefetch_related("fields").order_by("order")
    
    context = {"groups": groups}
    return render(request, "bfagent/field_management/group_list.html", context)


def field_group_create(request):
    """Create a new field group"""
    
    if request.method == "POST":
        try:
            group = FieldGroup.objects.create(
                name=request.POST["name"],
                display_name=request.POST["display_name"],
                description=request.POST.get("description", ""),
                icon=request.POST.get("icon", ""),
                color=request.POST.get("color", ""),
                order=int(request.POST.get("order", 0)),
            )
            
            messages.success(request, f"✅ Group '{group.display_name}' created!")
            return redirect("bfagent:field-group-list")
            
        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")
    
    return render(request, "bfagent/field_management/group_form.html")


# ============================================================================
# API ENDPOINTS (for HTMX/AJAX)
# ============================================================================


def field_definition_api(request, pk):
    """JSON API for field definition details"""
    
    field = get_object_or_404(FieldDefinition, pk=pk)
    
    data = {
        "id": field.id,
        "name": field.name,
        "display_name": field.display_name,
        "description": field.description,
        "field_type": field.field_type,
        "target_model": field.target_model,
        "placeholder": field.placeholder,
        "help_text": field.help_text,
        "is_ai_enrichable": field.is_ai_enrichable,
        "ai_prompt_template": field.ai_prompt_template,
        "group": {
            "id": field.group.id,
            "name": field.group.display_name,
        } if field.group else None,
    }
    
    return JsonResponse(data)
