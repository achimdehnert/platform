"""registry_api — importierbarer Accessor für die kanonische Registry (ADR-234 P0).

Single Source of Truth ist `registry/canonical.yaml`. Die zwei Altdateien
(`scripts/repo-registry.yaml`, `registry/repos.yaml`) sind generierte, gate-
erzwungene Views (kein Edit von Hand). **Neuer Code** liest die Registry über
dieses Modul — bestehende View-Leser bleiben unverändert (Views sind eine
legitime, divergenzsichere Read-API).

Dies ist die EINE Projektion-Implementierung (`gen_flat`/`gen_rich`); die CLI
`registry-canonical.py` (build/flip/verify) **importiert** sie, damit Accessor
und Drift-Gate nie auseinanderlaufen.

Verwendung (neuer Code):
    import sys; sys.path.insert(0, "<…>/platform/tools")
    import registry_api as reg
    reg.flat()           # {server, repos:{name:{type,prod_url,port,health,…}}}  (= scripts/repo-registry.yaml-Form)
    reg.rich()           # {domains:[{name, systems:[…]}]}                        (= registry/repos.yaml-Form)
    reg.repos()          # sortierte Repo-Namen (alle ~44)
    reg.repo("risk-hub") # zusammengeführter Datensatz (flat+rich+meta) für EIN Repo
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "registry" / "canonical.yaml"


def load_canonical() -> dict:
    """Lädt die kanonische Union-Registry."""
    return yaml.safe_load(CANON.read_text())


def gen_flat(canon: dict) -> dict:
    """Projiziert die flache View (scripts/repo-registry.yaml-Form)."""
    out = {"server": canon["meta"].get("server", {}), "repos": {}}
    for n, e in canon["repos"].items():
        if e.get("in_flat"):
            out["repos"][n] = e["flat"]
    return out


def gen_rich(canon: dict) -> dict:
    """Projiziert die reiche View (registry/repos.yaml-Form, domains[])."""
    order = canon["meta"].get("domain_order", [])
    by_dom: dict[str, list] = {d: [] for d in order}
    for n, e in canon["repos"].items():
        if e.get("in_rich"):
            by_dom.setdefault(e.get("domain"), []).append(e["rich"])
    return {"domains": [{"name": d, "systems": by_dom[d]} for d in by_dom if by_dom[d]]}


# ── Convenience-Accessoren für neuen Code ──────────────────────────────────────

def flat() -> dict:
    return gen_flat(load_canonical())


def rich() -> dict:
    return gen_rich(load_canonical())


def repos() -> list[str]:
    """Alle Repo-Namen der Union (sortiert)."""
    return sorted(load_canonical()["repos"])


def repo(name: str) -> dict | None:
    """Zusammengeführter Datensatz für EIN Repo (flat+rich+meta) — None wenn unbekannt."""
    e = load_canonical()["repos"].get(name)
    if e is None:
        return None
    merged = {**(e.get("flat") or {}), **(e.get("rich") or {})}
    merged.update(domain=e.get("domain"), in_flat=e.get("in_flat", False), in_rich=e.get("in_rich", False))
    return merged
