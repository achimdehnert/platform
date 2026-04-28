# Project Facts: meiki-hub

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/meiki-hub.md` editieren!
> Sync: `/sync-project-facts meiki-hub` ausführen.

---

## Projekt

- **Name**: MEiKI — Mehrwert durch den Einsatz von KI in Bayerischen Landkreisen
- **Laufzeit**: März 2026 – März 2027
- **Konsortium**: LRA Traunstein · LRA Günzburg · TH Rosenheim · HNU Neu-Ulm
- **GitHub Org**: `meiki-lra` → https://github.com/meiki-lra/meiki-hub
- **Typ**: Dokumentations-Repo (kein Django, kein Docker, kein Python-Code)

---

## Umgebung (devuser)

| Variable | Wert |
|----------|------|
| Lokaler Pfad | `/home/devuser/github/meiki-hub` |
| MCP `mcp0_` | github |
| MCP `mcp1_` | orchestrator |

---

## Secrets — ZWEI Pfade (beide prüfen!)

| Pfad | Keys |
|------|------|
| `/home/devuser/shared/secrets/` | `openai_api_key`, `anthropic_api_key` |
| `~/.secrets/` | `github_token`, `cloudflare_*`, `hetzner_cloud_token`, `orchestrator_mcp_db_password` |

```python
SECRETS_DIRS = [Path("/home/devuser/shared/secrets"), Path.home() / ".secrets"]

def get_secret(name):
    if val := os.environ.get(name.upper()): return val
    for base in SECRETS_DIRS:
        if (p := base / name.lower()).exists(): return p.read_text().strip()
    return None
```

---

## Tools (lokal /home/devuser/shared/)

| Script | Zweck |
|--------|-------|
| `print_agent.py` | MD → PDF mit LLM-Anreicherung (gpt-4o-mini) |
| `meiki_pdf_gen.py` | MD → PDF ohne LLM (Fallback) |
| `meiki-pdf/` | PDF-Ausgabe |

---

## ADR-Verzeichnis

- **Kanonisch**: `docs/adr/` (ADR-001–ADR-006, nächste: ADR-007)
- Prüfen via: `mcp0_get_file_contents(owner="meiki-lra", repo="meiki-hub", path="docs/adr")`

---

## Gantt-Syntax (Custom Codefence für print_agent.py)

````
```gantt
März 2026 – März 2027
1 | Phasenname | start_monat | end_monat
```
````

Im GitHub-Viewer: lesbarer Code-Block. Im PDF: farbiges Gantt-Diagramm.
