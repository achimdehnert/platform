"""
SmartModel System - Auto-Form Generation with CRUDConfig Integration
Extends our Zero-Hardcoding System with intelligent form generation
"""

from typing import Dict, Optional, Type

from django import forms
from django.db import models
from django.forms import modelform_factory


class SmartModelMixin:
    """
    Mixin that provides intelligent form generation for models
    Integrates seamlessly with our existing CRUDConfig system
    """

    @classmethod
    def get_form_class(cls) -> Type[forms.ModelForm]:
        """
        Generates form class automatically or returns existing custom form
        Priority: Custom Form > CRUDConfig > Auto-Generated
        """
        # 1. Try to find existing custom form
        custom_form = cls._find_custom_form()
        if custom_form:
            return custom_form

        # 2. Generate form using CRUDConfig if available
        if hasattr(cls, "CRUDConfig"):
            return cls._generate_crud_config_form()

        # 3. Fallback to intelligent auto-generation
        return cls._generate_smart_form()

    @classmethod
    def _find_custom_form(cls) -> Optional[Type[forms.ModelForm]]:
        """Try to find manually created form class"""
        form_name = f"{cls.__name__}Form"
        app_label = cls._meta.app_label

        try:
            forms_module = __import__(f"{app_label}.forms", fromlist=[form_name])
            if hasattr(forms_module, form_name):
                return getattr(forms_module, form_name)
        except ImportError:
            pass

        return None

    @classmethod
    def _generate_crud_config_form(cls) -> Type[forms.ModelForm]:
        """Generate form using CRUDConfig specifications"""
        crud_config = cls.CRUDConfig()

        # Get fields from CRUDConfig form_layout or use all fields
        if hasattr(crud_config, "form_layout") and crud_config.form_layout:
            # Extract fields from form_layout sections
            fields = []
            for section_fields in crud_config.form_layout.values():
                fields.extend(section_fields)
        else:
            # Use all model fields except excluded ones
            fields = [f.name for f in cls._meta.get_fields() if not f.auto_created and f.editable]

        # Apply exclusions from CRUDConfig
        exclude_fields = getattr(crud_config, "form_exclude", [])
        exclude_fields.extend(["id", "created_at", "updated_at"])

        # Filter out excluded fields
        fields = [f for f in fields if f not in exclude_fields]

        # Generate widgets using CRUDConfig theme
        widgets = cls._get_crud_config_widgets(fields)

        return modelform_factory(cls, fields=fields, widgets=widgets)

    @classmethod
    def _generate_smart_form(cls) -> Type[forms.ModelForm]:
        """Generate form with intelligent defaults"""
        exclude_fields = ["id", "created_at", "updated_at"]
        widgets = cls._get_smart_widgets()

        return modelform_factory(cls, exclude=exclude_fields, widgets=widgets)

    @classmethod
    def _get_crud_config_widgets(cls, fields: list) -> Dict[str, forms.Widget]:
        """Generate widgets based on CRUDConfig theme and field types"""
        widgets = {}

        for field_name in fields:
            try:
                field = cls._meta.get_field(field_name)
                widget = cls._get_widget_for_field(field)
                if widget:
                    widgets[field_name] = widget
            except:
                continue

        return widgets

    @classmethod
    def _get_smart_widgets(cls) -> Dict[str, forms.Widget]:
        """Generate intelligent widgets for all model fields"""
        widgets = {}

        for field in cls._meta.get_fields():
            if not field.auto_created and field.editable:
                widget = cls._get_widget_for_field(field)
                if widget:
                    widgets[field.name] = widget

        return widgets

    @classmethod
    def _get_widget_for_field(cls, field) -> Optional[forms.Widget]:
        """Get appropriate widget for a field type"""
        base_attrs = {"class": "form-control"}

        if isinstance(field, models.TextField):
            rows = 10 if "content" in field.name.lower() else 3
            if "description" in field.name.lower():
                rows = 2
            return forms.Textarea(attrs={**base_attrs, "rows": rows})

        elif isinstance(field, models.CharField):
            if field.max_length and field.max_length <= 100:
                return forms.TextInput(attrs=base_attrs)
            else:
                return forms.Textarea(attrs={**base_attrs, "rows": 2})

        elif isinstance(field, models.EmailField):
            return forms.EmailInput(attrs=base_attrs)

        elif isinstance(field, models.URLField):
            return forms.URLInput(attrs=base_attrs)

        elif isinstance(field, models.DateField):
            return forms.DateInput(attrs={**base_attrs, "type": "date"})

        elif isinstance(field, models.DateTimeField):
            return forms.DateTimeInput(attrs={**base_attrs, "type": "datetime-local"})

        elif isinstance(field, models.IntegerField):
            attrs = {**base_attrs, "type": "number"}
            if hasattr(field, "validators"):
                for validator in field.validators:
                    if hasattr(validator, "limit_value"):
                        if "min" in str(validator.__class__.__name__).lower():
                            attrs["min"] = validator.limit_value
                        elif "max" in str(validator.__class__.__name__).lower():
                            attrs["max"] = validator.limit_value
            return forms.NumberInput(attrs=attrs)

        elif isinstance(field, models.FloatField):
            return forms.NumberInput(attrs={**base_attrs, "type": "number", "step": "0.01"})

        elif isinstance(field, models.BooleanField):
            return forms.CheckboxInput(attrs={"class": "form-check-input"})

        elif isinstance(field, models.ForeignKey):
            return forms.Select(attrs={"class": "form-select"})

        elif isinstance(field, models.ManyToManyField):
            return forms.SelectMultiple(attrs={"class": "form-select"})

        return None


# Integration with existing CRUDConfigMixin
class SmartCRUDModel(SmartModelMixin, models.Model):
    """
    Base model that combines SmartModel with CRUDConfig
    Use this as base for new models
    """

    class Meta:
        abstract = True

    @classmethod
    def get_admin_form_class(cls):
        """Get form class optimized for admin interface"""
        form_class = cls.get_form_class()

        # Add admin-specific customizations
        if hasattr(cls, "CRUDConfig"):
            crud_config = cls.CRUDConfig()
            if hasattr(crud_config, "admin_readonly_fields"):
                # Create a new form class with readonly fields
                class AdminForm(form_class):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        for field_name in crud_config.admin_readonly_fields:
                            if field_name in self.fields:
                                self.fields[field_name].widget.attrs["readonly"] = True

                return AdminForm

        return form_class


def upgrade_existing_model(model_class):
    """
    Utility function to upgrade existing models to SmartModel
    Usage: upgrade_existing_model(BookProjects)
    """
    if not issubclass(model_class, SmartModelMixin):
        # Dynamically add SmartModelMixin to the model's bases
        model_class.__bases__ = (SmartModelMixin,) + model_class.__bases__

    return model_class
