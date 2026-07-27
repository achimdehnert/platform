---
description: Uptime-Monitoring für alle Prod-Endpoints einrichten (Betterstack)
---

# /uptime-monitoring

> Einmalig einrichten — dann vollautomatisch.
> Kein Code, keine Abhängigkeiten, 0 Wartungsaufwand.
>
> ⚠️ **Das Kontingent ist erschöpft — vor dem Anlegen eines Monitors erst einen Slot
> freimachen.** Gemessen 2026-07-27 gegen `GET /api/v2/monitors`: **10 von 10** Slots
> belegt (eine Ergebnisseite, kein `next`). Ein `POST /api/v2/monitors` wird seit
> 2026-07-22 abgelehnt mit `Monitor quota reached. Please upgrade your account to add
> another monitor.` — die frühere Angabe „kostenlos bis 50 Monitore (reicht für alle
> 21 Repos)" war falsch und hat eine Kapazitätsplanung getragen, die beim 11. Monitor
> auflief (Realfall writing-hub#322).
>
> *Nicht verifiziert:* welche Plan-Stufe das Konto hat, also ob 10 das kostenlose Limit
> oder ein bezahltes Kontingent ist. Billigster Check: Betterstack-Dashboard →
> Settings → Billing.

## Wenn die Quota voll ist

Belegt sind die 10 Slots aktuell durch: `schutztat.de/livez`, `137herz.de`,
`bieterpilot.de`, `billing-hub`, `dev-hub`, `dms-hub`, `kiohnerisiko.de`, `learn-hub`,
`nl2cad.de`, `prezimo.com` (Stand 2026-07-27).

Reihenfolge der Optionen:

1. **Umhängen statt löschen.** Ein Monitor kann auf eine andere URL zeigen — der Slot
   bleibt, das Ziel wechselt. Das ist fast immer richtig, wenn zwei Domains **denselben
   Container** bedienen.
2. **Slot freigeben** — nur bei einer Domain, die nachweislich nicht mehr live ist.
   Vorher gegen das Freeze-Register (#1314) **und** gegen den tatsächlichen HTTP-Status
   prüfen: `kiohnerisiko.de` steht dort als stillgelegt, war aber weiter live und wird
   vom selben Container bedient wie `coach-hub.iil.pet` — dort wäre Löschen falsch
   gewesen, Umhängen richtig.
3. **Upgraden** — Kostenentscheidung, gehört dem Owner, nicht dem Skill.

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
