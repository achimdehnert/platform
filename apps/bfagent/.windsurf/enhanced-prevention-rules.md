# Enhanced Prevention Rules for Configuration Errors

## 🔧 Mandatory Pre-Development Validation

### Before ANY Code Changes
```bash
# 1. System consistency check
python mcp_tools/system_validator.py

# 2. Database schema validation
python mcp_tools/server_error_healer.py

# 3. CRUD endpoint testing
python mcp_tools/comprehensive_crud_healer_v2.py
```

## 🛡️ SQLAlchemy Model Rules (CRITICAL)

### Base Class Inheritance Pattern
```python
# ✅ CORRECT - inherit from Base, no duplicate fields
class BookProject(Base):
    __tablename__ = "book_projects"
    # Base provides: id, created_at, updated_at
    title: Mapped[str] = mapped_column(String(200))

# ❌ FORBIDDEN - duplicate Base fields
class BadModel(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # DUPLICATE!
    created_at: Mapped[datetime] = mapped_column(DateTime)      # DUPLICATE!
```

## 📊 Database Configuration Consistency

### Single Source of Truth Rule
- ONE database file per environment
- ALL servers must use IDENTICAL DATABASE_URL
- NO mixed database configurations

### Validation Commands
```python
# Check database consistency
python -c "
import re, glob
configs = {}
for f in glob.glob('*.py'):
    with open(f) as file:
        content = file.read()
        match = re.search(r'DATABASE_URL.*=.*[\"\'](.*?)[\"\']', content)
        if match: configs[f] = match.group(1)
print('Database configs:', configs)
assert len(set(configs.values())) <= 1, 'Multiple databases found!'
"
```

## 🔄 Pydantic v2 Compatibility Rules

### Required Method Updates
```python
# ✅ Pydantic v2 - REQUIRED
response = Model.model_validate(data)
data_dict = model.model_dump()

# ❌ Pydantic v1 - FORBIDDEN
response = Model.from_orm(data)      # DEPRECATED
data_dict = model.dict()             # DEPRECATED
```

## 🚨 Error Prevention Workflow

### Development Cycle Integration
1. **Before coding**: Run system_validator.py
2. **After model changes**: Validate schema consistency
3. **Before commit**: Ensure 100% validation success
4. **Before deployment**: Execute full validation suite

### Automated Validation Script
```bash
#!/bin/bash
echo "🔍 Running comprehensive validation..."
python mcp_tools/system_validator.py || exit 1
python mcp_tools/server_error_healer.py || exit 1
python mcp_tools/comprehensive_crud_healer_v2.py || exit 1
echo "✅ All validations passed!"
```

## 📋 Memory Bank Integration

### Required Documentation
- Document ALL database schema changes
- Maintain validation success metrics
- Record configuration decisions and rationale
- Update prevention rules based on new error patterns

### Memory Bank Structure
```
memory-bank/
├── @database-consistency-rules.md
├── @validation-workflow.md
├── @error-patterns.md
└── @prevention-tools.md
```

## 🎯 Success Metrics

### Validation Targets
- System validation: 100% success rate
- Database consistency: 0 configuration mismatches
- Pydantic compatibility: 0 deprecated method usage
- CRUD operations: 0 server errors

### Monitoring Commands
```bash
# Daily validation check
python mcp_tools/system_validator.py > validation_$(date +%Y%m%d).log

# Error pattern analysis
grep -r "from_orm\|\.dict(" *.py || echo "✅ No Pydantic v1 usage"
```
