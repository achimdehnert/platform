-- System-Daten Restore Script
-- ==============================
-- Kopiert essentielle System-Daten von Backup-DB in neue DB
--
-- Verwendung:
--   1. Backup erstellen: copy db.sqlite3 db_backup.sqlite3
--   2. DB reset: remove db.sqlite3, python manage.py migrate
--   3. Dieses Script ausführen (siehe unten)

-- WICHTIG: Diese Tabellen enthalten System-Konfiguration (KEINE Bewegungsdaten)
-- ============================================================================

-- CORE Models
-- -----------
-- domains (Tabelle: core_domain)
-- handlers (Tabelle: core_handler)
-- handlercategory (Tabelle: core_handlercategory)

-- BFAGENT Models
-- --------------
-- llms (Tabelle: bfagent_llms)
-- agents (Tabelle: bfagent_agents)
-- agenttype (Tabelle: bfagent_agenttype)
-- domainart (Tabelle: bfagent_domainart)
-- domaintype (Tabelle: bfagent_domaintype)
-- domainphase (Tabelle: bfagent_domainphase)
-- actionhandler (Tabelle: bfagent_actionhandler)

-- CONTROL CENTER Models
-- --------------------
-- workflowdomain (Tabelle: control_center_workflowdomain)
-- navigationsection (Tabelle: control_center_navigationsection)
-- navigationitem (Tabelle: control_center_navigationitem)

-- WRITING HUB Models
-- -----------------
-- handlerphase (Tabelle: writing_hub_handlerphase)

-- GENAGENT Models
-- --------------
-- phase (Tabelle: genagent_phase)
-- action (Tabelle: genagent_action)
-- customdomain (Tabelle: genagent_customdomain)

-- BFAGENT MCP Models
-- -----------------
-- domain (Tabelle: bfagent_mcp_domain)
-- phase (Tabelle: bfagent_mcp_phase)
-- handler (Tabelle: bfagent_mcp_handler)
-- bestpractice (Tabelle: bfagent_mcp_bestpractice)
-- prompttemplate (Tabelle: bfagent_mcp_prompttemplate)

-- =============================================================================
-- AUSFÜHRUNG (nach DB-Reset)
-- =============================================================================

-- In PowerShell:
-- --------------
-- sqlite3 db.sqlite3 < scripts\restore_system_data.sql

-- ODER manuell in SQLite:
-- ----------------------
-- .open db.sqlite3
-- ATTACH DATABASE 'db_backup.sqlite3' AS backup;
-- [dann die INSERT Statements unten ausführen]

-- =============================================================================
-- RESTORE COMMANDS (zum Kopieren in SQLite)
-- =============================================================================

ATTACH DATABASE 'db_backup.sqlite3' AS backup;

-- Core Models
INSERT OR REPLACE INTO core_domain SELECT * FROM backup.core_domain;
INSERT OR REPLACE INTO core_handler SELECT * FROM backup.core_handler;
INSERT OR REPLACE INTO core_handlercategory SELECT * FROM backup.core_handlercategory;

-- BFAgent Essential Models
INSERT OR REPLACE INTO bfagent_llms SELECT * FROM backup.bfagent_llms;
INSERT OR REPLACE INTO bfagent_agents SELECT * FROM backup.bfagent_agents;
INSERT OR REPLACE INTO bfagent_agenttype SELECT * FROM backup.bfagent_agenttype;
INSERT OR REPLACE INTO bfagent_domainart SELECT * FROM backup.bfagent_domainart;
INSERT OR REPLACE INTO bfagent_domaintype SELECT * FROM backup.bfagent_domaintype;
INSERT OR REPLACE INTO bfagent_domainphase SELECT * FROM backup.bfagent_domainphase;
INSERT OR REPLACE INTO bfagent_actionhandler SELECT * FROM backup.bfagent_actionhandler;

-- Control Center Navigation
INSERT OR REPLACE INTO control_center_workflowdomain SELECT * FROM backup.control_center_workflowdomain;
INSERT OR REPLACE INTO control_center_navigationsection SELECT * FROM backup.control_center_navigationsection;
INSERT OR REPLACE INTO control_center_navigationitem SELECT * FROM backup.control_center_navigationitem;

-- Writing Hub
INSERT OR REPLACE INTO writing_hub_handlerphase SELECT * FROM backup.writing_hub_handlerphase;

-- GenAgent
INSERT OR REPLACE INTO genagent_phase SELECT * FROM backup.genagent_phase;
INSERT OR REPLACE INTO genagent_action SELECT * FROM backup.genagent_action;
INSERT OR REPLACE INTO genagent_customdomain SELECT * FROM backup.genagent_customdomain;

-- BFAgent MCP
INSERT OR REPLACE INTO bfagent_mcp_domain SELECT * FROM backup.bfagent_mcp_domain;
INSERT OR REPLACE INTO bfagent_mcp_phase SELECT * FROM backup.bfagent_mcp_phase;
INSERT OR REPLACE INTO bfagent_mcp_handler SELECT * FROM backup.bfagent_mcp_handler;
INSERT OR REPLACE INTO bfagent_mcp_bestpractice SELECT * FROM backup.bfagent_mcp_bestpractice;
INSERT OR REPLACE INTO bfagent_mcp_prompttemplate SELECT * FROM backup.bfagent_mcp_prompttemplate;

DETACH DATABASE backup;

-- =============================================================================
-- VERIFICATION (Anzahl kopierter Zeilen prüfen)
-- =============================================================================

-- SELECT 'core_domain' as table_name, COUNT(*) as rows FROM core_domain
-- UNION ALL SELECT 'core_handler', COUNT(*) FROM core_handler
-- UNION ALL SELECT 'bfagent_llms', COUNT(*) FROM bfagent_llms
-- UNION ALL SELECT 'bfagent_agents', COUNT(*) FROM bfagent_agents
-- UNION ALL SELECT 'control_center_navigationitem', COUNT(*) FROM control_center_navigationitem;
