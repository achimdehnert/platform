# skip_tests-Opt-out-Audit — 2026-07-02

> Fleet-Konvergenz-Runde, Cluster B. Zweck: je Repo belegen, **warum** `skip_tests:true` gesetzt ist,
> und den Template-Default vom bewussten Opt-out trennen. Read-only Bestandsaufnahme (grep, file:line).

## Prämissen-Korrektur (wichtig)

Der ursprüngliche trading-hub-Befund vermutete „shared-ci hat keinen DB-Service". **Falsch:**
`shared-ci/.github/workflows/_ci-python.yml:258-260` stellt bereits einen Postgres-Service bereit
(gated auf `!skip_tests`) **plus** einen Migration-Smoke-Opt-in (`:99`) für genau den skip-Fall.
→ Der Fix ist **kein** shared-ci-Change, sondern ein Per-Repo-Opt-out-Audit.

## Zweite Erkenntnis: `deploy.yml:35` ist ein Template-Default

18 der 21 Treffer stehen in `deploy.yml` auf **identischer Zeile 35** — das ist ein kopierter
Template-Default (Deploy-Pfad überspringt Tests), keine 18 unabhängigen Entscheidungen. Die eigentliche
Frage ist zweigeteilt:
- **ci.yml-Treffer** (billing-hub:12, coach-hub:12, pptx-hub:18/23, trading-hub:12) → hier laufen im
  regulären CI **keine** Tests. Das ist der ernste Fall.
- **deploy.yml-Treffer** → Deploy überspringt Tests. Vertretbar, WENN ci.yml sie auf PR/push fährt.

## Bestandsaufnahme (grep, file:line)

| Repo | ci.yml skip? | deploy.yml skip? | Einordnung |
|---|---|---|---|
| billing-hub | **ci.yml:12** | deploy.yml:35 | ⛔ CI testet nicht — Prio |
| coach-hub | **ci.yml:12** | deploy.yml:44 | ⛔ CI testet nicht — Prio |
| pptx-hub | **ci.yml:18/23** | deploy.yml:35 | ⛔ CI testet nicht — Prio |
| trading-hub | **ci.yml:12** | deploy.yml:46 | ⛔ CI testet nicht (bewusst: TimescaleDB-Hypertables, lokale Tests) — Migration-Smoke-Opt-in prüfen |
| 137-hub | — | deploy.yml:35 | 🟡 nur Deploy-Skip — ci.yml verifizieren |
| ausschreibungs-hub | — | deploy.yml:35 | 🟡 |
| dev-hub | — | deploy.yml:37 | 🟡 (TENANCY disabled, ci.yml prüfen) |
| dms-hub | — | deploy.yml:35 | 🟡 |
| illustration-hub | — | deploy.yml:35 | 🟡 |
| learn-hub | — | deploy.yml:35 | 🟡 |
| mcp-hub | — | deploy.yml:38 | 🟡 |
| recruiting-hub | — | deploy.yml:40 | 🟡 |
| research-hub | — | deploy.yml:35 | 🟡 |
| risk-hub | — | deploy.yml:37 | 🟡 |
| tax-hub | — | deploy.yml:35 | 🟡 |
| travel-beat | — | deploy.yml:35 | 🟡 |
| wedding-hub | — | deploy.yml:35 | 🟡 |
| weltenhub | — | deploy.yml:35 | 🟡 |

## Empfohlenes Vorgehen (keine autonome Umsetzung)

1. **Prio (⛔, 4 Repos):** ci.yml von `skip_tests:true` befreien — sofern nicht wie trading-hub bewusst
   (dann Migration-Smoke-Opt-in `_ci-python.yml:99` aktivieren, damit Migrationen trotzdem CI-verifiziert
   sind). Je Repo einzeln, kein Massen-Flip.
2. **🟡 (18 Repos):** verifizieren, dass ci.yml die Tests fährt; wenn ja, ist der deploy.yml-Skip ok →
   dokumentieren. Wenn nein → in Prio hochstufen.
3. **Template:** den `deploy.yml`-Default entscheiden — soll der Deploy-Pfad testen, wenn ci.yml es
   bereits tut? (Doppel-Compute vs. Sicherheitsnetz.) Das ist eine Template-Politik-Frage, kein Bug.

_Belegkommando: `grep -rnE 'skip_tests:\s*true' */.github/workflows/`_
