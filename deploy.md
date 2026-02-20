---
description: Deploy any app to production (bfagent, cad-hub, travel-beat, etc.)
---

# Deploy Workflow

## Automatischer Deploy (dev-hub)

Jeder `git push` auf `main` des `dev-hub` Repos deployt **automatisch** via GitHub Actions
self-hosted Runner auf dev-server (46.225.113.1) → prod-server (88.198.191.108).

Kein manueller Eingriff nötig. Status: https://github.com/achimdehnert/dev-hub/actions

---

## Manueller Deploy

### dev-hub (https://devhub.iil.pet)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh dev-hub'`

### bfagent (https://bfagent.iil.pet)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh bfagent'`

### weltenhub (https://weltenforger.com)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh weltenhub'`

### travel-beat (https://drifttales.app)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh travel-beat'`

### risk-hub (Schutztat)

// turbo
Run: `ssh root@88.198.191.108 'bash /opt/scripts/deploy.sh risk-hub'`

---

## Runner-Management (dev-hub CI/CD)

### Runner-Status prüfen

// turbo
Run: `ssh deploy@46.225.113.1 "sudo systemctl status actions.runner.achimdehnert-dev-hub.dev-server.service --no-pager | tail -5"`

### Runner neu starten

// turbo
Run: `ssh deploy@46.225.113.1 "sudo systemctl restart actions.runner.achimdehnert-dev-hub.dev-server.service"`

### Runner-Log (letzte Runs)

// turbo
Run: `ssh deploy@46.225.113.1 "sudo journalctl -u actions.runner.achimdehnert-dev-hub.dev-server.service --since '1 hour ago' --no-pager | tail -20"`

### Session-Konflikt beheben

// turbo
Run: `ssh deploy@46.225.113.1 "pkill -f 'Runner.Listener' 2>/dev/null; sudo systemctl restart actions.runner.achimdehnert-dev-hub.dev-server.service"`

### Runner neu registrieren (Token erforderlich)
Token holen: https://github.com/achimdehnert/dev-hub/settings/actions/runners/new

// turbo
Run: `ssh deploy@46.225.113.1 "rm -f ~/actions-runner/.credentials ~/actions-runner/.runner && sudo rm -f /etc/systemd/system/actions.runner.achimdehnert-dev-hub.dev-server.service && sudo systemctl daemon-reload && echo CLEAN"`

Dann mit neuem Token:
Run: `ssh deploy@46.225.113.1 "cd ~/actions-runner && ./config.sh --url https://github.com/achimdehnert/dev-hub --token TOKEN --name dev-server --labels self-hosted,dev-server --unattended --replace && sudo ./svc.sh install && sudo ./svc.sh start"`

---

## Troubleshooting

- **Deploy schlägt fehl**: `ssh root@88.198.191.108 'docker logs devhub_web --tail 50'`
- **Migration-Fehler**: `ssh root@88.198.191.108 'docker exec devhub_web python manage.py showmigrations adr_lifecycle'`
- **Scripts fehlen**: `ssh root@88.198.191.108 'cd /opt/dev-hub && git pull && cp -r scripts /opt/scripts && chmod +x /opt/scripts/*.sh && echo OK'`
