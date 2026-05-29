# Concept: Evidence Discipline + SSOT Enforcement

Status: **for review** · 2026-05-19 · no new ADR (enforces ADR-157/198;
behavioural part is a policy, not architecture) · review item-by-item.

## 1. Problem (one class, three faces)

Repeated platform incidents share one root: **a consequential claim
asserted above what its cheapest check would prove.**

- *Over-claim:* "Festgehalten: memory X" (file never existed), "Integration
  Tests in 1m2s", premature ADR go-live.
- *Over-diagnose:* "CF Flexible SSL loop", "deploy_check server-side
  broken", "infra smell / not my code" — labels emitted before the one
  cheap check that disambiguates.
- *SSOT drift:* one truth (`ports.yaml`, ADR-198) + many stale copies
  (`repo-registry.yaml`, `repos.json:health_url`, `project-facts/*`,
  `setup-server.sh`) → "falsche Angaben" for staging/prod hosts.

These are the same failure. Enforcement that exists
(`audit_platform.py`) probes `localhost:PORT` (CF blocks edge automation),
so it structurally cannot see the loop/SSL/ingress class that keeps
biting (schutztat 301-loop).

## 2. Findings (verified this session)

| # | Finding | Evidence | Status |
|---|---------|----------|--------|
| F1 | schutztat 301-loop = cloudflared ingress `http://localhost:80` → nginx 301, **not** CF SSL mode | origin `curl` http→301 / https→405 | verified |
| F2 | `deploy_check` "broken" was a config error: ports.yaml resolved at `/opt/platform`\|`/root/github`; canonical `/home/devuser/github/...`, healthy | tool call + `ls` | verified |
| F3 | `ports.yaml` is the only complete (service×env) registry (domain_prod/staging, container) | read | verified |
| F4 | `/livez/` is universal (100% repos); `repos.json` `/healthz/` is the divergence | platform-wide grep | verified |
| F5 | `nginx_gen.py` injects **no** response security headers | full read | verified |
| F6 | Better Stack supports `request_headers` → CF Access service-token probe possible (no IP-allowlist toil) | API doc | verified |
| F7 | iil.pet staging domains must be single-label (CF Universal SSL); `ports.yaml` mixes patterns | ADR-198 §1.1 | verified |

## 3. Delivered (open PRs / files — review these)

- **Policy** `~/.claude/policies/evidence-discipline.md` — active, hook-injected,
  trimmed to operative core, **binding falsification test** (cut if it
  doesn't beat baseline over ~10 sessions). Recall surface = memory
  `claim-confidence-vs-cheapest-check` (incident log only).
- **PR #207** — `drift-check` Step 9 resolution-direction rule (correct
  SSOT toward proven reality).
- **PR #208** — `infra/STAGING-PROD-CONTRACT.md` + `staging_prod_contract.py`
  (R1 registry completeness, R2 single-label SSL hard gate, R3 naming
  advisory). Lint verified: 24 services conform, exit 0.

## 4. Proposed, not yet actioned (decide per item)

| P | Action | Cost | Owner |
|---|--------|------|-------|
| P1 | Wire `staging_prod_contract.py` into CI next to existing infra checks | 1 line | platform CI |
| P2 | One CF Access app over `staging-*` + service token; `CF-Access-Client-*` into Better Stack `request_headers`; monitor per (service×{prod,staging}) `/livez/` | 1 dashboard action + monitor entries from `ports.yaml` | infra owner |
| P3 | Make `repo-registry.yaml` / `repos.json:health_url` / `project-facts/*` **generated from** `ports.yaml`, not parallel-edited | medium | platform |
| P4 | Hand F2 (orchestrator ports.yaml path/mount) to orchestrator owner | small | mcp-hub |

## 5. Open / unverified (honest)

- P2 feasibility of CF Access service token end-to-end not tested live
  (Better Stack header support verified; CF app not created).
- F5 implies generated nginx has no security headers — real gap, **out
  of scope here**, flagged not fixed.
- Effectiveness of the policy itself is unproven until the binding
  forward test runs.

## 6. Deliberately NOT done (anti-over-engineering)

No conformance-scanner framework, no new monitoring tool, no new ADR, no
internal-knob spec. Reuse: `ports.yaml` (registry), Better Stack
(enforcement), ADR-157/198 (decision). New artifacts kept to one lint +
two docs + one policy.
