# Database/Model Consistency Prevention Rules

## 🛡️ SQLAlchemy Model Design Rules

### Base Class Inheritance
- **NEVER** duplicate fields between Base class and model classes
- Base class automatically provides: `id`, `created_at`, `updated_at`
- Models should only define domain-specific fields
- Use `__tablename__` consistently across all models

### Field Definition Pattern
```python
class BookProject(Base):
    __tablename__ = "book_projects"

    # ❌ WRONG - duplicates Base fields
    # id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ✅ CORRECT - only domain fields
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    genre: Mapped[Genre] = mapped_column(SQLEnum(Genre), nullable=False)
```

## 🔧 Database Configuration Validation

### Consistency Requirements
- All server files MUST use identical `DATABASE_URL`
- Single source of truth for database configuration
- Validate schema matches models before server start
- Check for Pydantic v1/v2 compatibility issues

### Configuration Pattern
```python
# ✅ CORRECT - centralized configuration
DATABASE_URL = "sqlite:///ecosystem_dashboard.db"

# ❌ WRONG - multiple different databases
# server1: "sqlite:///ecosystem_dashboard.db"
# server2: "sqlite:///simple_books.db"
```

## 📋 Mandatory Validation Workflow

### Pre-Deployment Checklist
1. **Run System Validator**: `python mcp_tools/system_validator.py`
2. **Fix All Errors**: Address database/schema mismatches
3. **Execute Auto-Fix**: Run generated `auto_fix_system.py` if available
4. **Achieve 100% Success**: Validation must pass completely
5. **Test CRUD Operations**: Verify endpoints work after changes

### Validation Commands
```bash
# 1. System validation
python mcp_tools/system_validator.py

# 2. Auto-fix if needed
python auto_fix_system.py

# 3. CRUD validation
python mcp_tools/comprehensive_crud_healer_v2.py
```

## ⚠️ Common Error Patterns to Avoid

### Database Configuration Errors
- Multiple database files configured inconsistently
- Missing database table creation before server start
- Schema mismatch between models and actual database

### SQLAlchemy Model Errors
- Duplicate field definitions in models inheriting from Base
- Incorrect field type mappings
- Missing `__tablename__` declarations

### Pydantic Compatibility Errors
- Using `.from_orm()` instead of `.model_validate()` (Pydantic v2)
- Using `.dict()` instead of `.model_dump()` (Pydantic v2)
- Mixed Pydantic v1/v2 usage across codebase

## 🔨 MCP Tools for Prevention

### System Validation Tools
- `system_validator.py`: Comprehensive system validation
- `server_error_healer.py`: 500 error diagnosis and fixing
- `comprehensive_crud_healer_v2.py`: CRUD operation validation

### Tool Usage Pattern
```bash
# Regular validation workflow
python mcp_tools/system_validator.py
python mcp_tools/server_error_healer.py
python mcp_tools/comprehensive_crud_healer_v2.py
```

## 📁 File Organization Rules

### Database Management
- Keep database configuration centralized in `config.py`
- Use consistent naming for database files
- Document schema changes in migration scripts
- Validate model imports before server startup

### Code Organization
- Separate model definitions from business logic
- Use consistent import patterns across modules
- Maintain clear separation between SQLAlchemy and Pydantic models
- Document database relationships and constraints

## 🚀 Integration Guidelines

### CI/CD Pipeline Integration
- Add system validation as mandatory pre-deployment step
- Fail builds on validation errors
- Generate auto-fix scripts in build artifacts
- Test database connectivity in deployment environment

### Development Workflow
- Run validation before committing changes
- Include validation results in pull request descriptions
- Maintain validation success rate metrics
- Document configuration changes in commit messages
