# STRICT STANDARDIZED CREATION PROCESS - BF Agent v2.0.0
**MANDATORY: This process is ENFORCED and cannot be bypassed!**

---

## 🎯 CORE PRINCIPLE: GENERATOR-FIRST DEVELOPMENT

**RULE #1**: Niemals manuell erstellen - IMMER den Generator verwenden!

```
❌ VERBOTEN: Manuelles Erstellen von CRUD-Komponenten
✅ PFLICHT: Automated Generation mit consistency_framework.py
```

---

## 📋 STANDARDIZED CREATION WORKFLOW

### Phase 1: Model Creation (EINZIGER manueller Schritt)

#### Step 1.1: Model definieren
```python
# apps/bfagent/models.py
from django.db import models
from .utils.crud_config import CRUDConfigMixin

class YourModel(CRUDConfigMixin, models.Model):
    """Model description"""
    
    # Fields
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=50)
    
    # CRUDConfig - MANDATORY!
    class CRUDConfig:
        # List display
        list_display_fields = ['name', 'status', 'created_at']
        list_searchable_fields = ['name']
        list_filterable_fields = ['status']
        
        # Form configuration
        form_fields = ['name', 'status']
        form_required_fields = ['name']
        form_help_texts = {
            'name': 'Enter a unique name',
        }
        
        # Display configuration
        detail_display_sections = {
            'Basic Info': ['name', 'status'],
            'Metadata': ['created_at', 'updated_at'],
        }
    
    class Meta:
        db_table = 'yourmodel'
        verbose_name = 'Your Model'
        verbose_name_plural = 'Your Models'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
```

#### Step 1.2: Migration erstellen
```bash
make migrate
# OR
python manage.py makemigrations
python manage.py migrate
```

---

### Phase 2: AUTOMATED Component Generation (STRICTLY ENFORCED)

#### Step 2.1: Analyze Model
```bash
python scripts/consistency_framework.py analyze YourModel
```

**Output:**
```
📊 Model Analysis: YourModel
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Model exists
✅ CRUDConfig defined
❌ Form missing
❌ Views missing  
❌ Templates missing
❌ URLs missing
❌ Tests missing

Completeness: 30%
```

#### Step 2.2: Generate ALL Components
```bash
python scripts/consistency_framework.py generate YourModel --force
```

**This ONE command creates:**
1. ✅ `apps/bfagent/utils/form_mixins.py` - YourModelFormFieldsMixin
2. ✅ `apps/bfagent/views/crud_views.py` - yourmodel_create, yourmodel_edit, yourmodel_delete, yourmodel_list
3. ✅ `templates/bfagent/yourmodel_list.html` - List page
4. ✅ `templates/bfagent/yourmodel_form.html` - Form page
5. ✅ `templates/bfagent/partials/yourmodel_list.html` - HTMX partial
6. ✅ `templates/bfagent/partials/yourmodel_form.html` - HTMX partial
7. ✅ `apps/bfagent/urls.py` - URL patterns added
8. ✅ `tests/test_yourmodel.py` - Complete test suite

---

### Phase 3: MANDATORY Validation (AUTOMATED)

#### Step 3.1: Run Consistency Checks
```bash
# URL-Template consistency
make check-urls

# Model-Form-Template consistency
make check-models

# HTMX pattern validation
make htmx-scan

# Code formatting
make format-code
```

**ALL MUST PASS** before proceeding!

#### Step 3.2: Run Tests
```bash
make test
# OR
pytest tests/test_yourmodel.py -v
```

---

### Phase 4: Custom Logic (Optional, aber regelbasiert)

#### Step 4.1: Customize Form (SAFE)
```python
# apps/bfagent/forms.py
from .utils.form_mixins import YourModelFormFieldsMixin
from django import forms

class YourModelForm(YourModelFormFieldsMixin, forms.ModelForm):
    """Custom form - SAFE TO EDIT
    
    The mixin provides base fields from CRUDConfig.
    Add custom fields and validation here.
    """
    
    # Add custom fields
    confirm_action = forms.BooleanField(
        required=False,
        label='Confirm this action'
    )
    
    # Custom validation
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if 'invalid' in name.lower():
            raise forms.ValidationError('Name cannot contain "invalid"')
        return name
```

#### Step 4.2: Customize Views (SAFE)
```python
# apps/bfagent/views/crud_views.py
# CUSTOM SECTION START - Your code here
def yourmodel_create(request):
    """Extended create logic"""
    if request.method == "POST":
        # Pre-save custom logic
        form = YourModelForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # Custom modifications
            obj.created_by = request.user
            obj.save()
            # Post-save actions
            send_notification(obj)
            messages.success(request, f'{obj.name} created!')
            # Return response...
# CUSTOM SECTION END
```

---

## 🚫 FORBIDDEN ACTIONS

### NEVER DO THIS:
1. ❌ Manually create CRUD files without generator
2. ❌ Skip CRUDConfig in models
3. ❌ Hardcode field lists in forms
4. ❌ Create templates without partials
5. ❌ Add URLs without corresponding views
6. ❌ Skip consistency validation
7. ❌ Commit without running all checks

### CONSEQUENCES:
- **PR Rejection** - Automatic
- **Build Failure** - CI/CD blocks
- **Code Review** - Required fixes before merge

---

## 📊 NAMING CONVENTIONS (STRICTLY ENFORCED)

### Model Names
```python
✅ YourModel          # PascalCase, singular
❌ your_model         # Wrong case
❌ YourModels         # Plural
```

### URL Names
```python
✅ yourmodel-list     # lowercase, hyphen-separated
✅ yourmodel-create
✅ yourmodel-edit
✅ yourmodel-delete
❌ your_model_list    # Underscores
❌ YourModelList      # PascalCase
```

### View Function Names
```python
✅ yourmodel_list     # lowercase, underscore-separated
✅ yourmodel_create
✅ yourmodel_edit
✅ yourmodel_delete
❌ YourModelList      # PascalCase
❌ yourmodel-list     # Hyphens
```

### Template Names
```python
✅ yourmodel_list.html              # Main template
✅ yourmodel_form.html
✅ partials/yourmodel_list.html     # HTMX partial
✅ partials/yourmodel_form.html
❌ YourModelList.html               # PascalCase
❌ yourmodel-list.html              # Hyphens
```

### Service Method Names
```python
✅ get_yourmodel_by_id(id)          # Singular entity
✅ get_yourmodels_by_project(project_id)  # Plural collection
✅ create_yourmodel(data)
✅ update_yourmodel(id, data)
✅ delete_yourmodel(id)

❌ get_yourmodels_by_project_id()  # Redundant _id
❌ getYourModel()                  # CamelCase
```

---

## 🔧 AUTOMATED ENFORCEMENT

### Pre-Commit Hooks (.pre-commit-config.yaml)
```yaml
repos:
  - repo: local
    hooks:
      - id: check-creation-process
        name: Verify Standardized Creation Process
        entry: python scripts/check_creation_compliance.py
        language: system
        pass_filenames: false
        
      - id: check-urls
        name: URL-Template Consistency
        entry: python scripts/url_template_consistency_checker.py
        language: system
        pass_filenames: false
        
      - id: check-models
        name: Model-Form-Template Consistency
        entry: python scripts/model_consistency_checker.py
        language: system
        pass_filenames: false
        
      - id: check-naming
        name: Naming Convention Validator
        entry: python scripts/naming_convention_checker.py
        language: system
        pass_filenames: false
```

### CI/CD Pipeline (GitHub Actions)
```yaml
name: Quality Gate

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v2
        
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
          
      - name: Run Consistency Checks
        run: |
          make check-urls
          make check-models
          make htmx-scan
          make format-code
          
      - name: Run Tests
        run: make test
        
      - name: Validate Creation Process
        run: python scripts/check_creation_compliance.py --strict
```

---

## 📝 CREATION CHECKLIST (MANDATORY)

### Before Creating ANY New Model/Feature:
- [ ] Read this document completely
- [ ] Understand the standardized process
- [ ] Have consistency_framework.py ready
- [ ] Understand naming conventions

### During Model Creation:
- [ ] Model has CRUDConfig defined
- [ ] Model follows naming conventions
- [ ] Migrations created and applied
- [ ] Ran `analyze` command first

### During Component Generation:
- [ ] Used generator (not manual creation)
- [ ] Generated ALL components at once
- [ ] Verified all files created
- [ ] No manual modifications yet

### After Generation:
- [ ] All consistency checks pass
- [ ] All tests pass
- [ ] Code formatted
- [ ] Custom logic documented

### Before Commit:
- [ ] Pre-commit hooks pass
- [ ] All validation green
- [ ] Documentation updated
- [ ] Tests cover custom logic

---

## 🎯 QUALITY GATES

### Gate 1: Model Definition
**Check:** CRUDConfig exists and is complete  
**Tool:** `consistency_framework.py analyze`  
**Action:** Cannot proceed without CRUDConfig

### Gate 2: Component Generation
**Check:** All components generated successfully  
**Tool:** `consistency_framework.py generate --force`  
**Action:** Manual creation rejected

### Gate 3: Consistency Validation
**Check:** No URL/Form/Template inconsistencies  
**Tool:** `make check-urls`, `make check-models`  
**Action:** Must fix before commit

### Gate 4: Code Quality
**Check:** Formatting, linting, naming conventions  
**Tool:** `make format-code`, `naming_convention_checker.py`  
**Action:** Auto-fix or manual correction

### Gate 5: Testing
**Check:** All tests pass, coverage > 80%  
**Tool:** `make test`, `pytest --cov`  
**Action:** Must achieve minimum coverage

### Gate 6: Pre-Commit
**Check:** All hooks pass  
**Tool:** `pre-commit run --all-files`  
**Action:** Cannot commit until green

### Gate 7: CI/CD
**Check:** Build passes, all checks green  
**Tool:** GitHub Actions workflow  
**Action:** PR cannot merge until passing

---

## 🚀 QUICK REFERENCE COMMANDS

```bash
# Complete creation workflow
make new-model MODEL=YourModel    # Interactive model creation
make generate MODEL=YourModel     # Generate all components
make validate                     # Run all checks
make test-model MODEL=YourModel   # Run model tests

# Individual steps
python scripts/consistency_framework.py analyze YourModel
python scripts/consistency_framework.py generate YourModel --force
make check-urls
make check-models
make htmx-scan
make format-code
make test

# Fix issues
python scripts/consistency_framework.py fix YourModel
make check-urls-fix
```

---

## 📚 ADDITIONAL RESOURCES

- **Naming Conventions:** `.windsurf/service-naming-conventions.md`
- **CRUD Patterns:** `.windsurf/CRUD_PATTERN_RULES.md`
- **Prevention System:** `docs/PREVENTION_SYSTEM_RULES.md`
- **Consistency Framework:** `docs/modular-consistency-framework.md`
- **Tool Concepts:** `docs/TOOL_CONCEPT_URL_VIEW_CONSISTENCY_CHECKER.md`

---

## ✅ SUCCESS METRICS

### Individual Feature:
- **100%** CRUDConfig compliance
- **100%** URL-Template consistency
- **100%** Model-Form-Template sync
- **100%** Test coverage on custom logic
- **0** manual CRUD files

### Project-Wide:
- **< 5 min** from model to working CRUD
- **0** NoReverseMatch errors
- **0** missing form fields
- **0** broken URLs
- **100%** automated generation

---

**REMEMBER: One standardized process prevents hundreds of errors!** 🚀
