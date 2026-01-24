-- Drop workflow tables to recreate them with correct schema
-- Run: python manage.py dbshell < drop_workflow_tables.sql

DROP TABLE IF EXISTS project_phase_history;
DROP TABLE IF EXISTS phase_action_configs;
DROP TABLE IF EXISTS workflow_phase_steps;
DROP TABLE IF EXISTS workflow_templates;
DROP TABLE IF EXISTS workflow_phases;

-- Delete migration record so it can be reapplied
DELETE FROM django_migrations WHERE name = '0015_add_workflow_engine_system';
