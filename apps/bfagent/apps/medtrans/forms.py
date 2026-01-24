from django import forms

from .models import Customer, Presentation


class CustomerForm(forms.ModelForm):
    """Form for creating/editing customers"""

    class Meta:
        model = Customer
        fields = ["customer_id", "customer_name", "dashboard_access"]
        widgets = {
            "customer_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., MEDTECH_DE"}
            ),
            "customer_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., MedTech Deutschland GmbH"}
            ),
            "dashboard_access": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        help_texts = {
            "customer_id": "Unique identifier (uppercase, underscores allowed)",
            "customer_name": "Display name for the customer",
            "dashboard_access": "Allow this customer to access the dashboard",
        }


class PresentationUploadForm(forms.ModelForm):
    """Form for uploading PowerPoint presentations"""

    class Meta:
        model = Presentation
        fields = ["customer", "pptx_file", "source_language", "target_language"]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "pptx_file": forms.FileInput(attrs={"class": "form-control", "accept": ".pptx"}),
            "source_language": forms.Select(attrs={"class": "form-select"}),
            "target_language": forms.Select(attrs={"class": "form-select"}),
        }
        help_texts = {
            "pptx_file": "PowerPoint file (.pptx format)",
            "source_language": "Original language of the presentation",
            "target_language": "Language to translate to",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter customers by current user
        if user:
            self.fields["customer"].queryset = Customer.objects.filter(user=user)
