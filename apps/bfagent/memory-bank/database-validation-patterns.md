# Database Validation Patterns

## Critical Database Patterns

### Shape ID Format Standards
- **Current Standard**: `S{slide_number}-{shape_number}`
- **Examples**: S1-1, S2-3, S12-5
- **Pattern**: `^S\d+-\d+$`
- **Never Use**: LAYOUT-X-Y, SLIDE-X-Y, random UUIDs

### Column Naming Conventions
- **snake_case** for all columns
- **_id** suffix for foreign keys (presentation_id, shape_id)
- **_at** suffix for timestamps (created_at, updated_at)
- **_count** suffix for counts (slide_count, shape_count)

### Status Field Standards
- **Valid Values**: pending, translated, failed, skipped
- **Default**: pending
- **Consistency Rule**: status='translated' MUST have translated_text

### Foreign Key Patterns
- **shapes.presentation_id** → presentations.id
- **Always validate** orphaned records
- **Use parameterized queries** to prevent SQL injection

## Prevention Checklist

### Before Database Code Changes
1. ✅ Validate current schema: `python database/schema_validator.py`
2. ✅ Check data integrity: `python database/validators/data_validator.py`
3. ✅ Verify shape ID format consistency
4. ✅ Test foreign key relationships
5. ✅ Backup database before modifications

### Common Database Mistakes to Avoid
- **Shape ID Mismatch**: Pipeline expects S1-1, database has LAYOUT-1-1
- **Column Name Changes**: Code uses old column names after schema updates
- **Missing Foreign Keys**: Orphaned records causing silent failures
- **Status Inconsistency**: translated_text without status='translated'
- **NULL Required Fields**: Missing data in required columns

### Query Safety Patterns
```python
# ✅ GOOD - Parameterized query
cursor.execute("SELECT * FROM shapes WHERE presentation_id = ?", (presentation_id,))

# ❌ BAD - String formatting (SQL injection risk)
cursor.execute(f"SELECT * FROM shapes WHERE presentation_id = {presentation_id}")

# ✅ GOOD - Error handling
try:
    cursor.execute("SELECT shape_id FROM shapes WHERE status = ?", ("translated",))
    results = cursor.fetchall()
except sqlite3.Error as e:
    logger.error(f"Database query failed: {e}")
    return []
```

### Schema Evolution Best Practices
1. **Version Control**: Use v1_0_0.py, v1_1_0.py for schema versions
2. **Migration Scripts**: Create SQL migration files for schema changes
3. **Backward Compatibility**: Test old code with new schema
4. **Documentation**: Update schema docs with every change

## Integration Points

### In validate_core.py
```python
def test_database_schema():
    from database.schema_validator import validate_current_database
    return validate_current_database()

def test_database_data():
    from database.validators.data_validator import validate_current_database_data
    return validate_current_database_data()
```

### In Pipeline Classes
```python
class Pipeline:
    def __init__(self):
        self._validate_database_compatibility()

    def _validate_database_compatibility(self):
        from database.schemas.current import SHAPE_ID_FORMAT, VALID_STATUSES
        self.shape_id_format = SHAPE_ID_FORMAT
        self.valid_statuses = VALID_STATUSES
```

## Memory Bank Integration

Store database patterns in memory-bank/ for cross-project reference:
- `database-validation-patterns.md` (this file)
- `sql-query-safety.md`
- `schema-evolution-guide.md`

## Future Project Template

```
project/
├── database/
│   ├── schemas/
│   │   ├── current.py → v1_0_0.py
│   │   └── v1_0_0.py
│   ├── validators/
│   │   ├── schema_validator.py
│   │   └── data_validator.py
│   └── migrations/
│       └── 001_initial.sql
├── .windsurf/
│   └── database-validation.md
└── validate_core.py (includes DB validation)
```

## Benefits
- **Catch Issues Early**: Before runtime failures
- **Prevent Regressions**: When refactoring database code
- **Cross-Project Consistency**: Reusable patterns and templates
- **Team Collaboration**: Clear database contracts and standards
- **Debugging Speed**: Quick identification of schema vs code mismatches
