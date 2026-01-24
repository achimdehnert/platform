-- Writing Hub Navigation Items
-- Fügt Items zu den erstellten Sections hinzu

-- ============================================================================
-- CORE SECTION (ID: 30)
-- ============================================================================

INSERT INTO navigation_items (section_id, code, name, description, item_type, url_name, url_params, external_url, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, created_at, updated_at)
VALUES 
(30, 'wh_dashboard', 'Dashboard', 'Writing Hub overview', 'internal', 'writing_hub:dashboard', '{}', '', 'bi-speedometer2', '', '', 1, 1, 0, datetime('now'), datetime('now')),
(30, 'wh_book_projects', 'Book Projects', 'Manage your book projects', 'internal', 'bookwriting:projects', '{}', '', 'bi-book', '', '', 2, 1, 0, datetime('now'), datetime('now')),
(30, 'wh_story_projects', 'Story Projects', 'Manage story projects', 'internal', 'writing_hub:story_projects', '{}', '', 'bi-journal-bookmark', '', '', 3, 1, 0, datetime('now'), datetime('now')),
(30, 'wh_statuses', 'Writing Statuses', 'Manage project statuses', 'internal', 'writing_hub:statuses', '{}', '', 'bi-flag', '', '', 4, 1, 0, datetime('now'), datetime('now'));

-- ============================================================================
-- STORY STRUCTURE SECTION (ID: 31)
-- ============================================================================

INSERT INTO navigation_items (section_id, code, name, description, item_type, url_name, url_params, external_url, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, created_at, updated_at)
VALUES
(31, 'wh_story_arcs', 'Story Arcs', 'Manage story arcs', 'internal', 'writing_hub:story_arcs', '{}', '', 'bi-bezier2', '', '', 1, 1, 0, datetime('now'), datetime('now')),
(31, 'wh_story_strands', 'Story Strands', 'Narrative threads and storylines', 'internal', 'writing_hub:story_strands', '{}', '', 'bi-layers', '', '', 2, 1, 0, datetime('now'), datetime('now')),
(31, 'wh_story_memories', 'Story Memories', 'Character memories and backstory', 'internal', 'writing_hub:story_memories', '{}', '', 'bi-stars', '', '', 3, 1, 0, datetime('now'), datetime('now'));

-- ============================================================================
-- CONTENT SECTION (ID: 32)
-- ============================================================================

INSERT INTO navigation_items (section_id, code, name, description, item_type, url_name, url_params, external_url, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, created_at, updated_at)
VALUES
(32, 'wh_chapters', 'Chapters', 'Manage book chapters', 'internal', 'bookwriting:chapters', '{}', '', 'bi-file-earmark-text', '', '', 1, 1, 0, datetime('now'), datetime('now')),
(32, 'wh_story_chapters', 'Story Chapters', 'Story chapter organization', 'internal', 'writing_hub:story_chapters', '{}', '', 'bi-list-ol', '', '', 2, 1, 0, datetime('now'), datetime('now')),
(32, 'wh_plot_points', 'Plot Points', 'Key story moments and beats', 'internal', 'writing_hub:plot_points', '{}', '', 'bi-bullseye', '', '', 3, 1, 0, datetime('now'), datetime('now'));

-- ============================================================================
-- WORLD & CHARACTERS SECTION (ID: 33)
-- ============================================================================

INSERT INTO navigation_items (section_id, code, name, description, item_type, url_name, url_params, external_url, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, created_at, updated_at)
VALUES
(33, 'wh_characters', 'Characters', 'Manage your characters', 'internal', 'bookwriting:characters', '{}', '', 'bi-people', '', '', 1, 1, 0, datetime('now'), datetime('now')),
(33, 'wh_worlds', 'Worlds', 'Build your fictional worlds', 'internal', 'bookwriting:worlds', '{}', '', 'bi-globe2', '', '', 2, 1, 0, datetime('now'), datetime('now'));

-- ============================================================================
-- AI GENERATION SECTION (ID: 34)
-- ============================================================================

INSERT INTO navigation_items (section_id, code, name, description, item_type, url_name, url_params, external_url, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, created_at, updated_at)
VALUES
(34, 'wh_generation_logs', 'Generation Logs', 'AI content generation history', 'internal', 'writing_hub:generation_logs', '{}', '', 'bi-clock-history', '', '', 1, 1, 0, datetime('now'), datetime('now'));

-- ============================================================================
-- VERIFY
-- ============================================================================

SELECT '=== WRITING HUB NAVIGATION ===' as info;
SELECT '' as empty;

SELECT 'SECTIONS:' as type;
SELECT id, code, name, "order" 
FROM navigation_sections 
WHERE domain_id = 9
ORDER BY "order";

SELECT '' as empty;
SELECT 'ITEMS:' as type;
SELECT ni.id, ni.code, ni.name, ns.name as section_name, ni."order"
FROM navigation_items ni
JOIN navigation_sections ns ON ni.section_id = ns.id
WHERE ns.domain_id = 9
ORDER BY ns."order", ni."order";

SELECT '' as empty;
SELECT 'TOTALS:' as label;
SELECT 'Sections:' as type, COUNT(*) as count FROM navigation_sections WHERE domain_id = 9
UNION ALL
SELECT 'Items:' as type, COUNT(*) as count FROM navigation_items ni JOIN navigation_sections ns ON ni.section_id = ns.id WHERE ns.domain_id = 9;
