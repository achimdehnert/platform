# Database Migration Patterns for BookFactory

## TEXT Field Migration Strategy

### When to Use TEXT vs VARCHAR
- **TEXT Fields**: Unlimited content (story_premise, main_conflict, chapter content)
- **VARCHAR Fields**: Predictable length limits (names, titles, short descriptions)

### Migration Process for SQLite
1. **Schema Analysis**
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('bookfactory.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(table_name)'); [print(f'{i}: {col}') for i, col in enumerate(cursor.fetchall())]; conn.close()"
   ```

2. **Table Recreation Pattern**
   ```python
   # Create new table with updated schema
   cursor.execute("CREATE TABLE table_new (...)")

   # Copy all data
   cursor.execute("INSERT INTO table_new SELECT * FROM table_old")

   # Replace old table
   cursor.execute("DROP TABLE table_old")
   cursor.execute("ALTER TABLE table_new RENAME TO table_old")
   ```

3. **Always Include**
   - Database backup before migration
   - Transaction rollback on failure
   - Data integrity verification
   - Exact column order matching

### BookProject Schema (26 columns)
```sql
id, title, genre, content_rating, description, tagline, target_word_count,
current_word_count, status, deadline, created_at, updated_at, story_premise,
target_audience, story_themes, setting_time, setting_location, atmosphere_tone,
main_conflict, stakes, protagonist_concept, antagonist_concept,
inspiration_sources, unique_elements, genre_settings, book_type_id
```

### Successful TEXT Migrations
- `story_premise`: Complex story concepts
- `main_conflict`: Detailed conflict descriptions
- `description`: Comprehensive project descriptions
- `genre_settings`: Flexible JSON configurations
- `Chapter.content`: Already uses `sa_column=Column(Text)`
- `Scene.content`: Already uses `sa_column=Column(Text)`
