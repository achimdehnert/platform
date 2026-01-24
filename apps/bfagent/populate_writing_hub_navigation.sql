-- Writing Hub Navigation Setup
-- Erstellt Sections und Items für das Writing Hub

-- ============================================================================
-- 1. WRITING HUB SECTIONS
-- ============================================================================

-- Writing Hub Domain ID finden (sollte 9 sein basierend auf vorherigen Queries)
-- Wenn unsicher: SELECT id, slug FROM domain_arts WHERE slug = 'writing-hub';

-- Section: CORE
INSERT OR IGNORE INTO navigation_sections (code, name, description, domain_id, icon, color, "order", is_active, is_collapsible, is_collapsed_default, created_at, updated_at)
VALUES ('writing_hub_core', 'CORE', 'Core writing functionality', 9, 'bi-pen', 'primary', 1, 1, 1, 0, datetime('now'), datetime('now'));

-- Section: STORY STRUCTURE  
INSERT OR IGNORE INTO navigation_sections (code, name, description, domain_id, icon, color, "order", is_active, is_collapsible, is_collapsed_default, created_at, updated_at)
VALUES ('writing_hub_story', 'STORY STRUCTURE', 'Story arcs, strands, and memories', 9, 'bi-diagram-3', 'info', 2, 1, 1, 0, datetime('now'), datetime('now'));

-- Section: CONTENT
INSERT OR IGNORE INTO navigation_sections (code, name, description, domain_id, icon, color, "order", is_active, is_collapsible, is_collapsed_default, created_at, updated_at)
VALUES ('writing_hub_content', 'CONTENT', 'Chapters, scenes, and plot points', 9, 'bi-journal-text', 'success', 3, 1, 1, 0, datetime('now'), datetime('now'));

-- Section: WORLD & CHARACTERS
INSERT OR IGNORE INTO navigation_sections (code, name, description, domain_id, icon, color, "order", is_active, is_collapsible, is_collapsed_default, created_at, updated_at)
VALUES ('writing_hub_world', 'WORLD & CHARACTERS', 'Characters, worlds, and settings', 9, 'bi-globe', 'warning', 4, 1, 1, 0, datetime('now'), datetime('now'));

-- Section: AI GENERATION
INSERT OR IGNORE INTO navigation_sections (code, name, description, domain_id, icon, color, "order", is_active, is_collapsible, is_collapsed_default, created_at, updated_at)
VALUES ('writing_hub_ai', 'AI GENERATION', 'AI-powered content generation logs', 9, 'bi-cpu-fill', 'danger', 5, 1, 1, 0, datetime('now'), datetime('now'));


-- ============================================================================
-- 2. NAVIGATION ITEMS - CORE
-- ============================================================================

-- Dashboard
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_dashboard', 'Dashboard', 'Writing Hub overview', 'internal', 'writing_hub:dashboard', 'bi-speedometer2', NULL, NULL, 1, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_core';

-- Book Projects
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_book_projects', 'Book Projects', 'Manage your book projects', 'internal', 'writing_hub:book_projects', 'bi-book', NULL, NULL, 2, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_core';

-- Story Projects
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_story_projects', 'Story Projects', 'Manage story projects', 'internal', 'writing_hub:story_projects', 'bi-journal-bookmark', NULL, NULL, 3, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_core';

-- Writing Statuses
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_statuses', 'Writing Statuses', 'Manage project statuses', 'internal', 'writing_hub:statuses', 'bi-flag', NULL, NULL, 4, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_core';


-- ============================================================================
-- 3. NAVIGATION ITEMS - STORY STRUCTURE
-- ============================================================================

-- Story Arcs
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_story_arcs', 'Story Arcs', 'Manage story arcs', 'internal', 'writing_hub:story_arcs', 'bi-bezier2', NULL, NULL, 1, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_story';

-- Story Strands
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_story_strands', 'Story Strands', 'Narrative threads and storylines', 'internal', 'writing_hub:story_strands', 'bi-layers', NULL, NULL, 2, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_story';

-- Story Memories
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_story_memories', 'Story Memories', 'Character memories and backstory', 'internal', 'writing_hub:story_memories', 'bi-stars', NULL, NULL, 3, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_story';


-- ============================================================================
-- 4. NAVIGATION ITEMS - CONTENT
-- ============================================================================

-- Chapters
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_chapters', 'Chapters', 'Manage book chapters', 'internal', 'writing_hub:chapters', 'bi-file-earmark-text', NULL, NULL, 1, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_content';

-- Story Chapters
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_story_chapters', 'Story Chapters', 'Story chapter organization', 'internal', 'writing_hub:story_chapters', 'bi-list-ol', NULL, NULL, 2, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_content';

-- Plot Points
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_plot_points', 'Plot Points', 'Key story moments and beats', 'internal', 'writing_hub:plot_points', 'bi-bullseye', NULL, NULL, 3, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_content';


-- ============================================================================
-- 5. NAVIGATION ITEMS - WORLD & CHARACTERS
-- ============================================================================

-- Characters
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_characters', 'Characters', 'Manage your characters', 'internal', 'writing_hub:characters', 'bi-people', NULL, NULL, 1, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_world';

-- Worlds
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_worlds', 'Worlds', 'Build your fictional worlds', 'internal', 'writing_hub:worlds', 'bi-globe2', NULL, NULL, 2, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_world';


-- ============================================================================
-- 6. NAVIGATION ITEMS - AI GENERATION
-- ============================================================================

-- Generation Logs
INSERT OR IGNORE INTO navigation_items (section_id, code, name, description, item_type, url_name, icon, badge_text, badge_color, "order", is_active, opens_in_new_tab, parent_id, created_at, updated_at)
SELECT id, 'wh_generation_logs', 'Generation Logs', 'AI content generation history', 'internal', 'writing_hub:generation_logs', 'bi-clock-history', NULL, NULL, 1, 1, 0, NULL, datetime('now'), datetime('now')
FROM navigation_sections WHERE code = 'writing_hub_ai';


-- ============================================================================
-- VERIFY
-- ============================================================================

-- Prüfe Sections
SELECT 'SECTIONS:' as type;
SELECT id, code, name, domain_id, icon, "order" 
FROM navigation_sections 
WHERE domain_id = 9
ORDER BY "order";

-- Prüfe Items
SELECT '' as separator;
SELECT 'ITEMS:' as type;
SELECT ni.id, ni.code, ni.name, ns.name as section_name, ni."order"
FROM navigation_items ni
JOIN navigation_sections ns ON ni.section_id = ns.id
WHERE ns.domain_id = 9
ORDER BY ns."order", ni."order";

-- Count
SELECT '' as separator;
SELECT 'TOTAL:' as label, COUNT(*) as sections FROM navigation_sections WHERE domain_id = 9;
SELECT 'TOTAL:' as label, COUNT(*) as items FROM navigation_items ni JOIN navigation_sections ns ON ni.section_id = ns.id WHERE ns.domain_id = 9;
