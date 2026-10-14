#!/usr/bin/env python3
"""Risiko-Klassifikator und Routine-Artefakte des Advocatus Diaboli (KONZ-070 Z2 Stufe 2, WP4).

Quelle ist `registry/review-risiko.yaml` (Trigger, Autoren-Ausschluss, Routine-Parameter);
Regel-Trigger verweisen auf `registry/review-regeln.yaml` und wiederholen kein Muster (K1).
Pilot-Repos kommen aus `registry_api.review_pilot()` (review-profile.yaml, O2).

CLI:

    python3 tools/review_risiko.py --repo owner/name --pr 17 [--json]   # Exit 0 = Advocatus laeuft, 1 = nicht
    python3 tools/review_risiko.py --repos                              # Pilot-Repos als owner/name
    python3 tools/review_risiko.py --render                             # agents/advocatus/PROMPT.md + routine.json
    python3 tools/review_risiko.py --check                              # Schema + Drift, Exit 1 bei Befund

`--check` laeuft ueber `make test` (tools/tests/test_review_risiko.py) und damit im CI.
PR-Daten holt `gh api` (REST: pulls, files, issue-comments, Diff); der Klassifikator selbst ist
eine reine Funktion. Kein `gh pr …`: der GitHub-Proxy der Cloud-Routinen laesst nur REST durch,
GraphQL bekommt dort 403 — unabhaengig vom Token (Doku cloud-environments, 2026-10-14).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_api as reg  # noqa: E402
import review_regeln as rr  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PFAD = REPO_ROOT / "registry" / "review-risiko.yaml"
ADVOCATUS_DIR = REPO_ROOT / "agents" / "advocatus"
TEMPLATE = ADVOCATUS_DIR / "PROMPT.template.md"
PROMPT_MD = ADVOCATUS_DIR / "PROMPT.md"
ROUTINE_JSON = ADVOCATUS_DIR / "routine.json"

MARK = "MANAGED-BY: platform/tools/review_risiko.py"
TRIGGER_ARTEN = ("regel", "inhalt")
ID_MUSTER = re.compile(r"^RK-\d{3}$")
ROUTINE_PFLICHT = (
    "name",
    "modell",
    "cron",
    "max_prs_je_lauf",
    "dedup_marker",
    "ledger_url",
    "ledger_bulk_max",
    "token_env",
    "quelle_ledger",
    "checkout",
    "event_uuid",
    "erlaubte_werkzeuge",
)
#: Review-Profil (review-profile.yaml) → Regel-Profil (review-regeln.yaml).
#: Alles ohne eigenen Regelsatz (plattform, static, keins) prueft der Advocatus mit `default`.
REGEL_PROFIL = {"deployed": "deployed", "library": "library"}
#: Platzhalter fuer die Umgebung der Cloud-Routine; Wert kennt nur der Owner (Trigger-API).
ENVIRONMENT_PLATZHALTER = "ENVIRONMENT_ID"
#: Accept-Header, mit dem `GET /repos/{r}/pulls/{n}` den Diff statt JSON liefert.
GH_DIFF_ACCEPT = "Accept: application/vnd.github.v3.diff"


class SchemaFehler(ValueError):
    def __init__(self, fehler: list[str]):
        self.fehler = fehler
        super().__init__("\n".join(fehler))


# ───────────────────────── Laden und Pruefen ─────────────────────────────────────────


def pruefe_schema(doc: Any, regeln_doc: dict | None = None) -> list[str]:
    """Schema-Verletzungen der Risiko-Datei; leer = gueltig."""
    fehler: list[str] = []
    if not isinstance(doc, dict):
        return ["Wurzel ist kein Mapping"]
    for kopf in ("version", "quelle", "routine", "autoren_ausschluss", "trigger"):
        if kopf not in doc:
            fehler.append(f"Kopffeld fehlt: {kopf}")
    routine = doc.get("routine")
    if not isinstance(routine, dict):
        fehler.append("routine ist kein Mapping")
    else:
        for f in ROUTINE_PFLICHT:
            if f not in routine:
                fehler.append(f"routine.{f} fehlt")
        n = routine.get("max_prs_je_lauf")
        if not isinstance(n, int) or n <= 0:
            fehler.append("routine.max_prs_je_lauf muss positive Ganzzahl sein")
        if not isinstance(routine.get("erlaubte_werkzeuge"), list):
            fehler.append("routine.erlaubte_werkzeuge muss Liste sein")
    if not isinstance(doc.get("autoren_ausschluss"), list):
        fehler.append("autoren_ausschluss muss Liste sein")

    trigger = doc.get("trigger")
    if not isinstance(trigger, list) or not trigger:
        return fehler + ["`trigger` fehlt oder ist leer"]
    bekannte_regeln = (
        {r["id"] for r in regeln_doc["regeln"]} if regeln_doc is not None else None
    )
    gesehen: set[str] = set()
    for i, t in enumerate(trigger):
        wo = t.get("id", f"trigger[{i}]") if isinstance(t, dict) else f"trigger[{i}]"
        if not isinstance(t, dict):
            fehler.append(f"{wo}: Trigger ist kein Mapping")
            continue
        tid = t.get("id")
        if not isinstance(tid, str) or not ID_MUSTER.match(tid):
            fehler.append(f"{wo}: id nicht im Format RK-NNN")
        elif tid in gesehen:
            fehler.append(f"{wo}: id doppelt")
        else:
            gesehen.add(tid)
        if not t.get("titel"):
            fehler.append(f"{wo}: titel fehlt")
        art = t.get("art")
        if art not in TRIGGER_ARTEN:
            fehler.append(f"{wo}: art {art!r} nicht in {TRIGGER_ARTEN}")
        elif art == "regel":
            rid = t.get("regel_id")
            if not isinstance(rid, str) or not rr.ID_MUSTER.match(rid):
                fehler.append(f"{wo}: regel_id nicht im Format RR-NNN")
            elif bekannte_regeln is not None and rid not in bekannte_regeln:
                fehler.append(f"{wo}: regel_id {rid} unbekannt in review-regeln.yaml")
            if "muster" in t:
                fehler.append(f"{wo}: art regel wiederholt kein Muster (K1)")
        else:
            muster = t.get("muster")
            if not isinstance(muster, list) or not muster:
                fehler.append(f"{wo}: muster fehlt oder leer")
            else:
                for m in muster:
                    try:
                        re.compile(m)
                    except re.error as exc:
                        fehler.append(f"{wo}: muster {m!r} kein gueltiger Regex: {exc}")
            if not isinstance(t.get("pfade"), list) or not t["pfade"]:
                fehler.append(f"{wo}: pfade fehlt oder leer")
    return fehler


def lade_risiko(pfad: str | Path | None = None, regeln_doc: dict | None = None) -> dict:
    """Risiko-Datei laden und pruefen; wirft SchemaFehler."""
    p = Path(pfad) if pfad else DEFAULT_PFAD
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    fehler = pruefe_schema(doc, regeln_doc if regeln_doc is not None else rr.lade_regeln())
    if fehler:
        raise SchemaFehler([f"{p}: {f}" for f in fehler])
    return doc


# ───────────────────────── Pilot-Repos ───────────────────────────────────────────────


def pilot_repos(canon: dict | None = None, profile: dict | None = None) -> list[str]:
    """Pilot-Repos als owner/name (review-profile.yaml `pilot` + canonical.yaml Owner)."""
    canon = canon if canon is not None else reg.load_canonical()
    profile = profile if profile is not None else reg.load_review_profile()
    out = []
    for name in reg.review_pilot(profile):
        o = reg.owner(name, canon)
        if o is None:
            raise SchemaFehler([f"Pilot-Repo {name!r} ohne Owner in canonical.yaml"])
        out.append(f"{o}/{name}")
    return out


def regel_profil(name: str, canon: dict | None = None, profile: dict | None = None) -> str:
    """Regel-Profil (review-regeln.yaml) eines Repos aus seinem Review-Profil."""
    rp = reg.review_profil(name, canon, profile)
    return REGEL_PROFIL.get(rp or "", rr.PROFILE[0])


# ───────────────────────── Klassifikator (reine Funktion) ────────────────────────────


def hinzugefuegte_zeilen(diff: str) -> dict[str, list[str]]:
    """Unified Diff → {pfad: [hinzugefuegte Zeilen ohne `+`]}."""
    out: dict[str, list[str]] = {}
    pfad = None
    for zeile in diff.splitlines():
        if zeile.startswith("+++ "):
            ziel = zeile[4:].strip()
            pfad = None if ziel == "/dev/null" else ziel.removeprefix("b/")
            if pfad is not None:
                out.setdefault(pfad, [])
        elif pfad is not None and zeile.startswith("+") and not zeile.startswith("+++"):
            out[pfad].append(zeile[1:])
    return out


def _marker(konfig: dict, head_sha: str) -> str:
    return f"<!-- {konfig['routine']['dedup_marker']}:{head_sha} -->"


def _regel_trigger(t: dict, regel: dict, pfade: list[str], zeilen: dict, umfang: int):
    """Treffer eines Regel-Triggers: Detektor der Regel gegen den PR."""
    d = regel["detektor"]
    treffer: list[str] = []
    if d["typ"] == "pfad":
        treffer = [p for p in pfade if any(rr.pfad_passt(p, m) for m in d["muster"])]
    elif d["typ"] == "regex":
        muster = [re.compile(m, re.IGNORECASE) for m in d["muster"]]
        for p, zs in zeilen.items():
            if not any(rr.pfad_passt(p, g) for g in regel["geltung"]["pfade"]):
                continue
            for n, z in enumerate(zs, 1):
                if any(m.search(z) for m in muster):
                    treffer.append(f"{p} (+{n})")
    elif d["typ"] == "umfang" and umfang > d["max_zeilen"]:
        treffer = [f"{umfang} geaenderte Zeilen > {d['max_zeilen']}"]
    return treffer


def _inhalt_trigger(t: dict, zeilen: dict) -> list[str]:
    muster = [re.compile(m, re.IGNORECASE) for m in t["muster"]]
    treffer = []
    for p, zs in zeilen.items():
        if not any(rr.pfad_passt(p, g) for g in t["pfade"]):
            continue
        for n, z in enumerate(zs, 1):
            if any(m.search(z) for m in muster):
                treffer.append(f"{p} (+{n})")
    return treffer


def klassifiziere(
    pr: dict,
    diff: str,
    konfig: dict,
    regeln_doc: dict,
    repo: str,
    pilot: list[str],
) -> dict:
    """Entscheid fuer EINEN PR. Rueckgabe: laeuft, gruende (gegen), trigger (fuer), head_sha.

    `pr` ist die Klassifikator-Form (number, isDraft, author.login, headRefOid, additions,
    deletions, files[].path, comments[].body) — aus REST per `pr_aus_rest`.
    """
    head_sha = pr.get("headRefOid", "")
    gruende: list[str] = []
    if repo not in pilot:
        gruende.append(f"Repo {repo} nicht im Pilot ({', '.join(pilot)})")
    if pr.get("isDraft"):
        gruende.append("Draft")
    autor = (pr.get("author") or {}).get("login", "")
    if autor in konfig["autoren_ausschluss"]:
        gruende.append(f"Autor ausgeschlossen: {autor}")
    marker = _marker(konfig, head_sha)
    if any(marker in (c.get("body") or "") for c in pr.get("comments") or []):
        gruende.append(f"Marker vorhanden: {marker}")

    pfade = [f["path"] for f in pr.get("files") or []]
    zeilen = hinzugefuegte_zeilen(diff)
    umfang = int(pr.get("additions") or 0) + int(pr.get("deletions") or 0)
    regeln = {r["id"]: r for r in regeln_doc["regeln"]}
    trigger: list[dict] = []
    for t in konfig["trigger"]:
        if t["art"] == "regel":
            treffer = _regel_trigger(t, regeln[t["regel_id"]], pfade, zeilen, umfang)
        else:
            treffer = _inhalt_trigger(t, zeilen)
        if treffer:
            trigger.append(
                {
                    "id": t["id"],
                    "titel": t["titel"],
                    "regel_id": t.get("regel_id", ""),
                    "locator": treffer,
                }
            )
    if not trigger:
        gruende.append("kein Risiko-Trigger")
    return {
        "repo": repo,
        "pr": pr.get("number"),
        "head_sha": head_sha,
        "laeuft": not gruende,
        "gruende": gruende,
        "trigger": trigger,
    }


# ───────────────────────── gh-Adapter ────────────────────────────────────────────────


def _gh(*args: str) -> str:
    lauf = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if lauf.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} … rc={lauf.returncode}: {lauf.stderr.strip()}")
    return lauf.stdout


def json_dokumente(text: str) -> list[Any]:
    """Alle JSON-Dokumente eines `gh api --paginate`-Ausgabestroms, Listen flach zusammengefuegt.

    `--paginate` haengt die Seiten ohne Trenner aneinander (`[…][…]`); das ist kein gueltiges
    JSON-Dokument, aber eine Folge davon.
    """
    dec = json.JSONDecoder()
    aus: list[Any] = []
    pos = 0
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            return aus
        dok, pos = dec.raw_decode(text, pos)
        if isinstance(dok, list):
            aus.extend(dok)
        else:
            aus.append(dok)


def pr_aus_rest(meta: dict, dateien: list[dict], kommentare: list[dict]) -> dict:
    """REST-Antworten (pulls/N, pulls/N/files, issues/N/comments) → Klassifikator-Form."""
    return {
        "number": meta.get("number"),
        "isDraft": bool(meta.get("draft")),
        "author": {"login": (meta.get("user") or {}).get("login", "")},
        "headRefOid": (meta.get("head") or {}).get("sha", ""),
        "additions": meta.get("additions") or 0,
        "deletions": meta.get("deletions") or 0,
        "files": [{"path": d["filename"]} for d in dateien],
        "comments": [{"body": k.get("body") or ""} for k in kommentare],
    }


def pr_laden(repo: str, nr: int) -> tuple[dict, str]:
    """PR-Metadaten und Diff ueber `gh api` (REST; GraphQL blockt der Cloud-Proxy)."""
    basis = f"repos/{repo}/pulls/{nr}"
    meta = json.loads(_gh("api", basis))
    dateien = json_dokumente(_gh("api", "--paginate", f"{basis}/files"))
    kommentare = json_dokumente(_gh("api", "--paginate", f"repos/{repo}/issues/{nr}/comments"))
    diff = _gh("api", "-H", GH_DIFF_ACCEPT, basis)
    return pr_aus_rest(meta, dateien, kommentare), diff


# ───────────────────────── Routine-Artefakte ─────────────────────────────────────────


def _trigger_tabelle(konfig: dict, regeln_doc: dict) -> str:
    regeln = {r["id"]: r for r in regeln_doc["regeln"]}
    zeilen = ["| Trigger | Titel | Quelle | Prueft |", "|---|---|---|---|"]
    for t in konfig["trigger"]:
        if t["art"] == "regel":
            r = regeln[t["regel_id"]]
            quelle, prueft = f"`{t['regel_id']}`", rr.pruefauftrag(r)
        else:
            quelle = "eigenes Muster"
            prueft = (
                "Regex (hinzugefuegt) in "
                + " · ".join(f"`{p}`" for p in t["pfade"])
                + ": "
                + " · ".join(f"`{m}`" for m in t["muster"])
            )
        zeilen.append(
            f"| `{t['id']}` | {t['titel']} | {quelle} | {prueft.replace('|', chr(92) + '|')} |"
        )
    return "\n".join(zeilen)


def _quellen() -> tuple[Path, ...]:
    return (DEFAULT_PFAD, rr.DEFAULT_PFAD, TEMPLATE)


def _quellen_hash() -> str:
    h = hashlib.sha256()
    for p in _quellen():
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _fusszeile() -> str:
    quellen = "+".join(str(p.relative_to(REPO_ROOT)) for p in _quellen())
    return f"{MARK} · source={quellen} · content_hash=sha256:{_quellen_hash()} · do_not_edit"


def render_prompt(konfig: dict | None = None, regeln_doc: dict | None = None) -> str:
    """agents/advocatus/PROMPT.md aus Vorlage, Risiko-Datei und Regelblock."""
    regeln_doc = regeln_doc or rr.lade_regeln()
    konfig = konfig or lade_risiko(regeln_doc=regeln_doc)
    r = konfig["routine"]
    text = TEMPLATE.read_text(encoding="utf-8")
    ersetzungen = {
        "{{MODELL}}": r["modell"],
        "{{TOKEN_ENV}}": r["token_env"],
        "{{MAX_PRS}}": str(r["max_prs_je_lauf"]),
        "{{DEDUP_MARKER}}": r["dedup_marker"],
        "{{AUTOREN_AUSSCHLUSS}}": ", ".join(f"`{a}`" for a in konfig["autoren_ausschluss"]),
        "{{TRIGGER_TABELLE}}": _trigger_tabelle(konfig, regeln_doc),
        "{{REGELBLOCK}}": rr.render_advocatus_block(regeln_doc),
    }
    for k, v in ersetzungen.items():
        text = text.replace(k, v)
    offen = re.findall(r"\{\{[A-Z_]+\}\}", text)
    if offen:
        raise SchemaFehler([f"Vorlage hat unbekannte Platzhalter: {sorted(set(offen))}"])
    return text.rstrip("\n") + f"\n\n<!-- {_fusszeile()} -->\n"


def render_routine(konfig: dict | None = None) -> str:
    """agents/advocatus/routine.json — Body fuer die Trigger-API (RemoteTrigger create).

    Feldform wie die Schedule-Routine sie 2026-10-13 dokumentiert: name, cron_expression,
    enabled, job_config.ccr{environment_id, session_context{model, sources, allowed_tools},
    events[{data{uuid, session_id, type, parent_tool_use_id, message{role, content}}}]}.
    `environment_id` bleibt Platzhalter; den Wert setzt der Owner beim Anlegen.
    `sources` = Checkout + alle Pilot-Repos: der GitHub-Proxy der Cloud-Sitzung bedient nur
    Repos, die der Sitzung angehaengt sind (sonst 403), und `pr_laden` liest jedes Pilot-Repo.
    """
    konfig = konfig or lade_risiko()
    r = konfig["routine"]
    quellen = [r["checkout"]] + [
        u for u in (f"https://github.com/{p}" for p in pilot_repos()) if u != r["checkout"]
    ]
    prompt_rel = PROMPT_MD.relative_to(REPO_ROOT)
    bootstrap = (
        f"Du bist die Routine `{r['name']}` (KONZ-platform-070 Z2 Stufe 2, Mandat "
        f"achimdehnert/platform#3903 WP4). Lies im Checkout von {r['checkout']} die Datei "
        f"`{prompt_rel}` vollstaendig und folge ihr Schritt fuer Schritt. Die Umgebungsvariable "
        f"`{r['token_env']}` wird erwartet (nur auf Vorhandensein pruefen, nie ausgeben). "
        f"Du bist advisory: kein Approve, kein Request-Changes, kein Label, kein Commit, kein Push."
    )
    body = {
        "_managed_by": _fusszeile(),
        "name": r["name"],
        "cron_expression": r["cron"],
        "enabled": True,
        "job_config": {
            "ccr": {
                "environment_id": ENVIRONMENT_PLATZHALTER,
                "session_context": {
                    "model": r["modell"],
                    "sources": [{"git_repository": {"url": u}} for u in quellen],
                    "allowed_tools": list(r["erlaubte_werkzeuge"]),
                },
                "events": [
                    {
                        "data": {
                            "uuid": r["event_uuid"],
                            "session_id": "",
                            "type": "user",
                            "parent_tool_use_id": None,
                            "message": {"role": "user", "content": bootstrap},
                        }
                    }
                ],
            }
        },
    }
    return json.dumps(body, ensure_ascii=False, indent=2) + "\n"


def pruefe_drift(
    prompt_md: str | Path | None = None, routine_json: str | Path | None = None
) -> list[str]:
    """Abweichungen der generierten Artefakte vom Stand der Quellen; leer = kein Drift."""
    regeln_doc = rr.lade_regeln()
    konfig = lade_risiko(regeln_doc=regeln_doc)
    befunde = []
    for ziel, soll in (
        (Path(prompt_md) if prompt_md else PROMPT_MD, render_prompt(konfig, regeln_doc)),
        (Path(routine_json) if routine_json else ROUTINE_JSON, render_routine(konfig)),
    ):
        ist = ziel.read_text(encoding="utf-8") if ziel.exists() else ""
        if ist != soll:
            befunde.append(f"{ziel}: weicht vom Render ab — `python3 tools/review_risiko.py --render`")
    return befunde


# ───────────────────────── CLI ───────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--repo", help="owner/name des PR-Repos")
    ap.add_argument("--pr", type=int, help="PR-Nummer")
    ap.add_argument("--json", action="store_true", help="Entscheid als JSON ausgeben")
    ap.add_argument("--repos", action="store_true", help="Pilot-Repos als owner/name")
    ap.add_argument("--render", action="store_true", help="PROMPT.md und routine.json schreiben")
    ap.add_argument("--check", action="store_true", help="Schema + Drift, Exit 1 bei Befund")
    a = ap.parse_args(argv)

    try:
        regeln_doc = rr.lade_regeln()
        konfig = lade_risiko(regeln_doc=regeln_doc)
    except (rr.SchemaFehler, SchemaFehler) as exc:
        for f in exc.fehler:
            print(f"SCHEMA: {f}", file=sys.stderr)
        return 1

    if a.repos:
        for r in pilot_repos():
            print(r)
        return 0
    if a.render:
        PROMPT_MD.write_text(render_prompt(konfig, regeln_doc), encoding="utf-8")
        ROUTINE_JSON.write_text(render_routine(konfig), encoding="utf-8")
        print(f"geschrieben: {PROMPT_MD}, {ROUTINE_JSON}")
        return 0
    if a.check:
        befunde = pruefe_drift()
        for b in befunde:
            print(f"DRIFT: {b}", file=sys.stderr)
        if befunde:
            return 1
        print(f"review-risiko: Schema gueltig, {len(konfig['trigger'])} Trigger, kein Drift")
        return 0
    if a.repo and a.pr:
        pilot = pilot_repos()
        pr, diff = pr_laden(a.repo, a.pr)
        name = a.repo.split("/", 1)[-1]
        entscheid = klassifiziere(pr, diff, konfig, regeln_doc, a.repo, pilot)
        entscheid["regel_profil"] = regel_profil(name)
        if a.json:
            print(json.dumps(entscheid, ensure_ascii=False, indent=2))
        else:
            print(f"{a.repo}#{a.pr} @ {entscheid['head_sha'][:12]}: "
                  f"{'ADVOCATUS LAEUFT' if entscheid['laeuft'] else 'kein Lauf'}")
            for g in entscheid["gruende"]:
                print(f"  gegen: {g}")
            for t in entscheid["trigger"]:
                print(f"  trigger {t['id']} {t['titel']}: {'; '.join(t['locator'][:3])}")
        return 0 if entscheid["laeuft"] else 1
    ap.print_help()
    return 64


if __name__ == "__main__":
    raise SystemExit(main())
