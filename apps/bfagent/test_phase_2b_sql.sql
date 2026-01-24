-- ============================================================================
-- Phase 2b - SQL Test Queries
-- Teste Handler Normalisierung direkt in der Datenbank
-- ============================================================================

-- TEST 1: Zeige alle HandlerCategory Records
-- Erwartung: 3 Records (input, processing, output)
SELECT 
    id,
    code,
    name,
    display_order,
    is_system,
    is_active
FROM handler_categories
ORDER BY display_order;

-- ============================================================================

-- TEST 2: Zeige Handler Table Schema
PRAGMA table_info(handlers);

-- ============================================================================

-- TEST 3: Zähle Handler pro Kategorie (ALT - CharField)
SELECT 
    category as old_category,
    COUNT(*) as handler_count
FROM handlers
GROUP BY category
ORDER BY category;

-- ============================================================================

-- TEST 4: Zähle Handler pro Kategorie (NEU - FK)
SELECT 
    hc.code as category_code,
    hc.name as category_name,
    COUNT(h.id) as handler_count
FROM handler_categories hc
LEFT JOIN handlers h ON h.category_id = hc.id
GROUP BY hc.id, hc.code, hc.name
ORDER BY hc.display_order;

-- ============================================================================

-- TEST 5: Zeige Handler mit beiden Category-Feldern
SELECT 
    h.id,
    h.code,
    h.name,
    h.category as old_category,
    hc.code as new_category,
    CASE 
        WHEN h.category = hc.code THEN '✓ Match'
        WHEN h.category_id IS NULL THEN '⚠ Not Migrated'
        ELSE '✗ Mismatch'
    END as status
FROM handlers h
LEFT JOIN handler_categories hc ON h.category_id = hc.id
LIMIT 10;

-- ============================================================================

-- TEST 6: Finde Handler ohne category_fk (nicht migriert)
SELECT 
    id,
    code,
    name,
    category as old_category
FROM handlers
WHERE category_id IS NULL;

-- ============================================================================

-- TEST 7: Finde Handler mit Mismatch (category ≠ category_fk)
SELECT 
    h.id,
    h.code,
    h.name,
    h.category as old_value,
    hc.code as new_value
FROM handlers h
INNER JOIN handler_categories hc ON h.category_id = hc.id
WHERE h.category != hc.code;

-- ============================================================================

-- TEST 8: Performance Check - Index Usage
-- Prüfe ob Indizes existieren
SELECT 
    name,
    tbl_name,
    sql
FROM sqlite_master
WHERE type = 'index' 
  AND tbl_name IN ('handlers', 'handler_categories')
ORDER BY tbl_name, name;

-- ============================================================================

-- TEST 9: Foreign Key Constraints Check
PRAGMA foreign_key_list(handlers);

-- ============================================================================

-- TEST 10: Statistiken
SELECT 
    'Total Handlers' as metric,
    COUNT(*) as value
FROM handlers

UNION ALL

SELECT 
    'Migrated Handlers' as metric,
    COUNT(*) as value
FROM handlers
WHERE category_id IS NOT NULL

UNION ALL

SELECT 
    'Not Migrated' as metric,
    COUNT(*) as value
FROM handlers
WHERE category_id IS NULL

UNION ALL

SELECT 
    'Total Categories' as metric,
    COUNT(*) as value
FROM handler_categories

UNION ALL

SELECT 
    'Active Categories' as metric,
    COUNT(*) as value
FROM handler_categories
WHERE is_active = 1;

-- ============================================================================
-- BONUS: Detaillierte Handler-Übersicht
-- ============================================================================

SELECT 
    h.id,
    h.code as handler_code,
    h.name as handler_name,
    h.category as old_category,
    hc.code as new_category,
    hc.name as category_name,
    h.is_active,
    h.is_deprecated,
    h.total_executions,
    h.success_rate,
    CASE 
        WHEN h.category_id IS NULL THEN '❌ Not Migrated'
        WHEN h.category = hc.code THEN '✅ Migrated OK'
        ELSE '⚠️ Mismatch'
    END as migration_status
FROM handlers h
LEFT JOIN handler_categories hc ON h.category_id = hc.id
ORDER BY migration_status, hc.display_order, h.code;
