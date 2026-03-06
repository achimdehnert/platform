# ADR-101 Ergänzung: Hetzner Cloud API & Cloudflare DNS — MCP-Lückenanalyse

| Attribut | Wert |
|---|---|
| **Bezug** | ADR-101: MCP-Plattformkonzept |
| **Typ** | Gap-Ergänzung (nicht in §4 adressiert) |
| **Datum** | 2026-03-06 |
| **Priorität** | P1 |
| **Vorgeschlagene Gap-ID** | G-09 (Hetzner Cloud Control Plane), G-10 (Cloudflare DNS) |

---

## Problem

Der aktuelle `deployment-mcp` operiert ausschließlich **auf dem Server via SSH** — er sieht nur was innerhalb der Hetzner-VM passiert. Die **Hetzner Cloud Control Plane** (Cloud-Firewalls, Server-Ressourcen, Snapshots, Volumes, Traffic-Stats) und **Cloudflare DNS** sind für Cascade vollständig blind.

**Konsequenz:** Cascade kann keine Aussagen machen über:
- Ob die Cloud-Firewall einen Port korrekt freigibt
- Welche Firewall-Rules auf welchem Server aktiv sind
- Snapshot/Backup-Status der 14 Produktions-Apps
- DNS-Propagation nach Änderungen an `*.iil.pet` / `kiohnerisiko.de`
- Monatlichen Traffic-Verbrauch je Server
- Inkonsistenzen zwischen Nginx-Config (im Container) und Cloud-Firewall-Rules

---

## G-09: Hetzner Cloud Control Plane — kein MCP-Zugriff

### Ist-Zustand

`deployment-mcp` kennt nur SSH-Befehle auf dem Server. Die Hetzner Cloud API
(Server-Status, Cloud-Firewall, Volumes, Snapshots, Netzwerk) ist nicht
erreichbar.

### Existierende MCP-Implementierungen (Marktübersicht)

| Projekt | Sprache | Stars | Lizenz | Qualität |
|---|---|---|---|---|
| `dkruyt/mcp-hetzner` | Python | 56 | MIT | Minimal — 4 Commits, kein FastMCP |
| `MahdadGhasemian/mcp-hetzner-go` | Go | — | MIT | Read-Only/Read-Write Modi, stabil |
| `valerius21/hetzner-mcp` | TypeScript | — | MIT | Bun-basiert |

**Bewertung für BF Platform:** Keine der Community-Implementierungen ist
direkt einsetzbar. Alle verletzen ADR-044 (FastMCP, `src/`-Layout,
`pyproject.toml`, lifespan-Hook). Integration als externer Server würde
auch das Tool-Budget (ADR-101 §11) unnötig belasten.

### Empfehlung: deployment-mcp erweitern (Option C)

Der bestehende `deployment_mcp` hat bereits einen `HetznerClient` als
Skeleton im lifespan-Hook (ADR-044 §3.3). Konsequente Erweiterung mit
Hetzner Cloud API Actions — **kein neuer Server, keine neuen Tool-Slots**.

#### Neue Actions in `hetzner_manage`:

```python
# deployment_mcp/tools/hetzner_cloud.py

from hcloud import Client
from fastmcp import Context

@mcp.tool()
async def hetzner_manage(
    action: Literal[
        "server_overview",
        "server_detail",
        "firewall_audit",
        "firewall_rules",
        "snapshot_list",
        "volume_list",
        "network_info",
        "traffic_stats",
    ],
    server_name: str | None = None,
    ctx: Context = None,
) -> str:
    """
    Hetzner Cloud Control Plane — Server, Firewalls, Snapshots, Volumes.
    Nutzt HCLOUD_TOKEN aus Umgebungsvariable (nie in Logs).
    """
    client = ctx.request_context.lifespan_context["hetzner_cloud"]

    match action:
        case "server_overview":
            # Alle Server: Name, Status, IP, Server-Type, Datacenter
            servers = client.servers.get_all()
            return _format_server_overview(servers)

        case "firewall_audit":
            # Welche Cloud-Firewall-Rules sind auf welchem Server aktiv?
            # Abgleich: Cloud-Firewall-Port vs. Nginx-Config
            firewalls = client.firewalls.get_all()
            return _format_firewall_audit(firewalls)

        case "snapshot_list":
            # Snapshots aller Server mit Alter und Größe
            images = client.images.get_all(type="snapshot")
            return _format_snapshots(images)

        case "traffic_stats":
            # Monatlicher Traffic-Verbrauch je Server (Included vs. Used)
            servers = client.servers.get_all()
            return _format_traffic(servers)
```

#### Lifespan-Erweiterung:

```python
# deployment_mcp/server.py

from hcloud import Client as HCloudClient

@asynccontextmanager
async def lifespan(server):
    hetzner_ssh = HetznerSSHClient()          # bestehend
    hetzner_cloud = HCloudClient(             # NEU
        token=settings.hcloud_token
    )
    server.state["hetzner_ssh"] = hetzner_ssh
    server.state["hetzner_cloud"] = hetzner_cloud
    try:
        yield
    finally:
        await hetzner_ssh.close()
        # hcloud Client ist sync — kein async close nötig
```

#### Benötigte Umgebungsvariable:

```bash
# .env (bereits für SSH vorhanden — ergänzen)
HCLOUD_TOKEN=<read-only API token aus Hetzner Console>
```

**Wichtig:** Read-Only API Token erstellen — Cascade soll nur lesen,
nicht Ressourcen verändern. Hetzner unterstützt granulare Token-Permissions.

#### Tool-Budget-Impact:

```
Vorher:  deployment-mcp  12 Tools
Nachher: deployment-mcp  15 Tools  (+3 neue hetzner_manage Actions)
Netto:   +3 Tool-Slots  (Budget bleibt: 47/100 aktiv, 76/100 max)
```

### Aufwand

| Task | Aufwand |
|---|---|
| `hcloud` Python-Library installieren + lifespan-Hook | 30 min |
| `hetzner_manage` mit 4 Actions implementieren | 2h |
| Tests (pytest + mocked hcloud responses) | 1h |
| **Gesamt** | **~3.5h** |

---

## G-10: Cloudflare DNS — kein MCP-Zugriff

### Ist-Zustand

`deployment-mcp` kann `dns_record_list` über die Hetzner DNS API abfragen
(sofern Hetzner DNS genutzt wird). Für Cloudflare-verwaltete Domains
(`*.iil.pet`, `kiohnerisiko.de`) gibt es keinen MCP-Zugriff.

**Konsequenz:** Bei DNS-Problemen muss Cascade blind debuggen.
Typische Szenarien ohne MCP-Sichtbarkeit:
- Welcher A-Record zeigt auf welche IP?
- Ist DNS-Propagation nach Deployment abgeschlossen?
- Welche Subdomains haben Proxied vs. DNS-only?
- SSL-Zertifikat-Status je Zone

### Existierende MCP-Implementierung: Offizieller Cloudflare MCP

Cloudflare betreibt **offizielle, remote-gehostete MCP-Server** — kein
eigener Code, keine Installation, nur Config-Eintrag.

#### Option A: Cloudflare API MCP (vollständig, empfohlen)

```json
{
  "mcpServers": {
    "cloudflare-api": {
      "url": "https://mcp.cloudflare.com/mcp",
      "disabled": true,
      "comment": "Tier 2 — gesamte Cloudflare API via OAuth"
    }
  }
}
```

Deckt über 2.500 Cloudflare-Endpoints ab (DNS, Firewall Rules, SSL,
Load Balancer, Analytics) über zwei Tools: `search()` und `execute()`.
Token-effizient: ~1.000 Tokens statt 1+ Million bei naiver Tool-Exposition.
Authentifizierung via **Cloudflare OAuth** (Browser-Flow beim ersten Connect).

#### Option B: Cloudflare DNS Analytics MCP (spezialisiert)

```json
{
  "mcpServers": {
    "cloudflare-dns": {
      "command": "npx",
      "args": ["mcp-remote", "https://dns-analytics.mcp.cloudflare.com/sse"],
      "disabled": true,
      "comment": "Tier 2 — DNS Analytics & Optimierung"
    }
  }
}
```

Fokussiert auf DNS-Traffic-Analyse, Performance-Reports und Optimierungs-
empfehlungen. Leichtgewichtiger als die vollständige API.

#### Empfehlung

**Option A** für die BF Platform — der vollständige Cloudflare API MCP
ist token-effizienter und deckt auch Firewall-Rules auf Cloudflare-Ebene ab.

**Aufwand:** 30 Minuten — nur `windsurf_cascade_config.json` ergänzen,
OAuth-Flow einmalig durchlaufen.

**Tool-Budget-Impact:** 2 neue Tools (`search`, `execute`) — Tier-2
(disabled), nur bei DNS/Cloudflare-Arbeit aktivieren.

---

## Aktualisierung ADR-101 §4 Gap-Analyse

Folgende Zeilen in §4.1 ergänzen:

| Gap | Problem | Lösung | Priorität |
|---|---|---|---|
| **G-09: Hetzner Cloud Control Plane** | Cloud-Firewalls, Snapshots, Volumes, Traffic-Stats unsichtbar für Cascade | `deployment-mcp` um `hetzner_manage` Actions erweitern (hcloud Python-Library, Read-Only Token) | P1 |
| **G-10: Cloudflare DNS** | DNS-Records, Propagation, SSL-Status für `*.iil.pet` und `kiohnerisiko.de` unsichtbar | Offiziellen `cloudflare/mcp` Remote-Server als Tier-2 konfigurieren (kein Code, nur Config + OAuth) | P1 |

---

## Aktualisierung ADR-101 §9 MCP-Config Ziel-Zustand

```json
{
  "mcpServers": {
    "deployment-mcp":   { "disabled": false, "comment": "Tier 1 — Infra+SSH+HCloud (erweitert)" },
    "github":           { "disabled": false, "comment": "Tier 1 — Code" },
    "platform-context": { "disabled": false, "comment": "Tier 1 — Rules" },
    "test-generator":   { "disabled": true,  "comment": "Tier 2 — bei Tests (war Tier 1, siehe Review)" },
    "health-mcp":       { "disabled": false, "comment": "Tier 1 — Monitoring (NEU)" },
    "docs-search-mcp":  { "disabled": false, "comment": "Tier 1 — RAG Docs (NEU)" },

    "cloudflare-api":   { "disabled": true,  "comment": "Tier 2 — DNS, Firewall, SSL (NEU, G-10)" },
    "registry-mcp":     { "disabled": true,  "comment": "Tier 2 — bei Bedarf" },
    "dependency-mcp":   { "disabled": true,  "comment": "Tier 2 — bei Bedarf" },
    "code-quality":     { "disabled": true,  "comment": "Tier 2 — bei Reviews" },
    "llm-mcp":          { "disabled": true,  "comment": "Tier 2 — bei LLM-Arbeit" },
    "orchestrator":     { "disabled": true,  "comment": "Tier 2 — bei Orchestrierung" },

    "bfagent":          { "disabled": true,  "comment": "Tier 3 — repo-spezifisch" },
    "bfagent-db":       { "disabled": true,  "comment": "Tier 3 — repo-spezifisch" },
    "bfagent-monitoring":{ "disabled": true, "comment": "Tier 3 — repo-spezifisch" },
    "cadhub":           { "disabled": true,  "comment": "Tier 3 — repo-spezifisch" },
    "illustration":     { "disabled": true,  "comment": "Tier 3 — repo-spezifisch" }
  }
}
```

**Ergebnis nach Ergänzung:** 17 Server total, 5 Always-On, 6 Tier-2, 5 Tier-3.

---

## Aktualisierung ADR-101 §11 Tool-Budget

```
Aktiv (Tier 1):         47 Tools / 100       (+2 gegenüber Original)
  deployment-mcp:       15  (+3 hetzner_manage Actions)
  github:               26
  platform-context:      4
  health-mcp:            5  (neu)
  docs-search-mcp:       5  (neu, query_agent_mcp)
  test-generator:        —  (verschoben nach Tier 2, siehe Review K-02/H-04)

Disabled (Tier 2+3):    35 Tools
  cloudflare-api:        2  (search, execute — NEU)
  test-generator:        3  (von Tier 1 verschoben)
  registry:              5
  dependency-mcp:        5
  code-quality:          1
  llm-mcp:               2
  orchestrator:          3
  bfagent:               5
  bfagent-db:            2
  bfagent-monitoring:    2
  cadhub:                3
  illustration:          3
                        ──
Max bei allen aktiv:    82 / 100  (18 Reserve)
```

---

## Umsetzungsreihenfolge

| Schritt | Task | Aufwand | Abhängigkeit |
|---|---|---|---|
| 1 | Cloudflare Read-Only API Token erstellen (Permissions: Zone:Read, DNS:Read) | 10 min | — |
| 2 | `cloudflare-api` Remote MCP in windsurf config eintragen, OAuth-Flow | 20 min | Schritt 1 |
| 3 | Hetzner Read-Only API Token erstellen (Hetzner Console) | 10 min | — |
| 4 | `hcloud` zu `deployment_mcp/pyproject.toml` dependencies ergänzen | 5 min | — |
| 5 | `HCloudClient` in lifespan-Hook integrieren | 30 min | Schritt 3+4 |
| 6 | `hetzner_manage` Actions implementieren + Tests | 3h | Schritt 5 |
| 7 | ADR-101 §4, §9, §11 aktualisieren | 30 min | Schritte 2+6 |

**Gesamt:** ~4.5h für vollständige Umsetzung beider Gaps.

---

## Referenzen

- [dkruyt/mcp-hetzner](https://github.com/dkruyt/mcp-hetzner) — Community Python MCP für Hetzner
- [cloudflare/mcp](https://github.com/cloudflare/mcp) — Offizieller Cloudflare API MCP
- [cloudflare/mcp-server-cloudflare](https://github.com/cloudflare/mcp-server-cloudflare) — Spezialisierte Cloudflare MCP Server
- [Cloudflare MCP Docs](https://developers.cloudflare.com/agents/model-context-protocol/mcp-servers-for-cloudflare/)
- [hcloud Python SDK](https://github.com/hetznercloud/hcloud-python)
- ADR-044: MCP-Hub Architecture Consolidation (FastMCP-Standard)
- ADR-075: deployment-mcp Robustness
- ADR-101: MCP-Plattformkonzept (Basis-ADR)
