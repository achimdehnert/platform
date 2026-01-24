# Systematic Development Protocol

## Pre-Development Investigation

### 1. Search Before Creating
Always use these tools before implementing new functionality:

```bash
# Search for existing functionality
grep_search --query "functionality_keyword" --path "develop/"

# Find related files
find_by_name --pattern "*keyword*" --directory "develop/"
```

### 2. Investigation Checklist
- [ ] Search for similar existing implementations
- [ ] Check service layer patterns
- [ ] Review UI component patterns
- [ ] Verify database interaction patterns
- [ ] Look for AI agent integration examples

### 3. Pattern Reuse Strategy
- **Service Layer**: Use existing `*Service` classes (BookProjectService, etc.)
- **UI Components**: Follow Streamlit session state patterns
- **Database**: Use established factory patterns with proper session handling
- **AI Integration**: Reuse existing agent interfaces (plot_agent_interface.py)

## Implementation Examples from BookFactory

### Plot Agent Integration
✅ **Found existing**: `plot_agent_interface.py`
❌ **Avoided**: Creating new plot agent implementation
✅ **Reused**: Session state toggle pattern

### Form Persistence Fix
✅ **Found existing**: `BookProjectService.update_project()`
❌ **Avoided**: Creating new save mechanism
✅ **Extended**: Added missing fields to `valid_fields`

### Database Migration
✅ **Found existing**: SQLite table recreation pattern
❌ **Avoided**: Complex ALTER TABLE operations
✅ **Reused**: Backup and rollback strategy

## Memory Management Protocol

### Update Memories After:
- Major architectural decisions
- Successful integration patterns
- Database schema changes
- UI component implementations
- AI agent integrations

### Memory Categories:
- `architecture`: System design patterns
- `database_migration`: Schema evolution strategies
- `ui_patterns`: Streamlit component patterns
- `ai_integration`: Agent interface patterns
- `development_protocol`: Process improvements

## Benefits
- Prevents duplicate implementations
- Maintains architectural consistency
- Reduces development time
- Preserves established patterns
- Enables seamless context continuation
