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

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "registry" / "canonical.yaml"
REVIEW_PROFILE = ROOT / "registry" / "review-profile.yaml"

#: Profil-Override je Repo (einzige erlaubte Repo-Abweichung, KONZ-070 Z4).
REVIEW_PROFILE_FELD = "review_profile"
#: Name des erwarteten CI-Checks je Repo (sonst defaults.ci_gate_check).
REVIEW_CHECK_FELD = "review_check"
#: Platzhalter in review-profile.yaml: required_checks aus dem shared-ci-Aggregat.
AUS_CI = "aus_ci"


def load_canonical() -> dict:
    """Lädt die kanonische Union-Registry."""
    return yaml.safe_load(CANON.read_text())


def load_review_profile() -> dict:
    """Lädt die Profil-Deklaration (registry/review-profile.yaml)."""
    return yaml.safe_load(REVIEW_PROFILE.read_text())


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


def _lifecycle(e: dict) -> str | None:
    """Lifecycle eines Eintrags — Top-Level bevorzugt, sonst aus dem rich-Block
    (bfagent trägt es historisch unter rich.lifecycle)."""
    return e.get("lifecycle") or (e.get("rich") or {}).get("lifecycle")


def gen_archived(canon: dict) -> dict:
    """Projiziert die Archiv-View (registry/archived-repos.yaml) — ALLE Einträge mit
    lifecycle=='archived', unabhängig von in_flat/in_rich (ADR-275 P0). Bewusst schlank:
    nur github/description/lifecycle — genug für validate_repos-Cross-Check + Doku,
    ohne Deploy-Metadaten toter Repos mitzuschleppen."""
    out: dict[str, dict] = {}
    for n, e in sorted(canon["repos"].items()):
        if _lifecycle(e) != "archived":
            continue
        rich = e.get("rich") or {}
        out[n] = {
            "github": e.get("github") or rich.get("github"),
            "description": e.get("description") or rich.get("description"),
            "lifecycle": "archived",
        }
    return {"archived": out}


# ── Convenience-Accessoren für neuen Code ──────────────────────────────────────


def flat() -> dict:
    return gen_flat(load_canonical())


def rich() -> dict:
    return gen_rich(load_canonical())


def repos() -> list[str]:
    """Alle Repo-Namen der Union (sortiert)."""
    return sorted(load_canonical()["repos"])


def repo(name: str, strict: bool = False) -> dict | None:
    """Zusammengeführter Datensatz für EIN Repo (flat+rich+meta) — None wenn unbekannt.

    X-13 (repo-optimize 2026-07-03): ``strict=True`` wirft stattdessen ``KeyError``
    mit einer stderr-Meldung — ein Typo im Repo-Namen sollte nicht still als "keine
    Daten" durchgehen, wenn der Aufrufer das nicht erwartet.
    """
    e = load_canonical()["repos"].get(name)
    if e is None:
        if strict:
            print(
                f"registry_api.repo: unbekannter Repo-Name '{name}' (Typo?)",
                file=sys.stderr,
            )
            raise KeyError(name)
        return None
    merged = {**(e.get("flat") or {}), **(e.get("rich") or {})}
    merged.update(
        domain=e.get("domain"),
        in_flat=e.get("in_flat", False),
        in_rich=e.get("in_rich", False),
    )
    return merged


def owner(name: str, canon: dict | None = None) -> str | None:
    """GitHub-Owner (Ist-Owner, ADR-255) für ein Repo auflösen.

    Reihenfolge (spezifisch → generisch):
      1. per-Repo ``github: owner/repo``-Feld (tatsächliche Repo-Identität)
      2. explizite ``meta.repo_owner``-Map (Override für Repos ohne github-Feld)
      3. erste passende ``meta.owner_prefix_rules`` (meiki-/ttz-/bahn-…) — gilt
         auch für noch nicht registrierte Repos (Onboarding-Fall), da eine
         Prefix-Regel eine explizite Konfiguration ist, kein Raten.
      4. Default ``meta.server.github_org`` — NUR für Repos, die tatsächlich in
         ``canon["repos"]`` stehen (ein registriertes Repo ohne spezifischeren
         Treffer ist plausibel beim Default-Org).

    F-5 (repo-optimize 2026-07-03): ein Name, der GAR NICHT in ``canon["repos"]``
    vorkommt UND auch keine Prefix-Regel trifft (Typo/komplett unbekanntes Repo),
    liefert ``None`` — konsistent zu ``repo()``. Vorher fiel so ein Name still auf
    den Default-Owner durch, was der Docstring ("kein verstecktes Raten") gerade
    ausschließen wollte.

    ``canon`` optional injizierbar (Tests/Batch ohne wiederholtes File-IO).

    ⚠️ Migrations-Nuance (ADR-255): Der *Ziel*-Owner laufender ``iil-*``-Migrationen
    steht in ``registry/iil-migration.yaml`` (SSoT), NICHT hier. Diese Funktion
    liefert den *aktuellen* Owner laut canonical.yaml.
    """
    canon = canon if canon is not None else load_canonical()
    meta = canon.get("meta", {})
    repos = canon.get("repos") or {}
    known = name in repos
    entry = repos.get(name) or {}
    gh = (entry.get("rich") or {}).get("github") or (entry.get("flat") or {}).get(
        "github"
    )
    if gh and "/" in gh:
        return gh.split("/", 1)[0]
    explicit = (meta.get("repo_owner") or {}).get(name)
    if explicit:
        return explicit
    for rule in meta.get("owner_prefix_rules") or []:
        if name.startswith(rule["prefix"]):
            return rule["owner"]
    if known:
        return (meta.get("server") or {}).get("github_org", "achimdehnert")
    return None


def sitzungs_klasse(name: str, canon: dict | None = None) -> str | None:
    """`business` | `plattform` | `bibliothek` aus ``meta.sitzungs_klasse``
    (KONZ-platform-069 B1) — None fuer ein unbekanntes Repo. Der Aufrufer
    entscheidet, was unbekannt heisst; der Scope-Guard warnt dann nur."""
    canon = canon if canon is not None else load_canonical()
    return ((canon.get("meta") or {}).get("sitzungs_klasse") or {}).get(name)


# ── Review-Profil (KONZ-platform-070 Z4, Mandat #3903 WP5) ─────────────────────


def _profil_feldwert(name: str, entry: dict, canon: dict, feld: str):
    """Wert eines Ableitungsfelds aus review-profile.yaml `zuordnung`."""
    rich = entry.get("rich") or {}
    flat = entry.get("flat") or {}
    if feld == "flat.archived":
        return flat.get("archived")
    if feld == "lifecycle":
        return _lifecycle(entry)
    if feld == "rich.deployed":
        return rich.get("deployed")
    if feld == "sitzungs_klasse":
        return sitzungs_klasse(name, canon)
    raise KeyError(f"review-profile.yaml: unbekanntes Ableitungsfeld '{feld}'")


def _regel_trifft(wenn: dict, wert) -> bool:
    if "gleich" in wenn:
        return wert == wenn["gleich"]
    if "in" in wenn:
        return wert in wenn["in"]
    raise KeyError(f"review-profile.yaml: Regel ohne 'gleich'/'in': {wenn}")


def review_profil(
    name: str, canon: dict | None = None, profile: dict | None = None
) -> str | None:
    """Review-Profil eines Repos: `deployed` | `plattform` | `library` | `static` | `keins`.

    Reihenfolge: ``rich.review_profile`` (Override) gewinnt; sonst die erste passende
    Regel aus ``zuordnung`` in registry/review-profile.yaml; sonst deren ``sonst``.
    None fuer ein unbekanntes Repo (ohne Registry-Eintrag gibt es kein Profil, KONZ-070 §5).
    Ein Override auf ein nicht deklariertes Profil ist ein Datenfehler → KeyError.
    """
    canon = canon if canon is not None else load_canonical()
    profile = profile if profile is not None else load_review_profile()
    entry = (canon.get("repos") or {}).get(name)
    if entry is None:
        return None
    bekannt = set(profile["profile"])
    override = (entry.get("rich") or {}).get(REVIEW_PROFILE_FELD)
    if override is not None:
        if override not in bekannt:
            raise KeyError(
                f"{name}: rich.{REVIEW_PROFILE_FELD}='{override}' nicht in review-profile.yaml"
            )
        return override
    sonst = None
    for regel in profile["zuordnung"]:
        if "sonst" in regel:
            sonst = regel["sonst"]
            continue
        wert = _profil_feldwert(name, entry, canon, regel["wenn"]["feld"])
        if _regel_trifft(regel["wenn"], wert):
            return regel["profil"]
    return sonst


def review_soll(
    name: str, canon: dict | None = None, profile: dict | None = None
) -> dict | None:
    """Soll-Schutz von `main` fuer EIN Repo — Profil aufgeloest zu konkreten Werten.

    Rueckgabe: {repo, owner, profil, required_checks (Liste), approvals, bot_zaehlt,
    linear_history, force_push, messen}; None fuer ein unbekanntes Repo.
    ``aus_ci`` wird zu ``rich.review_check`` (je Repo) bzw. ``defaults.ci_gate_check``.
    """
    canon = canon if canon is not None else load_canonical()
    profile = profile if profile is not None else load_review_profile()
    profil = review_profil(name, canon, profile)
    if profil is None:
        return None
    p = profile["profile"][profil]
    rich = canon["repos"][name].get("rich") or {}
    checks = p.get("required_checks") or []
    if checks == AUS_CI:
        checks = [rich.get(REVIEW_CHECK_FELD) or profile["defaults"]["ci_gate_check"]]
    return {
        "repo": name,
        "owner": owner(name, canon),
        "profil": profil,
        "required_checks": list(checks),
        "approvals": int(p.get("approvals", 0)),
        "bot_zaehlt": bool(p.get("bot_zaehlt", False)),
        "linear_history": bool(p.get("linear_history", False)),
        "force_push": bool(p.get("force_push", True)),
        "messen": bool(p.get("messen", True)),
    }


def review_engine_profil(
    name: str, canon: dict | None = None, profile: dict | None = None
) -> str | None:
    """Regelprofil der Review-Engine fuer EIN Repo (KONZ-070 WP2, #3903 Ledger L1).

    Registry-Profile (`plattform`, `static`, …) sind Schutz-Profile; die Engine kennt
    nur ihre eigenen (review_regeln.PROFILE). Die Bruecke ist `engine_profil` je
    Profil in review-profile.yaml. None = unbekanntes Repo oder Profil ohne Lauf.
    """
    profile = profile if profile is not None else load_review_profile()
    profil = review_profil(name, canon, profile)
    if profil is None:
        return None
    return profile["profile"][profil].get("engine_profil")


def review_pilot(profile: dict | None = None) -> list[str]:
    """Pilot-Repos (Mandat #3903 O2) aus review-profile.yaml."""
    profile = profile if profile is not None else load_review_profile()
    return list(profile.get("pilot") or [])


if __name__ == "__main__":
    # `python3 tools/registry_api.py engine-profil <repo>` — fuer Workflows, die das
    # Engine-Profil eines Repos brauchen (review-check.yml); Exit 3 = kein Profil.
    if len(sys.argv) == 3 and sys.argv[1] == "engine-profil":
        ergebnis = review_engine_profil(sys.argv[2])
        if ergebnis is None:
            print(f"{sys.argv[2]}: kein Engine-Profil", file=sys.stderr)
            sys.exit(3)
        print(ergebnis)
        sys.exit(0)
    print("usage: registry_api.py engine-profil <repo>", file=sys.stderr)
    sys.exit(2)
