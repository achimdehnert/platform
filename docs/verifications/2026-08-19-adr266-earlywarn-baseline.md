# Verifikation 2026-08-19 — Frühwarn-Baseline der 19 aktiv-Pakete (ADR-266, #2075 K3)

**Methode:** `GH_TOKEN=... python3 tools/pypi_fleet_earlywarn.py` — read-only
gegen die GitHub-Contents-API (Default-Branch = Wahrheit), aktiv-Liste aus
`registry/pypi-fleet.yaml` (`strategy: aktiv`, neu maschinenlesbar via
`pypi_strategy` in canonical, schließt #2080).

**Ergebnis: 38 advisory-Findings über 19 Pakete** (voller Output im PR-Lauf
als erzwungener Dry-Run):

| Metrik | Findings | Kern-Befund |
|---|---|---|
| M1 heimat_drift | 13 | alle achimdehnert-Residenten (Heimat-Regel-Backlog, ADR-255-Bahn) |
| M2 python_eol | 2 | django-lms-lite, iil-klickdummy: `>=3.10`, EOL 2026-10-31 |
| M3 version_pin | 0 | Instrument positiv-geprüft (Regex findet `python3.12` im Testfall; Fetch-Pfad per Live-Datei belegt) — die Null ist inhaltlich |
| M4 reusable_lag | 22 | 14× `_ci-pypi.yml`-Pin auf **iilgmbh/shared-ci-Kopie** (12× @v1.1.0, 2× @v1.1.10; aktuell v1.1.11) + 8× handoff-banner-gate@v1.1.7 |
| M5 archival_info | 1 | nl2cad 21 Downloads/30d |

## Instrumenten-Lektion (im Bau gefunden und gefixt)

Die erste M4-Fassung verglich gegen `achimdehnert/shared-ci`-**Releases** und
schwieg, wenn kein Release auflösbar war → 0 Findings trotz 22 realer.
Zwei Fehler in einem: falsches Repo (kanonisch ist **iilgmbh/shared-ci**,
Tags v1.1.x; achimdehnert/shared-ci ist Überbleibsel mit nur `v1` → #2084)
und stummes Schlucken der Nicht-Auflösbarkeit (Fetch-Fehler-als-grün-Klasse).
Fix: Tag-Auflösung je **gepinntem** Owner/Repo (semver-max über `/tags`),
Nicht-Auflösbarkeit wird als eigenes Finding gemeldet.

## Strategischer Nebenbefund (→ #2084)

Die Fleet konsumiert `_ci-pypi.yml` de facto aus der shared-ci-Kopie
(14 Pin-Nachweise), nicht aus platform (ADR-226-Kanon). Kanon-Entscheid nötig:
Kopie zurückbauen oder Kanon offiziell umziehen — nicht parallel pflegen.

## Advisory-Kontrakt

rc immer 0 (`--strict` existiert für späteres Blocking, erst nach
Präzisions-Nachweis — Regel aus ADR-266-Amendment 2026-08-19). Baseline
dokumentiert = Vorbedingung erfüllt, Blocking bleibt Owner-Entscheid.
