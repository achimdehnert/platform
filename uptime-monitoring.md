---
description: Uptime-Monitoring für alle Prod-Endpoints einrichten (Betterstack)
---

# /uptime-monitoring

> Einmalig einrichten — dann vollautomatisch.
> Kein Code, keine Abhängigkeiten, 0 Wartungsaufwand.
> Kostenlos bis 50 Monitore (reicht für alle 21 Repos).

---

## Schritt 1: Betterstack Account (einmalig)

→ https://betterstack.com/ → "Start for free"
→ E-Mail: admin@iil.pet (empfohlen) oder eigene

---

## Schritt 2: Monitore anlegen

Für jeden Eintrag aus `scripts/repo-registry.yaml` mit `prod_url`:

```bash
# Alle prod_urls aus der Registry ausgeben
python3 - << 'EOF'
import yaml
from pathlib import Path
reg = yaml.safe_load(Path('scripts/repo-registry.yaml').read_text())
for name, props in reg.get('repos', {}).items():
    if isinstance(props, dict) and props.get('prod_url'):
        url = props['prod_url']
        port = props.get('port', '')
        print(f"https://{url}/livez/  ({name}, :{port})")
EOF
```

Für jeden URL in Betterstack anlegen:
- **URL**: `https://{prod_url}/livez/`
- **Check interval**: 1 minute
- **Alert after**: 2 consecutive failures
- **Recovery alert**: on

---

## Schritt 3: Alerting konfigurieren

In Betterstack → On-Call:
- **E-Mail**: sofort bei Downtime
- **Slack** (optional): Webhook aus Slack-App erstellen

---

## Schritt 4: Status-Page (optional, öffentlich)

Betterstack → Status Pages → "New Status Page"
- Name: "IIL Platform Status"
- Domain: status.iil.pet (Cloudflare CNAME → betterstack)
- Alle Monitore hinzufügen

---

## Aktuelle Prod-URLs (Stand repo-registry.yaml)

| Repo | URL | Port |
|------|-----|------|
| coach-hub | kiohnerisiko.de/livez/ | 8007 |
| travel-beat | — | 8008 |
| weltenhub | — | 8009 |
| (weitere aus registry) | | |

→ Immer aktuelle Liste: `python3 scripts/audit_platform.py --health --format=json`

---

## Hinweis: coach-hub /livez/ zeigt 403 von außen

Cloudflare blockiert automatisierte Requests von externen IPs.
`audit_platform.py` nutzt seit 2026-04-28 direkt `localhost:PORT` auf dem Self-Hosted Runner.
Betterstack prüft von außen → Cloudflare Access konfigurieren oder Betterstack-IPs whitelisten.

**Betterstack IP-Range whitelisten in Cloudflare:**
→ Betterstack Dashboard → Settings → IP Addresses (Liste verfügbar)
→ Cloudflare → WAF → IP Access Rules → Allow für diese IPs
