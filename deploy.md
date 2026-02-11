---
description: Deploy any app to production (bfagent, cad-hub, travel-beat, etc.)
---

# Universal Deployment Workflow

## Trigger

User says one of:
- "Deploy [app-name]"
- "Deploye [app-name]"
- "Deploy latest changes to [app-name]"

## App Configuration

| App Name | Host | Project Path | Compose File | Verify URL |
|----------|------|--------------|--------------|------------|
| bfagent | 88.198.191.108 | /opt/bfagent-app | docker-compose.prod.yml | https://bfagent.iil.pet/login/ |
| travel-beat | 88.198.191.108 | /opt/travel-beat | docker-compose.prod.yml | https://travel-beat.iil.pet/ |
| risk-hub | 88.198.191.108 | /opt/risk-hub | docker-compose.prod.yml | https://risk-hub.iil.pet/ |
| mcp-hub | 88.198.191.108 | /opt/mcp-hub | docker-compose.yml | https://mcp-hub.iil.pet/ |
| cad-hub | 88.198.191.108 | /opt/cad-hub | docker-compose.yml | https://cadhub.iil.pet/ |
| weltenhub | 88.198.191.108 | /opt/weltenhub | docker-compose.prod.yml | https://weltenforger.com/ |
| trading-hub | 88.198.191.108 | /opt/trading-hub | docker-compose.prod.yml | https://ai-trades.de/livez/ |
| wedding-hub | 88.198.191.108 | /opt/wedding-hub | docker-compose.prod.yml | https://wedding-hub.iil.pet/ |

## Step 1: Identify App

Parse user input to determine which app to deploy.
If unclear, ask: "Welche App soll ich deployen?"

## Step 2: Get Latest Commit (AUTOMATIC)

// turbo
Get the latest commit SHA automatically - DO NOT ask the user:
```
mcp7_list_commits owner=achimdehnert repo=[app-name] perPage=1
```

## Step 3: Show Deployment Plan

```text
🚀 Deployment Plan

App: [app-name]
Host: [host]
Path: [project_path]
Latest Commit: [sha] - "[message]"
URL: [verify_url]

Proceed? [Ja/Nein]
```

## Step 4: Deploy (after user confirms)

// turbo
Execute via SSH:
```bash
ssh root@[host] "cd [project_path] && docker compose -f [compose_file] pull && docker compose -f [compose_file] up -d --force-recreate"
```

## Step 5: Verify

// turbo
1. Check container status: mcp5_container_list
2. Verify all containers are running

## Step 6: Report

```text
✅ Deployment Complete

App: [app-name]
Commit: [sha]
Status: [running/failed]
URL: [verify_url]

Container Status:
[list of containers and their status]
```
