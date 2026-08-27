# KONZ-platform-052 — Anhang: Befunde, Diabolus-Verdikte, Messskript (2026-08-27)

> Rohmaterial zu [KONZ-platform-052](KONZ-platform-052-pypi-flotte-subtrahieren-statt-melden.md). Vier Read-only-Befundlaeufe (Subagenten), der Erstentwurf P1-P18, das Diabolus-Verdikt je Vorschlag, die OOTB-Optionen und das Provenance-Messskript. Stand der Messungen: 2026-08-27, gegen origin/main und PyPI.

---

## platform PyPI-Programm — Agent-Befund 2026-08-27
## Artefakte
- ADR-266 accepted 2026-07-04, partial; Amendment 2026-08-19. ADR-226 accepted, partial, Kanon seit 08-19 in iilgmbh/shared-ci; platform _ci-pypi.yml deprecated (Header :3). ADR-278 OIDC-only accepted 07-24, Kill-Gate-Review 2026-10-19. KONZ-018 pipeline_status idea (nie accepted, §13 30-Tage-Frist 08-11 verstrichen), consumer_canary.py existiert nicht.
- registry/pypi-fleet.yaml 23 Pakete, generated 2026-08-19 (Commit 9ea59948)
- Workflows gruen: pypi-fleet-health (Mo 06:30, 08-24), pypi-gate-meter (taegl., 08-26), pypi-ci-adoption-gate (Mo 06:00)
- Melder-Issues OPEN, 0 Kommentare: #968 (fleet-health), #373 (adr-226-adoption: 3 offen/18 adopted/3 ohne WF), #752 (publish-gate-backlog seit 06-30, 1 Repo django-lms-lite unveraendert)
- #2075 Loop/Cold-Start K1 erfuellt, K2/K4 offen; #1904 /release vs ADR-278 (Token bleibt, Owner); #2291 PyPI-Org iil, Frist 09-08
## Flotte (Inventory-Lauf 08-27, 118 s, Datei unveraendert)
- Findings: gaeb-toolkit not_on_pypi, iil-enrichment not_on_pypi, iil-django-commons hybrid_auth, iil-testkit token_auth, nl2cad version_drift (0.3.0≠0.2.1), researchfw version_drift (0.6.2≠0.6.0)
- DL/30d: aifw 4969, promptfw 4640, authoringfw 4559, weltenfw 4475, testkit 3517, fieldprefill 3372, reflex 2490, klickdummy 1018, illustration-fw 653, codeguard 497, ingest 405, gpufw 236, lms-lite 200, learnfw 177, outlinefw 80, researchfw 61, nl2cad 21, django-commons 35, riskfw 19; adrfw/doc-templates None (429!)
- aelteste Releases: riskfw 03-03, django-commons 03-24, fieldprefill 04-08, researchfw 04-17, learnfw 04-29
- gpufw + iil-doc-templates publishers:[] aber aktiv+Releases (Scanner blind, kein Finding); iil-codeguard pyproject_version None (K3 unpruefbar, kein Finding); packages/adr-review ohne Publisher
## Luecken
1. check_publish_oidc_auth.py prueft nur pypa-action password:, NICHT twine upload → publish-iil-testkit.yml (TWINE_PASSWORD :56-62) = "OIDC-only" rc0. Schreibweise≠Sache.
2. Gate hat in platform keinen Aufrufer (nur Inline-Klon im deprecated _ci-pypi.yml:333-360); validate-workflows.yml:100 faehrt nur publish_gate_invariant.sh (gitleaks)
3. K7 Consumer-Canary existiert nicht (ADR-266 Stufe 3a, KONZ-018 W2-1)
4. Cold-Start-Tools (pypi_coldstart_*) ohne Workflow-Aufrufer
5. Downloads-Null = 429 (fail-soft :257-265); earlywarn :277-281 isinstance(int) → rate-limitiertes Paket nie archival-Kandidat
6. Nicht gemessen: Dep-Alter/CVE, Release-Kadenz (last_upload da, unbewertet), DL-Trend, Konsumenten-Drift, API-Surface/Semver (ADR-222 proposed/gestrichen), Attestations/PEP-740, Trusted-Publisher-Bindings (headless nicht pruefbar), Yanks, SBOM
7. nl2cad = 6-Dist-Familie als 1 Zeile (#2076)
## Laeuft, wirkt nicht
1. 3 Melder, 0 Leser (#968/#373/#752)
2. Emitter DEFAULT_ALLOWLIST=("canary",) (pypi_fleet_issue_emitter.py:41); Seed nur bei PR-dry-run oder dispatch → 16 Fruehwarn-Befunde erreichen kein Issue
3. Loop-Canary last_cycle 2026-08-19, 8 d abgelaufen, niemand meldet
4. CI-Token sieht iilgmbh nicht: 6 Pakete "ORG NICHT AUFLOESBAR", 7 Falsch-Orphans; lokal 0 Orphans. Hypothese PAT-Scope.
5. deprecated _ci-pypi.yml traegt einzigen platform-seitigen ADR-278-Guard; Rueckbau "Folge-Schritt" ohne Issue
6. /release-Skill (release.md, Commit b5d9f6af 2026-05-15, 2 Monate VOR ADR-278): ~/.pypirc + Token Z.28-53, twine Z.92; verteilte Kopie ~/.claude/commands/release.md driftet zusaetzlich. Realschaden: aifw 0.13.0 Token-Upload 08-25 10:57Z, 2 min vor OIDC-Lauf (#1904)
7. ADR-278 Kill-Gate heute = Nein: testkit token, django-commons hybrid, 12/18 Repos halten PYPI_API_TOKEN (Handover:84)
8. KONZ-018 Meilensteine verstrichen ohne Status

---

## dev-hub (Konsument) — Agent-Befund 2026-08-27
- iil-aifw Pin >=0.11.7,<0.13 (pyproject:29, requirements.txt:12) vs PyPI 0.13.0 → Obergrenze schliesst latest aus
- iil-testkit >=0.5.3,<1 ; .venv hat 0.5.3 (PyPI 0.6.0); .venv iil-aifw 0.10.2 < Pin-Minimum 0.11.7 (lokal falsch-gruen moeglich)
- iil-mail-tools + iil-content-store als vendored Wheels (KONZ-040 MVC-1 / ADR-130); iil-content-store 0.1.0 inzwischen AUF PyPI → Begruendung veraltet (nicht verifiziert ob bewusst)
- platform_context-0.2.0 Alt-Wheel in wheels/, nicht im Install-Pfad (Rest)
- KEIN Lockfile; Django-Range pyproject >=5.2,<6.2 vs requirements.txt >=5.1,<7.0 (requirements gewinnt, Dockerfile)
- Python 3.12; Dependabot weekly pip+actions+docker, 0 offene PRs
- Contract-Gate tests/platform_packages/test_package_contracts.py + platform-package-gate.yml (Mo 06:00), 2026-08-24 success, 2026-08-10 failure
- check_platform_packages Command deckt 2 von 5 Paketen (fehlt platform-context, mail-tools, content-store)
- Kopplung: aifw 105 Imports / 16 Dateien
- Vorschlaege: (1) aifw-Obergrenze S (2) Django-Range SSoT S (3) Lockfile M (4) .venv neu S (5) check_platform_packages erweitern M
- Bewusst: vendored wheels (KONZ-040/ADR-130); pdfminer.six statt poppler (ADR-288)

---

## mcp-hub (Konsument) — Agent-Befund 2026-08-27 (achimdehnert/mcp-hub)
- iil-aifw >=0.11.7,<1 (orchestrator_mcp/pyproject:27) PyPI 0.13.0 in Range; iil-testkit >=0.5.3,<1; iil-promptfw >=0.8.1,<1 = latest
- mcp-SDK: 4 verschiedene Ranges im Polyrepo (<2.0 orchestrator+llm_mcp bewusst: dev-hub#58 Prod-Drift 2026-05-28, -32602; ifc_mcp >=2,<3; deployment_mcp >=1,<3) — PyPI 2.1.1
- fastapi <0.116 (llm_mcp/pyproject:11) vs 0.141.1 = 26 Minor; pydantic unbounded uneinheitlich
- KEIN Lockfile; Dockerfile pip install . → Build-Zeit-Drift (orchestrator_mcp/Dockerfile:29)
- 13 offene Dependabot-PRs seit 2026-08-14 (13 d), 9 davon lockern mcp<2.0; #218 CI gruen aber BLOCKED
- shared-ci v1.1.11 (aktuell); letzte 5 CI success; Deploy 2026-08-25 success
- Python 3.12 (3 Server) vs requires-python >=3.11 (7 Server), CI testet nur 3.12
- skip_tests: true im deploy.yml ci-Job (bewusst, Polyrepo; Tests in ci.yml)
- Kopplung aifw: 5 Fundstellen, oeffentliche API (aifw, aifw.schema, aifw.service)
- Prod-Version aifw/mcp NICHT verifiziert (kein Lock) — Check: ssh docker exec pip show
- Vorschlaege: (1) Lockfile M (2) #218 gezielt gegen dev-hub#58 retesten, mergen/schliessen S-M (3) fastapi-Pin heben M (4) requires-python vereinheitlichen / 3.11-Matrix S (5) mcp-SDK-Pin-Strategie fleet-weit dokumentieren M

---

## PyPI-Flotte (23 Pakete) — Agent-Befund 2026-08-27 (origin/main, 18/23 lokale Klone waren stale)
- Alle CI main gruen; kein Dependabot-Stau; alle haben CHANGELOG; keine @main-Caller; kein "aktiv" >180 d ohne Release (learnfw 04-29, fieldprefill 04-08 knapp drunter: 120/141 d)
- Tags: 3 nie getaggt (gpufw, iil-ingest, iil-testkit); 3 veraltet (outlinefw v0.1.1 vs 0.3.2; researchfw v0.2.1 vs 0.6.2; learnfw v0.3.0 vs 0.5.4); nl2cad Tag v0.3.0 vs PyPI 0.2.1
- Ohne CI: iil-doc-templates (kein .github/workflows), django-lms-lite (nur secret-scan.yml)
- iil-django-commons: publish.yml failure 03-11, PyPI-Upload 03-24 → am CI vorbei (hybrid_auth)
- gaeb-toolkit CI-Caller achimdehnert/shared-ci@v1 (falsche Org + floating), 18 andere iilgmbh/shared-ci@v1.1.11; 3 auf v1.1.0 (django-commons, enrichment, riskfw)
- requires-python >=3.10: django-lms-lite, iil-django-commons, iil-klickdummy (Py 3.10 EOL Okt 2026); >=3.11: gpufw, iil-ingest, riskfw
- Dep-Caps: Django <6.0 in aifw, django-commons, learnfw (Django 6.1 latest); tenacity <9 researchfw (9.1.4)
- Konsumenten-Graph intern: fieldprefill→aifw; reflex→promptfw; doc-templates→iil-concept-templates (NICHT in Registry, PyPI 0.5.0)
- DL/30d live 429 fuer 17/23; Registry-Snapshot 08-19
- Tests 0: iil-adrfw, nl2cad (Muster tests/test_*.py; evtl. anderes Verzeichnis)
- Release-Kadenz 90d: klickdummy 43, aifw 10, adrfw 5, weltenfw 5, illustration 4; 0: codeguard, django-commons, fieldprefill, ingest, learnfw, researchfw, riskfw, enrichment, gaeb
- Rohdaten: scratchpad/pkgdata*, gather*.sh, final.py

---

## Vorschlags-Entwurf (Synthese Fable, 2026-08-27) — Input fuer Diabolus/OOTB
Quellen: befund_platform.md, befund_devhub.md, befund_mcphub.md, befund_flotte.md (gleicher Ordner)

## CI = Continuous Improvement (den Loop schliessen)
P1 Emitter-Allowlist ("canary",) auf reale Fruehwarn-Klassen erweitern + Seed im Wochenlauf statt nur Dispatch. Preis S. Kill: Issues 4 Wo unbearbeitet → Emitter aus.
P2 Melder-Issues #968/#373/#752 bekommen einen Leser: Phase 0.7.x "pypi-fleet" im session-start-Runner (liest den Issue-Body, WARN bei neuen Findings). Preis S.
P3 Loop-Canary altert: WARN im Runner bei last_cycle > 14 d. Preis S.
P4 CI-Token mit iilgmbh-Reichweite fuer pypi-fleet-health (7 Falsch-Orphans, 6 Blindstellen). Preis S, Secret-Gate (Owner).
P5 ADR-278-Guard erkennt twine upload/TWINE_PASSWORD und wird in platform validate-workflows verdrahtet (heute: kein Aufrufer, publish-iil-testkit.yml = "OIDC-only" rc0). Preis S.
P6 /release-Skill an ADR-278 angleichen (Token-Pfad raus, zentraler Dispatch), Kopie redistribute (#1904; Owner: "Token bleibt"). Preis S-M.
P7 Tag-Gate im Publish: Tag == pyproject.version sonst kein Upload; Tag-Nachzug fuer 7 Pakete. Preis S.
P8 Registry-Vollstaendigkeit: iil-concept-templates aufnehmen; publishers:[] bei aktiv (gpufw, doc-templates) und pyproject_version None (codeguard) werden Findings. Preis S.
P9 KONZ-018 Status ehrlich (idea→accepted-MVP oder verworfen), ADR-266 Stufe 3 bekommt Tracking-Issue. Preis S.
P10 CI-Caller-Drift: gaeb-toolkit achimdehnert/shared-ci@v1 → iilgmbh@v1.1.11; 3 Repos v1.1.0 → v1.1.11; doc-templates + django-lms-lite bekommen CI. Preis S.

## PM = Predictive Maintenance (Ausfall vor dem Ausfall sehen)
P11 Konsumenten-Lockfiles (dev-hub, mcp-hub): uv.lock/pip-compile; mcp-hub Prod-Version ist heute unbekannt. Preis M.
P12 Consumer-Canary K7: taeglich pip install latest + Import-Smoke fuer die 3 internen Kanten + dev-hub/mcp-hub (dev-hub hat test_package_contracts als Vorlage). Preis M.
P13 Django-6-Vorlauf: 3 Pakete Cap <6.0, dev-hub Range <7.0 → Matrix-Job "django-next" allow-failure. Preis S-M.
P14 Python-3.10-EOL (Okt 2026): 3 Pakete requires-python >=3.10 → auf 3.12 heben; mcp-hub 7 Server >=3.11 nie getestet. Preis S.
P15 Downloads: 429 ≠ 0; Retry/Backoff + Trend aus Registry-Historie; earlywarn isinstance-Bug (rate-limitiert = nie Archiv-Kandidat). Preis S.
P16 mcp-SDK-Strategie: 4 Ranges → eine; #218 gezielt gegen dev-hub#58 retesten; fastapi <0.116 (26 Minor) heben. Preis S-M.
P17 Portfolio-Entscheid: riskfw (19 DL, 03-03), gaeb-toolkit + iil-enrichment (nie auf PyPI) archivieren; iil-django-commons einfrieren = Token raus. Preis S (Owner).
P18 dev-hub: aifw-Cap <0.13 vs 0.13.0; Django-Range-Doppel; .venv unter Pin-Minimum; content-store-Vendoring veraltet. Preis S.

---

## OOTB — Agent-Ergebnis 2026-08-27
O1 uv-Workspace-Monorepo iil-fw (10 fw-Pakete) L 15-25d, ADR T3 noetig (ADR-022 Multi-Repo Ausnahme; ADR-200 Praezedenz iil-ui pnpm+uv workspaces; KONZ-018 §9 "bewusst ausserhalb, eigenes T3"). Ersetzt P7 P10 P13 P14 P17. Kill: nach 3 Migrationen kein gruener OIDC-Upload je Dist oder CI >15 min.
O2 Version aus Tag (hatch-vcs) S-M 3-5d, kein ADR. Macht K3-Drift strukturell unmoeglich (P7 gegenstandslos). RISIKO: iil-codeguard macht das schon → pyproject_version None → Inventar 23x blind; Inventar zuerst auf Tag-Lesung. release-please scheidet aus: Conventional Commits in ADR-071 §4B verworfen.
O3 Reverse-Dependency-CI (Registry consumers:-Kanten, Paket-PR baut Wheel, dispatched in Konsumenten) M 5-8d, kein ADR; Gate autonomous-no-human-review (Cross-Repo-Token). Ersetzt P12 P18. Beleg: grep consumers pypi-fleet.yaml = 0. Kill: 4 Wo kein reproduzierbarer Rot-Lauf gegen Breakage-Korpus (aifw 0.6.0, dev-hub#58).
O4 iil-Cohort-Constraints (constraints/iil-cohort-YYYY.MM.txt, Konsumenten pinnen Kohorte) M 5-8d — BEREITS ENTSCHIEDEN ADR-234 P0.5a (accepted 2026-06-01, in_progress), nie gebaut (kein constraints/, 0 Treffer tools/). Ersetzt P11 P16 P18 + 13 Dependabot-PRs mcp-hub. Auflage: Alterungs-WARN im selben PR. Variante B: keine Pins + Latest-Canary + Lock-Snapshot.
O5 PEP-740-Attestation als Ist-Messung je Release (PyPI-Provenance-Feld im Inventar) S 1-2d, kein ADR (ADR-278 Z.41/74 nennt Attestations als Folge, niemand misst; check_publish_gate.py:104 schliesst "attestation" als Falschtreffer aus). Ersetzt P5 als Primaerbeweis (Text-Guard bleibt fuer Altbestand). Macht Kill-Gate 2026-10-19 entscheidbar. Kill: <50 % Releases seit 07-24 mit Attestation.
O6 Portfolio-Halbierung (PyPI nur ab 2 Konsumenten) M 4-10d, ADR fuer die Regel. RISIKO Realschaden ADR-180 Tier 2 (Rueckfaltung 2026-03, revertiert 07-08, Wheel-Kollision nl2cad-areas). Downloads als Sunset-Signal in KONZ-018 §9 verworfen (CI-Installs dominieren); ADR-266 3c: Kandidaten = Issue, nie Auto-Aktion → Kanten statt Downloads, P15 nebensaechlich.
O7 Fleet-Statement als committete Datei (Wochenlauf committet registry + FLEET_STATEMENT.md, git diff = Meldung, Handover verlinkt; #968/#373/#752 zu) S 2-3d, kein ADR; Gate autonomous-no-human-review (Schreib-Automat). Ersetzt P1 P2 P3 P9(t). Beleg: pypi-fleet-health.yml schreibt Registry NICHT (generated_at 08-19 trotz Laeufe 08-24/26); KONZ-018 §5.4 "kein neuer Meter, kein neues Rolling-Issue". Kill: 4 Wo kein Diff im Handover zitiert.
O8 K1–K7 als Required Check im Paket-Repo (gate-Job in iilgmbh/shared-ci _ci-pypi.yml) M 6-10d, ADR-266-Amendment (zentraler Gate-Job ≠ verworfener zentraler Publish; KONZ-018 K3/W2-E1 offen). Voraussetzung: Doppelquelle platform-Kopie MIT gate vs shared-ci OHNE aufloesen (shared-ci#20). Ersetzt P5 P10 + Melder-Flaeche.
Empfehlung: O5 (S) + O4 (M).

## Messung am Artefakt 2026-08-27 (scratchpad/prov.py, PyPI Integrity API)
weltenfw 0.5.0 (08-21, OIDC) bundles=1 · aifw 0.12.0 (08-12, OIDC) bundles=1 · promptfw 0.8.1 (07-19, OIDC) bundles=1
aifw 0.13.0 (08-25, Token-Upload #1904) provenance 404 bundles=0 · testkit 0.6.0 (08-26, Token) 404 bundles=0
→ Provenance trennt Token- von OIDC-Upload exakt; O5 ist heute mit 5 Datenpunkten belegt.

---

## Advocatus Diaboli — Verdikt je Erstvorschlag (Opus-Subagent, unabhaengig)

| P# | Verdikt | Staerkstes Gegenargument | Billigere Alternative |
|---|---|---|---|
| P1 | geschwaecht | Enge Allowlist ist dokumentierter Drossel-Entscheid (pypi-fleet-health.yml:78-80, cap 3); Emitter feuerte nie auf echten Befund | 16 Befunde einmalig als Checkliste in #968 |
| P2 | widerlegt | Runner hat 18 Melder-Phasen, Journal: 18 offene Befunde, 12 ohne Artefakt — 19. Phase ist die Fehlform selbst | Eine Phase abschalten statt addieren |
| P3 | geschwaecht | Melder zweiter Ordnung ueber einen synthetischen Canary | Canary loeschen |
| P4 | geschwaecht | Org-weiter PAT in oeffentlichem Repo fuer Melder mit 0 Lesern | Falsch-Orphans als „nicht pruefbar" ausgeben |
| P5 | haelt (Ort falsch) | Wirksamer Guard lebt in shared-ci (19 Consumer), platform-Kopie consumer-los (#1423) | publish-iil-testkit.yml loeschen, OIDC im eigenen Repo |
| P6 | haelt (staerkster) | Realer, wiederholter Schaden (25.08. aifw, 26.08. testkit) | ~/.pypirc [pypi] entfernen (Owner nannte es selbst, #1904) |
| P7 | geschwaecht | „Tag == pyproject.version" ist fuer die 6-Dist-Familie nl2cad falsch (#2076) | Tags nachziehen ohne Gate |
| P8 | geschwaecht | Steht in KONZ-018 W1-4; Regenerator scannt lokale Klone, iil-concept-templates hat keinen | KONZ-018 W1-4 vollziehen, Scanner auf gh-API |
| P9 | haelt | Slug accepted-plan-item-silently-dropped ist gate-pflichtig | Entscheiden (annehmen/verwerfen) |
| P10 | geschwaecht | Arbeit an Archiv-Kandidat ohne Konsumenten | gaeb-toolkit-Entscheid zuerst |
| P11 | haelt (teuer) | Lockfile bei 13 offenen Dependabot-PRs erhoeht Rauschen | pip show / Health-Feld fuer „Prod-Version unbekannt" |
| P12 | geschwaecht | Canary ab Tag 1 rot (dev-hub-Cap <0.13) = 4. stiller Melder; taeglich ueberdimensioniert | on-release, zuerst P18 |
| P13 | geschwaecht | Kein Konsument will Django 6; allow-failure = folgenloses Rot | Cap heben, wenn ein Hub Django 6 verlangt |
| P14 | widerlegt | requires-python >=3.10 ist Untergrenze, EOL erzeugt keinen Ausfall; echtes Risiko umgekehrt: aifw >=3.12 gegen Konsumenten | nichts anheben |
| P15 | haelt (halb) | isinstance-Verhalten ist fail-soft by design | Downloads als Signal streichen |
| P16 | haelt (halb) | mcp<2.0 ist die Narbe von dev-hub#58 | 9 PRs ohne mcp-Bezug mergen, #218 offen lassen |
| P17 | Vollzug | Owner hat entschieden, Registry traegt die Strategie | nur vollziehen |
| P18 | haelt | — | — |

**Grundsatz-Angriffe (tragen):** A) Loop ist geschlossen und laeuft leer (18 offene Befunde, 12 ohne Artefakt; 39 gate-pflichtige Slugs, 13 ohne Gate, 2 rueckfaellig; risiko_debt Ø 2,54). B) Downloads = eigene CI (klickdummy 1018 DL, 43 Releases/90 d, 0 Konsumenten); Kadenz 0 ist bei 4/9 Absicht; Dep-Abstand hat einen belegten Ausfall — dort ist der alte Pin Absicht. C) Last auf 4 Paketen (aifw 15, testkit 15, promptfw 10, authoringfw 10 deklarierende Repos); sauber 0 und klassifiziert: gaeb-toolkit, riskfw, iil-enrichment — **Korrektur nach Owner-Pruefung:** gaeb-toolkit wird in ausschreibungs-hub KONZ-003/ADR-001/UC-Dateien referenziert (nicht in pyproject) → 0 war Messartefakt.
**Uebersehen im Entwurf:** fast alles steht in KONZ-018 W1; Registry aus stale Klonen (18/23); zweiter Token-Upload testkit 26.08.; ADR-278 drift_check_paths beobachtet die Gesunden; kein Vorschlag reduziert.

---

## Messskript Provenance (PyPI Integrity API)

```python
import json, urllib.request
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/vnd.pypi.integrity.v1+json"}), timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
for name, ver in [("iil-weltenfw","0.5.0"),("iil-aifw","0.13.0"),("iil-aifw","0.12.0"),("iil-testkit","0.6.0"),("iil-promptfw","0.8.1")]:
    st, body = get(f"https://pypi.org/pypi/{name}/{ver}/json")
    for f in json.loads(body)["urls"]:
        if not f["filename"].endswith(".whl"): continue
        st2, body2 = get(f"https://pypi.org/integrity/{name}/{ver}/{f['filename']}/provenance")
        bundles = len(json.loads(body2).get("attestation_bundles", [])) if st2 == 200 and body2 else 0
        print(name, ver, f["upload_time"][:10], st2, bundles)
```

Ergebnis 2026-08-27: weltenfw 0.5.0 → 200/1 · aifw 0.12.0 → 200/1 · promptfw 0.8.1 → 200/1 · aifw 0.13.0 → 404/0 · testkit 0.6.0 → 404/0.
