#!/usr/bin/env python3
"""registry-canonical — Union-Canonical-Registry + View-Generatoren (ADR-234 P0, Schritt 1).

Die zwei Alt-Registries haben UNTERSCHIEDLICHEN Scope (kein Superset, verifiziert via
registry-consistency-check.py): `scripts/repo-registry.yaml` = flaches Flotten-Inventar
(42 Repos), `registry/repos.yaml` = kuratiertes deployed-Subset (18 Systeme, domains[]).

Dieses Tool baut programmatisch eine **kanonische Union** aus BEIDEN und kann beide
Altdateien daraus **semantisch verlustfrei** wieder erzeugen — der Beweis, dass die
Union-Canonical-Strategie trägt, BEVOR irgendein Konsument migriert wird.

Kanonisches Schema (`registry/canonical.yaml`):
    meta:   { server: {...}, domain_order: [...] }          # Alt-Metadaten erhalten
    repos:
      <name>:
        in_flat: bool         # stand in scripts/repo-registry.yaml
        in_rich: bool         # stand in registry/repos.yaml
        domain: <str|null>    # Domain-Gruppe (für Rich-View-Regruppierung)
        flat: { ...verbatim flache Felder... }
        rich: { ...verbatim reiche System-Felder... }
    Felder werden VERBATIM aus den Quellen übernommen (keine verlustbehaftete Ableitung)
    → beide Views sind exakte Projektionen.

Registry-Schreibpfad (SSoT seit dem Flip 2026-06-01, ADR-234): `registry/canonical.yaml`
per Hand editieren → `python3 tools/registry-canonical.py build` (oder `make registry-build`)
→ `python3 tools/registry-canonical.py verify` (oder `make registry-verify`). Die Altdateien
(`scripts/repo-registry.yaml`, `registry/repos.yaml`) sind generierte Views — nie von Hand
editieren, sie werden vom `verify`-Gate (registry-consistency.yml) gegen canonical.yaml geprüft.

Subcommands:
    build    — beide Altdateien → registry/canonical.yaml (Union)
    gen-flat — canonical → flache Struktur (stdout)
    gen-rich — canonical → reiche domains[]-Struktur (stdout)
    verify   — round-trip: regeneriere beide, vergleiche SEMANTISCH mit den Altdateien
    flip     — schreibt beide Altdateien als generierte Views aus canonical.yaml (GEN-Header;
               einmalig genutzt für den Kanonisierungs-Flip, danach nur bei bewusster
               Header-Auffrischung — siehe `flip()` unten)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FLAT = ROOT / "scripts" / "repo-registry.yaml"
RICH = ROOT / "registry" / "repos.yaml"
CANON = ROOT / "registry" / "canonical.yaml"


def _load(p: Path):
    return yaml.safe_load(p.read_text())


def build() -> dict:
    flat_doc = _load(FLAT)
    rich_doc = _load(RICH)
    flat_repos = {k: v for k, v in (flat_doc.get("repos") or {}).items() if isinstance(v, dict)}

    domain_order = []
    rich_sys = {}     # name -> (domain, system-dict)
    for dom in rich_doc.get("domains", []):
        dname = dom.get("name")
        domain_order.append(dname)
        for s in dom.get("systems", []):
            key = s.get("repo") or s.get("name")
            rich_sys[key] = (dname, s)

    names = sorted(set(flat_repos) | set(rich_sys))
    repos = {}
    for n in names:
        entry = {"in_flat": n in flat_repos, "in_rich": n in rich_sys}
        if n in flat_repos:
            entry["flat"] = flat_repos[n]
        if n in rich_sys:
            dname, s = rich_sys[n]
            entry["domain"] = dname
            entry["rich"] = s
        repos[n] = entry

    return {
        "meta": {
            "server": flat_doc.get("server", {}),
            "domain_order": domain_order,
            # Governance-Scope für registry_coverage_drift (KONZ-001 R5): welche GitHub-Owner
            # die clean-state-Invariante umfasst. Hier (nicht in repos.yaml), weil der flip-
            # Roundtrip top-level Source-Keys droppt. bahn-sqf IN (Owner hat Admin), pactive-de
            # bewusst AUSSEN (separates Kunden-Vault). Entscheidung 2026-06-06, Issue #488.
            "enterprise_owners": ["achimdehnert", "iilgmbh", "ttz-lif", "meiki-lra", "bahn-sqf"],
            # Per-Repo-Owner-Override (Transition, = IST-Zustand). KONZ-001 P0 Teil 2:
            # flat-only Repos können keinen rich.github tragen (circular pipeline),
            # darum die per-gh-VERIFIZIERTEN KONZ-002-Migrationen hier als meta-Override
            # (build-stabil). Stopgap bis das echte per-Repo-owner-Feld kommt.
            # ⚠ Nur Repos eintragen, die WIRKLICH schon unter der Org liegen — sonst
            #   findet das Tooling das Repo am falschen Ort. ZIEL-Owner (Migration)
            #   gehören in registry/iil-migration.yaml, NICHT hierher (ADR-255 REC-3).
            # Re-verifiziert gh 2026-06-23 (ADR-255 Phase-0).
            "repo_owner": {
                "iil-fieldprefill": "iilgmbh",
                "iil-relaunch": "iilgmbh",
                "illustration-fw": "iilgmbh",
                # Org-Mapping-Externalisierung (Konsument: iil-klickdummy detect_org,
                # 2026-06-12) — Werte identisch zu dessen bisheriger Code-Heuristik.
                "iil-klickdummy": "iilgmbh",
                # iil-testkit ENTFERNT 2026-06-23: Eintrag behauptete iilgmbh (angeblich
                # gh-verifiziert 2026-06-06), real aber achimdehnert/iil-testkit (gh
                # 2026-06-23, Gegenprobe: nicht in `gh repo list iilgmbh`). Default
                # (server.github_org=achimdehnert) ist jetzt korrekt. Ziel-Owner in
                # registry/iil-migration.yaml als status=pending. (ADR-255 Drift-Fund.)
            },
            # Geordnete Präfix-Heuristik für Repos OHNE repo_owner-Eintrag. Konsument:
            # iil-klickdummy genesor (detect_org) — ersetzt dessen hartkodierte Heuristik.
            # Gleicher Stopgap-Status wie repo_owner (REC-11: gehört langfristig als
            # owner_team-Feld ins Datenmodell). Default für Nicht-Treffer: server.github_org.
            "owner_prefix_rules": [
                {"prefix": "meiki-", "owner": "meiki-lra"},
                {"prefix": "ttz-", "owner": "ttz-lif"},
                {"prefix": "sqf-", "owner": "bahn-sqf"},
                {"prefix": "pg-", "owner": "bahn-sqf"},
                {"prefix": "bahn-", "owner": "bahn-sqf"},
            ],
            # App-Anzeigenamen (Konsument: iil-klickdummy genesor render_fallback) —
            # externalisiert aus dessen app_name_map (2026-06-12). Fallback dort:
            # Titel-Heuristik aus dem Repo-Namen.
            "app_display_names": {
                "meiki-hub": "MEiKI · LRA-Plattform",
                "ausschreibungs-hub": "Bieterpilot",
                "writing-hub": "Writing-Hub",
                "risk-hub": "Risk-Hub",
                "ttz-hub": "TTZ-Hub",
                "sqf-hub": "SQF-Hub",
                "pg-hub": "PG-Hub",
            },
            "_note": "KANONISCHE SSoT (ADR-234 P0, Flip vollzogen 2026-06-01 via "
                     "`registry-canonical.py flip`). Union aus scripts/repo-registry.yaml + "
                     "registry/repos.yaml; beide Altdateien sind jetzt generierte, "
                     "gate-erzwungene Views (verify-Gate in registry-consistency.yml). Edits "
                     "nur hier, nie in den Views. Accessor: tools/registry_api.py.",
        },
        "repos": repos,
    }


# Projektion-Logik lebt in registry_api (eine Implementierung → Accessor + Drift-Gate
# laufen nie auseinander). Sibling-Import: beim Direktaufruf ist tools/ in sys.path[0].
from registry_api import gen_flat, gen_rich  # noqa: E402


def _norm(x):
    """Sortier-normalisierte Tiefkopie für reihenfolge-unabhängigen Vergleich."""
    if isinstance(x, dict):
        return {k: _norm(x[k]) for k in sorted(x)}
    if isinstance(x, list):
        # Listen von Systemen: nach repo/name sortieren; sonst elementweise normalisieren
        norm = [_norm(i) for i in x]
        try:
            return sorted(norm, key=lambda d: d.get("repo") or d.get("name") or str(d) if isinstance(d, dict) else str(d))
        except TypeError:
            return norm
    return x


def verify(canon: dict) -> int:
    rc = 0
    # Flat
    gen_f = gen_flat(canon)
    cur_f = _load(FLAT)
    cur_f = {"server": cur_f.get("server", {}), "repos": cur_f.get("repos", {})}
    if _norm(gen_f) == _norm(cur_f):
        print("✅ flat-View: semantisch identisch zu scripts/repo-registry.yaml")
    else:
        rc = 1
        print("🔴 flat-View weicht ab:")
        _diff(_norm(cur_f), _norm(gen_f))
    # Rich
    gen_r = gen_rich(canon)
    cur_r = {"domains": _load(RICH).get("domains", [])}
    if _norm(gen_r) == _norm(cur_r):
        print("✅ rich-View: semantisch identisch zu registry/repos.yaml")
    else:
        rc = 1
        print("🔴 rich-View weicht ab:")
        _diff(_norm(cur_r), _norm(gen_r))
    return rc


def _diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                print(f"  + nur generiert: {path}/{k}")
            elif k not in b:
                print(f"  - nur original:  {path}/{k}")
            else:
                _diff(a[k], b[k], f"{path}/{k}")
    elif a != b:
        print(f"  ≠ {path}: orig={a!r} gen={b!r}")


GEN_NOTICE = (
    "# ╔══════════════════════════════════════════════════════════════════════╗\n"
    "# ║  GENERATED — NICHT VON HAND EDITIEREN (ADR-234 P0).                    ║\n"
    "# ║  Kanonische Quelle: registry/canonical.yaml                           ║\n"
    "# ║  Regenerieren:  python3 tools/registry-canonical.py flip               ║\n"
    "# ║  CI-Drift-Gate (registry-consistency.yml) failt bei Divergenz.        ║\n"
    "# ╚══════════════════════════════════════════════════════════════════════╝\n"
)


def _leading_comments(path: Path) -> str:
    """Führenden Kommentarblock (Zeilen bis zum ersten Daten-Key) verbatim zurückgeben."""
    out = []
    for line in path.read_text().splitlines():
        s = line.lstrip()
        if s.startswith("#") or s == "":
            out.append(line)
        else:
            break
    return "\n".join(out).rstrip() + "\n" if out else ""


# Exakte Zeilen-Identität der GEN_NOTICE-Konstante (REC-5: deterministisch statt Box-Zeichen-
# Heuristik — robust, auch falls Schema-Docs je Box-Zeichen nutzen). Test: test_registry_canonical.
_GEN_NOTICE_LINES = frozenset(GEN_NOTICE.strip("\n").splitlines())


def _strip_gen_notice(text: str) -> str:
    """Entfernt einen aus einem FRÜHEREN flip vorhandenen GEN_NOTICE-Block per exakter
    Zeilen-Identität (kein Heuristik-Match), bevor flip ihn neu setzt — sonst akkumuliert jeder
    Roundtrip einen weiteren Header (Doppel-Header-Bug, belegt beim C9-Lag-PR). Idempotent."""
    return "\n".join(ln for ln in text.splitlines() if ln not in _GEN_NOTICE_LINES).strip("\n")


def flip(canon: dict) -> int:
    """Schreibt BEIDE Altdateien als generierte Views aus canonical (ADR-234 P0 Flip).
    Erhält den wertvollen Schema-Doc-Header der reichen Datei verbatim; die flache
    bekommt nur den GENERATED-Header. Danach muss `verify` weiterhin grün sein (semantisch).

    GRENZE (REC-7): `yaml.safe_dump` ist round-trip-**lossy** für Inline-Daten-Kommentare —
    flip behebt NUR die Header-Akkumulation, nicht den Kommentar-Verlust innerhalb der Daten.
    Vollständig verlustfrei wäre nur mit ruamel.yaml (eigene Entscheidung)."""
    rich_header = _strip_gen_notice(_leading_comments(RICH))
    FLAT.write_text(GEN_NOTICE + "\n" + yaml.safe_dump(gen_flat(canon), sort_keys=False, allow_unicode=True, width=100))
    RICH.write_text(GEN_NOTICE + "\n" + rich_header + "\n" + yaml.safe_dump(gen_rich(canon), sort_keys=False, allow_unicode=True, width=100))
    print(f"✅ geflippt: {FLAT.relative_to(ROOT)} (frischer GEN-Header) + {RICH.relative_to(ROOT)} (Schema-Docs erhalten).")
    return verify(canon)


def main() -> int:
    ap = argparse.ArgumentParser(description="Union-Canonical-Registry (ADR-234 P0 Schritt 1).")
    ap.add_argument("cmd", choices=["build", "gen-flat", "gen-rich", "verify", "flip"])
    args = ap.parse_args()

    if args.cmd == "build":
        canon = build()
        CANON.write_text(yaml.safe_dump(canon, sort_keys=False, allow_unicode=True, width=100))
        nf = sum(1 for e in canon["repos"].values() if e["in_flat"])
        nr = sum(1 for e in canon["repos"].values() if e["in_rich"])
        print(f"✅ {CANON.relative_to(ROOT)} gebaut: {len(canon['repos'])} Repos (flat={nf}, rich={nr}).")
        return 0

    if not CANON.exists():
        print("FEHLER: registry/canonical.yaml fehlt — erst `build`.", file=sys.stderr)
        return 2
    canon = _load(CANON)

    if args.cmd == "gen-flat":
        print(yaml.safe_dump(gen_flat(canon), sort_keys=False, allow_unicode=True, width=100))
    elif args.cmd == "gen-rich":
        print(yaml.safe_dump(gen_rich(canon), sort_keys=False, allow_unicode=True, width=100))
    elif args.cmd == "verify":
        return verify(canon)
    elif args.cmd == "flip":
        return flip(canon)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
