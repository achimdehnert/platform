---
description: Create database backups for any app
---

# Database Backup Workflow

## Trigger

User says one of:
- "Backup [app/database]"
- "Erstelle Backup für [app]"
- "Sichere die Datenbank"

## Database Configuration

| App | Database Name | Backup Path |
|-----|---------------|-------------|
| bfagent | bfagent_prod | /opt/backups/bfagent/ |
| cad-hub | cadhub_prod | /opt/backups/cadhub/ |
| travel-beat | travelbeat_prod | /opt/backups/travelbeat/ |
| trading-hub | tradinghub_prod | /opt/backups/tradinghub/ |

Host: 88.198.191.108

## Step 1: Identify Database

Parse user input to determine which database to backup.
If unclear, ask: "Welche Datenbank soll ich sichern?"

## Step 2: Show Backup Plan

```text
💾 Backup Plan

Database: [db_name]
Host: 88.198.191.108
Format: custom (pg_dump -Fc)
Target: [backup_path]

Proceed? [Ja/Nein]
```

## Step 3: Create Backup

// turbo
Use mcp5_db_backup with:
- db_name: [database name]
- backup_path: [configured path]
- format_type: custom

## Step 4: Verify

// turbo
Use mcp5_db_backup_list to show available backups

## Step 5: Report

```text
✅ Backup Complete

Database: [db_name]
File: [backup_filename]
Size: [file_size]

Available Backups:
[list from mcp5_db_backup_list]
```
