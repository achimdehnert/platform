# @database-schema.md - SQLite Database Schema Documentation

## 🗄️ Database Overview

### Schema Analysis
This document tracks the existing SQLite database schema and Django model integration strategy.

### Database Inspection Commands

```bash
# View database schema
sqlite3 db.sqlite3 .schema

# List all tables
sqlite3 db.sqlite3 .tables

# Describe specific table
sqlite3 db.sqlite3 "PRAGMA table_info(table_name);"

# View table data sample
sqlite3 db.sqlite3 "SELECT * FROM table_name LIMIT 5;"
```

## 📊 Table Structure

### Core Tables
*To be populated after database inspection*

```sql
-- Example table structure will be documented here
-- after inspecting the existing SQLite database
```

### Relationships
*Foreign key relationships and constraints will be documented here*

## 🔄 Django Model Integration

### Model Generation Process

1. **Database Inspection**
   ```bash
   python manage.py inspectdb > temp_models.py
   ```

2. **Model Refinement**
   - Clean up field types
   - Add proper relationships
   - Implement model methods
   - Add Meta classes

3. **Migration Creation**
   ```bash
   python manage.py makemigrations
   python manage.py migrate --fake-initial
   ```

### Model Customizations

#### Field Type Mappings
- SQLite TEXT → Django CharField/TextField
- SQLite INTEGER → Django IntegerField
- SQLite REAL → Django FloatField
- SQLite BLOB → Django BinaryField

#### Relationship Handling
- Foreign keys → ForeignKey fields
- Many-to-many → ManyToManyField
- One-to-one → OneToOneField

## 🛠️ Migration Strategy

### Existing Data Preservation
- Use `--fake-initial` for first migration
- Create data migration scripts if needed
- Backup database before major changes
- Test migrations on development copy

### Migration Best Practices
- Keep migrations small and focused
- Document complex migrations
- Test rollback procedures
- Monitor migration performance

## 📝 Data Integrity

### Constraints
*Database constraints will be documented here*

### Validation Rules
*Business logic validation will be documented here*

### Indexes
*Database indexes will be documented here*

---

*This file will be updated after database inspection*
*Status: Template created - awaiting database analysis*
