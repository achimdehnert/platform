#!/usr/bin/env python3
"""SessionStart-Melder fuer drei stille Ansammlungen.

Beide Klassen wachsen, ohne dass jemand es merkt — weil das Werkzeug, das sie
aufraeumt, aus gutem Grund schweigt, wenn es nichts tun darf.

**Abgelaufene Leases.** `repo-session.sh reap` ueberspringt dirty Worktrees
korrekt (fremde, unfertige Arbeitsstaende) und meldet das nur im eigenen Lauf.
Wer nie reapt, erfaehrt nie davon. Gemessen 2026-08-02: 79 von 116 offenen
Leases waren ueber ihr `expires_at` hinaus, die aeltesten sieben Wochen alt.

Seit 2026-08-10 (#1866) nennt der Melder nicht mehr EINE Zahl. Eine einzige Zahl
war eine Aufforderung, die niemand erfuellen konnte: von 68 abgelaufenen Leases
konnte `reap` an dem Tag **keines** abraeumen, weil keines einen gemergten PR
hatte. Ein Melder, dessen Zahl durch das von ihm empfohlene Mittel nicht kleiner
wird, wird dauerhaft rot — und ein dauerhaft roter Melder meldet nichts mehr.

Getrennt wird deshalb in zwei Klassen, lokal und ohne Netz:

    Kandidat   Worktree clean, Branch bestimmbar → `reap` entscheidet am
               PR-Zustand, ob es ihn nimmt. Das ist die Aufforderung.
    Sichten    dirty, detached HEAD oder Worktree weg → `reap` fasst diese
               NIE an. Das ist ein Bestand, keine Aufgabe.

Die Klassifikation ruft `git status` je Lease und laeuft unter einem Zeitbudget
(gemessen: 68 Leases in 0,8 s). Reisst das Budget, wird der Rest als
**unklassifiziert** ausgewiesen statt stillschweigend einer Klasse zugeschlagen.

**Gemergt, aber offen** (2026-09-07, platform#2374 — Umbau des Gates
`worktree-midsession-accumulation`, das ×3 rueckfaellig war). Die Klasse oben
misst **abgelaufene** Leases: eine Sieben-Tage-Uhr. Die Fehlform, die den Slug
wiederkehren liess, spielt sich in Minuten ab — der PR wird gemergt, der
Arbeitsbaum bleibt offen, und beides faellt erst in der Retro auf:

    Retro fdd368 (2026-08-26)  17 Baeume eines einzigen Tages ungeraeumt
    Retro m1zgqt (2026-09-02)  zwei Leases nach dem Merge nicht geschlossen
    Retro 0f59ce (2026-09-03)  6 Baeume gemergter PRs offen bis zur Retro

Der Reaper kennt den Zustand laengst — er ist squash-aware — raeumt einen
gemergten Baum aber erst verzoegert ab: ein aktives Lease plus die
Karenzfrist (12 h) halten ihn, damit niemandem der Boden unter den Fuessen
weggezogen wird. Das ist richtig fuer das ENTFERNEN und falsch fuer das MELDEN.
Deshalb misst diese Klasse dieselbe Wahrheit ohne Karenz und ohne Lease-Uhr: PR
gemergt und Baum noch da = eine Zeile beim naechsten Sitzungsstart.

Die Merge-Erkennung wird aus `tools/worktree-reaper.py` IMPORTIERT, nicht
nachgebaut. Eine zweite Kopie waere die zweite Gelegenheit fuer denselben
Fehler — und beim naechsten `gh`-Formatwechsel wuerde nur eine nachgezogen.
Sie braucht `gh`; faellt das aus oder reisst das Zeitbudget, wird die Klasse
still uebersprungen (der Melder darf den Sitzungsstart nie aufhalten).

**Verteilte Kopien.** Hooks unter `~/.claude/hooks/` sind Kopien aus
`platform/tools/claude-hooks/` bzw. `platform/tools/hooks/`. Driften sie, wirkt
ein Fix in platform nicht — und der laufende Hook ist die Kopie. Der
cc-skill-dist-Generator bleibt hier ungenutzt: sein `--target` tauscht ein
ganzes Verzeichnis aus und hat `~/.claude` schon einmal ersetzt.

Vertrag: **immer Exit 0**, Ausgabe nur bei Befund. Ein Melder darf nie blockieren.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

#: Maschinenlesbarer Kopf (KONZ-038 D8). Zweiter Traeger des Gates
#: `worktree-midsession-accumulation` seit dem Umbau 2026-09-07: der Reaper
#: ENTFERNT (mit Karenz), dieser Melder MELDET (ohne Karenz).
GATE_HEADER = {
    "slug": "worktree-midsession-accumulation",
    "mode": "process",
    "owner": "achim",
    "last_drill_pass": "2026-09-07",
    "evidence": "tools/claude-hooks/tests/test_hygiene_melder.py",
}

LEASES = Path.home() / ".repo-session" / "leases"
KOPIEN = Path.home() / ".claude" / "hooks"
QUELLEN = ("tools/claude-hooks", "tools/hooks")


def abgelaufene_leases(
    jetzt: dt.datetime, wurzel: Path = LEASES
) -> list[tuple[str, int]]:
    """(Lease-Name, Tage ueberfaellig), aelteste zuerst."""
    if not wurzel.is_dir():
        return []
    treffer: list[tuple[str, int]] = []
    for p in sorted(wurzel.glob("*.json")):
        try:
            daten = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        roh = daten.get("expires_at")
        if not roh:
            continue
        try:
            ende = dt.datetime.fromisoformat(str(roh).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ende.tzinfo is None:
            ende = ende.replace(tzinfo=dt.timezone.utc)
        if ende < jetzt:
            treffer.append((p.stem, (jetzt - ende).days))
    return sorted(treffer, key=lambda t: -t[1])


def _git(pfad: str, *args: str, timeout: float = 5.0) -> tuple[int, str]:
    """git im Worktree. Jeder Fehler wird zu (rc!=0, "") — ein Melder wirft nie."""
    try:
        fertig = subprocess.run(
            ["git", "-C", pfad, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return fertig.returncode, fertig.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def lease_klassen(
    jetzt: dt.datetime,
    wurzel: Path = LEASES,
    zeitbudget: float = 8.0,
    _uhr=time.monotonic,
) -> dict[str, list[str] | int]:
    """Abgelaufene Leases in 'kandidat' und die Sicht-Klassen trennen.

    Rein lokal: kein `gh`, kein Netz. Die Frage "nimmt `reap` das?" haengt am
    PR-Zustand und ist damit hier nicht abschliessend beantwortbar — deshalb
    heisst die Klasse **Kandidat** und nicht "abraeumbar".
    """
    ergebnis: dict[str, list[str] | int] = {
        "kandidat": [],
        "dirty": [],
        "detached": [],
        "ohne_worktree": [],
        "unklassifiziert": 0,
    }
    start = _uhr()
    for name, _tage in abgelaufene_leases(jetzt, wurzel):
        pfad = wurzel / f"{name}.json"
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        baum = daten.get("worktree") or ""
        if not baum or not Path(baum).is_dir():
            ergebnis["ohne_worktree"].append(name)  # type: ignore[union-attr]
            continue
        if _uhr() - start > zeitbudget:
            # Lieber ehrlich unklassifiziert als falsch einsortiert.
            ergebnis["unklassifiziert"] += 1  # type: ignore[operator]
            continue
        rc, aus = _git(baum, "status", "--porcelain", "--untracked-files=no")
        if rc != 0:
            ergebnis["ohne_worktree"].append(name)  # type: ignore[union-attr]
            continue
        if aus.strip():
            ergebnis["dirty"].append(name)  # type: ignore[union-attr]
            continue
        if _git(baum, "symbolic-ref", "-q", "HEAD")[0] != 0:
            ergebnis["detached"].append(name)  # type: ignore[union-attr]
            continue
        ergebnis["kandidat"].append(name)  # type: ignore[union-attr]
    return ergebnis


#: Zeitbudget fuer die Merge-Abfrage. Ein Sitzungsstart hat wenige Sekunden;
#: reisst das Budget, wird der Rest NICHT als "in Ordnung" gewertet, sondern
#: gezaehlt und mitgemeldet (dieselbe Ehrlichkeitsregel wie bei lease_klassen).
MERGE_BUDGET = float(os.environ.get("HYGIENE_MERGE_BUDGET", "20"))

#: Wie jung ein Lease sein muss, damit die Merge-Abfrage es anfasst. Die Klasse
#: fragt „ist der Baum nach dem Merge liegengeblieben?" — das ist eine Frage der
#: letzten Tage. Ein zwei Monate alter gemergter Baum ist ein BESTAND und gehoert
#: dem `reap`-Lauf, nicht dem Sitzungsstart. Ohne diese Grenze zahlt jeder Start
#: eine gh-Abfrage je offenem Lease: gemessen am 2026-09-07 waren das 85 Abfragen
#: in 35 s (Ergebnis: 46 gemergte Baeume offen) — zu teuer fuer einen Melder, der
#: vor der ersten Zeile Arbeit laeuft.
FRISCH_TAGE = int(os.environ.get("HYGIENE_MERGE_FRISCH_TAGE", "3"))


def _reaper_pr_state():
    """`pr_state` aus tools/worktree-reaper.py — importiert, nicht nachgebaut.

    Der Dateiname traegt einen Bindestrich und ist damit kein Modulname; deshalb
    der Umweg ueber importlib. Schlaegt der Import fehl (Datei verschoben, andere
    Baumstruktur), gibt diese Funktion None zurueck und die Klasse wird still
    uebersprungen — ein Melder, der den Sitzungsstart zerreisst, wird abgeschaltet.
    """
    import importlib.util

    quelle = _platform_wurzel() / "tools" / "worktree-reaper.py"
    if not quelle.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("worktree_reaper", quelle)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul.pr_state
    except Exception:  # noqa: BLE001 — Melder wirft nie
        return None


def voller_repo_name(repo: str, baum: str) -> str | None:
    """`owner/repo` aus dem nackten Lease-Feld plus dem Remote des Arbeitsbaums.

    Das Lease traegt nur den Repo-NAMEN (`wedding-hub`). `gh pr list --repo
    wedding-hub` scheitert damit und `pr_state` antwortet `unknown` — die
    Merge-Klasse waere still gruen gewesen, ohne je etwas geprueft zu haben.
    Gemessen am 2026-09-07 an 85 offenen Leases: 85x `unknown`, 0 Befunde,
    3,8 Sekunden. Genau die Sorte Melder, gegen die dieses Repo Gates baut.

    Der Owner kommt deshalb aus `git remote get-url origin` im Baum selbst —
    die im Haus vorgeschriebene Weise, eine Link-Basis zu bestimmen, statt sie
    aus einem anderen Repo zu uebertragen (die Orgs unterscheiden sich).
    """
    if not repo:
        return None
    if "/" in repo:
        return repo
    rc, aus = _git(baum, "remote", "get-url", "origin")
    if rc != 0 or not aus.strip():
        return None
    url = aus.strip()
    # git@github.com:owner/repo.git  |  https://github.com/owner/repo(.git)
    rest = url.split("github.com", 1)[-1].lstrip(":/")
    teile = [t for t in rest.removesuffix(".git").split("/") if t]
    if len(teile) < 2:
        return None
    return f"{teile[-2]}/{teile[-1]}"


def ist_frisch(daten: dict, jetzt: dt.datetime, tage: int) -> bool:
    """Lease aus den letzten `tage` Tagen? Ohne lesbaren Zeitstempel: ja.

    „Im Zweifel pruefen" ist hier die richtige Richtung — ein uebersehener
    frischer Baum ist der Fehler, gegen den die Klasse gebaut ist; eine
    zusaetzliche gh-Abfrage kostet nur Zeit.
    """
    for feld in ("last_touch", "created_at"):
        roh = daten.get(feld)
        if not roh:
            continue
        try:
            zeit = dt.datetime.fromisoformat(str(roh).replace("Z", "+00:00"))
        except ValueError:
            continue
        if zeit.tzinfo is None:
            zeit = zeit.replace(tzinfo=dt.timezone.utc)
        return (jetzt - zeit).days <= tage
    return True


def gemergt_aber_offen(
    wurzel: Path = LEASES,
    pr_state=None,
    zeitbudget: float = MERGE_BUDGET,
    _uhr=time.monotonic,
    jetzt: dt.datetime | None = None,
    frisch_tage: int = FRISCH_TAGE,
) -> dict[str, list[tuple[str, str]] | int]:
    """Offene Leases, deren PR bereits gemergt ist — ohne Karenz, ohne Lease-Uhr.

    `pr_state(branch, repo)` wird hereingereicht, damit der Drill die Klasse ohne
    `gh` und ohne Netz pruefen kann. Der Aufrufer setzt die echte Funktion aus
    dem Reaper ein.

    Gezaehlt wird JEDES offene Lease, auch ein nicht abgelaufenes: genau darin
    liegt der Umbau. Ein Lease laeuft sieben Tage, ein Merge dauert Sekunden.
    """
    ergebnis: dict[str, list[tuple[str, str]] | int] = {"offen": [], "unklar": 0}
    if pr_state is None or not wurzel.is_dir():
        return ergebnis
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    start = _uhr()
    for pfad in sorted(wurzel.glob("*.json")):
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        baum = daten.get("worktree") or ""
        branch = daten.get("branch") or ""
        if not branch or not baum or not Path(baum).is_dir():
            continue  # kein Baum mehr = nichts, was hier offen waere
        if not ist_frisch(daten, jetzt, frisch_tage):
            continue  # Bestand, nicht Ansammlung — s. FRISCH_TAGE
        if _uhr() - start > zeitbudget:
            ergebnis["unklar"] += 1  # type: ignore[operator]
            continue
        voll = voller_repo_name(str(daten.get("repo") or ""), baum)
        try:
            zustand = pr_state(branch, voll)
        except Exception:  # noqa: BLE001 — Melder wirft nie
            zustand = "unknown"
        if zustand == "merged":
            ergebnis["offen"].append((branch, baum))  # type: ignore[union-attr]
        elif zustand == "unknown":
            # `unknown` heisst NICHT "kein Befund". Ohne diese Zeile waere die
            # Klasse bei jedem gh-Ausfall still gruen — der Fehlermodus, den
            # dieser Melder eine Ebene hoeher gerade behebt.
            ergebnis["unklar"] += 1  # type: ignore[operator]
    return ergebnis


def _hash(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def driftende_kopien(platform: Path, kopien: Path = KOPIEN) -> list[str]:
    """Dateinamen, die als Kopie existieren und von ihrer Quelle abweichen."""
    if not kopien.is_dir():
        return []
    quelle: dict[str, Path] = {}
    for rel in QUELLEN:
        d = platform / rel
        if d.is_dir():
            for p in d.iterdir():
                if p.is_file():
                    quelle.setdefault(p.name, p)

    drift: list[str] = []
    for kopie in sorted(kopien.iterdir()):
        if not kopie.is_file() or kopie.name not in quelle:
            continue
        a, b = _hash(kopie), _hash(quelle[kopie.name])
        if a and b and a != b:
            drift.append(kopie.name)
    return drift


def _platform_wurzel() -> Path:
    """Der platform-Checkout — von hier aus zwei Ebenen hoch."""
    return Path(__file__).resolve().parent.parent.parent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", default=str(_platform_wurzel()))
    ap.add_argument("--leases", default=str(LEASES))
    ap.add_argument(
        "--ohne-merge-pruefung",
        action="store_true",
        help="Die Klasse 'gemergt, aber offen' ueberspringen (sie braucht gh).",
    )
    args = ap.parse_args(argv)

    try:
        json.load(sys.stdin)  # SessionStart-JSON; Inhalt wird nicht gebraucht
    except Exception:  # noqa: BLE001 — stdin darf fehlen oder Muell sein
        pass

    zeilen: list[str] = []

    jetzt = dt.datetime.now(dt.timezone.utc)
    alt = abgelaufene_leases(jetzt, Path(args.leases))
    if alt:
        klassen = lease_klassen(jetzt, Path(args.leases))
        kandidat = len(klassen["kandidat"])  # type: ignore[arg-type]
        sichten = (
            len(klassen["dirty"])  # type: ignore[arg-type]
            + len(klassen["detached"])  # type: ignore[arg-type]
            + len(klassen["ohne_worktree"])  # type: ignore[arg-type]
        )
        teile = [
            f"· {len(alt)} abgelaufene repo-session-Leases (aeltester {alt[0][1]} Tage "
            f"ueberfaellig): {kandidat} Kandidat(en), {sichten} zum Sichten."
        ]
        if kandidat:
            teile.append(
                "  Kandidaten sind clean und haben einen Branch — "
                "`bash tools/repo-session.sh reap ~/github/<repo>` nimmt davon die, "
                "deren PR gemergt ist. Die uebrigen bleiben liegen, das ist richtig."
            )
        gruende = [
            f"{len(klassen[k])} {wort}"  # type: ignore[arg-type]
            for k, wort in (
                ("dirty", "dirty"),
                ("detached", "detached HEAD"),
                ("ohne_worktree", "ohne Worktree"),
            )
            if klassen[k]
        ]
        if gruende:
            teile.append(
                "  Zum Sichten (" + ", ".join(gruende) + ") — `reap` fasst diese NIE "
                "an; sie gehoeren jemandem und wollen angesehen, nicht entfernt werden."
            )
        if klassen["unklassifiziert"]:
            teile.append(
                f"  {klassen['unklassifiziert']} unklassifiziert (Zeitbudget) — "
                f"nicht als 'in Ordnung' lesen."
            )
        zeilen.append("\n".join(teile))

    # Gemergt, aber offen — die Klasse ohne Karenz und ohne Lease-Uhr.
    if not args.ohne_merge_pruefung:
        merge = gemergt_aber_offen(Path(args.leases), _reaper_pr_state())
        offen = merge["offen"]
        if offen:
            namen = ", ".join(b for b, _ in offen[:3])  # type: ignore[union-attr]
            rest = len(offen) - 3  # type: ignore[arg-type]
            zeilen.append(
                f"· {len(offen)} Arbeitsbaum/-baeume mit BEREITS GEMERGTEM PR sind noch "
                f"offen: {namen}"
                + (f" (+{rest} weitere)" if rest > 0 else "")
                + ".\n  Aufraeumen gehoert in den Merge-Zug, nicht ans Sitzungsende — "
                "`bash tools/repo-session.sh end <pfad>` je Baum. (Gate "
                "worktree-midsession-accumulation, Umbau 2026-09-07: der Reaper haelt "
                "einen gemergten Baum bewusst 12 h Karenz, dieser Melder wartet nicht.)"
            )
        if merge["unklar"]:
            zeilen.append(
                f"· {merge['unklar']} Lease(s) beim Merge-Abgleich nicht beurteilbar "
                "(Zeitbudget oder gh) — nicht als 'in Ordnung' lesen."
            )

    drift = driftende_kopien(Path(args.platform))
    if drift:
        zeilen.append(
            f"· {len(drift)} verteilte Hook-Kopie(n) weichen von der platform-Quelle ab: "
            + ", ".join(drift)
            + ". Der LAUFENDE Hook ist die Kopie — ein Fix in platform wirkt erst nach "
            "dem Nachziehen."
        )

    if not zeilen:
        return 0

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "🧹 hygiene-melder:\n" + "\n".join(zeilen),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
