#!/usr/bin/env python3
"""registry_coverage_drift.py — KONZ-001 R5 „Liar-Liste" v2 (read-only, Issue #488).

Gleicht die GitHub-Realität gegen die SSoT `registry/canonical.yaml` ab und meldet die
*Lügen*-Liste statt der Grün-Liste. v2 arbeitet die adversariale Pilot-PR-Review ein:

- O1 — **Owner dynamisch entdeckt** (`gh api user/orgs` + User), NICHT hardcoded → blind für
  keinen Owner mehr (AD-1: die alte 4er-Hand-Liste übersah bahn-sqf/pactive-de/…).
- O3 — **Completeness-Attestation** als Erst-Klasse-Output: `owners_queried`, `truncation_*`,
  `schema_incomplete`, `advisory` → das Tool kann *ehrliches Scheitern* ausdrücken statt stiller
  false-negatives (AD-2/3/10).
- O6 — **SCHEMA-INCOMPLETE** eigene Klasse: Repos ohne expliziten `rich.github` werden NICHT
  still auf den globalen Org-Default gewaschen, sondern als Schema-Lücke geflaggt (AD-7).
- O2 — **Severity-gewichtet** (`critical|warn|info`) aus `lifecycle`/`deployed` statt flacher
  Integer; `--strict` gatet auf `critical>0` (AD-5).
- AD-4 — basename-Kollision: nur 1 Kandidat → MIGRATED; ≥2 → **AMBIGUOUS** (sichtbar, nicht still).
- O4 — `--ledger <pfad>`: hängt einen datierten Drift-Record an (Trend statt Snapshot — die
  Konzept-These „Health = Ableitung").

Read-only/advisory (exit 0); `--strict` → exit 1 bei `critical>0` (gated, KONZ-001 R2b, hinter ADR).
Reiner Kern (`compute_drift`) ist netz-frei → R7-Fault-Injection (s. test).
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import yaml

CANONICAL = Path(__file__).resolve().parents[1] / "registry" / "canonical.yaml"
DEFAULT_OWNERS = ["achimdehnert", "iilgmbh", "ttz-lif", "meiki-lra"]  # nur Fallback
LIMIT = 500


def _basename(full: str) -> str:
    return full.split("/", 1)[-1]


def _gh(args: list) -> str | None:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def discover_owners() -> list:
    """O1: reale Owner = User + alle Orgs, die der Token sieht (gh api). Fallback: DEFAULT_OWNERS."""
    owners = set()
    u = _gh(["api", "user", "--jq", ".login"])
    if u:
        owners.add(u.strip())
    o = _gh(["api", "user/orgs", "--jq", ".[].login"])
    if o:
        owners |= {x.strip() for x in o.splitlines() if x.strip()}
    return sorted(owners) if owners else list(DEFAULT_OWNERS)


def gh_repo_fullnames(owner: str) -> tuple[set, bool]:
    """Gibt (fullnames, truncated). truncated=True wenn das Limit erreicht wurde (AD-2)."""
    out = _gh(["repo", "list", owner, "--limit", str(LIMIT), "--json", "nameWithOwner",
               "-q", ".[].nameWithOwner"])
    if out is None:
        return set(), False  # Owner-Fehler → leer + Attestation-Warnung (AD-8: kein sys.exit)
    names = {ln.strip() for ln in out.splitlines() if ln.strip()}
    return names, len(names) >= LIMIT


def parse_canonical(path: str, default_org: str) -> dict:
    """fullname -> {lifecycle, deployed, owner_explicit, name}. owner_explicit=False ⇒ SCHEMA-INCOMPLETE (O6).

    Owner-Auflösung (Priorität): rich.github > meta.repo_owner-Override (P0-Transition für flat-only
    Migrationen) > default_org. Beide expliziten Quellen setzen owner_explicit=True."""
    d = yaml.safe_load(open(path))
    overrides = (d.get("meta") or {}).get("repo_owner") or {}
    out = {}
    for name, e in (d.get("repos") or {}).items():
        e = e or {}
        rich = e.get("rich") or {}
        flat = e.get("flat") or {}
        gh = rich.get("github")
        ov = overrides.get(name)
        if gh:
            fn, explicit = gh, True
        elif ov:
            fn, explicit = f"{ov}/{name}", True
        else:
            fn, explicit = f"{default_org}/{name}", False
        out[fn] = {
            "name": name,
            "lifecycle": rich.get("lifecycle") or flat.get("lifecycle"),
            "deployed": rich.get("deployed", flat.get("deployed")),
            "owner_explicit": explicit,
        }
    return out


def _critical(meta: dict) -> bool:
    return meta.get("lifecycle") == "production" or meta.get("deployed") is True


def compute_drift(ground: set, canonical: dict) -> dict:
    """Reine Klassifikation inkl. Severity + Ambiguität — netz-frei, R7-testbar."""
    canon_set = set(canonical)
    raw_gap = ground - canon_set
    raw_phantom = canon_set - ground
    gap_by_base = {}
    for fn in raw_gap:
        gap_by_base.setdefault(_basename(fn), []).append(fn)

    migrated, ambiguous, resolved = [], [], set()
    for pfn in sorted(raw_phantom):
        cands = sorted(gap_by_base.get(_basename(pfn), []))
        if len(cands) == 1:
            migrated.append({"repo": _basename(pfn), "canonical": pfn, "reality": cands[0]})
            resolved.add(pfn)
        elif len(cands) >= 2:                                    # AD-4: nicht still migrieren
            ambiguous.append({"repo": _basename(pfn), "canonical": pfn, "candidates": cands})
            resolved.add(pfn)
    busy_bases = {m["repo"] for m in migrated} | {a["repo"] for a in ambiguous}
    enrollment_gap = sorted(fn for fn in raw_gap if _basename(fn) not in busy_bases)
    phantom = sorted(fn for fn in raw_phantom if fn not in resolved)
    schema_incomplete = sorted(fn for fn, m in canonical.items() if not m["owner_explicit"])

    crit = (sum(1 for m in migrated if _critical(canonical.get(m["canonical"], {})))
            + sum(1 for fn in phantom if _critical(canonical.get(fn, {})))
            + len(ambiguous))                                   # Ambiguität ist immer kritisch
    warn = (len(enrollment_gap)
            + sum(1 for m in migrated if not _critical(canonical.get(m["canonical"], {})))
            + sum(1 for fn in phantom if not _critical(canonical.get(fn, {}))))
    return {
        "enrollment_gap": enrollment_gap,
        "migrated": sorted(migrated, key=lambda m: m["repo"]),
        "ambiguous": sorted(ambiguous, key=lambda a: a["repo"]),
        "phantom": phantom,
        "schema_incomplete": schema_incomplete,
        "covered": sorted(ground & canon_set),
        "severity": {"critical": crit, "warn": warn, "info": len(schema_incomplete)},
        "drift_score": crit + warn,                             # info (Schema) separat, nicht blockierend
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owners", default=None, help="Komma-Liste; Default: dynamisch entdeckt (gh api)")
    ap.add_argument("--canonical", default=str(CANONICAL))
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--strict", action="store_true", help="exit 1 bei critical>0 (gated)")
    ap.add_argument("--ledger", default=None, help="datierten Drift-Record an Datei anhängen (Trend, O4)")
    a = ap.parse_args()

    d = yaml.safe_load(open(a.canonical))
    canon_org = (d.get("meta") or {}).get("server", {}).get("github_org", "achimdehnert")
    canonical = parse_canonical(a.canonical, canon_org)

    # Scope ist GOVERNANCE, in der SSoT deklariert (meta.enterprise_owners) — nicht hardcoded
    # und nicht discover-all (sonst Rauschen durch externe Orgs). Discovery dient dem *Aufdecken*
    # von Kandidaten, die noch nicht im Scope stehen (Attestation), nicht dem blinden Verbreitern.
    meta = d.get("meta") or {}
    scope_source = "--owners"
    if a.owners:
        owners = [o.strip() for o in a.owners.split(",") if o.strip()]
    elif meta.get("enterprise_owners"):
        owners, scope_source = list(meta["enterprise_owners"]), "canonical.meta.enterprise_owners"
    else:
        owners, scope_source = list(DEFAULT_OWNERS), "FALLBACK (meta.enterprise_owners fehlt!)"
    discovered_unscoped = sorted(set(discover_owners()) - set(owners))

    ground, truncated, failed = set(), [], []
    for o in owners:
        names, trunc = gh_repo_fullnames(o)
        if not names:
            failed.append(o)
        ground |= names
        if trunc:
            truncated.append(o)
    res = compute_drift(ground, canonical)

    attestation = {
        "owners_queried": owners,
        "scope_source": scope_source,
        "discovered_unscoped": discovered_unscoped,  # Owner, die der Token sieht, aber NICHT im Scope → Review
        "owners_failed": failed,                      # leere/fehlgeschlagene Abfragen → Ergebnis unvollständig
        "truncation_warning": truncated,              # Limit erreicht → mögliche stille Lücke
        "schema_incomplete_count": res["severity"]["info"],
        "advisory": not a.strict,
    }

    if a.ledger:
        stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M")
        sev = res["severity"]
        line = (f"{stamp}\tdrift={res['drift_score']}\tcrit={sev['critical']}\twarn={sev['warn']}"
                f"\tschema_incomplete={sev['info']}\tgaps={len(res['enrollment_gap'])}"
                f"\tmigrated={len(res['migrated'])}\tambiguous={len(res['ambiguous'])}"
                f"\tphantom={len(res['phantom'])}\towners={len(owners)}\n")
        with open(a.ledger, "a", encoding="utf-8") as f:
            f.write(line)

    if a.format == "json":
        print(json.dumps({"attestation": attestation, **res}, indent=2, ensure_ascii=False))
    else:
        s = res["severity"]
        print(f"=== registry_coverage_drift v2 (KONZ-001 R5) — owners={len(owners)} (scope: {attestation['scope_source']}) ===")
        if discovered_unscoped:
            print(f"  ⚠ ATTESTATION: {len(discovered_unscoped)} entdeckte Owner NICHT im Scope ({', '.join(discovered_unscoped)}) — in canonical.meta.enterprise_owners aufnehmen oder bewusst ausschließen")
        if "FALLBACK" in attestation["scope_source"]:
            print(f"  ⚠ ATTESTATION: Scope-FALLBACK — die SSoT deklariert keine enterprise_owners; Governance-Entscheidung offen")
        if failed:
            print(f"  ⚠ ATTESTATION: {len(failed)} Owner-Abfrage(n) fehlgeschlagen ({','.join(failed)}) — Ergebnis UNVOLLSTÄNDIG")
        if truncated:
            print(f"  ⚠ ATTESTATION: Truncation bei {','.join(truncated)} (≥{LIMIT}) — mögliche stille Lücke")
        print(f"  Ground-Truth: {len(ground)} · canonical: {len(canonical)} · covered: {len(res['covered'])}")
        print(f"  SEVERITY: critical={s['critical']} · warn={s['warn']} · info/schema-incomplete={s['info']}")
        print(f"  ENROLLMENT-GAP ({len(res['enrollment_gap'])}):")
        for r in res["enrollment_gap"]:
            print(f"    + {r}")
        print(f"  MIGRATED ({len(res['migrated'])}):")
        for m in res["migrated"]:
            print(f"    ~ {m['repo']}: {m['canonical']} → {m['reality']}")
        if res["ambiguous"]:
            print(f"  AMBIGUOUS ({len(res['ambiguous'])} — basename-Kollision, NICHT still migriert):")
            for am in res["ambiguous"]:
                print(f"    ? {am['repo']}: {am['canonical']} ↔ {am['candidates']}")
        print(f"  PHANTOM ({len(res['phantom'])}): {', '.join(res['phantom']) or '—'}")
        print(f"  SCHEMA-INCOMPLETE ({len(res['schema_incomplete'])}): Repos ohne expliziten Owner in der SSoT")
        print(f"=== DRIFT-SCORE: {res['drift_score']} (critical+warn; 0 = sauber) · advisory={attestation['advisory']} ===")
    sys.exit(1 if (a.strict and res["severity"]["critical"]) else 0)


if __name__ == "__main__":
    main()
