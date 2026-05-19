# Staging/Prod Infra Contract

Enforcement of ADR-157 + ADR-198. **Not a new decision** — the transparent,
checkable form of existing ones. No ADR; CHANGELOG/PR on change.

One rule = one source = one check. If a rule has no check, it is not a
rule.

| # | Rule | Single source | Enforced by (red/green) |
|---|------|---------------|--------------------------|
| R1 | Every app-hub has `domain_prod`, `domain_staging`, `container_name` | `infra/ports.yaml` `services:` | `infra/scripts/staging_prod_contract.py` (exit 1) — CI gate |
| R2 | A staging domain under `iil.pet` is **single-label** (`staging-<app>.iil.pet` / `staging.iil.pet`); 2-label forbidden (CF Universal SSL covers 1 level) | ADR-198 §1.1 | same script (exit 1) — CI gate |
| R3 | iil.pet staging label is `staging` or `staging-<app>` | ADR-157 §4.1 / ADR-198 | same script (advisory, no fail) |
| R4 | Health probe path is **`/livez/`** (universal: defined in 100% of repos; `/healthz/` is not) | app code | the probe URL below |
| R5 | The contract is probed at the **edge** (CF→tunnel→nginx), not `localhost:PORT` — the localhost probe structurally cannot see the loop/SSL/ingress class (schutztat 301-loop) | — | Better Stack monitor, see below |

## Registry = `infra/ports.yaml` only

`repo-registry.yaml`, `repos.json:health_url`, and auto-gen
`project-facts/*` are **derived**, not parallel truth. They must be
generated from / reconciled to `ports.yaml`, never hand-edited to
diverge. (Divergence here is the root of the recurring "falsche Angaben".)

## Edge enforcement — no IP-allowlist toil

CF blocks anonymous external automation (verified: coach-hub `/livez/`
→ 403 from outside); ADR-198 §6 flags CF-IP-range allowlisting as
recurring toil. Therefore:

- One **Cloudflare Access** application over `staging-*.iil.pet` +
  `staging.<own-domain>` with **one service token**.
- Better Stack monitor per `(service × {prod,staging})`, URL
  `https://<domain_{prod,staging}>/livez/`, with `request_headers`:
  `CF-Access-Client-Id` / `CF-Access-Client-Secret` (verified: Better
  Stack supports `request_headers`). Stable, zero IP maintenance.

A red monitor = the contract is broken at the layer that actually breaks.
Diagnosis is then `evidence-discipline` (origin-direct `curl`), not more
config-guessing.

## Run the gate

```bash
python3 infra/scripts/staging_prod_contract.py     # exit 1 = block
```

Wire into CI alongside existing infra checks. Current state at authoring:
24 services conform, 0 violations.
