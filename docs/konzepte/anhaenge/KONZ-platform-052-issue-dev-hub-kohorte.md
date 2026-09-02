# Issue-Entwurf: dev-hub auf die iil-Kohorte umstellen

> Vorbereiteter Text, **noch nicht angelegt**. Zielrepo `achimdehnert/dev-hub` ist ein fremdes
> Repo → Scope-Checkpoint: der Owner (oder ich nach Freigabe) legt das Issue nach dem Merge
> von platform#… an. Quelle der Befunde: `KONZ-platform-052-befunde.md` §dev-hub (2026-08-27).

**Titel:** `deps: iil-Kohorte 2026.08 pinnen statt Einzel-Obergrenzen (platform ADR-234 P0.5a)`

**Labels:** `dependencies`, `platform`

---

## Warum

`platform` erzeugt seit 2026-08-27 zentral eine **iil-Dependency-Cohort**:
`constraints/iil-cohort-2026.08.txt` nagelt alle 20 veröffentlichten iil-Pakete auf genau eine
Version fest, mit Supportfenster `support_until: 2026-10-26`. Erzeugt von
`tools/iil_cohort.py`, `check` (pip-Auflösung in frischem venv) grün.

dev-hub pflegt heute stattdessen eigene Ober- und Untergrenzen je Paket — und genau eine davon
schließt den aktuellen Stand aus:

| Fundstelle | Heute | Problem |
|---|---|---|
| `pyproject.toml:29`, `requirements.txt:12` | `iil-aifw>=0.11.7,<0.13` | PyPI ist bei **0.13.0** — die Obergrenze schließt latest aus |
| `pyproject.toml`, `requirements.txt` | `iil-testkit>=0.5.3,<1` | `.venv` hat 0.5.3, PyPI 0.6.0 |
| `.venv` | `iil-aifw 0.10.2` | **unter** dem eigenen Pin-Minimum 0.11.7 → lokal falsch-grün möglich |

Die Kohorte ersetzt diese Obergrenzen: die Untergrenze bleibt die API-Aussage („ab hier kompiliert
mein Code"), die *Auswahl* trifft die Kohorte.

## Was zu tun ist

1. **Obergrenzen der iil-Pakete entfernen** in `pyproject.toml` und `requirements.txt` —
   `iil-aifw>=0.11.7`, `iil-testkit>=0.5.3` usw. Untergrenzen bleiben.
2. **Kohorte als constraints-Datei einhängen**, im Dockerfile und im lokalen Setup:
   ```
   pip install -c <kohorte> -r requirements.txt
   ```
   Zwei Wege, Entscheidung liegt bei dev-hub (`platform` ist ein **öffentliches** Repo, der Raw-Zugriff
   braucht also kein Token):
   * **a) Pinned Raw-URL** (reproduzierbar, empfohlen für Docker-Builds):
     `-c https://raw.githubusercontent.com/achimdehnert/platform/<commit-sha>/constraints/iil-cohort-2026.08.txt`
   * **b) Vendored Kopie** `constraints/iil-cohort.txt` im Repo, aktualisiert wenn platform eine
     neue Kohorte veröffentlicht. Offline-baubar, dafür eine zweite Kopie, die driften kann.
   `constraints/iil-cohort-latest.txt` in platform ist ein **beweglicher Zeiger** — bequem für
   lokale Läufe, für einen Docker-Build besser die versionierte Datei.
3. **`.venv` neu aufbauen** gegen die Kohorte (behebt `iil-aifw 0.10.2` unter dem Pin-Minimum).
4. **Contract-Gate laufen lassen**: `tests/platform_packages/test_package_contracts.py` +
   `platform-package-gate.yml` müssen mit `iil-aifw 0.13.0` grün sein. Das ist das eigentliche
   Akzeptanzkriterium — die Kohorte ist erst umgestellt, wenn dieses Gate sie trägt.

## Bewusst NICHT in diesem Issue

* Django-Range-SSoT (`pyproject >=5.2,<6.2` vs `requirements.txt >=5.1,<7.0`) — eigener Vorgang,
  betrifft kein iil-Paket.
* Lockfile-Einführung — die Kohorte ist der kleinere Schritt und ersetzt einen Teil des Nutzens.
* Die vendored Wheels `iil-mail-tools` / `iil-content-store` (KONZ-040 MVC-1 / ADR-130). Hinweis:
  `iil-content-store 0.1.0` ist inzwischen **auf PyPI**, die Vendoring-Begründung ist damit
  möglicherweise veraltet — separat prüfen.

## Akzeptanz

- [ ] Keine iil-Obergrenze mehr in `pyproject.toml` / `requirements.txt`
- [ ] `pip install -c <kohorte> -r requirements.txt` läuft im Dockerfile
- [ ] `.venv` ≥ Pin-Minimum, `iil-aifw` = Kohorten-Version
- [ ] `platform-package-gate.yml` grün mit der Kohorte
