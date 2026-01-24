"""
Django Management Command to check Model-Form synchronization
Identifies missing fields in Forms compared to Model definitions
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.forms import models as model_forms


class Command(BaseCommand):
    help = "Check synchronization between Models and Forms"

    def add_arguments(self, parser):
        parser.add_argument(
            "--app", type=str, help="Check only specific app (default: bfagent)", default="bfagent"
        )
        parser.add_argument(
            "--fix", action="store_true", help="Generate missing form fields automatically"
        )

    def handle(self, *args, **options):
        app_name = options["app"]

        self.stdout.write(self.style.SUCCESS(f"\n🔍 CHECKING MODEL-FORM SYNC FOR APP: {app_name}"))
        self.stdout.write("=" * 60)

        issues_found = 0
        models_checked = 0

        for model in apps.get_models():
            if model._meta.app_label != app_name:
                continue

            models_checked += 1
            issues = self.check_model_form_sync(model)
            if issues:
                issues_found += len(issues)
                self.display_issues(model, issues)

        self.stdout.write("\n" + "=" * 60)
        if issues_found == 0:
            self.stdout.write(
                self.style.SUCCESS(f"✅ ALL {models_checked} MODELS ARE PERFECTLY SYNCED!")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"⚠️  FOUND {issues_found} ISSUES IN {models_checked} MODELS")
            )

        if options["fix"]:
            self.stdout.write("\n🔧 AUTO-FIX MODE NOT IMPLEMENTED YET")
            self.stdout.write("Use the output above to manually fix forms.py")

    def check_model_form_sync(self, model):
        """Check if model fields are present in corresponding form"""
        issues = []

        # Get all editable model fields (exclude auto-created and non-editable)
        model_fields = {
            f.name
            for f in model._meta.get_fields()
            if not f.auto_created and f.editable and not f.name.endswith("_ptr")
        }

        # Exclude common auto-fields
        auto_exclude = {"id", "created_at", "updated_at", "pk"}
        model_fields = model_fields - auto_exclude

        # Try to find corresponding form
        form_class = self.find_form_class(model)

        if not form_class:
            issues.append(
                {"type": "NO_FORM", "message": f"No form class found for {model.__name__}"}
            )
            return issues

        # Get form fields
        form_fields = self.get_form_fields(form_class)

        # Find missing fields
        missing_in_form = model_fields - form_fields
        extra_in_form = form_fields - model_fields - auto_exclude

        if missing_in_form:
            issues.append(
                {
                    "type": "MISSING_IN_FORM",
                    "fields": missing_in_form,
                    "message": f"Fields exist in model but missing in form: {missing_in_form}",
                }
            )

        if extra_in_form:
            issues.append(
                {
                    "type": "EXTRA_IN_FORM",
                    "fields": extra_in_form,
                    "message": f"Fields in form but not in model: {extra_in_form}",
                }
            )

        return issues

    def find_form_class(self, model):
        """Try to find the form class for a model"""
        form_name = f"{model.__name__}Form"
        app_label = model._meta.app_label

        try:
            # Try direct import from apps.bfagent.forms
            forms_module = __import__(f"apps.{app_label}.forms", fromlist=[form_name])
            form_class = getattr(forms_module, form_name, None)
            if form_class:
                return form_class
        except ImportError:
            pass

        try:
            # Try alternative import path
            forms_module = __import__(f"{app_label}.forms", fromlist=[form_name])
            form_class = getattr(forms_module, form_name, None)
            if form_class:
                return form_class
        except ImportError:
            pass

        # Debug: List all available forms
        try:
            forms_module = __import__(f"apps.{app_label}.forms", fromlist=[""])
            available_forms = [name for name in dir(forms_module) if name.endswith("Form")]
            if available_forms:
                self.stdout.write(
                    self.style.NOTICE(f'     Available forms: {", ".join(available_forms)}')
                )
        except ImportError:
            pass

        return None

    def get_form_fields(self, form_class):
        """Extract field names from form class"""
        if not hasattr(form_class, "_meta"):
            return set()

        meta = form_class._meta

        if hasattr(meta, "fields"):
            if meta.fields == "__all__":
                # Get all model fields
                model_fields = {
                    f.name
                    for f in meta.model._meta.get_fields()
                    if not f.auto_created and f.editable
                }
                excluded = set(meta.exclude or [])
                return model_fields - excluded
            else:
                return set(meta.fields or [])

        return set()

    def display_issues(self, model, issues):
        """Display issues in a formatted way"""
        self.stdout.write(f"\n📋 {model._meta.label.upper()}:")

        for issue in issues:
            if issue["type"] == "NO_FORM":
                self.stdout.write(self.style.ERROR(f'  ❌ {issue["message"]}'))
            elif issue["type"] == "MISSING_IN_FORM":
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠️  Missing in form: {", ".join(sorted(issue["fields"]))}'
                    )
                )
                # Show suggested fix
                self.stdout.write(
                    self.style.NOTICE(f'     💡 Add to fields: {sorted(issue["fields"])}')
                )
            elif issue["type"] == "EXTRA_IN_FORM":
                self.stdout.write(
                    self.style.NOTICE(f'  ℹ️  Extra in form: {", ".join(sorted(issue["fields"]))}')
                )
