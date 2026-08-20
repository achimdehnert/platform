#!/usr/bin/env python3
"""Claude Code Stop hook — Evidence-Discipline claim scanner.

Makes the `~/.claude/policies/evidence-discipline.md` rule *executable* instead
of merely documented: scans the assistant's final turn for cheaply-falsifiable
claim markers (a number+status like "8 passed", or a status/outcome word like
"deployed"/"grün"/"verifiziert") and checks whether the SAME turn actually ran a
tool whose output corroborates the claim. If a claim fires with no corroborating
tool evidence in the turn, it appends a one-line reminder to the transcript so the
next turn sees it.

Why this exists: on 2026-06-01 the assistant wrote "8/8 grün" and "11 passed" into
a PR body *before any test ran*, and called a fixed RCE path "verified" against a
stale audit. The policy was in context and was violated anyway — a passive rule
does not change behaviour reliably. This hook is the active backstop.

Contract: read the Stop event JSON on stdin; ALWAYS exit 0 (a scanner failure must
never block Claude). On a fire, emit JSON `{"hookSpecificOutput":{"hookEventName":
"Stop","additionalContext": <reminder>}}` — the documented advisory channel for
exit-0 Stop hooks (surfaces to the next turn WITHOUT forcing continuation).
Conservative by design: flags specific numeric/status/verification/over-diagnosis
claims, tolerates any plausible corroboration, stays silent otherwise (no nagging).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)

# GATE-HEADER (KONZ-038 D8, maschinenlesbar — der Fenster-Prüflauf liest dieses Dict):
# Umstellung advisory→blocking ist Welle-1-Vorabtest (b) aus KONZ-038 D2; Messfenster
# 2026-08-02 bis 2026-08-16, Erfolgskriterium: Verstoßrate des Slugs sinkt im Retro-Delta.
GATE_HEADER = {
    "slug": "claim-before-cheapest-check",
    "mode": "blocking",  # Laufzeit-Opt-out: state-Datei, s. _mode()
    "owner": "achim",
    "last_drill_pass": "2026-08-02",  # Drill = test_should_block_* in tests/
    "evidence": "tools/claude-hooks/tests/test_evidence_claim_scanner.py",
}


def _mode() -> str:
    """blocking (Default) | advisory. Opt-out über State-Datei — bewusst KEIN stiller
    Advisory-Default bei fehlender Datei: fehlende Datei = blocking, sonst stürbe das
    Gate auf frischen Maschinen lautlos zurück in den Zustand, dessen Wirkungslosigkeit
    ×34 belegt ist (KONZ-038 §7)."""
    state_dir = Path(
        os.environ.get(
            "EVIDENCE_SCANNER_STATE_DIR", str(Path.home() / ".claude/hooks/state")
        )
    )
    try:
        if (state_dir / "evidence_scanner_mode").read_text(
            encoding="utf-8"
        ).strip().lower() == "advisory":
            return "advisory"
    except OSError:
        pass
    return "blocking"


# Claim markers: cheaply-falsifiable specificity. Kept deliberately narrow.
# --- Bejahende Ursachenbehauptung (2026-08-03) -------------------------------
# Absichtlich eng: nur Formulierungen, die eine Ursache als FESTSTELLUNG setzen.
# "Ursache könnte X sein" oder "Hypothese: X" sollen NICHT feuern — dafür der
# Hedge-Filter unten, der satzweise arbeitet (ein Hedge im selben Satz entwaffnet
# den Treffer, ein Hedge drei Absätze weiter nicht).
AFFIRMATIVE_CAUSE_RE = re.compile(
    r"\b(?:"
    r"(?:die\s+)?ursache\s+(?:ist|war|liegt|lag)\b"
    r"|root[- ]cause\s*[:=]"
    r"|(?:das|es|dies|der\s+fehler|das\s+problem)\s+(?:liegt|lag)\s+an\b"
    r"|verursacht\s+(?:durch|von)\b"
    r"|(?:ist|war)\s+ein\s+bekanntes\s+(?:muster|problem)\b"
    r"|\bcaused\s+by\b"
    r")",
    re.I,
)

# Ein Hedge im SELBEN Satz macht aus der Feststellung eine Hypothese — genau das,
# was die Policy verlangt. Dann darf der Scanner schweigen.
CAUSE_HEDGE_RE = re.compile(
    r"\b(?:vermutlich|wahrscheinlich|moeglicherweise|m(?:ö|oe)glicherweise|"
    r"hypothese|verdacht|vermute|k(?:ö|oe)nnte|d(?:ü|ue)rfte|scheint|"
    r"plausibel|nicht\s+verifiziert|unbelegt|nicht\s+belegt|"
    r"leithypothese|annahme|wohl|evtl\.?|eventuell|"
    r"maybe|likely|presumably|hypothesis|unverified)\b",
    re.I,
)

# Bewusst NICHT an ":" und ";" trennen — "Leithypothese: die Ursache ist X" ist EIN
# Gedanke, und der Hedge steht davor. Kalibrierlauf 2026-08-03: mit ":" im Splitter
# war genau dieser Satz der einzige Fehlalarm.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\n])\s+")


def _affirmative_cause_fires(text: str) -> bool:
    """True, wenn mindestens EIN Satz eine ungehedgte Ursachenbehauptung trägt."""
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        if AFFIRMATIVE_CAUSE_RE.search(sentence) and not CAUSE_HEDGE_RE.search(
            sentence
        ):
            return True
    return False


CLAIM_PATTERNS = [
    (
        re.compile(
            r"\b\d+\s*(?:/\s*\d+\s*)?(?:passed|failed|passing|grün|gruen|green)\b", re.I
        ),
        "test-result",
    ),
    (
        re.compile(
            r"\b(?:deployed|deployt|published|publiziert|live\s+(?:on|auf)\s+pypi)\b",
            re.I,
        ),
        "deploy/publish",
    ),
    (re.compile(r"\b\d+/\d+\s*(?:grün|gruen|green|passed|ok)\b", re.I), "ratio-claim"),
    # PR/Issue-Claim (Lehre 2026-06-25, claim-before-cheapest-check gate-pflicht):
    # eine konkrete PR/Issue-Nummer als angelegt/gemergt/existent behauptet.
    # Eng gehalten: VERB muss am #N kleben (mere "siehe #303" feuert NICHT).
    (
        re.compile(
            r"(?:PR|Pull Request|Issue)\s*#?\d+[^.\n]{0,45}"
            r"(?:angelegt|erstellt|er(?:ö|oe)ffnet|created|opened|gemergt|merged|existiert)"
            r"|(?:angelegt|erstellt|er(?:ö|oe)ffnet|created|opened|gemergt|merged)[^.\n]{0,25}#\d+",
            re.I,
        ),
        "pr/issue-status",
    ),
    # Verifikations-Claim (Retro-Increment 2026-06-30 F1: "#762 verifiziert"/"validiert"
    # fielen VOR dem Cheapest-Check — genau die Marker-Lücke, durch die claim-before-
    # cheapest-check ×12 rezidivierte, obwohl dieser Hook lief). Korroborations-gated:
    # feuert nur, wenn der Turn KEINEN belegenden Tool-Lauf hatte.
    (
        re.compile(
            r"\b(?:verifiziert|validiert|best(?:ä|ae)tigt|verified|validated|confirmed)\b",
            re.I,
        ),
        "verification",
    ),
    # Über-Diagnose (evidence-discipline: over-claiming UND over-diagnosing skippen beide
    # den Check). Realfälle 2026-06-30: "Konfabulation" (#734), "pre-existing" (Sweep-PRs),
    # "nicht meins". Selten genug für niedrige False-Positive-Rate.
    (
        re.compile(
            r"\b(?:pre-existing|vorbestehend|konfabuliert|konfabulation|confabulat\w*|"
            r"phantom|nicht mein(?:s|e|er)?|not my code|infra[- ]smell)\b",
            re.I,
        ),
        "over-diagnosis",
    ),
    # Bejahende Ursachenbehauptung (Lehre 2026-08-03, Retro 928b64). `over-diagnosis`
    # oben deckt nur die ABWEHRENDE Hälfte ab ("pre-existing", "nicht mein Code") —
    # eine bejahende Diagnose ("die Ursache ist X", "das liegt an X") trug keinen
    # dieser Marker und rutschte durch, obwohl evidence-discipline.md "root-cause
    # label" ausdrücklich als auslösenden Marker nennt. Realfall: ein 403 wurde als
    # "veraltetes Plätzchen" festgestellt und in ein durables Memory geschrieben,
    # bevor ein Befund das stützte; widerlegt wurde es erst durch eine Gegenprobe,
    # die in der bereits gelesenen Memory-Datei wörtlich vorgeschlagen war.
    # Korroboration ist RUN_EVIDENCE_TOKENS, nicht die generische Liste: eine Ursache
    # belegt man durch einen Lauf/Log, nicht durch das Lesen von Code.
    # Hedges werden satzweise ausgenommen — s. _affirmative_cause_fires().
    (AFFIRMATIVE_CAUSE_RE, "affirmative-cause"),
    # Coverage-/Exposure-Claim (Lehre 2026-07-06, GHAS-Audit: "13/20 Repos ohne
    # Secret-Scan" war 13× falsch — grep-Literal übersah shared-CI-uses:-Vererbung).
    # Feuert nur, wenn KEIN echter Coverage-Read (contents/actions/workflows) im Turn lief.
    (
        re.compile(
            r"\b\d+\s*(?:/\s*\d+|\s*von\s*\d+)?[^.\n]{0,15}?(?:repos?|repositories|repositorys)\b"
            r"[^.\n]{0,45}(?:exposed|ungesch(?:ü|ue)tzt|ungescannt|ohne\s+(?:secret|scan)|"
            r"offen|protected|abgedeckt|gescannt|scanned)"
            r"|(?:exposed|ungesch(?:ü|ue)tzt|abgedeckt|protected|gescannt)[^.\n]{0,20}"
            r"\b\d+\s*(?:/|von)\s*\d+\b",
            re.I,
        ),
        "coverage-claim",
    ),
    # Capability-Claim (Lehre 2026-07-06: "kein Scope-Wall, ich kann ausführen" aus
    # org-Rolle abgeleitet → attach 403/422 → 2 OAuth-Flows). Korroboration = ein
    # echter Scope-/Endpoint-Preflight im Turn (x-oauth-scopes / gh auth status / attach-dry).
    (
        re.compile(
            r"\bich\s+kann(?:'s|\s+es|\s+das)?\s+(?:jetzt\s+|sofort\s+|gleich\s+)*"
            r"(?:ausf(?:ü|ue)hren|attachen|durchf(?:ü|ue)hren|umh(?:ä|ae)ngen|anlegen)"
            r"|kein(?:e|en)?\s+scope[-\s]?wall"
            r"|\bI\s+can\s+execute\b"
            r"|habe\s+(?:die\s+)?(?:n(?:ö|oe)tigen\s+)?(?:schreib)?rechte\b",
            re.I,
        ),
        "capability-claim",
    ),
    # Absence-/Negativ-Claim (Lehre 2026-07-09, Retro-Increment 589606-incr: ein
    # Finder UND der ihn verifizierende Skeptiker behaupteten unabhängig "tax-hub
    # referenziert #1024 nie" — beide stützten sich auf `gh pr list --search`, das
    # Body-Text-Referenzen unzuverlässig matcht; ein `gh pr view --json body` (billiger!)
    # widerlegte es sofort. Struktureller Blindfleck dieses Hooks: er sieht nur das
    # Haupt-Transkript, NICHT die internen Bash-Aufrufe von Subagenten (Skeptiker laufen
    # isoliert) — kann also "Verify wiederholt exakt den Finder-Befehl" nicht direkt
    # erkennen. Fängt stattdessen die eine Ebene, die sichtbar ist: wenn DIESE Antwort
    # selbst eine Abwesenheits-/Negativ-Behauptung trifft ("X referenziert Y nicht",
    # "nirgends dokumentiert", "0 Treffer", "existiert nicht").
    (
        re.compile(
            r"\b(?:referenziert|verweist|erw(?:ä|ae)hnt)\b[^.\n]{0,30}\bnicht\b"
            r"|\bnicht\b[^.\n]{0,20}\b(?:referenziert|verweist|erw(?:ä|ae)hnt)\b"
            r"|\b(?:nirgends|nirgendwo|in\s+keiner)\b[^.\n]{0,25}"
            r"(?:dokumentiert|gefunden|vorhanden|festgehalten)"
            r"|\bkeine?\b[^.\n]{0,15}\b(?:referenz|verweis|dokumentation|doku|treffer)\b"
            r"|\bexistiert\s+nicht\b|\bgibt\s+es\s+nicht\b"
            r"|\bdoes\s+not\s+reference\b|\bnot\s+documented\s+anywhere\b|\bno\s+hits?\b"
            r"|\b0\s+(?:treffer|matches|hits|kommentare)\b"
            # Possessiv-Form (Lehre 2026-07-22, writing-hub#322 + platform#1328): „X hat
            # (aktuell/gar/überhaupt) kein Y" fiel durch — die alte Alternative verlangte
            # eines von referenz/verweis/doku/treffer als Objekt. Real war das Objekt ein
            # Ding („keinen Uptime-Monitor"), und die Absenz war nur die des EIGENEN
            # Werkzeugs (Betterstack-API); ein zweiter Suchpfad (grep über workflows/)
            # hätte sie sofort widerlegt. Aussage ging so in ZWEI Issues + eine gemergte Doku.
            # Negative-Lookahead auf Nicht-Artefakt-Objekte: „keine Eile/Zeit/Lust/Ahnung"
            # sind Redewendungen, keine prüfbaren Absenz-Behauptungen.
            r"|\b(?:hat|haben)\s+(?:aktuell\s+|derzeit\s+|gar\s+|(?:ü|ue)berhaupt\s+|bisher\s+|noch\s+)*"
            r"kein(?:e|en|erlei)?\s+(?!(?:Eile|Zeit|Lust|Ahnung|Sorge|Problem|Bedarf|Wahl|Grund|"
            r"Zweifel|Meinung|Angst|Chance|Idee|Bock|Geduld|Wahl)\b)"
            r"|\b(?:gibt\s+es|existiert)\s+(?:aktuell\s+|derzeit\s+|gar\s+|(?:ü|ue)berhaupt\s+)*"
            r"kein(?:e|en)?\b"
            r"|\b(?:ü|ue)berhaupt\s+kein(?:e|en)?\b"
            r"|\bhas\s+(?:currently\s+|absolutely\s+)?no\b|\bthere\s+(?:is|are)\s+no\b"
            # Aussagesatz-Form (Lehre 2026-07-22-incr, vom Skeptiker gefunden): die
            # obige Alternative verlangt die Wortfolge „gibt es kein" (Frage/Inversion)
            # und verfehlt damit das häufigere „Es gibt kein X". Gleiche Stopp-Liste.
            r"|\bes\s+gibt\s+kein(?:e|en)?\s+(?!(?:Eile|Zeit|Lust|Ahnung|Sorge|Problem|"
            r"Bedarf|Wahl|Grund|Zweifel|Meinung|Angst|Chance|Idee|Bock)\b)"
            # „X fehlt" — verlangt ein grossgeschriebenes Substantiv davor, damit
            # „mir fehlt die Zeit" nicht feuert. Stopp-Liste deckt Abstrakta UND
            # satzinitiale Pronomen ab (die sind ebenfalls gross geschrieben).
            r"|\b(?!(?:Zeit|Lust|Eile|Geld|Mut|Erfahrung|Ahnung|Mir|Dir|Ihm|Ihr|Uns|"
            r"Euch|Ihnen|Es|Das|Dem|Den|Der|Die|Was|Wer)\b)"
            r"[A-ZÄÖÜ][a-zäöüß-]{2,}\s+(?:fehlt|fehlen)\b"
            # „ohne jeden/jede/jegliche X" und englisches „lacks"
            r"|\bohne\s+(?:jede[nrs]?|jegliche[nrs]?)\s+"
            r"|\blacks?\s+(?:a|an|any)\b|\bis\s+missing\b|\bare\s+missing\b"
            # „nirgends aktiv/implementiert/verdrahtet/konfiguriert" — die bestehende
            # nirgends-Alternative deckt nur dokumentiert/gefunden/vorhanden/festgehalten.
            r"|\b(?:nirgends|nirgendwo)\b[^.\n]{0,25}"
            r"(?:aktiv|implementiert|verdrahtet|konfiguriert|gesetzt|verwendet)",
            re.I,
        ),
        "absence-claim",
    ),
    # Deckungs-/Vollständigkeits-Claim (Lehre 2026-07-22, writing-hub PR #320):
    # „seed_project_lookups deckt die gelöschte Fixture vollständig ab, einziger Rest
    # ist Hörbuch" — belegt über einen ANZAHL-Vergleich (6/14/5 vs. 9/15/8). Ein
    # Namens-Diff zeigte: GenreLookup 5/14, AudienceLookup 0/5 Treffer. Zwei Listen
    # können gleich lang und trotzdem disjunkt sein; der Zählvergleich fühlt sich wie
    # ein Beweis an, ist aber blind, sobald per name/slug gematcht wird. Die falsche
    # Aussage stand danach in drei gemergten Artefakten.
    (
        re.compile(
            r"\bdeckt\b[^.\n]{0,40}\b(?:vollst(?:ä|ae)ndig|komplett|g(?:ä|ae)nzlich)\b[^.\n]{0,15}\bab\b"
            r"|\b(?:vollst(?:ä|ae)ndig|komplett)\s+(?:abgedeckt|ersetzt|(?:ü|ue)bernommen)\b"
            r"|\bersetzt\b[^.\n]{0,40}\bvollst(?:ä|ae)ndig\b"
            r"|\beinzige[rns]?\b[^.\n]{0,30}\b(?:rest|eintrag|unterschied|abweichung)\b"
            r"|\b(?:covers?|replaces?)\b[^.\n]{0,30}\b(?:completely|entirely|fully)\b"
            r"|\bonly\s+(?:remaining|missing)\s+(?:entry|item|one)\b"
            # Ergänzt 2026-07-22-incr: Deckungs-Aussagen ohne das Wort „vollständig".
            # „deckungsgleich" und „1:1 ersetzt" behaupten dasselbe und rutschten durch.
            r"|\bdeckungsgleich\b|\b1\s*:\s*1\s+(?:ersetzt|(?:ü|ue)bernommen|abgebildet)\b"
            r"|\bidentisch\s+(?:zu|mit)\b[^.\n]{0,25}\b(?:liste|menge|satz|eintr(?:ä|ae)g)"
            r"|\bis\s+(?:a\s+)?superset\s+of\b|\bfully\s+covered\s+by\b",
            re.I,
        ),
        "coverage-completeness-claim",
    ),
    # ------------------------------------------------------------------ 2026-07-31
    # Drei Muster, jedes belegt an einem realen Fehlsatz DIESES Tages. Gemeinsame
    # Form: eine Aussage reicht weiter als der Blick, der sie stuetzt.
    #
    # Universal-Claim — „Kein einziger dieser Jobs fragt outcome ab" entstand nach
    # dem Lesen von 100 der 140 Zeilen. Drei der drei Meter-Jobs hatten den Zweig.
    # Der absence-claim-Block oben verlangt ein Objekt aus fester Liste (Referenz/
    # Verweis/Doku/Treffer) oder die Wortfolge „hat kein" — ein blosser Allquantor
    # ueber ein beliebiges Objekt faellt durch.
    (
        re.compile(
            r"\bkein(?:e|en)?\s+einzig(?:er|e|es|en)\b"
            r"|\b(?:keine[rs]?|in\s+keine[rm])\s+(?:der|dieser|von\s+den)\b"
            r"|\b(?:ausnahmslos|durchweg|s(?:ä|ae)mtliche[nrs]?)\b"
            r"|\balle[nrs]?\s+\d+\s+[A-Za-zÄÖÜäöüß-]{3,}\b"
            r"|\bnot\s+(?:a\s+)?single\b|\bnone\s+of\s+(?:the|these)\b|\bevery\s+single\b",
            re.I,
        ),
        "universal-claim",
    ),
    # Funktions-Negation — „Der Megatest laeuft weiterhin nicht" stand da, bevor der
    # heutige Lauf angesehen war; belegt war nur der Vortag. Eine Praesens-Aussage
    # ueber einen laufenden Job/Dienst verlangt einen frischen Lauf- oder Log-Blick.
    (
        re.compile(
            r"\b(?:l(?:ä|ae)uft|greift|feuert|funktioniert|reagiert|startet|triggert)\s+"
            r"(?:weiterhin\s+|immer\s+noch\s+|nach\s+wie\s+vor\s+|aktuell\s+|derzeit\s+|bis\s+heute\s+)*"
            r"nicht\b(?!\s+(?:auf|darauf|nur|zwingend|unbedingt))"
            r"|\bist\s+(?:weiterhin|immer\s+noch|nach\s+wie\s+vor)\s+(?:rot|defekt|kaputt|tot|down)\b"
            r"|\bwird\s+(?:weiterhin\s+|immer\s+noch\s+)?nicht\s+"
            r"(?:ausgef(?:ü|ue)hrt|aufgerufen|getriggert|gestartet)\b"
            r"|\b(?:still|currently)\s+(?:not\s+running|broken|failing)\b",
            re.I,
        ),
        "function-negation",
    ),
    # Zeit-/Wiederholungs-Claim — „das zweite Mal am selben Tag" war aus dem
    # Gedaechtnis geschrieben und falsch (29.07. vs. 30.07.), gefunden erst von einem
    # Finder im Retro. Datums- und Zaehlaussagen fuehlen sich wie Kontext an, sind
    # aber Behauptungen mit Zeitstempel-Beleg: git log, gh run list, Datei-mtime.
    (
        re.compile(
            r"\bzum\s+(?:zweiten|dritten|vierten|f(?:ü|ue)nften|\d+\.)\s+Mal\b"
            r"|\bam\s+selben\s+Tag\b|\bdas\s+(?:zweite|dritte)\s+Mal\b"
            r"|\bseit\s+\d+\s+(?:Tagen|Wochen|Monaten|Stunden)\b"
            r"|\bzwei(?:mal)?\s+(?:an\s+)?einem\s+Tag\b",
            re.I,
        ),
        "temporal-claim",
    ),
    # Weich-Quantor — „Viele dieser Issues sind laengst erledigt und wurden nur nie
    # geschlossen" war eine Vermutung im Gewand eines Befunds; die Pruefung ergab
    # NULL offene Issues mit `Closes` in einem gemergten PR. Der weiche Quantor macht
    # die Aussage nicht vorsichtiger, sondern nur schwerer widerlegbar — und faellt
    # deshalb durch jeden Allquantor-Filter. Eng gehalten: verlangt Demonstrativ oder
    # bestimmten Artikel plus Zustandsaussage, damit „viele Wege fuehren nach Rom"
    # nicht feuert.
    (
        re.compile(
            r"\b(?:viele|etliche|zahlreiche|die\s+meisten|ein\s+Gro(?:ß|ss)teil|"
            r"der\s+Gro(?:ß|ss)teil|gro(?:ß|ss)e\s+Teile)\s+"
            r"(?:dieser|der|den|von\s+(?:den|diesen))\s+[A-Za-zÄÖÜäöüß-]{3,}"
            r"[^.\n]{0,40}\b(?:sind|wurden|haben|waren|ist|wird)\b"
            r"|\b(?:most|many)\s+of\s+(?:these|the)\s+[a-z-]{3,}[^.\n]{0,40}\b(?:are|were|have)\b",
            re.I,
        ),
        "soft-quantifier-claim",
    ),
]

# Absence-Claims brauchen eine ECHTE Breitsuche als Beleg, nicht irgendeinen gh-Call —
# `gh pr list --search`/`gh issue list --search` matcht Body-Text unzuverlässig (das war
# exakt der Fehler) und zählt hier bewusst NICHT als Korroboration.
# Bewusst NUR echte Breitsuchen (grep -r/git grep/find) oder ein direkter,
# gezielter Read der spezifisch behaupteten Entität (--json body/view --json) —
# das Lesen ein paar EINZELNER Dateien zählt NICHT (das war exakt der Fehler:
# 4 gezielte Datei-Checks statt einer echten Breitsuche über infra/hosts.yaml).
# Funktions-Negationen und Zeit-Claims brauchen einen Blick auf den LAUF, nicht auf
# den Code: „laeuft nicht" ist eine Aussage ueber die Gegenwart, und ein Diff belegt
# Gegenwart nie. Ein `git show` der Workflow-Datei haette den Megatest-Satz heute
# NICHT gedeckt — genau deshalb steht `git log`/`gh run view` hier und `git show`
# bewusst nicht.
RUN_EVIDENCE_TOKENS = re.compile(
    r"gh\s+run\s+(?:view|list|watch)|docker\s+logs|journalctl|systemctl\s+status|"
    r"git\s+log|--log\b|curl\s+[^\n]*(?:livez|healthz|/health)|"
    r"gh\s+api\s+[^\n]*(?:runs|jobs|commits)|\bstat\s+|\bls\s+-l",
    re.I,
)

ABSENCE_EVIDENCE_TOKENS = re.compile(
    r"grep\s+-[a-zA-Z]*r|git\s+grep|find\s+[^\n]*-name|"
    r"--json\s+body|\bview\s+[^\n]*--json|"
    # Strukturiertes Listing OHNE --search zählt (2026-07-22): `gh pr list --json state`
    # ist ein verlässlicher Vollabzug; nur die --search-Variante matcht Body-Text
    # unzuverlässig und bleibt weiterhin ausgeschlossen (Lehre 589606-incr oben).
    r"gh\s+(?:pr|issue)\s+list(?![^\n]*--search)[^\n]*--json",
    re.I,
)

# Deckungs-Claims brauchen einen ELEMENTWEISEN Vergleich als Beleg — ein Zähl-Lauf
# (`wc -l`, `.count()`, `| wc -c`) belegt Deckung NICHT, das war exakt der Fehler
# (writing-hub PR #320: 6/14/5 vs. 9/15/8 gezählt, Namen nie gediffed). Als
# Korroboration zählen nur echte Diff-/Mengen-Operationen oder ein Test, der Werte
# statt Anzahlen prüft.
DIFF_EVIDENCE_TOKENS = re.compile(
    r"\bdiff\b|\bcomm\s+-|\bsort\b[^\n]*\buniq\b|"
    r"set\s*\(|\.difference\(|\.symmetric_difference\(|"
    r"\bgit\s+diff\b|\bgh\s+pr\s+diff\b|"
    # elementweiser Vergleich in einem Test/Skript statt reiner Zählung
    r"assert\s+[^\n]*==\s*\[|assertCountEqual|assertSetEqual|"
    r"sorted\([^\n]*\)\s*==\s*sorted\(",
    re.I,
)

# Tokens in tool output that corroborate a test/deploy/publish claim.
EVIDENCE_TOKENS = re.compile(
    r"\bpassed\b|\bfailed\b|\bpytest\b|\bgh\s+run\b|run\s+watch|"
    r"conclusion|HTTP/\d|status_code|completed/success|"
    r"upload\.pypi|/livez/|deploy\.yml|gh\s+pr\s+(?:merge|checks)|"
    # PR/Issue-Beleg: ein gh-Kommando ODER eine echte GitHub-PR/Issue-URL
    # (gh pr/issue create gibt die URL zurück → starke Korroboration).
    r"gh\s+pr\s+(?:create|view|list)|gh\s+issue\s+(?:create|view|list)|"
    r"gh\s+api[^\n]*(?:pulls|issues)|github\.com/[^\s\"]+/(?:pull|issues)/\d+|"
    # Security-/Governance-Reads als Beleg: secret-scanning-Alert-Zählung,
    # Ruleset-/Branch-Protection- und Actions-Permissions-Checks sind echte
    # gh-api-Verifikationen (2026-07-02: fehlten → FP-Schleife auf jeder
    # „verifiziert"-Antwort trotz gelaufenem gh-api-Check).
    r"gh\s+api[^\n]*(?:secret-scanning|rulesets|rules/branches|actions/permissions|/alerts)|"
    # Coverage-Read + Scope-/Endpoint-Preflight als Beleg (Lehre 2026-07-06): ein
    # echter uses:-/Workflow-/Config-Read korroboriert eine Coverage-Behauptung; ein
    # Token-Scope-/auth-Check korroboriert einen Capability-Claim.
    r"gh\s+api[^\n]*(?:contents/\.github/workflows|actions/workflows|code-security-configuration|/attach|settings/billing)|"
    r"x-oauth-scopes|gh\s+auth\s+status|oauth-scopes",
    re.I,
)

# Strengere Korroboration für PUBLISHED-BODY-Claims (PR-/Issue-Bodies): nur echte
# READS zählen — der Carrier (gh pr create/edit/comment) ist die Behauptung selbst,
# nicht ihr Beleg. Lücke 2026-07-03 (retro 54a76c-incr Befund A, claim-before-
# cheapest-check ×9): #890-Body behauptete „verifiziert: #884/#885 rot/blockiert",
# beide waren 16 min zuvor gemergt; der Turn enthielt gh pr create → alter Token-Satz
# hätte den Claim als korroboriert durchgewunken, und Body-Text wurde nie gescannt.
BODY_EVIDENCE_TOKENS = re.compile(
    r"\bpassed\b|\bfailed\b|\bpytest\b|\bgh\s+run\b|conclusion|HTTP/\d|status_code|"
    r"completed/success|/livez/|curl\s|"
    r"gh\s+pr\s+(?:view|checks|list)|gh\s+issue\s+(?:view|list)|gh\s+api\s",
    re.I,
)

# Body-Extraktion aus Bash-Kommandos: heredoc (cat > f <<'BODY' … BODY), inline
# --body '…'/"…", und --body-file <pfad> (Datei zur Stop-Zeit lesen, best effort).
_HEREDOC_RE = re.compile(r"<<-?\s*'?([A-Z_]{2,16})'?\n(.*?)\n\1\b", re.S)
_INLINE_BODY_RE = re.compile(r"--(?:body|comment)[= ]+(['\"])(.+?)\1", re.S)
_BODY_FILE_RE = re.compile(r"(?:--body-file|-F)[= ]+(\S+)")
# deckt $(cat f) UND den Bashism $(< f) (d2522c-incr #6); Backticks bleiben
# bewusst ungedeckt (Carrier-Kommandos nutzen sie real nicht; bei Vorkommen ergänzen)
CAT_SUBST_RE = re.compile(r"^\$\(\s*(?:cat\s+|<\s*)\"?'?([^\"')]+)\"?'?\s*\)$")
_GH_BODY_CARRIER_RE = re.compile(
    r"\bgh\s+(?:pr|issue)\s+(?:create|edit|comment|close|merge)\b"
)


def _published_bodies(tool_inputs: list) -> list:
    """Sammelt Texte, die als PR-/Issue-Body VERÖFFENTLICHT werden — aus Bash-Kommandos
    mit gh-create/edit/comment (inline --body, heredoc, --body-file) sowie aus
    Write-Inhalten, deren Pfad im selben Turn per --body-file referenziert wird."""
    bodies: list[str] = []
    write_contents: dict[str, str] = {}
    body_file_paths: list[str] = []
    for name, inp in tool_inputs:
        if not isinstance(inp, dict):
            continue
        if name == "Write":
            fp = str(inp.get("file_path", ""))
            write_contents[fp] = str(inp.get("content", ""))
        elif name == "Bash":
            cmd = str(inp.get("command", ""))
            if not _GH_BODY_CARRIER_RE.search(cmd):
                continue  # konservativ: nur Kommandos, die wirklich publizieren
            for _tag, txt in _HEREDOC_RE.findall(cmd):
                bodies.append(txt)
            for _q, txt in _INLINE_BODY_RE.findall(cmd):
                # $(cat <pfad>)-Substitution: Inhalt zur Stop-Zeit nachlesen
                # (Retro d2522c M7 — der 167-Close nutzte --comment "$(cat file)";
                # close-Carrier + --comment ebenfalls seit d2522c gedeckt)
                m_cat = CAT_SUBST_RE.match(txt.strip())
                if m_cat:
                    body_file_paths.append(m_cat.group(1))
                else:
                    bodies.append(txt)
            body_file_paths.extend(_BODY_FILE_RE.findall(cmd))
    for p in body_file_paths:
        if p in write_contents:
            bodies.append(write_contents[p])
        else:
            try:  # Datei existiert zur Stop-Zeit meist noch (Scratchpad)
                bodies.append(
                    Path(p).read_text(encoding="utf-8", errors="replace")[:20000]
                )
            except OSError:
                pass
    return bodies


#: Woran ein Satz seinen Gegenstand nennt: Datei, PR/Issue, Lauf-ID, Repo,
#: Backtick-Bezeichner. Bewusst eng — ein nicht erkanntes Subjekt fuehrt zum
#: bisherigen Verhalten zurueck (generische Korroboration), nie zu einem Block
#: aus dem Nichts.
_SUBJEKT_MUSTER = (
    re.compile(r"\b[\w./-]+\.(?:py|md|ya?ml|json|sh|toml|ts|tsx|js|sql)\b"),
    re.compile(r"#\d{2,6}\b"),
    re.compile(r"\b\d{9,}\b"),
    re.compile(r"`([^`\n]{3,60})`"),
    re.compile(r"\b[a-z][a-z0-9]+-(?:hub|beat|lab|agent)\b"),
)

#: Rauschen, das als Backtick-Bezeichner durchrutscht und nichts identifiziert.
_SUBJEKT_STOPP = {"ja", "nein", "ok", "main", "true", "false", "null"}


def _subjekte(text: str) -> list[str]:
    """Die Gegenstaende, ueber die der Text etwas behauptet.

    Leere Liste heisst: kein benennbarer Gegenstand — dann bleibt es beim alten
    Verhalten. Der Scanner darf nie werfen, deshalb ist alles hier tolerant.
    """
    gefunden: list[str] = []
    try:
        for muster in _SUBJEKT_MUSTER:
            for treffer in muster.findall(text or ""):
                wert = (treffer if isinstance(treffer, str) else treffer[0]).strip()
                if len(wert) >= 3 and wert.lower() not in _SUBJEKT_STOPP:
                    gefunden.append(wert)
    except Exception:  # noqa: BLE001 — Scanner darf nie werfen
        return []
    # Reihenfolge erhalten, Dubletten raus
    gesehen: set[str] = set()
    ergebnis = []
    for w in gefunden:
        if w.lower() not in gesehen:
            gesehen.add(w.lower())
            ergebnis.append(w)
    return ergebnis[:12]


def _last_turn_blocks(transcript_path: str):
    """Return (assistant_text, tool_evidence_text, tool_inputs) for the turn since
    the last user message. tool_evidence_text concatenates tool_result/tool_use
    payloads; tool_inputs is a list of (tool_name, input_dict) for published-body scans."""
    try:
        lines = (
            Path(transcript_path)
            .read_text(encoding="utf-8", errors="replace")
            .splitlines()
        )
    except OSError:
        return "", "", []

    # Walk from the end: collect records back to (and including) the most recent
    # user message that is NOT a tool_result carrier.
    turn = []
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        turn.append(rec)
        if rec.get("type") == "user":
            msg = rec.get("message") or {}
            content = msg.get("content")
            # A real user prompt is a string or a non-tool_result block; tool_results
            # are also type=user but carry tool_result blocks — don't stop on those.
            is_tool_result = isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in content
            )
            if not is_tool_result:
                break
    turn.reverse()

    assistant_text = []
    evidence_text = []
    tool_inputs = []  # (tool_name, input_dict) — für Published-Body-Scan
    for rec in turn:
        msg = rec.get("message") or {}
        content = msg.get("content")
        if rec.get("type") == "assistant":
            if isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text":
                        assistant_text.append(b.get("text", ""))
                    elif b.get("type") == "tool_use":
                        evidence_text.append(json.dumps(b.get("input", "")))
                        tool_inputs.append((b.get("name", ""), b.get("input", {})))
            elif isinstance(content, str):
                assistant_text.append(content)
        elif rec.get("type") == "user":  # tool_result carriers
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        c = b.get("content", "")
                        if isinstance(c, list):
                            c = " ".join(
                                x.get("text", "") for x in c if isinstance(x, dict)
                            )
                        evidence_text.append(str(c))
    return "\n".join(assistant_text), "\n".join(evidence_text), tool_inputs


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    # Don't re-fire inside a stop-hook-triggered continuation: the analysis window
    # (since the last *real* user message) still holds earlier marker words, so we
    # would re-flag every Stop until Claude Code's block-cap force-ends the turn
    # (observed 2026-07-03: 9 consecutive blocks). One check per real turn is enough.
    if event.get("stop_hook_active"):
        return 0
    transcript_path = event.get("transcript_path") or ""
    if not transcript_path:
        return 0

    assistant_text, evidence_text, tool_inputs = _last_turn_blocks(transcript_path)

    fired = []
    if assistant_text:
        for pat, label in CLAIM_PATTERNS:
            if label == "affirmative-cause":
                # Braucht den satzweisen Hedge-Filter, nicht den Volltext-search:
                # "Hypothese: die Ursache ist X" darf NICHT feuern.
                if _affirmative_cause_fires(assistant_text):
                    fired.append(label)
                continue
            if pat.search(assistant_text):
                fired.append(label)

    # Absence-Claims separat behandeln, BEVOR die generische Korroboration greift:
    # ein `gh pr list --search` (in EVIDENCE_TOKENS als "gh pr list" enthalten) darf
    # eine Negativ-Behauptung NICHT decken — genau dieses Muster war zweimal falsch.
    absence_fired = [label for label in fired if label == "absence-claim"]
    fired = [label for label in fired if label != "absence-claim"]
    if absence_fired and not ABSENCE_EVIDENCE_TOKENS.search(evidence_text):
        fired.extend(absence_fired)

    # Deckungs-Claims genauso separat: ein generischer gh-/Test-Lauf (in EVIDENCE_TOKENS)
    # darf eine Vollständigkeits-Behauptung NICHT decken — nur ein elementweiser Diff.
    # (Lehre 2026-07-22: der begleitende Test prüfte `.count() == len(DEFAULT_*)` und
    # war damit strukturell blind für genau die Frage, die er zu belegen schien.)
    coverage_fired = [
        label for label in fired if label == "coverage-completeness-claim"
    ]
    fired = [label for label in fired if label != "coverage-completeness-claim"]
    if coverage_fired and not DIFF_EVIDENCE_TOKENS.search(evidence_text):
        fired.extend(coverage_fired)

    # Universal-Claims teilen die Strenge der Absence-Claims: eine Aussage ueber ALLE
    # Elemente einer Menge braucht eine Breitsuche, kein Stichproben-Read.
    universal_fired = [
        label
        for label in fired
        if label in ("universal-claim", "soft-quantifier-claim")
    ]
    fired = [
        label
        for label in fired
        if label not in ("universal-claim", "soft-quantifier-claim")
    ]
    if universal_fired and not ABSENCE_EVIDENCE_TOKENS.search(evidence_text):
        fired.extend(universal_fired)

    # Funktions-Negation und Zeit-Claim brauchen den Lauf, nicht den Code.
    lauf_fired = [
        label
        for label in fired
        if label in ("function-negation", "temporal-claim", "affirmative-cause")
    ]
    fired = [
        label
        for label in fired
        if label not in ("function-negation", "temporal-claim", "affirmative-cause")
    ]
    if lauf_fired and not RUN_EVIDENCE_TOKENS.search(evidence_text):
        fired.extend(lauf_fired)

    # Subjektbindung (2026-08-20, Ausweitung nach #2143): die Korroboration unten
    # fragt bisher nur, OB im Zug ueberhaupt belegartiges Werkzeug lief — nicht, ob
    # es den GENANNTEN Gegenstand beruehrt hat. Wer zwanzig Kommandos zu Thema A
    # ausfuehrt und danach etwas ueber Thema B behauptet, kommt durch. Genau so
    # liefen die Rueckfaelle nach dem letzten Umbau: zwei falsche Ursachen in
    # gemergten Artefakten und eine Abwesenheits-Behauptung ueber ein Issue, das
    # seit 13 Tagen existierte (Retros 37e8e0 und f9cbb7, 2026-08-17/20).
    subjekte = _subjekte(assistant_text)
    subjekt_unbelegt = bool(subjekte) and not any(
        sub.lower() in evidence_text.lower() for sub in subjekte
    )

    # Corroboration: did the turn run any tool whose output looks like real
    # test/deploy/publish evidence?
    # Ein unbelegtes Subjekt entwaffnet die generische Korroboration: dieselbe
    # Logik wie bei `lauf_fired` oben, nur nach Gegenstand statt nach Belegart.
    # Kalibrierfenster (2026-08-20 bis 2026-09-03): die Subjektbindung entwaffnet
    # die Korroboration nur, wenn sie ausdruecklich scharf geschaltet ist. Sonst
    # meldet sie den Fall als Hinweis, ohne zu blocken — dieselbe SUGGEST-first-
    # Disziplin wie bei den anderen neuen Mustern. Ein Gate, das am ersten Tag
    # blockt, wird abgeschaltet statt kalibriert.
    subjekt_scharf = os.environ.get("EVIDENCE_SCANNER_SUBJEKTBINDUNG", "") == "scharf"
    kalibrier_fall = bool(
        fired and subjekt_unbelegt and EVIDENCE_TOKENS.search(evidence_text)
    )
    if fired and EVIDENCE_TOKENS.search(evidence_text) and not (
        subjekt_unbelegt and subjekt_scharf
    ):
        fired = [
            label
            for label in fired
            if label
            in (
                "absence-claim",
                "coverage-completeness-claim",
                "universal-claim",
                "function-negation",
                "temporal-claim",
                "soft-quantifier-claim",
                # Eine Ursache belegt man durch einen Lauf/Log, nicht durch das Lesen
                # von Code oder einen gruenen Test — die generische Korroboration
                # darf sie deshalb nicht entwaffnen (s. lauf_fired oben).
                "affirmative-cause",
            )
        ]

    # Published-Body-Claims (PR-/Issue-Bodies via gh create/edit/comment): eigener
    # Scan mit STRENGERER Korroboration — der Carrier (gh pr create) belegt nichts
    # über den Body-Inhalt (Lücke 2026-07-03, claim-before-cheapest-check ×9).
    try:
        bodies = _published_bodies(tool_inputs)
    except Exception:  # noqa: BLE001 — Scanner darf nie werfen
        bodies = []
    if bodies:
        body_text = "\n".join(bodies)
        body_fired = any(pat.search(body_text) for pat, _ in CLAIM_PATTERNS)
        if body_fired:
            # Selbst-Korroboration verhindern: der Body landet (als Write-/Bash-Input)
            # auch in evidence_text — seine eigenen Wörter („passed", „grün") dürfen
            # ihn nicht belegen. Roh- UND json-escaped Form strippen.
            ev = evidence_text
            for b in bodies:
                ev = ev.replace(b, "")
                ev = ev.replace(json.dumps(b)[1:-1], "")
            if not BODY_EVIDENCE_TOKENS.search(ev):
                fired.append(
                    "published-body (PR/Issue-Body-Claim ohne Read-Beleg im Turn)"
                )

    if kalibrier_fall and not subjekt_scharf:
        # Im Kalibrierfenster wird der Fall PROTOKOLLIERT, nicht gemeldet: so
        # entstehen Messdaten, ohne die Sitzung mit Hinweisen zu fluten. Scharf
        # geschaltet (EVIDENCE_SCANNER_SUBJEKTBINDUNG=scharf) entwaffnet er
        # stattdessen die Korroboration weiter oben.
        try:
            gate_hits.notiere(
                GATE_HEADER["slug"],
                "kinds=subjekt-unbelegt-kalibrierung",
                session=str(event.get("session_id", "")),
                modus="advisory",
            )
        except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie kippen
            pass

    if not fired:
        return 0

    kinds = ", ".join(sorted(set(fired)))

    # Treffer mitschreiben (Retro 9d861a, Befund #1). Dieser Scanner meldete bis
    # 2026-08-16 ausschliesslich in den Sitzungs-Kontext und schrieb NICHTS auf
    # Platte — genau wie `untested_command_scanner`. Von fuenf aktiven Scannern
    # protokollierten damit nur drei, und die Auswertung in platform#1640 stand
    # unbemerkt auf einer unvollstaendigen Datenbasis: aus "16 von 16 Eintraegen
    # stammen von einem Melder" liess sich ueber die uebrigen NICHTS folgern.
    # Die pytest-Sperre in notiere() gilt unveraendert (platform#1986).
    gate_hits.notiere(
        GATE_HEADER["slug"],
        f"kinds={kinds}",
        session=str(event.get("session_id", "")),
        modus=_mode(),
    )

    msg = (
        "⚠️ evidence-discipline check: deine letzte Antwort enthält eine prüfbare "
        f"Behauptung ({kinds}), aber dieser Turn hat keinen Tool-Lauf, der sie belegt. "
        "Falls die Behauptung steht, führe den billigsten Check JETZT aus (z.B. `make test`, "
        "`gh run watch`, `curl /livez/`, bei PR/Issue-Nummern `gh pr view <N>`/`gh pr create`, "
        "bei re-run-baren Runs mit `--attempt`/updatedAt statt nur createdAt) "
        "und korrigiere die Aussage, bevor du fortfährst. "
        "Falls sie nicht belegbar ist, kennzeichne sie als Hypothese. "
        "Und: ein Check, der NICHTS findet, belegt erst dann eine Abwesenheit, wenn "
        "derselbe Check nachweislich auch etwas finden KANN — sonst ist die Null "
        "womoeglich dein Filter, nicht die Welt (Realfall 2026-07-31: `grep -c` gab 0 "
        "auf einem Log, das den Treffer enthielt; ANSI-Codes im Muster). "
        "(Quelle: ~/.claude/policies/evidence-discipline.md; Backstop nach Vorfall 2026-06-01.)"
    )
    if _mode() == "blocking":
        # decision:block statt Exit 2 — bewusst: Exit 2 wird teils als Nutzer-Ablehnung
        # gelesen und würde den Turn stallen statt korrigieren (KONZ-038 EXT2-M28-5).
        # Der stop_hook_active-Guard oben begrenzt auf EINEN erzwungenen Korrektur-Zug
        # pro Turn (kein Block-Loop; Vorfall 2026-07-03: 9 Blocks in Folge).
        reason = (
            "Automatischer Evidenz-Check (Gate claim-before-cheapest-check, KONZ-038 "
            "§5.2 — dies ist KEINE Nutzer-Ablehnung, sondern Maschinen-Feedback): "
            + msg
            + " Danach den Turn normal beenden; dieser Check feuert pro Turn nur einmal."
        )
        print(json.dumps({"decision": "block", "reason": reason}))
        return 0
    # advisory (Opt-out): dokumentierte additionalContext-Form (exit-0 Stop-Hooks
    # parsen JSON-stdout); der Plain-Text-String bleibt als additionalContext
    # erhalten → robustes Surfacing ohne erzwungene Fortsetzung.
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg}}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
