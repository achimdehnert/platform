# Verifikation 2026-09-02 — K3: venv-first-Welle und M4 nominal (ADR-266, #2591)

**Freigabe:** Owner 2026-09-02, Kapitäns-Kanal, wörtlich „Welle venv-first go, M4 schärfen"
(Kommentar in [#2591](https://github.com/achimdehnert/platform/issues/2591)).

## Teil 1 — venv-first: 9/9 Cold-Start grün

Befund aus K2 (`2026-09-02-adr266-k2-befund.md`): 9 Repos, `make setup` füllt `./.venv`,
`make test` rief `$(PYTHON)=python3` vom PATH → `No module named pytest` in einer Shell
ohne System-pytest. Fix je Repo (ein PR, Beweis vor dem Push):
`PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)`.

PRs: aifw#62 · authoringfw#33 · gpufw#3 · iil-testkit#23 · illustration-fw#32 · learnfw#19 ·
outlinefw#27 · promptfw#41 · researchfw#24 — alle gemergt, Publish in allen 9 Repos nur auf
Tags (kein Publish gefeuert).

**Beweis nach Merge** — `tools/pypi_coldstart_baseline.sh` gegen main, frischer Shallow-Clone,
leeres venv aktiviert (dieselbe Messung, die in K2 rot war):

| Repo | Einstieg | setup | tests | Dauer | Commit |
|---|---|---|---|---|---|
| [achimdehnert/aifw](https://github.com/achimdehnert/aifw) | `make setup+test` | ok | ok | 40s | [cbdc9eb0](https://github.com/achimdehnert/aifw/commit/cbdc9eb0936099002569ed1c4508e812136456bf) |
| [achimdehnert/authoringfw](https://github.com/achimdehnert/authoringfw) | `make setup+test` | ok | ok | 13s | [b9a13cbc](https://github.com/achimdehnert/authoringfw/commit/b9a13cbc095875ad476a49ef5a889bb32633582d) |
| [iilgmbh/gpufw](https://github.com/iilgmbh/gpufw) | `make setup+test` | ok | ok | 20s | [8be244aa](https://github.com/iilgmbh/gpufw/commit/8be244aaa561b123df1a68340fe7fad58c83aab4) |
| [achimdehnert/iil-testkit](https://github.com/achimdehnert/iil-testkit) | `make setup+test` | ok | ok | 28s | [9c51f633](https://github.com/achimdehnert/iil-testkit/commit/9c51f633100be0fea7abaf2b74cfbe56a2834dfd) |
| [iilgmbh/illustration-fw](https://github.com/iilgmbh/illustration-fw) | `make setup+test` | ok | ok | 14s | [b82b7430](https://github.com/iilgmbh/illustration-fw/commit/b82b7430931d249f749d5de242aa508d30bd81b0) |
| [achimdehnert/learnfw](https://github.com/achimdehnert/learnfw) | `make setup+test` | ok | ok | 29s | [66a0e11d](https://github.com/achimdehnert/learnfw/commit/66a0e11d1b2254a1cb23e1f5ea3ff26a00d95e8f) |
| [achimdehnert/outlinefw](https://github.com/achimdehnert/outlinefw) | `make setup+test` | ok | ok | 15s | [be3b10aa](https://github.com/achimdehnert/outlinefw/commit/be3b10aa1c9c167fa2d7f258d2391f2bbf58249e) |
| [achimdehnert/promptfw](https://github.com/achimdehnert/promptfw) | `make setup+test` | ok | ok | 15s | [1e82236f](https://github.com/achimdehnert/promptfw/commit/1e82236f3563aa0609f31e76eff752192765c806) |
| [achimdehnert/researchfw](https://github.com/achimdehnert/researchfw) | `make setup+test` | ok | ok | 21s | [c9393d8f](https://github.com/achimdehnert/researchfw/commit/c9393d8f63d3703aca99d4f632915ec344466ec7) |

Vorher (K2, gleiche Messung): 9× `fail`. Nachher: 9× `ok`. Damit Cold-Start flottenweit
22/23; der Rest ist gaeb-toolkit (eingefroren, echte Testfehler im PDF/OCR-Pfad).

## Teil 2 — M4 schärfen: 43 → 19 Findings, 24 nominal

**Fakt:** 18 Repos pinnen `iilgmbh/shared-ci/_ci-pypi.yml@v1.1.11`, neuester Tag v1.1.14.
Compare v1.1.11…v1.1.14 ändert nur `_ci-python.yml`, `_deploy-hetzner.yml`,
`_deploy-unified.yml`; `_ci-pypi.yml` ist byte-identisch und delegiert nicht an
`_ci-python.yml` (nur Composite-Actions `@main`).

**Neue M4-Semantik** (`tools/pypi_fleet_earlywarn.py`): `reusable_lag` nur, wenn die gepinnte
Datei samt ihrer lokalen Reusable-Aufrufe (`uses: ./.github/workflows/…`) zwischen Ref und
neuestem Tag wirklich differiert. Identisch → `M4 lag_nominal` als `[info]`-Zeile im
Text-Report, nicht gezählt, nicht im JSON (kein Emitter-Input). Nicht prüfbar (Fetch-Fehler)
→ bleibt Finding mit Zusatz „Datei-Vergleich nicht prüfbar" (kein grüner Zustand aus einem
Fehler). `tools/pypi_fleet_report.py` zeigt denselben Zustand als `lag nominal` und trennt
die Summenzeile in „Datei geändert" / „Datei identisch (nominal)".

**Messung** (lokal, `GH_TOKEN`, Registry vom 2026-09-01):

| | Findings | davon M4 | nominal (info) |
|---|---|---|---|
| vorher (K2, 2026-09-02 früh) | 43 | 24 | — |
| nachher (dieser Stand) | 19 | 0 | 24 |

Rest: M1 14 (Heimat-Drift, ADR-255-Bahn, Owner) · M2 2 (Python-Floor `>=3.10`, Owner-Entscheid
offen) · K4 2 (gpufw 0.1.1, iil-reflex 0.6.1 unattested, Heilung = Release = Owner) · M5 1
(nl2cad, 14 Downloads/30d).

**K3-Vorher-Zahl** bleibt der Wochenlauf
[33366432594](https://github.com/achimdehnert/platform/actions/runs/33366432594) (2026-08-31):
45 Findings über 20 Pakete. Die Nachher-Zahl liefert der nächste Montagslauf
(`pypi-fleet-health.yml`, 06:30 UTC) nach Merge dieses PRs; der PR-Lauf ist der erzwungene
Dry-Run derselben Kette.

## Was das nicht ist

Kein Bump der 18 Pins. Die Bump-Welle wird gefahren, sobald `_ci-pypi.yml` sich wirklich
ändert — dann meldet M4 wieder, mit Grund.
