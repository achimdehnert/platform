# FW-Speicher-Baseline — RAM-Anteil der iil-Frameworks (hetzner-prod)

> Artefakt zu [#1899](https://github.com/achimdehnert/platform/issues/1899),
> Kriterien 1 (reproduzierbares Messkommando) und 2 (Ranking-Artefakt).
> Messdatum: 2026-08-11 · Messkommando: `bash tools/fw_mem_baseline.sh hetzner-prod`

## Kernaussage

`import aifw` kostet in jedem der **17 aifw-tragenden App-Container** ~144–196 MiB RSS
(Median ~179 MiB) — Ursache ist der eager litellm-Import (seit iil-aifw 0.11.7 lazy,
aifw#40). promptfw (+2 MiB) und authoringfw (≤+2 MiB) sind vernachlässigbar.
Obergrenze des Einsparpotenzials: 17 × ~180 MiB ≈ **3,0 GiB** auf dem Host.

**Caveat (ehrliche Grenze der Messung):** Die Probe misst einen frischen
Python-Prozess je Container. Laufende gunicorn-/celery-Prozesse können Seiten per
Copy-on-Write teilen, und Container mit mehreren Workern zahlen den Import ggf.
mehrfach. Der tatsächliche Host-Effekt wird nach dem Rollout gemessen (Kriterium 4).

## Reproduzierbarkeit (Kriterium 1)

Zwei Läufe am 2026-08-11 (05:06 und 05:12 UTC): aifw-Spalte weicht je Container
um max. ±3 MiB (< 2 %) ab — Kriterium „< 10 %" erfüllt. Vergleichstabelle unten.

## Lauf 1 (vollständig)

# FW-RAM-Baseline — Host: hetzner-prod — 2026-08-11T05:06:24Z

## Host-Speicher (MB)

```
               total        used        free      shared  buff/cache   available
Mem:           23456       16010         417        1499        8926        7445
```

## Container-RSS-Ranking (docker stats)

| RSS | Limit | Container |
|---|---|---|
| 1.29GiB | 4GiB | iil_dochub_web |
| 93.66MiB | 512MiB | pptx_hub_web |
| 90.42MiB | 512MiB | coach_hub_web |
| 87.27MiB | 512MiB | illustration_db |
| 8.586MiB | 128MiB | decks_hub_web |
| 79.14MiB | 384MiB | recruiting_hub_celery |
| 74.85MiB | 384MiB | pptx_hub_worker |
| 70.67MiB | 384MiB | coach_hub_worker |
| 68.54MiB | 128MiB | coach_hub_beat |
| 65.25MiB | 256MiB | risk_hub_minio |
| 610.5MiB | 1GiB | tax_hub_web |
| 54.97MiB | 256MiB | dms_hub_beat |
| 537.8MiB | 1GiB | iil_authentik_server |
| 505.5MiB | 768MiB | hub137_web |
| 479.7MiB | 768MiB | risk_hub_web |
| 47.03MiB | 512MiB | risk_hub_db |
| 463.4MiB | 512MiB | ausschreibungs_hub_web |
| 45.18MiB | 512MiB | cad_hub_web |
| 440.8MiB | 1GiB | writing_hub_web |
| 37.75MiB | 512MiB | writing_hub_db |
| 376.4MiB | 1.5GiB | risk_hub_celery |
| 3.758MiB | 128MiB | learn-hub-redis-1 |
| 3.668MiB | 22.91GiB | tax_hub_redis |
| 3.648MiB | 128MiB | illustration_redis |
| 3.641MiB | 64MiB | writing_hub_redis |
| 3.469MiB | 256MiB | devhub_redis |
| 3.457MiB | 128MiB | recruiting_hub_redis |
| 340.1MiB | 512MiB | writing_hub_worker |
| 3.359MiB | 128MiB | hub137_redis |
| 33.55MiB | 512MiB | iil_dochub_gotenberg |
| 32.81MiB | 256MiB | dms_hub_db |
| 323.7MiB | 1GiB | devhub_web |
| 322.1MiB | 512MiB | ausschreibungs_hub_worker |
| 320.8MiB | 640MiB | tax_hub_worker |
| 3.195MiB | 22.91GiB | mon_node_exporter |
| 309.8MiB | 512MiB | hub137_worker |
| 30.72MiB | 256MiB | hub137_db |
| 3.062MiB | 128MiB | billing-hub-redis |
| 30.43MiB | 1GiB | coach_hub_db |
| 30.38MiB | 512MiB | learn-hub-db-1 |
| 287.9MiB | 512MiB | iil_knowledge_outline |
| 2.859MiB | 192MiB | pptx_hub_redis |
| 27.89MiB | 512MiB | billing-hub-db |
| 27.17MiB | 512MiB | recruiting_hub_db |
| 26.46MiB | 512MiB | ausschreibungs_hub_db |
| 2.379MiB | 64MiB | iil_dochub_redis |
| 2.305MiB | 64MiB | iil_knowledge_outline_redis |
| 22.93MiB | 512MiB | cad_hub_db |
| 225.5MiB | 512MiB | devhub_beat |
| 223.1MiB | 512MiB | iil_authentik_worker |
| 2.223MiB | 128MiB | cad_hub_redis |
| 2.168MiB | 320MiB | risk_hub_redis |
| 210.6MiB | 512MiB | billing-hub-web |
| 206.8MiB | 256MiB | ausschreibungs_hub_beat |
| 205.7MiB | 256MiB | hub137_beat |
| 20.44MiB | 512MiB | wedding_hub_db |
| 2.012MiB | 128MiB | dms_hub_redis |
| 2.012MiB | 128MiB | ausschreibungs_hub_redis |
| 198.6MiB | 512MiB | iil_dochub_tika |
| 1.781MiB | 256MiB | coach_hub_redis |
| 17.08MiB | 512MiB | pptx_hub_db |
| 166.2MiB | 512MiB | iil_authentik_db |
| 16.48MiB | 512MiB | aifw_service |
| 163.8MiB | 512MiB | billing-hub-celery |
| 157.6MiB | 512MiB | mcp_hub_orchestrator_http |
| 15.48MiB | 512MiB | wedding_hub_web |
| 1.484MiB | 128MiB | iil_authentik_redis |
| 143.2MiB | 512MiB | cad_hub_worker |
| 14.29MiB | 22.91GiB | buildx_buildkit_builder-c2898c88-4dd9-428b-becc-4914f75040f80 |
| 142.2MiB | 256MiB | iil_knowledge_outline_db |
| 1.414MiB | 192MiB | wedding_hub_redis |
| 139.1MiB | 512MiB | learn-hub-web-1 |
| 134.7MiB | 512MiB | illustration_worker |
| 134.5MiB | 512MiB | dms_hub_worker |
| 127.1MiB | 22.91GiB | mon_cadvisor |
| 124.6MiB | 512MiB | illustration_web |
| 121.2MiB | 384MiB | learn-hub-worker-1 |
| 113.2MiB | 512MiB | dms_hub_web |
| 104.7MiB | 512MiB | recruiting_hub_web |
| 100.6MiB | 22.91GiB | tax_hub_db |
| 50.8MiB | 256MiB | iil_dochub_db |
| 50.1MiB | 256MiB | recruiting_hub_celery_beat |
| 427MiB | 512MiB | devhub_celery |
| 214MiB | 384MiB | tax_hub_beat |
| 207MiB | 512MiB | risk_hub_worker |
| 171MiB | 1GiB | devhub_db |
| 107MiB | 512MiB | mcp_hub_db |

## Import-Kosten je App-Container (MiB, frischer Python-Prozess)

| Container | aifw | promptfw | authoringfw |
|---|---|---|---|
| ausschreibungs_hub_beat | kein python | — | — |
| ausschreibungs_hub_web | +192 | +1 | +0 |
| ausschreibungs_hub_worker | +196 | +2 | +0 |
| billing-hub-celery | n/a | n/a | n/a |
| billing-hub-web | n/a | n/a | n/a |
| cad_hub_web | +144 | n/a | +1 |
| cad_hub_worker | +146 | n/a | +1 |
| coach_hub_beat | n/a | n/a | n/a |
| coach_hub_web | n/a | n/a | n/a |
| coach_hub_worker | n/a | n/a | n/a |
| decks_hub_web | kein python | — | — |
| devhub_beat | +179 | n/a | n/a |
| devhub_celery | +177 | n/a | n/a |
| devhub_web | +180 | n/a | n/a |
| dms_hub_beat | n/a | n/a | n/a |
| dms_hub_web | n/a | n/a | n/a |
| dms_hub_worker | n/a | n/a | n/a |
| hub137_beat | kein python | — | — |
| hub137_web | +179 | n/a | +1 |
| hub137_worker | +179 | n/a | +1 |
| iil_authentik_worker | n/a | n/a | n/a |
| iil_dochub_web | n/a | n/a | n/a |
| illustration_web | n/a | n/a | n/a |
| illustration_worker | n/a | n/a | n/a |
| learn-hub-web-1 | n/a | n/a | n/a |
| learn-hub-worker-1 | n/a | n/a | n/a |
| pptx_hub_web | n/a | n/a | n/a |
| pptx_hub_worker | n/a | n/a | n/a |
| recruiting_hub_celery | n/a | n/a | n/a |
| recruiting_hub_celery_beat | n/a | n/a | n/a |
| recruiting_hub_web | n/a | n/a | n/a |
| risk_hub_celery | +188 | +2 | +0 |
| risk_hub_web | +189 | +2 | +0 |
| risk_hub_worker | +189 | +2 | +0 |
| tax_hub_beat | +176 | +2 | n/a |
| tax_hub_web | +175 | +2 | n/a |
| tax_hub_worker | +177 | +2 | n/a |
| wedding_hub_web | n/a | n/a | n/a |
| writing_hub_web | +179 | +2 | +2 |
| writing_hub_worker | +180 | +2 | +2 |

## Lauf 2 vs. Lauf 1 — aifw-Spalte (MiB)

| Container | Lauf 1 | Lauf 2 |
|---|---|---|
| ausschreibungs_hub_web | +192 | +194 |
| ausschreibungs_hub_worker | +196 | +197 |
| cad_hub_web | +144 | +146 |
| cad_hub_worker | +146 | +146 |
| devhub_beat | +179 | +180 |
| devhub_celery | +177 | +180 |
| devhub_web | +180 | +181 |
| hub137_web | +179 | +179 |
| hub137_worker | +179 | +180 |
| risk_hub_celery | +188 | +188 |
| risk_hub_web | +189 | +188 |
| risk_hub_worker | +189 | +188 |
| tax_hub_beat | +176 | +177 |
| tax_hub_web | +175 | +176 |
| tax_hub_worker | +177 | +177 |
| writing_hub_web | +179 | +180 |
| writing_hub_worker | +180 | +180 |
