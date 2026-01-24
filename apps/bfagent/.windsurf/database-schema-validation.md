# Database Schema Validation System

## Problem

## Solution Framework

### 1. Schema Definition Files

### 2. Validation Functions
```python
# database/schema_validator.py
def validate_database_schema(db_path: str, expected_schema: dict) -> dict:
    """Validate actual database matches expected schema"""
    results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # Check tables exist
    # Check columns exist and have correct types
    # Validate foreign key relationships
    # Test shape ID format compliance

    return results
```

### 3. Integration Points

#### A. In validate_core.py
```python
def test_database_schema():
    from database.schema_validator import validate_database_schema
    from database.schemas.v1_0_0 import TABLES, SHAPE_ID_FORMAT

    result = validate_database_schema("analysis.db", TABLES)
    if not result["valid"]:
        print("❌ Database schema validation failed")
        for error in result["errors"]:
            print(f"   Error: {error}")
        return False

    print("✅ Database schema validated")
    return True
```

#### B. In Pipeline Classes
```python
class MCPSelfHealingPipeline:
    def __init__(self):
        # Validate schema before any operations
        self._validate_schema_compatibility()

    def _validate_schema_compatibility(self):
        from database.schemas.current import SHAPE_ID_FORMAT
        # Ensure pipeline uses correct shape ID format
        self.shape_id_format = SHAPE_ID_FORMAT
```

### 4. Memory Bank Integration

#### database-patterns.md
```markdown
# Database Patterns and Standards

## Shape ID Format
- **Current**: S{slide_number}-{shape_number}
- **Examples**: S1-1, S2-3, S12-5
- **Never use**: LAYOUT-X-Y, SLIDE-X-Y

## Column Naming
- snake_case for all columns
- _id suffix for foreign keys
- _at suffix for timestamps

## Query Patterns
- Always use parameterized queries
- Include error handling for missing columns
- Validate foreign key relationships
```

### 5. Prevention System Integration

#### prevention-system-template/database_validation.py
```python
def validate_database_consistency():
    """Project-independent database validation"""
    checks = [
        check_schema_version(),
        check_column_existence(),
        check_foreign_keys(),
        check_data_integrity(),
        validate_shape_id_format()
    ]
    return all(checks)
```

### 6. Automated Checks

#### .windsurf/pre-development-checklist.md
```markdown
# Pre-Development Database Checklist

Before modifying database-related code:

1. ✅ Run schema validation: `python validate_database_schema.py`
2. ✅ Check shape ID format consistency
3. ✅ Verify column names match schema definition
4. ✅ Test foreign key relationships
5. ✅ Backup database before schema changes

Never assume database structure - always validate!
```

### 7. Future Project Template

#### project-template/database/
```
database/
├── schemas/
│   ├── __init__.py
│   ├── current.py -> v1_0_0.py
│   └── v1_0_0.py
├── migrations/
│   └── 001_initial_schema.sql
├── validators/
│   ├── schema_validator.py
│   └── data_validator.py
└── tests/
    └── test_schema_validation.py
```

## Implementation Priority

1. **Immediate**: Add schema validation to validate_core.py
2. **Short-term**: Create schema definition files
3. **Long-term**: Automated migration system

## Benefits

- **Catch mismatches early** before runtime failures
- **Document schema evolution** with version control
- **Prevent regression** when refactoring
- **Cross-project reusability** with templates
- **Team collaboration** with clear schema contracts
