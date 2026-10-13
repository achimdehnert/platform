#!/usr/bin/env python3
"""branch-protection-meter — Soll-Schutz von `main` aus der Registry, Ist aus der API.

ADR-242 §Rollout 4 („Enforcement der Enforcement“), fortgeschrieben durch
KONZ-platform-070 Z4 „Branch-Schutz als Deklaration“ (Mandat platform#3903 WP5):

* **Soll** kommt aus `registry/canonical.yaml` + `registry/review-profile.yaml`
  (``registry_api.review_soll``) — kein eigenes Repo-Verzeichnis mehr. Die Dateien
  `governance/rulesets/wave1-repos.json` / `wave2-repos.json` sind **generierte
  Views** dieser Ableitung (``--views schreiben`` / ``--views pruefen``), fuer
  Altleser (break_glass_meter.py, apply-branch-protection.yml).
* **Ist** = Rulesets (mit Regel-Details) **und** klassische Branch-Protection
  (`GET repos/{o}/{r}/branches/main/protection`, 404 = kein Schutz) je Repo.
* **Drift** = Soll nicht vom Ist gedeckt (Soll ist Mindestanforderung; mehr Schutz
  im Ist ist keine Drift). Break-Glass (Ruleset `main-required-checks` nicht
  `active`) bleibt wie in ADR-242 meldepflichtig.
* Je Drift-Repo ein **kopierfertiger Befehl**. Dieses Skript wendet **nie** an —
  Anwenden ist Owner-Zug (Security-Config-Gate, autonomy-gates).

Exit-Codes: 0 = alles deckungsgleich · 1 = mindestens eine Drift
            2 = Konfigurations-/Aufruffehler oder nicht messbar (ohne Drift)

Usage:
    python3 tools/branch_protection_meter.py                       # alle Repos mit Soll
    python3 tools/branch_protection_meter.py --pilot --kurz        # Session-Start 0.7.34
    python3 tools/branch_protection_meter.py --profile deployed plattform --report /tmp/r.md
    python3 tools/branch_protection_meter.py --soll-json           # Soll ohne API (Apply-Skript)
    python3 tools/branch_protection_meter.py --views pruefen       # Drift-Test der Views
    TOKEN=<pat> python3 tools/branch_protection_meter.py --expected governance/rulesets/wave1-repos.json
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_api as reg  # noqa: E402

API = "https://api.github.com"
RULESET_NAME = "main-required-checks"
ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "governance" / "rulesets" / "main-required-checks-template.json"
VIEWS = {
    ROOT / "governance" / "rulesets" / "wave1-repos.json": (
        1,
        ("deployed", "plattform"),
    ),
    ROOT / "governance" / "rulesets" / "wave2-repos.json": (2, ("library",)),
}
#: Felder, die ein Ruleset-PATCH/POST annimmt (Rest ist read-only Antwort-Schmuck).
RULESET_SCHREIBFELDER = (
    "name",
    "target",
    "enforcement",
    "conditions",
    "rules",
    "bypass_actors",
)
#: Ref-Muster, unter denen ein Branch-Ruleset `main` trifft.
MAIN_REFS = {"refs/heads/main", "~DEFAULT_BRANCH", "~ALL"}
API_WORKERS = 6

STATUS_OK = "ok"
STATUS_DRIFT = "drift"
STATUS_NICHT_MESSBAR = "nicht_messbar"
STATUS_DEFERRED = "deferred"


# ── Soll ────────────────────────────────────────────────────────────────────────


def soll_aus_registry(
    repos: list[str] | None = None,
    profile_filter: list[str] | None = None,
    pilot: bool = False,
    canon: dict | None = None,
    profile: dict | None = None,
) -> list[dict]:
    """Soll-Liste aus Registry + Profil. Ohne Filter: alle Repos mit `messen: true`.

    ``repos`` und ``profile_filter`` wirken als Vereinigung; ``pilot`` ergaenzt die
    Pilot-Repos aus review-profile.yaml plus alle `deployed`. Ergebnis sortiert:
    deployed/plattform zuerst (KONZ-070 §6: Prod-Repos zuerst), dann Name.
    """
    canon = canon if canon is not None else reg.load_canonical()
    profile = profile if profile is not None else reg.load_review_profile()
    gewollt_repos = set(repos or [])
    gewollt_profile = set(profile_filter or [])
    if pilot:
        gewollt_repos |= set(reg.review_pilot(profile))
        gewollt_profile.add("deployed")
    alles = not gewollt_repos and not gewollt_profile

    out = []
    for name in sorted(canon["repos"]):
        s = reg.review_soll(name, canon, profile)
        if not s["messen"]:
            continue
        if alles or name in gewollt_repos or s["profil"] in gewollt_profile:
            out.append(s)
    rang = {"deployed": 0, "plattform": 0}
    out.sort(key=lambda s: (rang.get(s["profil"], 1), s["repo"]))
    return out


def soll_aus_wave(entry: dict) -> dict:
    """Altformat (wave*-repos.json) → Soll-Datensatz; `deferred` bleibt erhalten."""
    return {
        "repo": entry["repo"],
        "owner": entry.get("owner"),
        "profil": entry.get("profile", f"wave{entry.get('wave', '?')}"),
        "required_checks": [entry["required_check"]]
        if entry.get("required_check")
        else [],
        "approvals": 0,
        "bot_zaehlt": False,
        "linear_history": False,
        "force_push": True,
        "messen": True,
        "deferred": entry.get("deferred"),
    }


def load_expected(paths: list) -> list:
    """Lädt und konkateniert eine oder mehrere Soll-Listen (Wave-Dateien, Altformat)."""
    merged: list = []
    for path in paths:
        with open(path) as fh:
            merged.extend(json.load(fh))
    return merged


# ── Views (generiert, drift-getestet) ───────────────────────────────────────────


def view_eintraege(
    canon: dict | None = None, profile: dict | None = None
) -> dict[Path, list]:
    """Inhalt der wave*-Views aus der Registry-Ableitung (Altformat je Eintrag)."""
    canon = canon if canon is not None else reg.load_canonical()
    profile = profile if profile is not None else reg.load_review_profile()
    out: dict[Path, list] = {}
    for pfad, (wave, profile_der_welle) in VIEWS.items():
        eintraege = []
        for s in soll_aus_registry(
            profile_filter=list(profile_der_welle), canon=canon, profile=profile
        ):
            eintraege.append(
                {
                    "repo": s["repo"],
                    "owner": s["owner"],
                    "required_check": s["required_checks"][0]
                    if s["required_checks"]
                    else None,
                    "wave": wave,
                    "profile": s["profil"],
                }
            )
        out[pfad] = sorted(eintraege, key=lambda e: e["repo"])
    return out


def views_schreiben() -> int:
    for pfad, eintraege in view_eintraege().items():
        pfad.write_text(json.dumps(eintraege, indent=2, ensure_ascii=False) + "\n")
        print(f"✅ {pfad.relative_to(ROOT)}: {len(eintraege)} Repos geschrieben")
    return 0


def views_pruefen() -> int:
    rc = 0
    for pfad, soll in view_eintraege().items():
        try:
            ist = json.loads(pfad.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"🔴 {pfad.relative_to(ROOT)}: nicht lesbar ({exc})")
            rc = 1
            continue
        if ist == soll:
            print(f"✅ {pfad.relative_to(ROOT)}: identisch zur Registry-Ableitung")
        else:
            rc = 1
            print(
                f"🔴 {pfad.relative_to(ROOT)} weicht ab — "
                "`python3 tools/branch_protection_meter.py --views schreiben`"
            )
    return rc


# ── Ist ─────────────────────────────────────────────────────────────────────────


def _token() -> str | None:
    tok = os.environ.get("TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        tok = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return tok or None


def _api_get(path: str, token: str):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_rulesets(owner: str, repo: str, token: str) -> list:
    """Liefert alle Branch-Rulesets MIT rules-Array.

    Gotcha: der List-Endpoint (/rulesets) liefert nur Summaries ohne 'rules';
    die Regel-Details gibt es nur per GET /rulesets/{id} — daher zweistufig.
    """
    summaries = _api_get(f"/repos/{owner}/{repo}/rulesets", token)
    return [
        _api_get(f"/repos/{owner}/{repo}/rulesets/{s['id']}", token)
        for s in summaries
        if s.get("target", "branch") == "branch"
    ]


def fetch_classic(owner: str, repo: str, token: str) -> dict | None:
    """Klassische Branch-Protection von `main`; None = kein Schutz (404) oder
    fuer dieses Repo nicht verfuegbar (403, plan-gated bei privaten Repos)."""
    try:
        return _api_get(f"/repos/{owner}/{repo}/branches/main/protection", token)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404):
            return None
        raise


def _ruleset_trifft_main(rs: dict) -> bool:
    """Ohne `conditions` (Altformat/Fixtures) gilt das Ruleset als main-wirksam."""
    if "conditions" not in rs:
        return True
    refs = set(
        ((rs.get("conditions") or {}).get("ref_name") or {}).get("include") or []
    )
    return bool(refs & MAIN_REFS)


def ist_zusammenfassen(rulesets: list, classic: dict | None) -> dict:
    """Vereinigt aktive Rulesets auf `main` und klassischen Schutz zu EINEM Ist-Bild."""
    checks: set[str] = set()
    approvals = 0
    linear = False
    force_push_blockiert = False
    enforcement = None
    ruleset_id = None
    for rs in rulesets:
        if rs.get("name") == RULESET_NAME:
            enforcement = rs.get("enforcement")
            ruleset_id = rs.get("id")
        if rs.get("enforcement") != "active" or not _ruleset_trifft_main(rs):
            continue
        for rule in rs.get("rules") or []:
            typ = rule.get("type")
            params = rule.get("parameters") or {}
            if typ == "required_status_checks":
                checks |= {
                    c.get("context") for c in params.get("required_status_checks") or []
                }
            elif typ == "pull_request":
                approvals = max(
                    approvals, int(params.get("required_approving_review_count") or 0)
                )
            elif typ == "required_linear_history":
                linear = True
            elif typ == "non_fast_forward":
                force_push_blockiert = True
    if classic:
        checks |= set(
            ((classic.get("required_status_checks") or {}).get("contexts")) or []
        )
        rev = classic.get("required_pull_request_reviews") or {}
        approvals = max(approvals, int(rev.get("required_approving_review_count") or 0))
        linear = linear or bool(
            (classic.get("required_linear_history") or {}).get("enabled")
        )
        afp = classic.get("allow_force_pushes")
        if afp is not None and not afp.get("enabled", True):
            force_push_blockiert = True
    return {
        "checks": checks,
        "approvals": approvals,
        "linear_history": linear,
        "force_push_blockiert": force_push_blockiert,
        "ruleset_enforcement": enforcement,
        "ruleset_id": ruleset_id,
        "classic": classic is not None,
    }


def fetch_ist(owner: str, repo: str, token: str) -> dict:
    rulesets = fetch_rulesets(owner, repo, token)
    classic = fetch_classic(owner, repo, token)
    ist = ist_zusammenfassen(rulesets, classic)
    ist["rulesets"] = rulesets
    return ist


# ── Bewertung ───────────────────────────────────────────────────────────────────


def bewerte(soll: dict, ist: dict) -> dict:
    """Soll gegen Ist (pure, testbar). status: ok | drift | deferred."""
    if soll.get("deferred"):
        return {
            **_basis(soll, ist),
            "status": STATUS_DEFERRED,
            "gruende": [str(soll["deferred"])],
        }
    gruende = []
    fehlend = [c for c in soll["required_checks"] if c not in ist["checks"]]
    if fehlend:
        gruende.append(
            f"required check(s) {fehlend} fehlt (gefunden: {sorted(ist['checks']) or 'keine'})"
        )
    if soll["approvals"] > ist["approvals"]:
        gruende.append(f"approvals {ist['approvals']} < {soll['approvals']}")
    if soll["linear_history"] and not ist["linear_history"]:
        gruende.append("required_linear_history fehlt")
    if not soll["force_push"] and not ist["force_push_blockiert"]:
        gruende.append("Force-Push auf main nicht blockiert (non_fast_forward fehlt)")
    enf = ist.get("ruleset_enforcement")
    if enf is not None and enf != "active":
        gruende.append(
            f"Ruleset '{RULESET_NAME}' enforcement='{enf}' (Break-Glass offen? ADR-242 verlangt Re-Aktivierung)"
        )
    ergebnis = {**_basis(soll, ist), "gruende": gruende}
    ergebnis["status"] = STATUS_DRIFT if gruende else STATUS_OK
    ergebnis["befehl"] = befehl_fuer(soll, ist) if gruende else None
    return ergebnis


def _basis(soll: dict, ist: dict | None) -> dict:
    return {
        "repo": soll["repo"],
        "owner": soll.get("owner"),
        "profil": soll["profil"],
        "soll": soll_kurz(soll),
        "ist": ist_kurz(ist) if ist else "—",
        "befehl": None,
    }


def soll_kurz(soll: dict) -> str:
    teile = [", ".join(soll["required_checks"]) or "kein Check"]
    if soll["approvals"]:
        teile.append(
            f"{soll['approvals']} Approval"
            + (" (Bot zählt)" if soll["bot_zaehlt"] else "")
        )
    if soll["linear_history"]:
        teile.append("linear")
    if not soll["force_push"]:
        teile.append("kein Force-Push")
    return " + ".join(teile)


def ist_kurz(ist: dict) -> str:
    teile = [", ".join(sorted(ist["checks"])) or "kein Check"]
    teile.append(f"{ist['approvals']} Approval")
    if ist["linear_history"]:
        teile.append("linear")
    if ist["force_push_blockiert"]:
        teile.append("kein Force-Push")
    enf = ist.get("ruleset_enforcement")
    if enf is None:
        teile.append(f"Ruleset {RULESET_NAME} fehlt")
    elif enf != "active":
        teile.append(f"Ruleset {enf}")
    if ist.get("classic"):
        teile.append("klassischer Schutz")
    return " + ".join(teile)


def ruleset_ziel(
    soll: dict, bestehend: dict | None, template: dict | None = None
) -> dict:
    """Ziel-Ruleset = bestehendes Ruleset (oder Template) PLUS fehlendes Soll.

    Bestehende Regeln bleiben erhalten (ein PATCH ersetzt das `rules`-Array komplett —
    ein nacktes Template haette z. B. platform drei weitere required checks gekostet).
    """
    if bestehend:
        ziel = {
            k: copy.deepcopy(bestehend[k])
            for k in RULESET_SCHREIBFELDER
            if k in bestehend
        }
    else:
        template = (
            template if template is not None else json.loads(TEMPLATE.read_text())
        )
        ziel = {
            k: copy.deepcopy(template[k])
            for k in RULESET_SCHREIBFELDER
            if k in template
        }
        ziel["rules"] = [
            r
            for r in ziel.get("rules", [])
            if r.get("type") != "required_status_checks"
        ]
    ziel["enforcement"] = "active"
    regeln = ziel.setdefault("rules", [])

    def regel(typ: str) -> dict:
        for r in regeln:
            if r.get("type") == typ:
                return r
        r = {"type": typ}
        regeln.append(r)
        return r

    if soll["required_checks"]:
        r = regel("required_status_checks")
        params = r.setdefault("parameters", {})
        params.setdefault("strict_required_status_checks_policy", False)
        vorhanden = params.setdefault("required_status_checks", [])
        kontexte = {c.get("context") for c in vorhanden}
        for c in soll["required_checks"]:
            if c not in kontexte:
                vorhanden.append({"context": c})
    if soll["approvals"]:
        r = regel("pull_request")
        params = r.setdefault("parameters", {})
        params["required_approving_review_count"] = max(
            int(params.get("required_approving_review_count") or 0), soll["approvals"]
        )
        for k, v in (
            ("dismiss_stale_reviews_on_push", False),
            ("require_code_owner_review", False),
            ("require_last_push_approval", False),
            ("required_review_thread_resolution", False),
        ):
            params.setdefault(k, v)
    if soll["linear_history"]:
        regel("required_linear_history")
    if not soll["force_push"]:
        regel("non_fast_forward")
    return ziel


def befehl_fuer(soll: dict, ist: dict, template: dict | None = None) -> str:
    """Kopierfertiger Befehl je Drift-Repo — ausgefuehrt wird hier nichts.

    Deckt `apply-branch-protection.sh` das Profil (nur required check, keine
    Approvals/Flags), ist das der Befehl; sonst ein `gh api`-Aufruf mit dem
    Ziel-Ruleset (bestehendes Ruleset + fehlendes Soll).
    """
    nur_check = (
        soll["approvals"] == 0 and not soll["linear_history"] and soll["force_push"]
    )
    if nur_check:
        return f"bash tools/apply-branch-protection.sh --repo {soll['repo']}"
    bestehend = next(
        (r for r in ist.get("rulesets") or [] if r.get("name") == RULESET_NAME), None
    )
    ziel = ruleset_ziel(soll, bestehend, template)
    body = json.dumps(ziel, ensure_ascii=False, separators=(",", ":")).replace(
        "'", "'\\''"
    )
    pfad = f"repos/{soll['owner']}/{soll['repo']}/rulesets"
    if bestehend:
        return (
            f"printf '%s' '{body}' | gh api {pfad}/{bestehend['id']} -X PATCH --input -"
        )
    return f"printf '%s' '{body}' | gh api {pfad} -X POST --input -"


# ── Ausgabe ─────────────────────────────────────────────────────────────────────


def _gruende(r: dict) -> list:
    return r.get("gruende", r.get("reasons", []))


def render_report(results: list) -> str:
    """Markdown-Report: Tabelle Repo · Profil · Soll · Ist · Drift, dann Befehle."""
    ok = [r for r in results if r["status"] == STATUS_OK]
    drift = [r for r in results if r["status"] == STATUS_DRIFT]
    deferred = [r for r in results if r["status"] == STATUS_DEFERRED]
    unmessbar = [r for r in results if r["status"] == STATUS_NICHT_MESSBAR]

    lines = ["# branch-protection-meter (ADR-242 · KONZ-070 Z4)", ""]
    lines.append(
        f"**{len(ok)} konform · {len(drift)} Drift · {len(unmessbar)} nicht messbar · {len(deferred)} deferred**"
    )
    lines += ["", "| Repo | Profil | Soll | Ist | Drift |", "|---|---|---|---|---|"]
    for r in results:
        gr = _gruende(r)
        if r["status"] == STATUS_OK:
            d = "—"
        elif r["status"] == STATUS_NICHT_MESSBAR:
            d = "nicht messbar: " + "; ".join(gr)
        else:
            d = "; ".join(gr)
        lines.append(
            f"| {r['repo']} | {r.get('profil', '—')} | {r.get('soll', '—')} | {r.get('ist', '—')} | {d} |"
        )
    if drift:
        lines += [
            "",
            "## Drift — Befehle (Owner-Zug, Anwenden ist Security-Config)",
            "",
        ]
        for r in drift:
            lines.append(f"- **{r['repo']}**: {'; '.join(_gruende(r))}")
            if r.get("befehl"):
                lines.append(f"  `{r['befehl']}`")
    if unmessbar:
        lines += ["", "## Nicht messbar (keine Entwarnung)", ""]
        for r in unmessbar:
            lines.append(f"- {r['repo']}: {'; '.join(_gruende(r))}")
    if deferred:
        lines += ["", "## ⏸ Deferred (kein Alarm)", ""]
        for r in deferred:
            lines.append(f"- {r['repo']}: {_gruende(r)[0]}")
    if ok:
        lines += ["", "## ✅ Konform", ""]
        for r in ok:
            lines.append(f"- {r['repo']}")
    return "\n".join(lines) + "\n"


def render_kurz(results: list, umfang: str) -> str:
    """Eine Zeile fuer den Session-Start-Runner (0.7.34)."""
    drift = [r for r in results if r["status"] == STATUS_DRIFT]
    unmessbar = [r for r in results if r["status"] == STATUS_NICHT_MESSBAR]
    n = len(results)
    if not drift and not unmessbar:
        return f"OK: {n}/{n} Repos deckungsgleich ({umfang})"
    teile = []
    if drift:
        teile.append(
            f"DRIFT {len(drift)}/{n}: "
            + ", ".join(
                f"{r['repo']} ({r['gruende'][0].split(' (')[0]})" for r in drift[:4]
            )
            + (" …" if len(drift) > 4 else "")
        )
    if unmessbar:
        teile.append(
            f"nicht messbar {len(unmessbar)}: "
            + ", ".join(r["repo"] for r in unmessbar[:4])
        )
    teile.append("Befehle: python3 tools/branch_protection_meter.py --pilot")
    return " — ".join(teile)


# ── main ────────────────────────────────────────────────────────────────────────


def messen(soll_liste: list[dict], token: str) -> list[dict]:
    def eins(soll: dict) -> dict:
        if soll.get("deferred"):
            return bewerte(soll, ist_zusammenfassen([], None))
        try:
            ist = fetch_ist(soll["owner"], soll["repo"], token)
        except urllib.error.HTTPError as exc:
            return {
                **_basis(soll, None),
                "status": STATUS_NICHT_MESSBAR,
                "gruende": [f"API HTTP {exc.code}"],
            }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # Nicht-pruefbar bleibt sichtbar (Schweigen waere Schein-Gruen) und bricht
            # den Flotten-Scan nicht ab (F-6, repo-optimize 2026-07-03).
            return {
                **_basis(soll, None),
                "status": STATUS_NICHT_MESSBAR,
                "gruende": [f"API nicht erreichbar ({exc})"],
            }
        return bewerte(soll, ist)

    with ThreadPoolExecutor(max_workers=API_WORKERS) as pool:
        return list(pool.map(eins, soll_liste))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    quelle = parser.add_mutually_exclusive_group()
    quelle.add_argument(
        "--aus-registry",
        action="store_true",
        help="Soll aus Registry + Profil (Default)",
    )
    quelle.add_argument(
        "--expected", nargs="+", help="Altformat: Soll aus wave*-repos.json"
    )
    parser.add_argument(
        "--repos",
        nargs="+",
        metavar="REPO",
        help="nur diese Repos (Vereinigung mit --profile)",
    )
    parser.add_argument(
        "--profile", nargs="+", metavar="PROFIL", help="nur Repos dieser Profile"
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Pilot-Repos (review-profile.yaml) + alle deployed",
    )
    parser.add_argument(
        "--kurz", action="store_true", help="eine Zeile (Session-Start 0.7.34)"
    )
    parser.add_argument("--report", help="Markdown-Report in Datei schreiben")
    parser.add_argument(
        "--soll-json",
        action="store_true",
        help="Soll-Liste als JSON ausgeben, keine API",
    )
    parser.add_argument(
        "--views",
        choices=["schreiben", "pruefen"],
        help="wave*-Views generieren/pruefen",
    )
    args = parser.parse_args()

    if args.views:
        return views_schreiben() if args.views == "schreiben" else views_pruefen()

    try:
        if args.expected:
            soll_liste = [soll_aus_wave(e) for e in load_expected(args.expected)]
            umfang = "wave-Dateien"
        else:
            soll_liste = soll_aus_registry(args.repos, args.profile, args.pilot)
            umfang = (
                "Pilot + deployed"
                if args.pilot
                else (
                    "Profile " + "/".join(args.profile)
                    if args.profile
                    else "alle Repos mit Soll"
                )
            )
            if args.repos:
                umfang += " + " + ", ".join(args.repos)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"❌ Soll nicht ableitbar: {exc}", file=sys.stderr)
        return 2

    if args.soll_json:
        for s in soll_liste:
            s["required_check"] = (
                s["required_checks"][0] if s["required_checks"] else None
            )
        print(json.dumps(soll_liste, ensure_ascii=False, indent=2))
        return 0

    token = _token()
    if not token:
        print(
            "❌ TOKEN/GH_TOKEN nicht gesetzt und `gh auth token` leer", file=sys.stderr
        )
        if args.kurz:
            print("nicht messbar: kein Token")
        return 2

    results = messen(soll_liste, token)

    if args.kurz:
        print(render_kurz(results, umfang))
    else:
        print(render_report(results))
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(render_report(results))

    drift = sum(1 for r in results if r["status"] == STATUS_DRIFT)
    unmessbar = sum(1 for r in results if r["status"] == STATUS_NICHT_MESSBAR)
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"violations={drift + unmessbar}\n")

    if drift:
        return 1
    return 2 if unmessbar else 0


if __name__ == "__main__":
    sys.exit(main())
