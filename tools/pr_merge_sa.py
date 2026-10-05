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
from datetime import datetime, timezone

from bot_review_kandidaten import juengste_je_name


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
# Markdown-tolerant: `Freigabe:`, `**Freigabe:**`, `**Freigabe**:` — der Vermerk aus
# /prompt (Auftrag-Modus) kam fett, der Regex las nur plain (#2603, Realfall #2602).
FREIGABE_VERMERK = re.compile(
    r"\**Freigabe\**:\**\s*akzeptiert durch Owner", re.IGNORECASE
)
PROD_IM_APPROVAL = re.compile(
    r"\b(deploy|prod|production|publish|release)\b", re.IGNORECASE
)
# Ein Approval, das sich selbst als "kein inhaltliches Urteil" ausweist, ist kein
# Mandat fuer einen Merge durch die Sitzung (Owner-Entscheid 2026-10-05). Der Satz
# steht im Text des Bot-Reviews (`.github/workflows/bot-review.yml`); ein Test haelt
# beide Stellen zusammen.
OHNE_INHALTLICHES_URTEIL = re.compile(r"kein\s+inhaltliches\s+Urteil", re.IGNORECASE)
# Nur fuer den Issue-Vermerk-Pfad (#2814 Review-Befund): PROD_IM_APPROVAL matcht
# auch "prod"/"release"/"publish" und wuerde einen M1-Vermerk wie "PR #2804
# (Prod-Rueckstand)" versehentlich zu M3 machen. Der Owner hat den Vermerk
# woertlich auf das Wort "deploy" festgelegt (Freigabe: akzeptiert durch Owner
# — deploy) — der Vermerk-Pfad prueft deshalb ausschliesslich dieses Wort.
DEPLOY_IM_VERMERK = re.compile(r"\bdeploy\b", re.IGNORECASE)
# Pruefrage (autonomy-gates.md, Owner-Weisung 2026-08-27; Block angeglichen
# 2026-09-16, #3244): W3 braucht M1 — Auto-Deploy ist Normalbetrieb, kein
# Vorlagegrund. Vorlagepflichtig bleiben die vier Klassen der Pruefrage; zwei
# davon sind mechanisch erkennbar und halten M3 (Deploy-Wort) aufrecht:
# Datenmigration (Migrationsdatei im Diff) und Irreversibles (Publish-Workflow,
# den der Merge anstoesst). Security-Config faengt der Governance-Pfad (M2),
# die echte Wahlfrage ist kein Werkzeug-Kriterium, sondern Urteil des Agenten VOR dem Aufruf.
PUBLISH_MARKER = re.compile(r"\b(publish|pypi|ghcr\.io|docker\s+push)\b", re.IGNORECASE)
MIGRATION_PFAD = re.compile(r"(^|/)migrations/[^/]+\.py$")
# Issue-Verweise im PR-Text: `#123` (PR-Repo) oder `owner/repo#123`. Der Auftrag
# eines Cross-Repo-Programms liegt im Leit-Repo (Realfall dev-hub#357 mit
# Auftrag platform#3234), nicht im Repo des PR.
ISSUE_VERWEIS = re.compile(r"(?:\b([\w.-]+/[\w.-]+))?#(\d+)\b")


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
    # Gruende, warum die Pruefrage bei W3 doch M3 verlangt (leer = M1 genuegt)
    pruef_pflicht: list = field(default_factory=list)
    # Nur bei Org-Profil: per API aufgeloeste Repo-ID, vor dem Merge erneut verglichen
    repo_id: int | None = None
    # Der gepruefte Kopf-Commit; der Merge greift nur, wenn der PR noch auf ihm steht
    head_sha: str = ""


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
    if f.checks_total == 0 and not r.get("actions_aus"):
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
    if f.wirkung == "W3" and f.pruef_pflicht:
        noetig = "M3"
    if RANG[f.mandat] < RANG[noetig]:
        if noetig == "M3":
            anlass = f" ({'; '.join(f.pruef_pflicht)})" if f.pruef_pflicht else ""
            grund = (
                f"fehlt: M3{anlass} — Approve-Review mit Deploy-Wort ODER Vermerk "
                "„Freigabe: akzeptiert durch Owner — deploy” mit dieser "
                "PR-Nummer im verlinkten Issue (#2812)"
            )
        else:
            grund = f"fehlt: {noetig} — {f.wirkung} verlangt es, vorliegt {f.mandat}"
        return Verdict(f.wirkung, f.mandat, False, grund)
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


def aufgeloestes_repo(repo: str) -> tuple[str, int]:
    """(full_name, id) laut GitHub-API — nach Umbenennung/Transfer der NEUE Eigentuemer."""
    daten = _gh(["api", f"repos/{repo}"])
    try:
        return daten["full_name"], int(daten["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise Unklar(f"Repo {repo} nicht aufloesbar: {exc}")


def actions_an(repo: str) -> bool:
    daten = _gh(["api", f"repos/{repo}/actions/permissions"])
    if not isinstance(daten, dict) or "enabled" not in daten:
        raise Unklar(f"Actions-Zustand von {repo} nicht lesbar")
    return bool(daten["enabled"])


#: Was ein Org-Profil heute tragen darf. Jeder andere Schluessel ist eine
#: unbekannte Angabe und verweigert (ADR-308 §4.4) — sonst wirkte ein Tippfehler
#: still als Grundregel oder ein neuer Schluessel ohne Werkzeug-Pruefung.
PROFIL_SCHLUESSEL = {"actions_aus"}


def gepruefte_profile(roh) -> dict:
    """org_profile normalisiert; unbekannte oder widerspruechliche Angaben => UNKLAR.

    Auch fuer Repos ausserhalb jeder Profil-Org: ein kaputter Policy-Block wird nicht
    teilweise angewandt (fail_closed wie bei `regeln`)."""
    if roh is None:
        return {}
    if not isinstance(roh, dict):
        raise Unklar("org_profile ist keine Zuordnung Org → Profil")
    profile: dict = {}
    for org, profil in roh.items():
        schluessel = str(org).lower()
        if schluessel in profile:
            raise Unklar(f"org_profile nennt {schluessel} doppelt — widerspruechlich")
        if not isinstance(profil, dict) or set(profil) - PROFIL_SCHLUESSEL:
            raise Unklar(f"org_profile {schluessel}: unbekannte Angabe {profil!r}")
        if profil.get("actions_aus") is not True:
            raise Unklar(
                f"org_profile {schluessel}: M0 setzt actions_aus: true voraus (§4.4)"
            )
        profile[schluessel] = profil
    return profile


def regeln_fuer(
    repo: str, r: dict, aufloesen=None, actions=None
) -> tuple[dict, int | None]:
    """Org-Profil aus `sa_m.org_profile` (ADR-308 §4.4) — sonst die Grundregeln.

    Sicherheitsvertrag: Das Profil gilt nur, wenn die API das Repo derselben Org
    zuordnet wie der Aufruf. Leitet GitHub nach Umbenennung oder Transfer zu einem
    anderen Eigentuemer weiter, ist das UNKLAR, nie die Grundregel. Die ID geht
    mit, damit main() vor dem Merge einen Zielwechsel bemerkt. `actions_aus` wird
    gemessen, nicht geglaubt: laufen Actions doch, ist das UNKLAR.
    """
    aufloesen = aufloesen or aufgeloestes_repo
    actions = actions or actions_an
    org = repo.split("/")[0].lower()
    profile = gepruefte_profile(r.get("org_profile"))
    if org not in profile:
        return r, None
    voller_name, repo_id = aufloesen(repo)
    if voller_name.lower() != repo.lower():
        raise Unklar(f"{repo} zeigt laut API auf {voller_name} — Org-Profil verweigert")
    profil = {**r, **profile[org]}
    if profil.get("actions_aus") and actions(repo):
        raise Unklar(f"Org-Profil {org} setzt Actions aus voraus, {repo} hat sie an")
    return profil, repo_id


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


def pruef_pflicht_gruende(repo: str, dateien: list, r: dict) -> list:
    """Die mechanisch pruefbaren Klassen der Pruefrage — leer heisst: M1 genuegt."""
    gruende = []
    if any(MIGRATION_PFAD.search(p) for p in dateien):
        gruende.append("Datenmigration im Diff")
    if repo not in r.get("sync_only_repos", []):
        for text in workflow_texte(repo):
            kopf = text.split("jobs:", 1)[0]
            if "push:" not in kopf or not re.search(r"\bmain\b", kopf):
                continue
            if _paths_ignore_deckt_alles(kopf, dateien):
                continue
            if PUBLISH_MARKER.search(text):
                gruende.append("Publish-Workflow auf main (irreversibel)")
                break
    return gruende


def mandat_des_prs(repo: str, nummer: int, pr: dict) -> str:
    # `reviewDecision` bleibt leer, wenn GitHub kein Review ERZWINGT — auch dann,
    # wenn ein Code-Owner approved hat. Gemessen an platform#2348: latestReviews
    # trug "wirdigital:APPROVED", reviewDecision war leer, mergeState CLEAN.
    # Massgeblich ist also die Review-Liste, nicht die Gesamtentscheidung.
    alle_approvals = [
        rv
        for rv in (pr.get("latestReviews") or pr.get("reviews") or [])
        if rv.get("state") == "APPROVED"
    ]
    approvals = [
        rv
        for rv in alle_approvals
        if not OHNE_INHALTLICHES_URTEIL.search(rv.get("body") or "")
    ]
    # Die Gesamtentscheidung traegt nur, wenn sie nicht allein auf Approvals ohne
    # Urteil beruht — sonst kaeme das ausgeschlossene Approval hier wieder herein.
    if approvals or (
        pr.get("reviewDecision") == "APPROVED" and not alle_approvals
    ):
        for rv in approvals:
            if PROD_IM_APPROVAL.search(rv.get("body") or ""):
                return "M3"
        return "M2"

    # (b) 2026-09-04 (#2812, praezisiert #2814): M3 auf eigenem PR ist per
    # Review unerreichbar (GitHub laesst kein Approve-Review auf ein eigenes PR
    # zu). Ein Vermerk im verlinkten Issue deckt W3 als M3-Aequivalent NUR, wenn
    # dieselbe Zeile alle drei Bedingungen traegt: Freigabe-Vermerk, das Wort
    # "deploy" (DEPLOY_IM_VERMERK, bewusst enger als PROD_IM_APPROVAL — sonst
    # wuerde z.B. "PR #2804 (Prod-Rueckstand)" versehentlich M3), UND diese
    # PR-Nummer (Wortgrenze, damit #280 nicht #2804 deckt). Fehlt eine davon,
    # bleibt es beim bestehenden M1 (Vermerk irgendwo im Issue-Body reicht dafuer
    # weiterhin, unveraendert).
    pr_nummer_in_zeile = re.compile(rf"(?<!\d)#{nummer}(?!\d)")
    gefunden_m1 = False
    for verweis_repo, treffer in ISSUE_VERWEIS.findall(pr.get("body") or ""):
        try:
            issue = _gh(
                [
                    "issue",
                    "view",
                    treffer,
                    "-R",
                    verweis_repo or repo,
                    "--json",
                    "body,state",
                ]
            )
        except Unklar:
            continue
        issue_body = issue.get("body") or ""
        if not FREIGABE_VERMERK.search(issue_body):
            continue
        gefunden_m1 = True
        for zeile in issue_body.splitlines():
            if (
                FREIGABE_VERMERK.search(zeile)
                and DEPLOY_IM_VERMERK.search(zeile)
                and pr_nummer_in_zeile.search(zeile)
            ):
                return "M3"
    if gefunden_m1:
        return "M1"
    return "M0"


#: Antwort von GitHub, wenn der Plan Rulesets fuer private Repos nicht kennt
#: (Free-Plan, etwa iilsandbox). Dort kann keine Regel existieren. Nur genau
#: dieser Text zaehlt — ein anderes 403 (Rate-Limit, fehlendes Recht) bleibt UNKLAR.
PLAN_OHNE_RULESETS = "Upgrade to GitHub Pro or make this repository public"


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
        # Live-Test S9 (#3724): ohne diesen Zweig war jeder iilsandbox-PR UNKLAR
        if PLAN_OHNE_RULESETS in str(exc):
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
        "files,baseRefName,statusCheckRollup,body,headRefOid"
    )
    pr = _gh(["pr", "view", str(nummer), "-R", repo, "--json", felder])
    if pr.get("mergeable") == "UNKNOWN":
        pr = _gh(["pr", "view", str(nummer), "-R", repo, "--json", felder])

    # Je Check-Name nur den juengsten Lauf werten (#2784): sonst zaehlt ein
    # alter roter Zwilling neben einem neuen gruenen Lauf desselben Namens
    # weiterhin als Fehlschlag. Dieselbe Auswahl wie beim Review-Bot (#2679,
    # `bot_review_kandidaten.juengste_je_name`) — keine zweite Kopie.
    roll = juengste_je_name(pr.get("statusCheckRollup") or [])
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
        # Actions aus (gemessen in regeln_fuer): kein Workflow kann wirken
        wirkung="W0" if r.get("actions_aus") else wirkung_des_merges(repo, dateien, r),
        pruef_pflicht=(
            [] if r.get("actions_aus") else pruef_pflicht_gruende(repo, dateien, r)
        ),
        mandat=mandat_des_prs(repo, nummer, pr),
        files=dateien,
        checks_total=len(roll),
        checks_failing=failing,
        checks_pending=pending,
        head_sha=pr.get("headRefOid") or "",
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
    pruefbar, und eine unpruefbare Ratsche ist keine. Der Zeitstempel macht
    Wochenwerte moeglich (Sandbox-Benchmark B1, platform#3685); Format wie
    beim Owner-Wort-Hook, damit beide Satzarten dieselbe Woche ergeben."""
    zeile = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **zeile}
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
        r, repo_id = regeln_fuer(repo, r)
        fakten = gather(repo, args.nummer, r)
        fakten.repo_id = repo_id
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

    if repo_id is not None:
        # Zielwechsel zwischen Pruefung und Merge (ADR-308 §8.2): dieselbe ID oder nichts
        try:
            jetzt = aufgeloestes_repo(repo)
        except Unklar as exc:
            print(f"UNKLAR: {exc}", file=sys.stderr)
            return 3
        if jetzt[0].lower() != repo.lower() or jetzt[1] != repo_id:
            print(
                f"UNKLAR: {repo} hat seit der Pruefung das Ziel gewechselt",
                file=sys.stderr,
            )
            return 3

    # Ohne Rulesets (iilsandbox) haelt nichts einen Push zwischen Pruefung und
    # Merge auf: gemergt wird genau der gepruefte Kopf oder nichts (#3724).
    if not fakten.head_sha:
        print("UNKLAR: Kopf-Commit des PR nicht lesbar — kein Merge", file=sys.stderr)
        return 3
    if r.get("actions_aus"):
        # Neu gemessen, nicht aus regeln_fuer() geglaubt: Actions koennen seitdem an sein
        try:
            an = actions_an(repo)
        except Unklar as exc:
            print(f"UNKLAR: {exc}", file=sys.stderr)
            return 3
        if an:
            print(
                f"UNKLAR: {repo} hat seit der Pruefung Actions an — W0 gilt nicht mehr",
                file=sys.stderr,
            )
            return 3

    befehl = [
        "gh",
        "pr",
        "merge",
        str(args.nummer),
        "-R",
        repo,
        "--squash",
        "--delete-branch",
        "--match-head-commit",
        fakten.head_sha,
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
