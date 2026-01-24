-- =============================================================================
-- BF Agent Database Initialization Script
-- =============================================================================
-- This script runs automatically when the PostgreSQL container starts
-- for the first time.
-- =============================================================================

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Create additional databases if needed
-- CREATE DATABASE bfagent_test;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE bfagent_dev TO bfagent;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'BF Agent database initialized successfully!';
END $$;
