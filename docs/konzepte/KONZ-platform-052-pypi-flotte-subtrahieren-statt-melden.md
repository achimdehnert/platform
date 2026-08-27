---
concept_id: KONZ-platform-052
title: "PyPI-Flotte 2026-08 — subtrahieren statt melden: Publish-Pfad am Artefakt beweisen, den fallengelassenen Plan entscheiden, Melder-Flaeche halbieren"
pipeline_status: idea
tier: T2
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: >
  Kein ADR fuer V1-V12: Vollzug bereits accepted-er Entscheide (ADR-234 P0.5a,
  ADR-278 Attestations, ADR-266 Portfolio-Strategien) oder Loeschungen. ADR-
  wuerdig sind nur die drei L-Optionen (O1 Monorepo, O6 Konsumenten-Regel, O8
  Gate als Required Check) — und die werden hier NICHT empfohlen.
review_by: 2026-10-19
kill_criteria: >
  Bis 2026-10-19 (ADR-278-Kill-Gate-Termin): (a) tragen weniger als 100 % der
  Releases seit 2026-09-01 eine PyPI-Attestation ODER (b) ist KONZ-018 immer
  noch pipeline_status idea ODER (c) ist die Zahl der offenen Melder-Issues der
  Flotte nicht von 3 auf 1 gesunken — dann ist dieses Konzept selbst die N+2-te
  Fassung desselben Plans: schliessen, Slug accepted-plan-item-silently-dropped
  in der Retro als Rueckfall zaehlen, kein neues KONZ.
superseded_by_spec: null
evidence_manifest:
  - {claim_id: F1, source_path: .github/workflows/publish-iil-testkit.yml, commit_or_pr: "Z.61-62, geprueft 2026-08-27", opened_in_session: true}
  - {claim_id: F2, source_path: tools/check_publish_oidc_auth.py, commit_or_pr: "Lauf 2026-08-27 rc0 gegen F1", opened_in_session: true}
  - {claim_id: F3, source_path: docs/konzepte/KONZ-platform-052-anhang-befunde.md, commit_or_pr: "Messung 2026-08-27", opened_in_session: true}
  - {claim_id: F4, source_path: tools/pypi_fleet_issue_emitter.py, commit_or_pr: "Z.41 DEFAULT_ALLOWLIST", opened_in_session: true}
  - {claim_id: F5, source_path: docs/konzepte/KONZ-platform-018-pypi-fleet-predictive-standard-funktional.md, commit_or_pr: "Frontmatter pipeline_status idea, §13", opened_in_session: true}
  - {claim_id: F6, source_path: docs/adr/ADR-234-clean-state-invariant.md, commit_or_pr: "Z.94-95 P0.5a", opened_in_session: true}
  - {claim_id: F7, source_path: registry/pypi-fleet.yaml, commit_or_pr: "9ea59948 generated_at 2026-08-19", opened_in_session: true}
  - {claim_id: F8, source_path: docs/adr/ADR-278-oidc-only-publish.md, commit_or_pr: "drift_check_paths Z.13-16", opened_in_session: true}
---

# KONZ-platform-052 — PyPI-Flotte: subtrahieren statt melden

> Auftrag Owner 2026-08-27: platform, dev-hub, mcp-hub und alle PyPI-Paket-Repos
> analysieren; Optimierungen in vier Linsen (Continuous Improvement, Predictive
> Maintenance, Out-of-the-Box, Advocatus Diaboli). Tracking: [#2361](https://github.com/achimdehnert/platform/issues/2361).
> Scope-Checkpoint (durabel in #2361): ~26 Repos read-only, kein Prod-/Publish-Schritt.

## Kernthese

Die Flotte hat kein Erkennungsproblem, sie hat ein Leserproblem und einen
Beweis am falschen Ort. Der einzige belegte Ausfall der letzten 30 Tage ist der
**Publish-Auth-Pfad** (zwei Token-Uploads, 25. und 26.08.) — deterministisch
verhinderbar, nicht prognostizierbar. Der Guard dafuer prueft die Schreibweise
eines Workflows statt das Artefakt auf PyPI, und er hat in platform keinen
Aufrufer. Alles andere, was der Entwurf dieser Sitzung zunaechst vorschlug,
steht bereits in KONZ-018 W1 und ADR-266 — accepted im Geist, still
fallengelassen. Die Antwort ist deshalb **kein neuer Melder**, sondern: den
Beweis ans Artefakt verlegen, den liegengebliebenen Plan entscheiden, und die
Melder-Flaeche verkleinern.

## Fakt

| # | Fakt | Beleg |
|---|---|---|
| F1 | `publish-iil-testkit.yml` publiziert per `TWINE_PASSWORD` + `twine upload` | Z.61-62 |
| F2 | ADR-278-Guard nennt F1 „OIDC-only", rc 0 — prueft nur `password:` der pypa-Action | `check_publish_oidc_auth.py`, Lauf 2026-08-27 |
| F3 | PyPI-Provenance trennt exakt: OIDC-Releases (weltenfw 0.5.0, aifw 0.12.0, promptfw 0.8.1) je 1 Attestation-Bundle; Token-Uploads aifw 0.13.0 (25.08.) und testkit 0.6.0 (26.08.) → 404 | Integrity API, 5 Datenpunkte |
| F4 | Verbesserungs-Loop feuert im Regelbetrieb nie: Emitter-Allowlist `("canary",)`, Seed nur bei PR-Dry-Run/Dispatch; Loop-Canary `last_cycle 2026-08-19` | `pypi_fleet_issue_emitter.py:41`, `pypi-fleet-health.yml:86-104` |
| F5 | KONZ-018 steht auf `idea`; §13-Frist 2026-08-11 verstrichen; W1-1…W1-4 nie vollzogen; `consumer_canary.py` existiert nicht | Frontmatter, §13, `ls tools/` |
| F6 | ADR-234 P0.5a (accepted 2026-06-01) nennt `constraints/iil-cohort-<YYYY.MM>.txt` als Primaer-Hebel; `constraints/` existiert nicht | ADR-234 Z.94-95 |
| F7 | Registry generiert 2026-08-19 aus lokalen Klonen (18/23 stale), sagt aifw 0.12.0, PyPI hat 0.13.0; `iil-concept-templates` (2 Konsumenten) fehlt | `pypi-fleet.yaml`, Konsumenten-Grep |
| F8 | ADR-278 `drift_check_paths` ueberwacht codeguard + ingest (beide sauber), nicht testkit (einziger Verstoss) | ADR-278 Z.13-16 |
| F9 | Drei Melder-Issues, 0 Kommentare: #968, #373, #752 (Backlog seit 30.06. unveraendert 1 Repo); Wochenlauf meldet 7 Falsch-Orphans + 6 Blindstellen, weil `GITHUB_TOKEN` `iilgmbh` nicht sieht | `gh issue view`, `pypi-fleet-health.yml:59` |
| F10 | Konsumenten-Last liegt auf 4 Paketen (aifw 15, testkit 15, promptfw 10, authoringfw 10 deklarierende Repos); 3 Pakete sauber 0 Konsumenten UND bereits `archivieren`/`einfrieren`: gaeb-toolkit, riskfw, iil-enrichment | Grep `~/github/*/pyproject.toml, requirements*` |
| F11 | Downloads messen die eigene CI: iil-klickdummy 1018 DL/30d, 43 Releases/90d, 0 deklarierende Repos; pypistats live 429 fuer 17/23 | Flotten-Lauf 2026-08-27 |
| F12 | dev-hub: `iil-aifw<0.13` schliesst latest aus; Django-Range doppelt (pyproject `<6.2`, requirements `<7.0`, Dockerfile nimmt requirements); kein Lock. mcp-hub: kein Lock, `pip install .` im Image, 13 Dependabot-PRs seit 14.08., 9 davon reissen den bewussten `mcp<2.0`-Pin (dev-hub#58) | dev-hub `requirements.txt:12`, mcp-hub `orchestrator_mcp/Dockerfile:29`, #218 |
| F13 | Tag-Disziplin: 3 Pakete nie getaggt (gpufw, ingest, testkit), 3 Tags Versionen zurueck (outlinefw, researchfw, learnfw); nl2cad ist 6-Dist-Familie (#2076) | `git ls-remote --tags` |
| F14 | Journal des Sitzungsstarts: 18 offene Befunde, 12 ohne Artefakt; 13 mehrfach aufgetretene Befundklassen nie gegated; 2 Gates rueckfaellig | `befund_journal.py --bericht`, `gate_deckung.py` |

## Was das Programm misst — und was nicht

Gemessen (K1-K7, woechentlich, gruen): Heimat-Org, CI-Adoption, Version pyproject↔PyPI, Auth-Schreibweise, Publisher-Ort, Downloads-Momentanwert.
**Nicht gemessen:** Provenance am Artefakt (F3), Konsumenten-Kanten (F10), Registry-Frische gegen origin (F7), Tag↔Version (F13), Konsumenten-Lock/Prod-Version (F12). Von diesen fuenf traegt nur die erste einen belegten Ausfall; die zweite ersetzt die einzige Metrik, die nachweislich Rauschen misst (F11).

## Vorschlaege — Portfolio nach Diabolus

Verdikt-Legende: **haelt** = Diabolus konnte nicht widerlegen · **Vollzug** = bereits entschieden, nie gebaut · **verworfen** = vom Diabolus gekippt.

### Linse 1 — Continuous Improvement: den Loop entlasten, nicht erweitern

| # | Vorschlag | Beleg | Preis | Gate | Kill | Verdikt |
|---|---|---|---|---|---|---|
| V1 | `publish-iil-testkit.yml` **loeschen**; iil-testkit publiziert per OIDC aus dem eigenen Repo (wie 18 andere). Beseitigt den Verstoss statt ihn zu detektieren | F1, F3 | S | Owner: Secret `PYPI_API_TOKEN` in platform entfaellt (Security-Config) | Erster OIDC-Upload von testkit ohne Attestation | haelt |
| V2 | `[pypi]`-Sektion aus `~/.pypirc` der Dev-Maschine entfernen — vom Owner in #1904 selbst benannt, nie vollzogen | #1904, F3 | S | Owner (Dev-Maschine) | dritter Token-Upload | haelt (staerkster) |
| V3 | `/release`-Skill an ADR-278 angleichen: Token-/`~/.pypirc`-Pfad raus, zentraler Dispatch rein; Kopie redistributen (Skill-Commit b5d9f6af ist 2 Monate aelter als ADR-278) | `.windsurf/workflows/release.md` Z.28-53, 92 | S | keins (Skill = Doku) | Skill nennt nach Redistribute noch `PYPI_API_TOKEN` | haelt |
| V4 | ADR-278 `drift_check_paths` um `publish-iil-testkit.yml` ergaenzen (bis V1 greift) und Guard um `twine upload`/`TWINE_PASSWORD` erweitern — als **Zweitspur** hinter V5, nicht als Primaerbeweis | F2, F8 | S | keins | Guard meldet F1 weiter gruen | haelt (Ort: shared-ci-Kopie ist die wirksame) |
| V5 | Melder subtrahieren: #373 und #752 in #968 aufgehen lassen (ein Flotten-Issue), Loop-Canary loeschen, Emitter unveraendert lassen. Falsch-Orphans als **„nicht pruefbar"** ausgeben statt Token erweitern (platform ist public) | F4, F9 | S | keins | #968 nach 4 Wochen ohne Handover-Zitat → auch dieses Issue schliessen | haelt |
| V6 | KONZ-018 **entscheiden**: W1-1…W1-4 als MVP annehmen ODER verwerfen — nicht laenger `idea`. Vollzug W1-4 (Registry: `iil-concept-templates`, Scanner liest origin/gh-API statt Klon) | F5, F7 | S | Owner-Entscheid | §13-Frist ein zweites Mal verstrichen | haelt |
| V7 | Portfolio **vollziehen** (nicht neu entscheiden): gaeb-toolkit + riskfw archivieren, iil-enrichment einfrieren, iil-django-commons `hybrid` → Token raus | F10, Registry-Strategien | S | Owner nur fuer Token-Entfernung | — | Vollzug |
| V8 | dev-hub: `iil-aifw`-Obergrenze heben, Django-Range auf eine Quelle, `.venv` neu bauen, content-store-Vendoring pruefen (0.1.0 ist inzwischen auf PyPI) | F12 | S | keins | — | haelt (billigster Nutzen) |
| V9 | mcp-hub: die 9 Dependabot-PRs ohne mcp-Bezug mergen, #218 **bewusst offen** lassen mit Verweis auf dev-hub#58 statt Pin-Strategie zu vereinheitlichen | F12 | S | keins | — | haelt (halb) |

**Verworfen (Diabolus):** Emitter-Allowlist erweitern, 19. Runner-Phase, Canary-Alterungs-WARN, taeglicher Consumer-Canary, `django-next`-Matrix, `requires-python` anheben (Untergrenze erzeugt keinen Ausfall — das umgekehrte Risiko ist aifw `>=3.12` gegen Konsumenten), pypistats-Retry/Trend (Downloads streichen, F11), Tag-Gate vor #2076 (bricht die nl2cad-Familie; Tags nachziehen ohne Gate).

### Linse 2 — Predictive Maintenance: eine Metrik mit Beweiskraft, vier ohne

Befund: Downloads, Release-Kadenz und Python-EOL prognostizieren bei dieser Flotte nichts (F11; Kadenz 0 ist bei 4 von 9 Paketen der beabsichtigte Zustand). Dep-Abstand hat genau einen belegten Ausfall — und dort ist der alte Pin Absicht (dev-hub#58). Die einzige Metrik mit Beweiskraft ist die **Provenance am Artefakt** (F3): sie sagt nicht voraus, sie beweist.

| # | Vorschlag | Beleg | Preis | Kill | Verdikt |
|---|---|---|---|---|---|
| V10 | **Provenance-Feld im Inventar** (O5): je Release `attestation_bundles` aus der PyPI-Integrity-API; K4 wird am Artefakt gemessen; ADR-278-Kill-Gate 2026-10-19 wird mit Beleg entscheidbar | F3, ADR-278 Z.41/74 | S (1-2 d) | <50 % der Releases seit 24.07. tragen Attestation | haelt |
| V11 | **iil-Cohort vollziehen** (O4 = ADR-234 P0.5a): `constraints/iil-cohort-YYYY.MM.txt`, dev-hub/mcp-hub pinnen die Kohorte statt 5 Einzelpakete; Alterungs-WARN im selben PR | F6, F12 | M (5-8 d) | erste Kohorte installiert nicht gruen in beiden Konsumenten | Vollzug |
| V12 | Konsumenten-Kanten in die Registry (`consumers:`) als einzige Nutzungsmetrik; ersetzt Downloads | F10, F11 | S | — | haelt |

### Linse 3 — Out-of-the-Box: was das Problem anders schneidet

| # | Option | Kernidee | Preis | ADR | Empfehlung |
|---|---|---|---|---|---|
| O2 | Version aus dem Tag (hatch-vcs) | K3-Drift wird strukturell unmoeglich; **Vorbedingung:** Inventar liest Tag statt pyproject, sonst 23× blind (iil-codeguard zeigt es heute: `pyproject_version None`) | S-M | nein | nach V6, nicht vorher |
| O3 | Reverse-Dependency-CI **on-release** | Paket-Release baut Wheel, Konsumenten (V12-Kanten) testen dagegen; Cross-Repo-Token → Gate `autonomous-no-human-review`, Dry-Run-in-CI Pflicht | M | nein | nach V12; Kill: 4 Wo kein Rot gegen Breakage-Korpus (aifw 0.6.0, dev-hub#58) |
| O7 | Fleet-Statement als committete Datei statt Issues | Wochenlauf committet Registry + Statement, git-Diff = Meldung; KONZ-018 §5.4 erlaubt genau diese Richtung | S | nein | Alternative zu V5, falls #968 nach 4 Wochen ungelesen |
| O1 | uv-Workspace-Monorepo `iil-fw` (10 Pakete) | ein Lock, eine CI, Publish je Dist bleibt (ADR-226 erfuellt); ADR-022-Ausnahme, 10× OIDC-Binding neu | L (15-25 d) | **T3** | **nicht jetzt** — erst wenn V11 die Pin-Last nicht senkt |
| O6 | PyPI-Regel „≥2 Konsumenten" | Rueckfaltung in den Konsumenten; **Realschaden ADR-180 Tier 2** (Wheel-Kollision, revertiert 07-08) | M | ja | **nicht empfohlen**; V7 deckt die drei sauberen Faelle |
| O8 | K1-K7 als Required Check im Paket-Repo | Praevention statt Melder; Voraussetzung shared-ci#20 (Doppelquelle gate-Job) | M | Amendment ADR-266 | ruht bis shared-ci#20 |

### Linse 4 — Advocatus Diaboli: drei Grundsatz-Angriffe, die tragen

1. **„Loop schliessen" ist bei einem Solo-Owner die falsche Richtung.** Der Loop ist geschlossen und laeuft leer (F14). Jeder Vorschlag, der einen Melder hinzufuegt, verschlechtert die Kennzahl, die er verbessern soll. Deshalb subtrahiert dieses Konzept (V5) und fuegt nur eine Messung hinzu, die einen belegten Ausfall traegt (V10).
2. **„Predictive Maintenance" hat hier keine Datengrundlage.** Vier von fuenf Metriken messen Eigenverkehr oder Absicht; der einzige Ausfall ist deterministisch (Auth-Pfad). Praevention am Publish-Pfad (V1-V4) schlaegt Prognose.
3. **Die 18 Vorschlaege des ersten Entwurfs waren die N+1-te Fassung von KONZ-018 W1.** Der eigentliche Defekt heisst `accepted-plan-item-silently-dropped` (gate-pflichtiger Slug). Darum ist V6 — den Plan entscheiden — wichtiger als jeder Einzelpunkt, und das Kill-Kriterium dieses Konzepts misst genau das.

Einschraenkung gegen den eigenen Beleg: „0 Kommentare" trennt Mensch von Agent nicht (#2075/#1904 tragen nur Kommentare unter dem Owner-Konto, unter dem auch Agenten schreiben). Die haertere Zahl ist das Befund-Journal (F14).

## Steelman (fuer den ersten Entwurf)

Melder sind billig, ein uebersehener Ausfall ist teuer; die 16 Fruehwarn-Befunde existieren ja. Antwort: sie existieren seit Wochen ohne Leser — ein weiterer Kanal aendert die Leserzahl nicht, ein kleinerer schon.

## Maintainer 2028

Findet: ein Provenance-Feld je Release (V10), eine Kohorten-Datei mit Datum (V11), ein Flotten-Issue (V5), KONZ-018 mit einem Entscheid (V6). Muss nicht wissen, welche Schreibweise ein Publisher 2028 benutzt — PyPI sagt es ihm. Was ihn aergert: falls O2 ohne Inventar-Umstellung kam.

## Alternativen

- **Alles lassen:** ADR-278-Kill-Gate am 19.10. wird mit Handzaehlung „Nein" — 12 von 18 Repos halten Token (Handover Z.84). Dritter Token-Upload wahrscheinlich.
- **Nur V1+V2+V10 (Minimal):** beseitigt den einzigen belegten Ausfall und macht ihn messbar. Der Rest ist Hygiene. Das ist der empfohlene Kern, wenn nur ein Tag Zeit ist.

## Top-3-Risiken

1. **Dieses Konzept wird selbst fallengelassen** — Kill-Kriterium (b)/(c) misst das am 19.10.
2. **V1 loest den Token-Pfad, aber `~/.pypirc` bleibt** (V2 ist Owner-Handarbeit auf der Dev-Maschine) → dritter Upload. Gegenmittel: V10 zeigt ihn binnen einer Woche.
3. **O2 vor Inventar-Umstellung** macht K3 flottenweit blind. Reihenfolge ist im Vorschlag fixiert.

## Kill-Gate + Threshold

Siehe Frontmatter `kill_criteria`. Messpunkte: PyPI-Integrity-API (V10, Skript im Anhang KONZ-052-anhang-befunde.md), `pipeline_status` von KONZ-018, `gh issue list --label pypi-fleet`. Termin: 2026-10-19 (mit ADR-278 zusammengelegt, ein Review statt zwei).

## Bezug

- Auftrag/Scope: [#2361](https://github.com/achimdehnert/platform/issues/2361)
- Ausfall-Serie: [#1904](https://github.com/achimdehnert/platform/issues/1904) · Melder: [#968](https://github.com/achimdehnert/platform/issues/968), [#373](https://github.com/achimdehnert/platform/issues/373), [#752](https://github.com/achimdehnert/platform/issues/752), [#2075](https://github.com/achimdehnert/platform/issues/2075) · Familie: [#2076](https://github.com/achimdehnert/platform/issues/2076) · PyPI-Org: [#2291](https://github.com/achimdehnert/platform/issues/2291) · mcp-SDK: [mcp-hub#218](https://github.com/achimdehnert/mcp-hub/pull/218)
- ADR-266, ADR-226, ADR-278, ADR-234 (P0.5a), ADR-180 (Rueckfaltungs-Lehre), ADR-071 §4B (Conventional Commits verworfen), KONZ-platform-018
- Werkzeuge: `tools/pypi_fleet_inventory.py`, `tools/check_publish_oidc_auth.py`, `tools/pypi_fleet_issue_emitter.py`, `registry/pypi-fleet.yaml`
- Analyse-Methode: vier Read-only-Befundlaeufe (platform-Programm, dev-hub, mcp-hub, 23-Paket-Flotte gegen origin/main + PyPI) → Entwurf 18 Vorschlaege → Advocatus Diaboli + OOTB (je unabhaengig) → Portfolio
