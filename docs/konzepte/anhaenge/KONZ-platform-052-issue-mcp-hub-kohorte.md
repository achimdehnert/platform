# Issue-Entwurf: mcp-hub auf die iil-Kohorte umstellen

> Vorbereiteter Text, **noch nicht angelegt**. Zielrepo `achimdehnert/mcp-hub` ist ein fremdes
> Repo → Scope-Checkpoint: der Owner (oder ich nach Freigabe) legt das Issue nach dem Merge
> von platform#… an. Quelle der Befunde: `KONZ-platform-052-befunde.md` §mcp-hub (2026-08-27).

**Titel:** `deps: iil-Kohorte 2026.08 pinnen statt Einzel-Obergrenzen (platform ADR-234 P0.5a)`

**Labels:** `dependencies`, `platform`

---

## Warum

`platform` erzeugt seit 2026-08-27 zentral eine **iil-Dependency-Cohort**:
`constraints/iil-cohort-2026.08.txt` nagelt alle 20 veröffentlichten iil-Pakete auf genau eine
Version fest, mit Supportfenster `support_until: 2026-10-26`. Erzeugt von
`tools/iil_cohort.py`, `check` (pip-Auflösung in frischem venv) grün.

mcp-hub ist ein Polyrepo mit sieben Servern und pflegt die iil-Grenzen je Server einzeln:

| Fundstelle | Heute |
|---|---|
| `orchestrator_mcp/pyproject.toml:27` | `iil-aifw>=0.11.7,<1` (PyPI 0.13.0 liegt in der Range) |
| dito | `iil-testkit>=0.5.3,<1` |
| dito | `iil-promptfw>=0.8.1,<1` (= aktuell latest) |
| `orchestrator_mcp/Dockerfile:29` | `pip install .` ohne Lock/Constraints → **Build-Zeit-Drift**: was gebaut wird, hängt vom Tag des Builds ab |

Die `<1`-Obergrenzen sind heute nicht der Schmerz — der Schmerz ist Zeile 4: es gibt kein
Lockfile, also ist die in Prod laufende iil-Version **nicht verifiziert**. Die Kohorte macht den
Build deterministisch, ohne ein Lockfile einzuführen.

## Was zu tun ist

1. **Obergrenzen der iil-Pakete entfernen** in allen `*/pyproject.toml` (`iil-aifw>=0.11.7`,
   `iil-testkit>=0.5.3`, `iil-promptfw>=0.8.1`). Untergrenzen bleiben — sie sind die API-Aussage.
2. **Kohorte im Dockerfile einhängen** (`orchestrator_mcp/Dockerfile:29` und die übrigen Server):
   ```
   pip install -c <kohorte> .
   ```
   `platform` ist **öffentlich**, der Raw-Zugriff braucht kein Token. Für einen Docker-Build die
   *versionierte* Datei nehmen, nicht den beweglichen `latest`-Zeiger:
   `-c https://raw.githubusercontent.com/achimdehnert/platform/<commit-sha>/constraints/iil-cohort-2026.08.txt`
   (Alternative: vendored Kopie im Repo — offline-baubar, dafür eine zweite Kopie, die driften kann.)
3. **Prod-Stand gegenprüfen**, sobald der erste Build mit Kohorte durch ist:
   `ssh … docker exec … pip show iil-aifw` — die Version muss die der Kohorte sein. Das ist der
   Beweis, dass die Umstellung wirkt, nicht der grüne Build.

## Was das an Dependabot-Rauschen wegnimmt

13 offene Dependabot-PRs seit 2026-08-14 — **9 davon lockern `mcp<2.0`** und sind damit von
diesem Issue nicht berührt.

**Wichtig, damit hier nichts kaputtgeht:** `mcp<2.0` in `orchestrator_mcp` und `llm_mcp` ist
**Absicht** — die Narbe von dev-hub#58 (Prod-Drift 2026-05-28, `-32602`). Die Kohorte enthält
**kein** `mcp` (kein iil-Paket) und rührt diesen Pin nicht an. Dieses Issue darf nicht als Anlass
genommen werden, `mcp<2.0` mit zu lockern; `#218` bleibt bis zum gezielten Retest gegen dev-hub#58
offen.

## Bewusst NICHT in diesem Issue

* `mcp`-SDK-Pin-Strategie (4 Ranges im Polyrepo), `#218` — eigener Vorgang mit eigener Historie.
* `fastapi<0.116` (26 Minor Rückstand) und uneinheitliches `requires-python` (3.11 vs 3.12).
* Lockfile-Einführung.

## Akzeptanz

- [ ] Keine iil-Obergrenze mehr in den `*/pyproject.toml`
- [ ] Dockerfiles installieren mit `-c <kohorte>`
- [ ] CI grün, Deploy durch
- [ ] `pip show iil-aifw` im Prod-Container zeigt die Kohorten-Version
- [ ] `mcp<2.0` unverändert, `#218` unberührt
