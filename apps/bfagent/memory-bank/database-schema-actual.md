# Actual Database Schema - medAI Localization Project

## Critical Database Structure Information

**Database File**: `analysis.db`
**Schema Version**: V5.1 (as of 2025-09-02)

### Table Structure Overview

#### 1. presentations
```sql
CREATE TABLE presentations (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT,
    total_slides INTEGER DEFAULT 0,
    total_shapes INTEGER DEFAULT 0,
    total_translatable INTEGER DEFAULT 0,
    analysis_version TEXT DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. slides
```sql
CREATE TABLE slides (
    slide_id TEXT PRIMARY KEY,
    presentation_id INTEGER NOT NULL,
    slide_index INTEGER NOT NULL,
    slide_title TEXT,
    slide_type TEXT DEFAULT 'content',
    slide_layout TEXT,
    layout_name TEXT,
    total_shapes INTEGER DEFAULT 0,
    translatable_shapes INTEGER DEFAULT 0,
    analysis_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. shapes (MAIN TABLE)
```sql
CREATE TABLE shapes (
    shape_id TEXT PRIMARY KEY,
    slide_id TEXT NOT NULL,           -- Links to slides.slide_id
    slide_index INTEGER NOT NULL,
    shape_index INTEGER NOT NULL,
    shape_type TEXT NOT NULL,
    shape_name TEXT,
    object_type TEXT,
    original_text TEXT,
    translated_text TEXT,
    text_content TEXT,               -- JSON array
    has_text BOOLEAN DEFAULT FALSE,
    formatting TEXT,                 -- JSON object
    position TEXT,                   -- JSON object
    extracted_structure TEXT,
    metadata TEXT,
    is_translatable BOOLEAN DEFAULT TRUE,
    status TEXT DEFAULT 'pending',   -- 'pending', 'translated', etc.
    priority INTEGER DEFAULT 2,
    translation_priority INTEGER DEFAULT 2,
    manual_override BOOLEAN DEFAULT FALSE,
    analysis_version TEXT DEFAULT '1.0',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    structured_text TEXT
);
```

#### 4. shape_audit
```sql
CREATE TABLE shape_audit (
    id INTEGER PRIMARY KEY,
    shape_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT DEFAULT 'system',
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Critical Relationships

**Presentation Isolation Pattern**:
```
presentations (id)
    ↓ 1:N
slides (presentation_id, slide_id)
    ↓ 1:N
shapes (slide_id)
```

### Key Insights for Development

1. **NO DIRECT presentation_id in shapes table**
   - Must join through slides table: `shapes.slide_id = slides.slide_id`
   - Filter by presentation: `slides.presentation_id = ?`

2. **Shape ID Format**: `S{slide_number}-{shape_index}`
   - Example: `S4-1`, `S4-2`, `S4-3`
   - NOT `LAYOUT-X-Y` format

3. **JSON Fields** (require parsing):
   - `text_content`: Array of text strings
   - `formatting`: Complex formatting object with runs
   - `position`: Coordinate and size information

4. **Translation Status Values**:
   - `pending`: Not yet translated
   - `translated`: Translation completed
   - Other custom statuses possible

### Common Query Patterns

**Get shapes for specific presentation**:
```sql
SELECT shapes.* FROM shapes
JOIN slides ON shapes.slide_id = slides.slide_id
WHERE slides.presentation_id = ?
AND shapes.is_translatable = TRUE
```

**Prevent cross-contamination**:
- ALWAYS filter by presentation_id when retrieving shapes
- Use proper JOIN with slides table
- Never query shapes table directly without presentation context

### Prevention Checklist

- ✅ Always use presentation_id filter in shape queries
- ✅ Join shapes with slides table for isolation
- ✅ Parse JSON fields (text_content, formatting, position)
- ✅ Use correct shape_id format (S{slide}-{shape})
- ✅ Check status field for translation state
- ❌ Never assume presentation_id exists in shapes table
- ❌ Never use LAYOUT-X-Y shape ID format
- ❌ Never query shapes without presentation context

### Database Stats (as of 2025-09-02)
- Presentations: 6
- Slides: 109
- Shapes: 307
- Shape Audit: 0

This schema documentation prevents cross-contamination bugs and ensures proper presentation isolation in the translation pipeline.
