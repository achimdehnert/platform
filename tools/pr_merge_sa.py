#!/usr/bin/env python3
"""pr-merge-sa — merged einen PR NUR, wenn SA-M ihn deckt.

GATE_HEADER (KONZ-038 D8):
  "slug": "merge-without-class-proof"
  "mode": "tool"
  "owner": "achim"
  "last_drill_pass": "2026-08-26"
  "evidence": "tools/tests/test_pr_merge_sa.py"

SA-M (policies/autonomy-gates.md): autonom mergen, wenn das MANDAT die WIRKUNG
deckt. Beides wird gemessen, nicht geschaetzt — die Wirkung an den Workflow-
Triggern des Repos, das Mandat am PR.

Dieses Werkzeug fuehrt KEINE eigene Freigabe-Liste. Es liest den `sa_m:`-Block
aus der Policy; eine Erweiterung der Autonomie geht damit immer ueber einen
Owner-approvten Policy-PR und nie ueber eine Konstante hier.

Grundregel (uebernommen von pr-gruen-ziehen.sh): Ein API-Fehler, eine leere
Antwort oder ein unlesbarer Workflow ist ABWESENHEIT VON BEWEIS — nie Beweis.
Jeder unklare Zustand fuehrt zu Exit != 0 und KEINEM Merge.

Aufruf:
  pr_merge_sa.py <pr-nr> [owner/repo] [--dry-run] [--json]

Exit-Codes:
  0  gedeckt (bei --dry-run: waere gedeckt) — Merge ausgefuehrt
  2  NICHT gedeckt (mit Grund)
  3  unklar — Daten fehlen oder API-Fehler (fail-closed, nie Merge)
"""

from __future__ import annotations

import argparse
import base64
import fnmatch
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field


class Unklar(Exception):
    """Fail-closed: die Datenlage erlaubt kein Urteil."""


POLICY = pathlib.Path(__file__).resolve().parents[1] / "policies" / "autonomy-gates.md"

RANG = {"M0": 0, "M1": 1, "M2": 2, "M3": 3}


def regeln(pfad=None) -> dict:
    """Liest den `sa_m:`-Block aus der Policy. Fehlt er, ist das UNKLAR — ein
    Werkzeug ohne Regel darf nicht ersatzweise selbst entscheiden."""
    quelle = pathlib.Path(pfad) if pfad else POLICY
    try:
        text = quelle.read_text()
    except OSError as exc:
        raise Unklar(f"Policy nicht lesbar: {exc}")
    treffer = re.search(r"```yaml\n(sa_m:.*?)```", text, re.S)
    if not treffer:
        raise Unklar("kein sa_m-Block in der Policy — Regel unbekannt")
    try:
        import yaml

        block = yaml.safe_load(treffer.group(1))["sa_m"]
    except Exception as exc:  # noqa: BLE001 — jede Lesestoerung ist UNKLAR
        raise Unklar(f"sa_m-Block nicht auswertbar: {exc}")
    for schluessel in ("deckung", "doku_glob", "governance_pfade"):
        if schluessel not in block:
            raise Unklar(f"sa_m-Block unvollstaendig: {schluessel} fehlt")
    return block


PROD_MARKER = re.compile(
    r"\b(prod|production|publish|pypi|ghcr\.io|docker\s+push|migrate)\b", re.IGNORECASE
)
DEPLOY_MARKER = re.compile(r"\b(deploy|ship|release|ssh)\b", re.IGNORECASE)
FREIGABE_VERMERK = re.compile(r"Freigabe:\s*akzeptiert durch Owner", re.IGNORECASE)
PROD_IM_APPROVAL = re.compile(
    r"\b(deploy|prod|production|publish|release)\b", re.IGNORECASE
)


@dataclass
class Facts:
    """Reine Daten — damit classify() ohne Netz pruefbar ist."""

    repo: str
    number: int
    state: str
    is_draft: bool
    mergeable: str
    merge_state: str
    review_required: bool
    wirkung: str
    mandat: str
    files: list = field(default_factory=list)
    checks_total: int = 0
    checks_failing: int = 0
    checks_pending: int = 0


@dataclass
class Verdict:
    wirkung: str
    mandat: str
    erlaubt: bool
    grund: str
    auto: bool = False  # Checks laufen noch -> GitHub merged, sobald sie gruen sind


def ist_doku(pfad: str, globs: list) -> bool:
    return any(
        fnmatch.fnmatch(pfad, g) or fnmatch.fnmatch(pfad.rsplit("/", 1)[-1], g)
        for g in globs
    )


def ist_governance(pfad: str, pfade: list) -> bool:
    name = pfad.rsplit("/", 1)[-1]
    return any(pfad.startswith(p) or name == p for p in pfade)


def classify(f: Facts, r: dict) -> Verdict:
    """Jede Ablehnung nennt ihren Grund — ein Verdict ohne Grund waere so
    nutzlos wie ein Skip ohne Grund."""
    if f.state != "OPEN":
        return Verdict(f.wirkung, f.mandat, False, f"PR ist {f.state}, nicht OPEN")
    if f.is_draft:
        return Verdict(f.wirkung, f.mandat, False, "PR ist ein Draft")
    if not f.files:
        raise Unklar("keine Dateiliste erhalten — ohne Diff kein Urteil")

    governance = [p for p in f.files if ist_governance(p, r["governance_pfade"])]
    if governance and RANG[f.mandat] < RANG["M2"]:
        return Verdict(
            f.wirkung,
            f.mandat,
            False,
            f"fehlt: ein Approval (Governance-Pfad {governance[0]})",
        )

    if f.review_required and RANG[f.mandat] < RANG["M2"]:
        return Verdict(
            f.wirkung, f.mandat, False, "fehlt: ein Approval (Ruleset verlangt Review)"
        )

    if f.mergeable != "MERGEABLE":
        raise Unklar(f"mergeable={f.mergeable} — GitHub hat den Merge nicht bestaetigt")
    if f.merge_state in ("DIRTY", "BLOCKED", "BEHIND"):
        return Verdict(f.wirkung, f.mandat, False, f"mergeStateStatus={f.merge_state}")

    if f.checks_failing:
        return Verdict(
            f.wirkung,
            f.mandat,
            False,
            f"fehlt: gruenes CI ({f.checks_failing} Check(s) rot)",
        )
    if f.checks_total == 0:
        nicht_doku = [p for p in f.files if not ist_doku(p, r["doku_glob"])]
        if nicht_doku:
            return Verdict(
                f.wirkung,
                f.mandat,
                False,
                f"kein einziger Check und nicht reine Doku ({nicht_doku[0]})",
            )

    noetig = r["deckung"].get(f.wirkung)
    if noetig is None:
        raise Unklar(f"Wirkung {f.wirkung} steht nicht in der Deckungstabelle")
    if RANG[f.mandat] < RANG[noetig]:
        return Verdict(
            f.wirkung,
            f.mandat,
            False,
            f"fehlt: {noetig} — {f.wirkung} verlangt es, vorliegt {f.mandat}",
        )
    if f.checks_pending:
        return Verdict(
            f.wirkung,
            f.mandat,
            True,
            f"{f.mandat} deckt {f.wirkung}; {f.checks_pending} Check(s) laufen — Auto-Merge",
            auto=True,
        )
    return Verdict(f.wirkung, f.mandat, True, f"{f.mandat} deckt {f.wirkung}")


def _gh(args: list):
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise Unklar(f"gh {' '.join(args[:3])} …: {p.stderr.strip()[:200]}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as exc:
        raise Unklar(f"gh-Antwort nicht lesbar: {exc}")


def _paths_ignore_deckt_alles(kopf: str, dateien: list) -> bool:
    """Greift `paths-ignore` fuer JEDE Datei des PR, laeuft der Workflow nicht —
    dann ist seine Wirkung fuer genau diesen PR null."""
    muster = re.findall(r"paths-ignore:\s*\n((?:\s*-\s*.+\n)+)", kopf)
    if not muster:
        return False
    globs = [z.strip().lstrip("- ").strip("'\"") for z in muster[0].splitlines()]
    return all(any(fnmatch.fnmatch(d, g) for g in globs) for d in dateien)


_WORKFLOW_CACHE: dict = {}


def workflow_texte(repo: str) -> list:
    """Die Workflow-Dateien eines Repos — je Prozess einmal geholt. Bei Repos mit
    30 Workflows sind das sonst 30 API-Calls pro geprueftem PR."""
    if repo in _WORKFLOW_CACHE:
        return _WORKFLOW_CACHE[repo]
    try:
        eintraege = _gh(["api", f"repos/{repo}/contents/.github/workflows"])
    except Unklar as exc:
        if "404" in str(exc) or "Not Found" in str(exc):
            _WORKFLOW_CACHE[repo] = []
            return []
        raise
    if not isinstance(eintraege, list):
        raise Unklar("Workflow-Verzeichnis nicht als Liste erhalten")

    texte = []
    for e in eintraege:
        if not e.get("name", "").endswith((".yml", ".yaml")):
            continue
        datei = _gh(["api", e["url"]])
        if not datei.get("content"):
            raise Unklar(f"Workflow {e['name']} ohne Inhalt")
        texte.append(
            base64.b64decode(datei["content"]).decode("utf-8", errors="replace")
        )
    _WORKFLOW_CACHE[repo] = texte
    return texte


def wirkung_des_merges(repo: str, dateien: list, r: dict) -> str:
    """Trigger lesen, nicht Dateinamen raten. Unlesbar => Unklar."""
    if repo in r.get("sync_only_repos", []):
        return "W1"

    stufe = "W0"
    for text in workflow_texte(repo):
        kopf = text.split("jobs:", 1)[0]
        if "push:" not in kopf or not re.search(r"\bmain\b", kopf):
            continue
        if _paths_ignore_deckt_alles(kopf, dateien):
            continue
        if PROD_MARKER.search(text):
            return "W3"
        if DEPLOY_MARKER.search(text):
            stufe = "W2"
    return stufe


def mandat_des_prs(repo: str, nummer: int, pr: dict) -> str:
    # `reviewDecision` bleibt leer, wenn GitHub kein Review ERZWINGT — auch dann,
    # wenn ein Code-Owner approved hat. Gemessen an platform#2348: latestReviews
    # trug "wirdigital:APPROVED", reviewDecision war leer, mergeState CLEAN.
    # Massgeblich ist also die Review-Liste, nicht die Gesamtentscheidung.
    approvals = [
        rv
        for rv in (pr.get("latestReviews") or pr.get("reviews") or [])
        if rv.get("state") == "APPROVED"
    ]
    if approvals or pr.get("reviewDecision") == "APPROVED":
        for rv in approvals:
            if PROD_IM_APPROVAL.search(rv.get("body") or ""):
                return "M3"
        return "M2"

    for treffer in re.findall(r"#(\d+)", pr.get("body") or ""):
        try:
            issue = _gh(["issue", "view", treffer, "-R", repo, "--json", "body,state"])
        except Unklar:
            continue
        if FREIGABE_VERMERK.search(issue.get("body") or ""):
            return "M1"
    return "M0"


def pull_request_regel(repo: str, branch: str) -> bool:
    """Liegt auf dem Zielbranch ueberhaupt eine `pull_request`-Regel?

    Nur der Plausibilitaetsanker: keine Regel -> nie Review-Pflicht. Ob die
    Regel fuer EINEN konkreten PR ein Approval verlangt, sagt sie nicht —
    dafuer siehe review_ist_pflicht().
    """
    try:
        rules = _gh(["api", f"repos/{repo}/rules/branches/{branch}"])
    except Unklar as exc:
        if "404" in str(exc) or "Not Found" in str(exc):
            return False
        raise
    if not isinstance(rules, list):
        raise Unklar("Ruleset-Antwort nicht als Liste erhalten")
    return any(x.get("type") == "pull_request" for x in rules)


def review_ist_pflicht(
    pr: dict, hat_regel: bool, checks_failing: int = 0, checks_pending: int = 0
) -> bool:
    """Verlangt GitHub fuer DIESEN PR ein Approval?

    Die blosse Existenz einer `pull_request`-Regel beantwortet das nicht: auf
    `platform/main` steht sie mit `required_approving_review_count=0` und
    `require_code_owner_review=true` — fuer Dateien ohne CODEOWNERS-Treffer
    verlangt GitHub dann kein Review, und `reviewDecision` bleibt leer bei
    `mergeStateStatus=CLEAN` (#2440, gemessen an #2438). Wer nur die Regel
    liest, haelt jeden solchen PR faelschlich fuer review-blockiert und
    macht ihn ueber SA-M unmergebar.

    Massgeblich ist deshalb die Aussage von GitHub ueber den PR selbst:
    - `reviewDecision` gesetzt (REVIEW_REQUIRED / CHANGES_REQUESTED /
      APPROVED) -> Review zaehlt fuer diesen PR;
    - leer und `CLEAN` -> GitHub verlangt keins;
    - leer und `BLOCKED`, ohne roten oder laufenden Check -> es blockt etwas
      anderes als das CI; das konservativ als Review-Pflicht lesen (der Fehler
      geht dann in Richtung Ablehnung, nie in Richtung Merge).
    """
    if not hat_regel:
        return False
    if (pr.get("reviewDecision") or "").strip():
        return True
    if (pr.get("mergeStateStatus") or "").upper() == "BLOCKED":
        return checks_failing == 0 and checks_pending == 0
    return False


def gather(repo: str, nummer: int, r: dict) -> Facts:
    felder = (
        "state,isDraft,mergeable,mergeStateStatus,reviewDecision,latestReviews,"
        "files,baseRefName,statusCheckRollup,body"
    )
    pr = _gh(["pr", "view", str(nummer), "-R", repo, "--json", felder])
    if pr.get("mergeable") == "UNKNOWN":
        pr = _gh(["pr", "view", str(nummer), "-R", repo, "--json", felder])

    roll = pr.get("statusCheckRollup") or []
    failing = pending = 0
    for c in roll:
        zustand = (c.get("conclusion") or c.get("state") or "").upper()
        if zustand in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "ERROR"):
            failing += 1
        elif zustand in ("", "PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED"):
            pending += 1

    dateien = [f["path"] for f in pr.get("files", [])]
    return Facts(
        repo=repo,
        number=nummer,
        state=pr.get("state", ""),
        is_draft=bool(pr.get("isDraft")),
        mergeable=pr.get("mergeable", "UNKNOWN"),
        merge_state=pr.get("mergeStateStatus", ""),
        review_required=review_ist_pflicht(
            pr,
            pull_request_regel(repo, pr.get("baseRefName", "main")),
            failing,
            pending,
        ),
        wirkung=wirkung_des_merges(repo, dateien, r),
        mandat=mandat_des_prs(repo, nummer, pr),
        files=dateien,
        checks_total=len(roll),
        checks_failing=failing,
        checks_pending=pending,
    )


def repo_aus_cwd() -> str:
    p = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True
    )
    if p.returncode != 0:
        raise Unklar("kein Repo bestimmbar — als zweites Argument angeben")
    return re.sub(r"^(git@[^:]+:|https://[^/]+/)", "", p.stdout.strip()).removesuffix(
        ".git"
    )


JOURNAL = pathlib.Path.home() / ".claude" / "pr-merge-sa.jsonl"


def journal(zeile: dict) -> None:
    """Jede Entscheidung wird protokolliert. Die Policy verlangt eine Ratsche
    ("erste Fehlanwendung setzt zurueck") — ohne Zaehlung waere sie nicht
    pruefbar, und eine unpruefbare Ratsche ist keine."""
    try:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with JOURNAL.open("a") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError:
        pass  # ein blindes Journal darf keinen Merge verhindern


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SA-M: Merge nur mit gedecktem Mandat")
    ap.add_argument("nummer", type=int)
    ap.add_argument("repo", nargs="?", default=None, help="owner/repo (sonst aus cwd)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true", dest="als_json")
    ap.add_argument("--policy", default=None, help="alternative Policy-Datei")
    args = ap.parse_args(argv)

    try:
        r = regeln(args.policy)
        repo = args.repo or repo_aus_cwd()
        fakten = gather(repo, args.nummer, r)
        urteil = classify(fakten, r)
    except Unklar as exc:
        print(f"UNKLAR: {exc}", file=sys.stderr)
        print("→ kein Merge (fail-closed).", file=sys.stderr)
        return 3

    if args.als_json:
        print(
            json.dumps({"facts": asdict(fakten), "verdict": asdict(urteil)}, indent=2)
        )
    else:
        marke = "✓" if urteil.erlaubt else "✗"
        print(
            f"{marke} {repo}#{args.nummer}: {urteil.wirkung}/{urteil.mandat} — {urteil.grund}"
        )

    journal(
        {
            "repo": repo,
            "pr": args.nummer,
            "wirkung": urteil.wirkung,
            "mandat": urteil.mandat,
            "erlaubt": urteil.erlaubt,
            "grund": urteil.grund,
            "dry_run": bool(args.dry_run),
        }
    )

    if not urteil.erlaubt:
        return 2
    if args.dry_run:
        print("(dry-run — nicht gemergt)")
        return 0

    befehl = [
        "gh",
        "pr",
        "merge",
        str(args.nummer),
        "-R",
        repo,
        "--squash",
        "--delete-branch",
    ]
    if urteil.auto:
        befehl.append("--auto")
    p = subprocess.run(befehl, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"Merge fehlgeschlagen: {p.stderr.strip()[:300]}", file=sys.stderr)
        return 3
    wie = "Auto-Merge gesetzt" if urteil.auto else "gemergt"
    print(f"{wie}: {repo}#{args.nummer} ({urteil.mandat} deckt {urteil.wirkung})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
