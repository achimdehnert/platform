-- Writing Hub Lookup Tables
-- Direkt erstellen statt über Django Migrations

-- 1. Content Ratings
CREATE TABLE IF NOT EXISTS writing_content_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    min_age INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data
INSERT INTO writing_content_ratings (code, name, description, min_age, sort_order) VALUES
('G', 'General Audiences', 'All ages admitted. Nothing that would offend parents for viewing by children.', 0, 1),
('PG', 'Parental Guidance', 'Some material may not be suitable for children. Parents urged to give "parental guidance."', 7, 2),
('PG-13', 'Parents Strongly Cautioned', 'Some material may be inappropriate for children under 13. Parents are urged to be cautious.', 13, 3),
('R', 'Restricted', 'Under 17 requires accompanying parent or adult guardian. Contains adult material.', 17, 4),
('NC-17', 'Adults Only', 'No one 17 and under admitted. Clearly adult content.', 18, 5);

-- 2. Writing Stages
CREATE TABLE IF NOT EXISTS writing_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    progress_percentage INTEGER DEFAULT 0,
    color VARCHAR(20) DEFAULT 'secondary',
    icon VARCHAR(50) DEFAULT 'bi-pencil',
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data
INSERT INTO writing_stages (code, name, description, progress_percentage, color, icon, sort_order) VALUES
('planning', 'Planning', 'Initial planning and brainstorming phase', 0, 'info', 'bi-lightbulb', 1),
('outlining', 'Outlining', 'Creating structure and outline', 10, 'primary', 'bi-list-ul', 2),
('drafting', 'Drafting', 'Writing the first draft', 25, 'warning', 'bi-pencil', 3),
('editing', 'Editing', 'Revising and editing content', 70, 'danger', 'bi-eraser', 4),
('reviewing', 'Reviewing', 'Final review and proofreading', 90, 'secondary', 'bi-eye', 5),
('published', 'Published', 'Work is published', 100, 'success', 'bi-check-circle', 6);

-- 3. Arc Types
CREATE TABLE IF NOT EXISTS writing_arc_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(20) DEFAULT 'primary',
    icon VARCHAR(50) DEFAULT 'bi-diagram-3',
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data
INSERT INTO writing_arc_types (code, name, description, color, icon, sort_order) VALUES
('main', 'Main Plot', 'The primary story arc driving the narrative', 'primary', 'bi-diagram-3-fill', 1),
('subplot', 'Subplot', 'A secondary story arc that supports or contrasts the main plot', 'secondary', 'bi-diagram-2', 2),
('character', 'Character Arc', 'Character development and transformation arc', 'info', 'bi-person', 3);

-- 4. Importance Levels
CREATE TABLE IF NOT EXISTS writing_importance_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(20) DEFAULT 'secondary',
    icon VARCHAR(50) DEFAULT 'bi-flag',
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data
INSERT INTO writing_importance_levels (code, name, description, color, icon, sort_order) VALUES
('critical', 'Critical', 'Critical importance - must have', 'danger', 'bi-exclamation-triangle-fill', 1),
('major', 'Major', 'Major importance - should have', 'warning', 'bi-flag-fill', 2),
('minor', 'Minor', 'Minor importance - nice to have', 'secondary', 'bi-flag', 3);
