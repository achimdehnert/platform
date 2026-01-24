# Universal Database Schema Patterns for Any Project

## Database Schema Documentation Template

### Essential Schema Information to Document

#### 1. Table Structure Analysis
```python
# Always run this script to understand actual schema
def analyze_database_schema(db_path: str):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # Document: name, type, constraints, relationships
```

#### 2. Relationship Mapping Pattern
```
Parent Table (primary_key)
    ↓ 1:N relationship
Child Table (foreign_key, other_fields)
    ↓ 1:N relationship
Grandchild Table (child_foreign_key)
```

#### 3. Critical Query Patterns

**Isolation Pattern** (prevent cross-contamination):
```sql
-- CORRECT: Filter by parent context
SELECT child.* FROM child_table child
JOIN parent_table parent ON child.parent_id = parent.id
WHERE parent.project_id = ?

-- WRONG: Direct query without context
SELECT * FROM child_table WHERE some_field = ?
```

**JSON Field Handling**:
```python
# Always parse JSON fields
shape_dict['json_field'] = json.loads(shape_dict['json_field'])
```

### Universal Prevention Checklist

#### Schema Assumptions (NEVER ASSUME)
- ❌ Column names without verification
- ❌ Direct foreign key relationships
- ❌ ID format patterns
- ❌ Table structure without inspection

#### Required Documentation
- ✅ Actual table schema with PRAGMA table_info
- ✅ Relationship mapping with foreign keys
- ✅ Sample data for understanding formats
- ✅ Query patterns for common operations
- ✅ JSON field structure and parsing requirements

#### Isolation Requirements
- ✅ Always filter by project/presentation/session context
- ✅ Use proper JOINs for related data
- ✅ Never query child tables without parent context
- ✅ Validate data belongs to current context

### Project-Specific Implementation

#### Step 1: Schema Discovery
```python
# Create: check_database_schema.py
def document_actual_schema():
    # Analyze all tables, columns, relationships
    # Generate schema documentation
    # Create sample queries
```

#### Step 2: Relationship Mapping
```python
# Identify parent-child relationships
# Document foreign key constraints
# Map data isolation boundaries
```

#### Step 3: Query Pattern Creation
```python
# Create safe query templates
# Implement isolation filters
# Test cross-contamination prevention
```

#### Step 4: Validation Rules
```python
# Create data validators
# Implement schema validators
# Test edge cases and error conditions
```

### Memory Integration Points

#### .windsurf/rules
- Add database schema patterns to project rules
- Include isolation requirements
- Document query safety patterns

#### memory-bank/
- `database-schema-actual.md` - Current project schema
- `database-validation-patterns.md` - Project-specific patterns
- `universal-database-patterns.md` - Cross-project patterns

#### prevention-system-template/
- `database_validation_template.py` - Reusable validation code
- `schema_discovery_template.py` - Schema analysis tools
- `query_safety_template.py` - Safe query patterns

### Cross-Project Benefits

1. **Faster Onboarding**: Immediate schema understanding
2. **Bug Prevention**: Avoid cross-contamination and schema assumptions
3. **Consistent Patterns**: Reusable validation and query approaches
4. **Documentation Standards**: Always document actual vs. assumed schema
5. **Testing Framework**: Validate schema assumptions early

### Implementation for New Projects

```python
# 1. Run schema discovery
python check_database_schema.py

# 2. Document relationships
# Create relationship mapping diagram

# 3. Implement isolation
# Add proper filtering to all queries

# 4. Create validation
# Test cross-contamination prevention

# 5. Document patterns
# Update memory-bank with project-specific info
```

This universal approach prevents database-related bugs across any project by ensuring proper schema understanding and data isolation.
