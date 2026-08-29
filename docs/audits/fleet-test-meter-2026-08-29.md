# Fleet-Test-Meter

Quelle: `tools/fleet_test_meter.py --root /home/devuser/github` · Auftrag platform#2428 Kriterium 1

## Aggregate

| Kennzahl | Wert |
|---|---|
| Repos gescannt | 74 |
| davon mit Tests | 62 |
| `make test` | 45 |
| testkit-Pin ≥ 0.6.0 | 1/16 |
| Coverage-Schwelle gesetzt | 20 |
| shared-ci-Nutzer | 41 |
| Marker-Schema reqid/gemischt | 4 |
| Repos mit ≥1 Contract-Test | 2 |
| Verletzungen | 20 |
| übersprungene Worktrees | platform-pinned |

## Verletzungen

| Repo | Befund | Tests | CI | Pin |
|---|---|---|---|---|
| ausschreibungs-hub | B2 Pin < 0.6.0 | 83 | shared:_ci-python@v1.1.12 | >=0.5,<1 |
| bfagent | B2 Pin < 0.6.0 | 132 | shared:platform/_ci-python@main | >=0.2.0 |
| cad-hub | B2 Pin < 0.6.0 | 15 | shared:_ci-python@v1.1.10 | >=0.5.3,<1 |
| coach-hub | B2 Pin < 0.6.0 | 35 | shared:_ci-python@v1.1.10 | >=0.5.3,<1 |
| dev-hub | B2 Pin < 0.6.0 | 111 | shared:_ci-python@v1.1.11 | >=0.5.3,<1 |
| django-lms-lite | B1 Test ohne Leser | 2 | wf-ohne-test | - |
| doc-hub | B1 Test ohne Leser | 1 | keiner | - |
| frist-hub | B2 Pin < 0.6.0 | 24 | shared:_ci-python@v1.0.11 | >=0.5.3,<1 |
| iil-doc-templates | B1 Test ohne Leser | 2 | keiner | - |
| illustration-hub | B2 Pin < 0.6.0 | 72 | shared:_ci-python@v1.1.10 | >=0.5.3,<1 |
| learn-hub | B2 Pin < 0.6.0 | 4 | shared:_ci-python@v1.1.0 | >=0.1 |
| meiki-hub | B1 Test ohne Leser | 1 | wf-ohne-test | - |
| pptx-hub | B2 Pin < 0.6.0 | 23 | shared:_ci-python@v1.1.10 | >=0.5.3,<1 |
| robo-lab | B1 Test ohne Leser | 9 | wf-ohne-test | - |
| tax-hub | B2 Pin < 0.6.0 | 15 | shared:_ci-python@v1.1.10 | >=0.5.3,<1 |
| trading-hub | B2 Pin < 0.6.0 | 72 | shared:_ci-python@v1.1.10 | >=0.2.0 |
| travel-beat | B2 Pin < 0.6.0 | 43 | shared:_ci-python@v1.1.10 | >=0.5.3,<1 |
| wedding-hub | B2 Pin < 0.6.0 | 6 | shared:_ci-python@v1.0.11+_ci-python@v1.0.5 | >=0.2.0 |
| weltenhub | B2 Pin < 0.6.0 | 25 | shared:_ci-python@v1.1.10 | >=0.5.3,<1 |
| writing-hub | B2 Pin < 0.6.0 | 305 | shared:_ci-python@v1.1.12 | >=0.5.3,<1 |

## Ausnahmen (begründet)

- iil-pet-portal: Playwright-KD-Paritaetstests ohne CI-Runner; Leser ist /kd-review (https://github.com/iilgmbh/iil-pet-portal/issues/41)

## Alle Repos

| Repo | Commit | Tests | Src | make | Pin | Cov | CI | Marker |
|---|---|---|---|---|---|---|---|---|
| writing-hub | 2026-08-29 | 305 | 333 | ja | >=0.5.3,<1 | - | shared:_ci-python@v1.1.12 | kanonisch |
| platform | 2026-08-29 | 299 | 610 | ja | - | - | own-pytest | kanonisch |
| risk-hub | 2026-08-27 | 260 | 694 | ja | >=0.6.0,<1 | - | shared:_ci-python@v1.1.11 | kanonisch |
| mcp-hub | 2026-08-27 | 154 | 596 | ja | - | - | shared:_ci-python@v1.1.11 | gemischt |
| bfagent | 2026-06-09 | 132 | 1116 | ja | >=0.2.0 | 14 | shared:platform/_ci-python@main | kanonisch |
| dev-hub | 2026-08-25 | 111 | 241 | ja | >=0.5.3,<1 | 65 | shared:_ci-python@v1.1.11 | kanonisch |
| ausschreibungs-hub | 2026-08-28 | 83 | 332 | ja | >=0.5,<1 | 80 | shared:_ci-python@v1.1.12 | kanonisch |
| illustration-hub | 2026-08-24 | 72 | 152 | ja | >=0.5.3,<1 | - | shared:_ci-python@v1.1.10 | - |
| trading-hub | 2026-08-20 | 72 | 196 | ja | >=0.2.0 | - | shared:_ci-python@v1.1.10 | - |
| travel-beat | 2026-08-25 | 43 | 326 | ja | >=0.5.3,<1 | - | shared:_ci-python@v1.1.10 | kanonisch |
| iil-voice-agent | 2026-08-17 | 40 | 47 | ja | - | - | own-pytest | - |
| coach-hub | 2026-08-20 | 35 | 159 | ja | >=0.5.3,<1 | 60 | shared:_ci-python@v1.1.10 | - |
| dms-hub | 2026-08-25 | 34 | 99 | - | - | - | shared:_ci-python@v1.1.10 | - |
| nl2cad | 2026-08-02 | 34 | 63 | ja | - | - | own-pytest | - |
| iil-klickdummy | 2026-08-23 | 26 | 80 | ja | - | - | shared:_ci-pypi@v1.1.11 | - |
| weltenhub | 2026-08-25 | 25 | 188 | ja | >=0.5.3,<1 | 80 | shared:_ci-python@v1.1.10 | kanonisch |
| frist-hub | 2026-08-02 | 24 | 43 | ja | >=0.5.3,<1 | 80 | shared:_ci-python@v1.0.11 | - |
| iil-pet-portal | 2026-07-28 | 24 | 10 | - | - | - | wf-ohne-test | - |
| iil-reflex | 2026-08-25 | 24 | 35 | ja | - | - | shared:_ci-pypi@v1.1.11 | kanonisch |
| pptx-hub | 2026-08-25 | 23 | 96 | ja | >=0.5.3,<1 | - | shared:_ci-python@v1.1.10 | - |
| aifw | 2026-08-25 | 20 | 33 | ja | - | 45 | shared:_ci-pypi@v1.1.11 | - |
| iil-adrfw | 2026-08-02 | 20 | 24 | ja | - | 85 | shared:_ci-pypi@v1.1.0 | - |
| research-hub | 2026-08-09 | 17 | 62 | - | - | 40 | shared:_ci-python@v1.0.11 | reqid |
| cad-hub | 2026-08-25 | 15 | 220 | ja | >=0.5.3,<1 | - | shared:_ci-python@v1.1.10 | - |
| promptfw | 2026-07-07 | 15 | 26 | ja | - | - | shared:_ci-pypi@v1.0.8 | - |
| tax-hub | 2026-08-23 | 15 | 131 | ja | >=0.5.3,<1 | - | shared:_ci-python@v1.1.10 | - |
| apo-hub | 2026-08-18 | 14 | 74 | ja | - | 80 | shared:_ci-python@v1.1.11 | reqid |
| authoringfw | 2026-07-31 | 12 | 33 | ja | - | - | shared:platform/_ci-pypi@main | - |
| billing-hub | 2026-08-25 | 12 | 60 | ja | - | 75 | shared:_ci-python@v1.1.10 | kanonisch |
| learnfw | 2026-06-01 | 12 | 47 | ja | - | - | own-pytest | - |
| gaeb-toolkit | 2026-08-02 | 11 | 17 | - | - | 55 | shared:_ci-pypi@v1 | - |
| iil-testkit | 2026-08-26 | 11 | 14 | ja | - | 80 | shared:_ci-pypi@v1.1.11 | - |
| researchfw | 2026-08-07 | 11 | 21 | ja | - | 65 | shared:_ci-pypi@v1.1.0 | - |
| 137-hub | 2026-08-25 | 10 | 80 | ja | - | - | shared:_ci-python@v1.1.10 | - |
| iil-ingest | 2026-06-15 | 10 | 17 | - | - | - | own-pytest | - |
| iil-django-commons | 2026-07-19 | 9 | 25 | ja | - | 70 | shared:platform/_ci-pypi@main | - |
| meiki-dms | 2026-07-07 | 9 | 68 | - | - | - | own-pytest | - |
| robo-lab | 2026-08-28 | 9 | 286 | - | - | - | wf-ohne-test | - |
| weltenfw | 2026-08-21 | 9 | 35 | ja | - | - | shared:_ci-pypi@v1.1.11 | - |
| iil-codeguard | 2026-08-02 | 8 | 15 | - | - | - | shared:_ci-pypi@v1 | - |
| recruiting-hub | 2026-08-17 | 8 | 59 | ja | - | - | shared:_ci-python@v1.1.10 | - |
| testkit | 2026-06-06 | 8 | 12 | ja | - | 80 | own-pytest | - |
| ttz-hub | 2026-06-30 | 8 | 33 | ja | - | - | own-pytest | - |
| outlinefw | 2026-07-04 | 7 | 11 | ja | - | - | shared:platform/_ci-pypi@main | - |
| bahn-hub | 2026-08-23 | 6 | 18 | - | - | - | own-pytest | - |
| iil-enrichment | 2026-08-02 | 6 | 13 | - | - | - | shared:_ci-pypi@v1.1.0 | - |
| wedding-hub | 2026-08-02 | 6 | 60 | ja | >=0.2.0 | 80 | shared:_ci-python@v1.0.11+_ci-python@v1.0.5 | - |
| illustration-fw | 2026-08-03 | 5 | 20 | ja | - | - | shared:_ci-pypi@v1.1.0 | - |
| lastwar-alliance-ops | 2026-07-28 | 5 | 8 | ja | - | - | own-pytest | - |
| riskfw | 2026-06-09 | 5 | 18 | ja | - | - | own-pytest | - |
| design-hub | 2026-08-17 | 4 | 16 | - | - | - | own-pytest | - |
| iil-fieldprefill | 2026-06-15 | 4 | 9 | - | - | - | own-pytest | - |
| lastwar-bot | 2026-07-08 | 4 | 6 | ja | - | 30 | shared:platform/_ci-pypi@main | - |
| learn-hub | 2026-08-02 | 4 | 30 | ja | >=0.1 | 80 | shared:_ci-python@v1.1.0 | - |
| odoo-hub | 2026-07-26 | 4 | 199 | - | - | - | own-pytest | - |
| onboarding-hub | 2026-08-18 | 3 | 38 | - | - | 80 | shared:_ci-python@v1.1.11 | - |
| chat-hub | 2026-08-23 | 2 | 4 | ja | - | - | own-pytest | reqid |
| django-lms-lite | 2026-08-03 | 2 | 8 | - | - | - | wf-ohne-test | - |
| iil-doc-templates | 2026-08-03 | 2 | 12 | - | - | - | keiner | - |
| doc-hub | 2026-08-19 | 1 | 1 | - | - | - | keiner | - |
| gpufw | 2026-08-16 | 1 | 3 | ja | - | - | own-pytest | - |
| meiki-hub | 2026-08-02 | 1 | 15 | - | - | - | wf-ohne-test | - |
| decks-hub | 2026-08-06 | 0 | 0 | - | - | - | wf-ohne-test | - |
| iil-relaunch | 2026-05-30 | 0 | 1 | - | - | - | wf-ohne-test | - |
| iilgmbh-iil-data | 2026-07-04 | 0 | 0 | - | - | - | keiner | - |
| iilgmbh-iil-relaunch | 2026-05-30 | 0 | 1 | - | - | - | wf-ohne-test | - |
| infra-deploy | 2026-08-25 | 0 | 4 | - | - | - | wf-ohne-test | - |
| manuskripte | 2026-08-12 | 0 | 10 | - | - | - | keiner | - |
| molkerei-landing | 2026-07-04 | 0 | 0 | - | - | - | keiner | - |
| music-lab | 2026-08-23 | 0 | 40 | ja | - | - | wf-ohne-test | - |
| nl2iot-hub | 2026-08-17 | 0 | 0 | - | - | - | wf-ohne-test | - |
| pg-hub | 2026-07-04 | 0 | 1 | - | - | - | wf-ohne-test | - |
| shared-ci | 2026-08-17 | 0 | 3 | - | - | - | shared:_ci-odoo@main+_ci-pypi@main+_ci-python@main | - |
| sqf-hub | 2026-07-04 | 0 | 1 | - | - | - | wf-ohne-test | - |
