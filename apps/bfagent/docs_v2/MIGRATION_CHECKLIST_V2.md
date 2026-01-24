# ✅ Migration Checklist v2.0
## From Code-Based to Database-First

**Estimated Time:** 2-4 hours (depending on project size)  
**Difficulty:** Medium  
**Risk:** Low (with rollback plan)

---

## 📋 Pre-Migration

### Preparation (30 Min)

- [ ] **Backup everything**
  ```bash
  # Code backup
  git commit -am "Pre-v2-migration backup"
  git push
  
  # Database backup
  python manage.py dumpdata > backup_before_v2.json
  
  # Or for PostgreSQL
  pg_dump dbname > backup_$(date +%Y%m%d).sql
  ```

- [ ] **Read documentation**
  - [ ] DATABASE_FIRST_ARCHITECTURE.md
  - [ ] UPDATE_SUMMARY_V2.md
  - [ ] IMPLEMENTATION_GUIDE_V2.md

- [ ] **Inventory existing templates**
  ```bash
  # List all template files
  find . -name "*template*.py" -type f
  
  # Document what needs migration:
  # - domains/books/templates.py → ?
  # - domains/science/templates.py → ?
  # etc.
  ```

- [ ] **Test environment ready**
  ```bash
  # Have a test environment
  # NOT production!
  python manage.py runserver --settings=config.settings.test
  ```

---

## 🗄️ Phase 1: Database Setup (30 Min)

### Step 1.1: Create Models

- [ ] **Copy models from DATABASE_FIRST_ARCHITECTURE.md**
  ```bash
  # Create file
  vim apps_v2/core/workflows/models.py
  
  # Paste models:
  # - DomainTemplate
  # - PhaseTemplate  
  # - ActionTemplate
  # - HandlerRegistry
  # - FeatureFlag
  # - WorkflowInstance
  # etc.
  ```

- [ ] **Verify syntax**
  ```bash
  python manage.py check
  # Should show: System check identified no issues
  ```

### Step 1.2: Create Migrations

- [ ] **Generate migrations**
  ```bash
  python manage.py makemigrations core
  ```
  
  **Expected output:**
  ```
  Migrations for 'core':
    core/migrations/0001_initial.py
      - Create model DomainTemplate
      - Create model PhaseTemplate
      - Create model ActionTemplate
      - Create model HandlerRegistry
      - ...
  ```

- [ ] **Review migration file**
  ```bash
  cat apps_v2/core/migrations/0001_initial.py
  # Check for any issues
  ```

- [ ] **Test migration (dry-run)**
  ```bash
  python manage.py migrate core --plan
  # Shows what will happen, doesn't execute
  ```

- [ ] **Apply migration**
  ```bash
  python manage.py migrate core
  ```
  
  **Expected:**
  ```
  Running migrations:
    Applying core.0001_initial... OK
  ```

- [ ] **Verify tables exist**
  ```bash
  python manage.py dbshell
  # \dt (PostgreSQL) or .tables (SQLite)
  # Should see: domain_templates, phase_templates, action_templates
  ```

---

## 🎨 Phase 2: Django Admin Setup (20 Min)

### Step 2.1: Configure Admin

- [ ] **Create admin.py**
  ```bash
  vim apps_v2/core/workflows/admin.py
  ```

- [ ] **Copy admin config from DATABASE_FIRST_ARCHITECTURE.md**
  - [ ] DomainTemplateAdmin
  - [ ] PhaseTemplateAdmin
  - [ ] ActionTemplateAdmin
  - [ ] HandlerRegistryAdmin
  - [ ] FeatureFlagAdmin

- [ ] **Register models**
  ```python
  @admin.register(DomainTemplate)
  class DomainTemplateAdmin(admin.ModelAdmin):
      ...
  ```

### Step 2.2: Test Admin

- [ ] **Create superuser** (if needed)
  ```bash
  python manage.py createsuperuser
  ```

- [ ] **Start server**
  ```bash
  python manage.py runserver
  ```

- [ ] **Open admin**
  - [ ] Go to http://localhost:8000/admin/
  - [ ] Login
  - [ ] Verify you see:
    - Core
      - Domain Templates
      - Phase Templates
      - Action Templates
      - Handler Registry
      - Feature Flags

- [ ] **Test CRUD operations**
  - [ ] Can create Domain Template
  - [ ] Can edit Domain Template
  - [ ] Can delete Domain Template
  - [ ] Inlines work (Phases, Actions)

---

## 📦 Phase 3: Import Existing Templates (1-2 Hours)

### Step 3.1: Create Import Script

- [ ] **Create management command**
  ```bash
  mkdir -p management/commands
  vim management/commands/import_templates.py
  ```

- [ ] **Implement import logic**
  ```python
  from django.core.management.base import BaseCommand
  from apps_v2.core.workflows.models import DomainTemplate
  
  class Command(BaseCommand):
      def handle(self, *args, **options):
          # Import logic here
          pass
  ```

### Step 3.2: Import Each Domain

- [ ] **Books Domain**
  ```bash
  # In import_templates.py, add:
  from domains.books.templates import BOOK_TEMPLATE
  
  domain = DomainTemplate.objects.create(
      domain_id=BOOK_TEMPLATE.domain_id,
      display_name=BOOK_TEMPLATE.display_name,
      # ... map all fields
  )
  
  for phase in BOOK_TEMPLATE.phases:
      phase_db = PhaseTemplate.objects.create(...)
      for action in phase.actions:
          ActionTemplate.objects.create(...)
  ```

- [ ] **Science Domain**
  - [ ] Same process as Books

- [ ] **Forensics Domain**
  - [ ] Same process as Books

- [ ] **Run import**
  ```bash
  python manage.py import_templates
  ```

- [ ] **Verify in Admin**
  - [ ] Check Domain Templates
  - [ ] All domains present?
  - [ ] All phases present?
  - [ ] All actions present?

---

## 🔧 Phase 4: Update Code (1-2 Hours)

### Step 4.1: Update Workflow Creation

- [ ] **Find all places where templates are used**
  ```bash
  grep -r "BOOK_TEMPLATE" . --include="*.py"
  grep -r "DomainTemplate(" . --include="*.py"
  ```

- [ ] **Update each location**
  
  **Before (v1):**
  ```python
  from domains.books.templates import BOOK_TEMPLATE
  workflow = create_workflow(BOOK_TEMPLATE)
  ```
  
  **After (v2):**
  ```python
  from apps_v2.core.workflows.models import DomainTemplate
  template = DomainTemplate.objects.get(domain_id='books', is_active=True)
  workflow = create_workflow(template)
  ```

### Step 4.2: Update Executor

- [ ] **Update WorkflowExecutor**
  ```python
  # OLD
  def __init__(self, template: DomainTemplate):
      self.template = template
  
  # NEW
  def __init__(self, domain_id: str):
      self.template = DomainTemplate.objects.get(
          domain_id=domain_id,
          is_active=True
      )
  ```

- [ ] **Add dynamic handler loading**
  ```python
  def _load_handler(self, class_path: str):
      module_path, class_name = class_path.rsplit('.', 1)
      module = importlib.import_module(module_path)
      return getattr(module, class_name)()
  ```

### Step 4.3: Update Tests

- [ ] **Update test fixtures**
  ```python
  # OLD
  @pytest.fixture
  def book_template():
      return BOOK_TEMPLATE
  
  # NEW
  @pytest.fixture
  def book_template():
      return DomainTemplate.objects.get(domain_id='books')
  ```

- [ ] **Run tests**
  ```bash
  pytest
  # All tests should pass
  ```

---

## 🧪 Phase 5: Testing (30 Min)

### Step 5.1: Unit Tests

- [ ] **Test model creation**
  ```bash
  pytest apps_v2/core/workflows/tests/test_models.py
  ```

- [ ] **Test admin**
  ```bash
  pytest apps_v2/core/workflows/tests/test_admin.py
  ```

- [ ] **Test executor**
  ```bash
  pytest apps_v2/core/workflows/tests/test_executor.py
  ```

### Step 5.2: Integration Tests

- [ ] **Test complete workflow**
  ```python
  # Create template via API/Admin
  # Execute workflow
  # Verify output
  ```

- [ ] **Test each domain**
  - [ ] Books workflow
  - [ ] Science workflow
  - [ ] Forensics workflow

### Step 5.3: Manual Testing

- [ ] **Django Admin**
  - [ ] Create new template
  - [ ] Edit existing template
  - [ ] Delete template
  - [ ] All forms work?

- [ ] **Workflow Execution**
  ```bash
  python manage.py execute_workflow books --context '{"book_id": 1}'
  # Should work
  ```

---

## 🚀 Phase 6: Deployment (30 Min)

### Step 6.1: Staging Deployment

- [ ] **Deploy to staging**
  ```bash
  git push staging v2-migration
  ```

- [ ] **Run migrations on staging**
  ```bash
  ssh staging
  cd /app
  python manage.py migrate core
  python manage.py import_templates
  ```

- [ ] **Test on staging**
  - [ ] Admin works?
  - [ ] Workflows execute?
  - [ ] No errors in logs?

- [ ] **Smoke tests**
  ```bash
  # Run critical workflows
  # Check outputs
  # Verify functionality
  ```

### Step 6.2: Production Deployment

- [ ] **Final backup**
  ```bash
  # Database backup
  pg_dump production > backup_before_v2_prod.sql
  ```

- [ ] **Deploy to production**
  ```bash
  git push production v2-migration
  ```

- [ ] **Run migrations on production**
  ```bash
  ssh production
  cd /app
  python manage.py migrate core
  python manage.py import_templates
  ```

- [ ] **Monitor**
  - [ ] Check logs
  - [ ] Check error rates
  - [ ] Check performance

---

## 🧹 Phase 7: Cleanup (Optional, after 2 weeks)

### Step 7.1: Deprecate Old Files

- [ ] **Add deprecation warnings**
  ```python
  # domains/books/templates.py
  import warnings
  warnings.warn(
      "templates.py is deprecated. Use Database instead.",
      DeprecationWarning
  )
  ```

- [ ] **Wait 2 weeks** for any issues

### Step 7.2: Remove Old Code

- [ ] **Remove template files**
  ```bash
  git rm domains/books/templates.py
  git rm domains/science/templates.py
  git rm domains/forensics/templates.py
  ```

- [ ] **Update documentation**
  ```bash
  # Update README
  # Update setup guides
  # Remove references to old templates.py
  ```

- [ ] **Commit**
  ```bash
  git commit -am "Remove deprecated template files"
  git push
  ```

---

## 🆘 Rollback Plan

If something goes wrong:

### Immediate Rollback

- [ ] **Stop application**
  ```bash
  systemctl stop bfagent
  ```

- [ ] **Restore database**
  ```bash
  # PostgreSQL
  psql dbname < backup_before_v2.sql
  
  # Django
  python manage.py loaddata backup_before_v2.json
  ```

- [ ] **Checkout old code**
  ```bash
  git checkout main  # or previous branch
  ```

- [ ] **Restart application**
  ```bash
  systemctl start bfagent
  ```

- [ ] **Verify**
  ```bash
  curl http://localhost:8000/health
  # Should be OK
  ```

---

## 📊 Success Metrics

After migration, verify:

- [ ] **Functionality**
  - [ ] All workflows execute
  - [ ] No errors in logs
  - [ ] Output quality same

- [ ] **Performance**
  - [ ] Response times ±10%
  - [ ] Database queries reasonable
  - [ ] No memory leaks

- [ ] **Usability**
  - [ ] Django Admin works
  - [ ] Templates editable via UI
  - [ ] Changes don't require deployment

---

## ✅ Final Verification

- [ ] All checklists completed
- [ ] Tests passing
- [ ] Production stable
- [ ] Team trained on Django Admin
- [ ] Documentation updated
- [ ] Rollback plan tested

---

## 🎉 Migration Complete!

**Congratulations!** You're now on Database-First Architecture v2.0!

### Benefits You Now Have:

✅ Zero-deployment for workflow changes  
✅ UI-based template management  
✅ Non-developer can create workflows  
✅ A/B testing capability  
✅ Audit trail built-in  
✅ Template versioning

### Next Steps:

1. Train team on Django Admin
2. Create new templates via UI
3. Optimize workflows
4. Enjoy the flexibility!

---

**Version 2.0 Migration Complete! 🚀**

**Questions?** See:
- DATABASE_FIRST_ARCHITECTURE.md
- IMPLEMENTATION_GUIDE_V2.md
- UPDATE_SUMMARY_V2.md
