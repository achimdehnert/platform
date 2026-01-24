-- Handler System Lookup Tables
-- Phase 2: Handler System Refactoring

-- 1. Handler Categories
CREATE TABLE IF NOT EXISTS handler_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(20) DEFAULT 'primary',
    icon VARCHAR(50) DEFAULT 'bi-gear',
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data
INSERT INTO handler_categories (code, name, description, color, icon, sort_order) VALUES
('input', 'Input Handler', 'Handlers that read and validate input data', 'info', 'bi-download', 1),
('processing', 'Processing Handler', 'Handlers that process and transform data', 'primary', 'bi-gear-fill', 2),
('output', 'Output Handler', 'Handlers that write and format output data', 'success', 'bi-upload', 3);

-- 2. Handler Phases
CREATE TABLE IF NOT EXISTS handler_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    execution_order INTEGER DEFAULT 0,
    color VARCHAR(20) DEFAULT 'info',
    icon VARCHAR(50) DEFAULT 'bi-arrow-right',
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data
INSERT INTO handler_phases (code, name, description, execution_order, color, icon, sort_order) VALUES
('input', 'Input Phase', 'Data collection and validation phase', 1, 'info', 'bi-box-arrow-in-down', 1),
('processing', 'Processing Phase', 'Data transformation and processing phase', 2, 'primary', 'bi-cpu', 2),
('output', 'Output Phase', 'Result formatting and output phase', 3, 'success', 'bi-box-arrow-up', 3);

-- 3. Error Strategies
CREATE TABLE IF NOT EXISTS error_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    stops_execution BOOLEAN DEFAULT 0,
    allows_retry BOOLEAN DEFAULT 0,
    max_retries INTEGER DEFAULT 0,
    color VARCHAR(20) DEFAULT 'warning',
    icon VARCHAR(50) DEFAULT 'bi-exclamation-triangle',
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data
INSERT INTO error_strategies (code, name, description, stops_execution, allows_retry, max_retries, color, icon, sort_order) VALUES
('stop', 'Stop Execution', 'Stop the entire workflow when an error occurs', 1, 0, 0, 'danger', 'bi-stop-circle-fill', 1),
('skip', 'Skip Handler & Continue', 'Skip the failed handler and continue with the next one', 0, 0, 0, 'warning', 'bi-skip-forward-fill', 2),
('retry', 'Retry Handler', 'Retry the failed handler with exponential backoff', 0, 1, 3, 'info', 'bi-arrow-repeat', 3),
('fallback', 'Use Fallback Handler', 'Use an alternative handler if the primary one fails', 0, 0, 0, 'secondary', 'bi-arrow-down-up', 4);
