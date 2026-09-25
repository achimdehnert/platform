"""Drill fuer scope_checkpoint_scanner.py Rev 2 (Slug scope-checkpoint-not-durably-recorded).

Rev 2 hat die Richtung des Gates umgedreht: die Bedingung kommt aus
Tool-Evidenz, der Wortlaut ist nur noch die Erfuellung. Die Drills spiegeln
das — der wichtigste ist ``test_should_fire_when_third_repo_written_and_no
_checkpoint_spoken``: genau diese Fehlerform (x10 im Retro) war fuer Rev 1
strukturell unsichtbar.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location(
    "scope_checkpoint_scanner", _DIR / "scope_checkpoint_scanner.py"
)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

import gate_hits  # noqa: E402  (haengt am sys.path oben)


@pytest.fixture(autouse=True)
def _isolieren(tmp_path, monkeypatch):
    """Protokoll UND Entprellungs-Merker isolieren.

    Ohne den zweiten Teil traegt der erste Drill den Merker in das echte
    /tmp und alle folgenden Drills derselben Session-ID sind still — der
    Drill wuerde sich selbst entwerten (dieselbe Klasse wie der
    Fixture-Leak, den Rev 1 am 2026-08-15 hatte).
    """
    monkeypatch.setattr(gate_hits, "HITS", tmp_path / "gate-hits.jsonl")
    monkeypatch.setattr(
        scanner, "_merker", lambda sid: tmp_path / f"merker_{sid or 'na'}.txt"
    )


def _zeile_text(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _zeile_bash(cmd: str, cwd: str = "") -> dict:
    return {
        "type": "assistant",
        "cwd": cwd,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Bash",
                    "id": "t1",
                    "input": {"command": cmd},
                }
            ]
        },
    }


def _zeile_edit(pfad: str) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Edit",
                    "id": "t2",
                    "input": {"file_path": pfad},
                }
            ]
        },
    }


def _transcript(tmp_path, zeilen):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def _run(monkeypatch, capsys, path, **event_extra):
    ev = {"transcript_path": str(path), "session_id": "drill", **event_extra}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ev)))
    rc = scanner.main()
    out = capsys.readouterr().out.strip()
    return rc, (json.loads(out) if out else {})


def _kontext(antwort: dict) -> str:
    return antwort.get("hookSpecificOutput", {}).get("additionalContext", "")


DREI_REPOS = [
    _zeile_edit("/home/devuser/github/platform/docs/x.md"),
    _zeile_edit("/home/devuser/github/risk-hub/app/y.py"),
    _zeile_edit("/home/devuser/github/dev-hub/app/z.py"),
]


# --- Fehlerform A: die Luecke, fuer die Rev 1 blind war --------------------


def test_should_fire_when_third_repo_written_and_no_checkpoint_spoken(
    tmp_path, monkeypatch, capsys
):
    p = _transcript(tmp_path, [*DREI_REPOS, _zeile_text("So, fertig.")])
    rc, antwort = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert "Fehlerform A" in _kontext(antwort)
    assert "3 beschriebene Repos" in _kontext(antwort)


def test_should_fire_when_prod_step_ran_and_no_checkpoint_spoken(
    tmp_path, monkeypatch, capsys
):
    p = _transcript(
        tmp_path,
        [_zeile_bash("bash deploy.sh risk-hub"), _zeile_text("Deploy laeuft.")],
    )
    _, antwort = _run(monkeypatch, capsys, p)
    assert "Fehlerform A" in _kontext(antwort)
    assert "Prod-/Publish-Schritt" in _kontext(antwort)


def test_should_count_worktree_paths_as_repos(tmp_path, monkeypatch, capsys):
    """ADR-233-Worktrees sind der Normalfall — ohne sie waere das Gate blind."""
    zeilen = [
        _zeile_edit("/home/devuser/.repo-session/worktrees/platform/abc/docs/a.md"),
        _zeile_edit("/home/devuser/.repo-session/worktrees/mcp-hub/def/b.py"),
        _zeile_edit("/home/devuser/.repo-session/worktrees/risk-hub/ghi/c.py"),
        _zeile_text("fertig"),
    ]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert "mcp-hub" in _kontext(antwort)


# --- Fehlerform B: Rev-1-Verhalten, sitzungsweit ---------------------------


def test_should_fire_form_b_when_checkpoint_spoken_but_nothing_durable(
    tmp_path, monkeypatch, capsys
):
    zeilen = [*DREI_REPOS, _zeile_text("Scope-Checkpoint: ist das noch gewollt?")]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert "Fehlerform B" in _kontext(antwort)


def test_should_stay_silent_when_checkpoint_spoken_and_durably_recorded(
    tmp_path, monkeypatch, capsys
):
    zeilen = [
        *DREI_REPOS,
        _zeile_text("Scope-Checkpoint: ist das noch gewollt?"),
        _zeile_bash("gh issue comment 42 -b 'Checkpoint: Owner hat zugestimmt'"),
    ]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert antwort == {}


# --- Nicht-Ausloesen: die Fehlalarm-Seite ---------------------------------


def test_should_stay_silent_below_repo_threshold(tmp_path, monkeypatch, capsys):
    zeilen = [
        _zeile_edit("/home/devuser/github/platform/a.md"),
        _zeile_edit("/home/devuser/github/risk-hub/b.py"),
        _zeile_text("nur zwei Repos, kein Prod"),
    ]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert antwort == {}


def test_should_not_count_read_only_git_commands_as_write(
    tmp_path, monkeypatch, capsys
):
    """`git status` in drei Repos ist keine Scope-Eskalation."""
    zeilen = [
        _zeile_bash("git status", cwd="/home/devuser/github/platform"),
        _zeile_bash("git log --oneline -5", cwd="/home/devuser/github/risk-hub"),
        _zeile_bash("git diff", cwd="/home/devuser/github/dev-hub"),
        _zeile_text("nur gelesen"),
    ]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert antwort == {}


def test_should_stay_silent_when_stop_hook_active(tmp_path, monkeypatch, capsys):
    p = _transcript(tmp_path, [*DREI_REPOS, _zeile_text("fertig")])
    _, antwort = _run(monkeypatch, capsys, p, stop_hook_active=True)
    assert antwort == {}


# --- Entprellung -----------------------------------------------------------


def test_should_report_each_failure_form_only_once_per_session(
    tmp_path, monkeypatch, capsys
):
    p = _transcript(tmp_path, [*DREI_REPOS, _zeile_text("fertig")])
    _, erste = _run(monkeypatch, capsys, p)
    _, zweite = _run(monkeypatch, capsys, p)
    assert "Fehlerform A" in _kontext(erste)
    assert zweite == {}


def test_should_not_accept_durable_artifact_written_before_the_checkpoint(
    tmp_path, monkeypatch, capsys
):
    """Ein frueherer docs/-Edit belegt den spaeteren Checkpoint nicht.

    Ohne die Reihenfolge-Kopplung war Fehlerform B praktisch tot: fast jede
    Sitzung fasst irgendwann eine Datei unter `docs/` an. Gefunden vom
    eigenen Drill am 2026-08-19, nicht im Review.
    """
    zeilen = [
        _zeile_edit("/home/devuser/github/platform/docs/frueher.md"),
        _zeile_edit("/home/devuser/github/risk-hub/app/y.py"),
        _zeile_edit("/home/devuser/github/dev-hub/app/z.py"),
        _zeile_text("Scope-Checkpoint: ist das noch gewollt?"),
    ]
    _, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert "Fehlerform B" in _kontext(antwort)


# ── Rev 3: Reichweite steht in der Wirkung, nicht in den Argumenten ──────────


def _zeile_bash_id(cmd: str, tid: str, cwd: str = "") -> dict:
    return {
        "type": "assistant",
        "cwd": cwd,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Bash",
                    "id": tid,
                    "input": {"command": cmd},
                }
            ]
        },
    }


def _zeile_ergebnis(tid: str, text: str) -> dict:
    return {
        "type": "user",
        "message": {
            "content": [{"type": "tool_result", "tool_use_id": tid, "content": text}]
        },
    }


#: So sieht die Ausgabe des Arbeitsbaum-Reapers aus — ein Aufruf, viele Repos.
REAPER_AUSGABE = (
    "entfernt: /home/devuser/.repo-session/worktrees/platform/2026-08-20-a-b + Lease geschlossen\n"
    "entfernt: /home/devuser/.repo-session/worktrees/risk-hub/2026-08-19-c-d + Lease geschlossen\n"
    "entfernt: /home/devuser/.repo-session/worktrees/dev-hub/2026-08-18-e-f + Lease geschlossen\n"
)


def test_should_flottenlauf_ueber_die_ausgabe_zaehlen(tmp_path, monkeypatch, capsys):
    """Der Rueckfall aus Retro 8d6869-incr #8, nachgestellt.

    Ein Kommando, ein Pfad im Aufruf — und 69 entfernte Arbeitskopien ueber die
    ganze Flotte. Rev 2 sah ein Repo und schwieg.
    """
    zeilen = [
        _zeile_bash_id(
            "python3 ~/github/platform/tools/worktree-reaper.py --apply --karenz-stunden 0",
            "reap1",
        ),
        _zeile_ergebnis("reap1", REAPER_AUSGABE),
    ]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert _kontext(antwort), "Flottenlauf blieb unter der Schwelle"


def test_should_lesendes_kommando_nicht_zaehlen(tmp_path, monkeypatch, capsys):
    """Gegenprobe: dieselbe Ausgabe, nur gelesen.

    Ein `grep -rn ~/github/` nennt dieselben Pfade und fasst nichts an. Ohne
    diese Trennung wuerde jede Suche ueber die Flotte einen Checkpoint fordern —
    und das Gate waere binnen einer Sitzung Rauschen.
    """
    zeilen = [
        _zeile_bash_id("grep -rn 'worktrees' /home/devuser/.repo-session/", "les1"),
        _zeile_ergebnis("les1", REAPER_AUSGABE),
    ]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert not _kontext(antwort)


def test_should_fremdes_ergebnis_nicht_zuordnen(tmp_path, monkeypatch, capsys):
    """Ein Ergebnis ohne passendes schreibendes Kommando zaehlt nicht.

    Die Zuordnung laeuft ueber `tool_use_id`. Faellt sie weg, zaehlt jede
    Ausgabe irgendeines Tools — dann misst das Gate wieder Erwaehnungen.
    """
    zeilen = [_zeile_ergebnis("gibt-es-nicht", REAPER_AUSGABE)]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert not _kontext(antwort)


def test_should_ergebnis_als_bloecke_lesen(tmp_path, monkeypatch, capsys):
    """`content` kommt je nach Client als String ODER als Block-Liste."""
    zeilen = [
        _zeile_bash_id(
            "bash ~/github/platform/tools/repo-session.sh reap --alle", "r2"
        ),
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "r2",
                        "content": [{"type": "text", "text": REAPER_AUSGABE}],
                    }
                ]
            },
        },
    ]
    rc, antwort = _run(monkeypatch, capsys, _transcript(tmp_path, zeilen))
    assert rc == 0
    assert _kontext(antwort)


def test_should_lange_ausgabe_beschneiden():
    """Kostenbremse: nur der Anfang der Ausgabe wird abgesucht."""
    text = "x" * (scanner._AUSGABE_MAX + 500) + "/home/devuser/github/spaet-hub/x"
    assert "spaet-hub" not in scanner._repos_aus_ausgabe(text)


# --- Rev 4 (2026-08-25): fremde laufende Ressource beendet ------------------------
# Anlass: Retro fdd368 §5a. Ein seit dem Vortag laufender Dev-Server wurde per
# `kill <pid>` beendet, waehrend zwoelf Sitzungen parallel liefen; die Zugehoerigkeit
# wurde erst danach ueber /proc/<pid>/cwd geprueft. Weder drittes Repo noch Prod —
# beide bestehenden Ausloeser griffen nicht.


@pytest.mark.parametrize(
    "cmd",
    [
        # Der Realfall, woertlich.
        "kill 2333741",
        "kill -9 2333741",
        "pkill -f runserver",
        "killall python3",
        "sudo systemctl stop ssh-tunnel-postgres",
        "systemctl restart nginx",
        "docker kill writing_hub_web_dev",
        "docker stop weltenhub_local_db",
    ],
)
def test_should_fremde_ressource_als_ausloeser_erkennen(cmd: str) -> None:
    from scope_checkpoint_scanner import _FREMDE_RESSOURCE

    assert _FREMDE_RESSOURCE.search(cmd), f"{cmd!r} loest den Checkpoint nicht aus"


@pytest.mark.parametrize(
    "cmd",
    [
        # Der eigene Stack hoch- und runterfahren ist Alltag, kein Scope-Wachstum.
        "docker compose up -d web worker",
        "docker compose down",
        "docker compose restart web",
        # Lesende Prozess-Sicht ist ausdruecklich erlaubt — sie ist sogar das,
        # was VOR einem kill passieren soll.
        "ps -o lstart= -p 2333741",
        "ss -tlnp | grep :8082",
        "docker ps --format '{{.Names}}'",
        # Wortbestandteile duerfen nicht treffen.
        "git log --oneline | grep killer-feature",
    ],
)
def test_should_alltagskommandos_nicht_als_ausloeser_werten(cmd: str) -> None:
    from scope_checkpoint_scanner import _FREMDE_RESSOURCE

    assert not _FREMDE_RESSOURCE.search(cmd), f"{cmd!r} ist ein Fehlalarm"


# --- Fehlerform C (Rev 5): der abgelegte Checkpoint ist ueberholt ----------
#
# Realfall Retro 33616e (2026-09-01, Befund #1): „Scope wuchs von '/mcp anzeigen'
# auf 13 PRs in 3 Repos + Staging-Schreibzugriff. Checkpoint einmal abgelegt,
# danach kein zweiter trotz weiterem Wachstum." Bis Rev 4 gab der Scanner nach dem
# ersten belegten Checkpoint fuer den Rest der Sitzung 0 zurueck.


_CHECKPOINT = _zeile_text(
    "Scope-Checkpoint: wir sind jetzt in drei Repos — ist das noch gewollt?"
)
_ARTEFAKT = _zeile_bash("gh issue comment 151 --body 'Scope-Checkpoint abgelegt'")


def test_should_stay_silent_when_scope_does_not_grow_after_checkpoint(
    tmp_path, monkeypatch, capsys
):
    # Gegenprobe zur Positivkontrolle unten: identische Sitzung OHNE Nachwachsen.
    p = _transcript(tmp_path, [*DREI_REPOS, _CHECKPOINT, _ARTEFAKT])
    rc, antwort = _run(monkeypatch, capsys, p)
    assert rc == 0
    assert _kontext(antwort) == ""


def test_should_flag_when_two_more_repos_written_after_checkpoint(
    tmp_path, monkeypatch, capsys
):
    # POSITIVKONTROLLE Fehlerform C am Realfall 33616e.
    p = _transcript(
        tmp_path,
        [
            *DREI_REPOS,
            _CHECKPOINT,
            _ARTEFAKT,
            _zeile_edit("/home/devuser/github/meiki-hub/app/a.py"),
            _zeile_edit("/home/devuser/github/writing-hub/app/b.py"),
            _zeile_text("Weiter geht's."),
        ],
    )
    rc, antwort = _run(monkeypatch, capsys, p)
    assert rc == 0
    kontext = _kontext(antwort)
    assert "Fehlerform C" in kontext
    assert "2 weitere Repos seit dem Checkpoint" in kontext


# --- Rev 8 (Retro 2026-09-24 e911bf Befund #5): Mengen statt Zahlen ----------
#
# Realfall: der Checkpoint nannte sechs Repos und stellte „weitere Repos" unter
# ein neues Owner-Wort; beschrieben hatte die Sitzung davon erst vier. Das siebte
# Repo (cad-hub, per repo-session-Worktree) ergab 5 - 4 = 1 < Schwelle 2 — stumm.

_WT = "/home/devuser/.repo-session/worktrees"

_REALFALL_VOR_CHECKPOINT = [
    _zeile_bash(
        f"cd {_WT}/platform/2026-09-24-x && git commit -m a", cwd="/home/devuser"
    ),
    _zeile_edit("/home/devuser/github/risk-hub/NEXT.md"),
    _zeile_bash("git -C /home/devuser/github/ttz-hub commit -m b"),
]

_REALFALL_CHECKPOINT = _zeile_text(
    "Scope-Checkpoint, wie die Hausregel verlangt: die Sitzung hat platform, "
    "risk-hub, ttz-hub, iil-adrfw, mcp-hub und news-hub beruehrt. Nicht "
    "freigegeben ohne neues Wort: weitere Repos."
)


def test_should_flag_first_edit_in_a_repo_the_checkpoint_did_not_name(
    tmp_path, monkeypatch, capsys
):
    # POSITIVKONTROLLE Rev 8 am Realfall e911bf: ein genanntes Repo (news-hub)
    # kommt nach dem Checkpoint dazu, dann ein ungenanntes (cad-hub) ueber den
    # Worktree-Pfad. Unter Rev 5 war das 5 - 3 = 2 bzw. im Realfall 5 - 4 = 1.
    p = _transcript(
        tmp_path,
        [
            *_REALFALL_VOR_CHECKPOINT,
            _REALFALL_CHECKPOINT,
            _ARTEFAKT,
            _zeile_edit("/home/devuser/github/news-hub/app/a.py"),
            _zeile_edit(f"{_WT}/cad-hub/2026-09-24-kd/klickdummy/shell.html"),
        ],
    )
    rc, antwort = _run(monkeypatch, capsys, p)
    assert rc == 0
    kontext = _kontext(antwort)
    assert "Fehlerform C" in kontext
    assert (
        "1 weitere Repos seit dem Checkpoint, die er nicht nennt (cad-hub;" in kontext
    )
    assert "news-hub;" not in kontext


def test_should_not_flag_a_new_repo_the_checkpoint_named(tmp_path, monkeypatch, capsys):
    # GEGENPROBE: dasselbe Wachstum, aber das neue Repo steht im Checkpoint —
    # dann hat der Owner es bereits gesehen, der Checkpoint ist nicht ueberholt.
    p = _transcript(
        tmp_path,
        [
            *_REALFALL_VOR_CHECKPOINT,
            _REALFALL_CHECKPOINT,
            _ARTEFAKT,
            _zeile_edit("/home/devuser/github/news-hub/app/a.py"),
            _zeile_edit(f"{_WT}/mcp-hub/2026-09-24-y/app/b.py"),
        ],
    )
    _, antwort = _run(monkeypatch, capsys, p)
    assert _kontext(antwort) == ""


def test_should_not_count_a_longer_repo_name_as_named():
    # Wortgrenze inkl. Bindestrich: „cad-hub-legacy" nennt cad-hub NICHT.
    texte = ["Scope-Checkpoint: cad-hub-legacy und risk-hub"]
    assert not scanner.im_checkpoint_genannt("cad-hub", texte)
    assert not scanner.im_checkpoint_genannt("hub", texte)
    assert scanner.im_checkpoint_genannt("risk-hub", texte)


def test_should_flag_a_single_unnamed_repo_after_checkpoint(
    tmp_path, monkeypatch, capsys
):
    # Bis Rev 7 hiess dieser Drill „not_flag_a_single_additional_repo" (Schwelle
    # 2). Genau diese Ausnahme war der Rueckfall e911bf: ein einzelnes Repo, das
    # der Checkpoint nicht nennt, IST ein Sprung. Zielrepo + platform sind beim
    # Checkpoint bereits beschrieben und damit gedeckt (s. naechster Drill).
    p = _transcript(
        tmp_path,
        [
            *DREI_REPOS,
            _CHECKPOINT,
            _ARTEFAKT,
            _zeile_edit("/home/devuser/github/meiki-hub/app/a.py"),
        ],
    )
    _, antwort = _run(monkeypatch, capsys, p)
    assert "Fehlerform C" in _kontext(antwort)


def test_should_not_flag_further_writes_in_repos_written_before_checkpoint(
    tmp_path, monkeypatch, capsys
):
    # Der Alltag, fuer den Rev 5 die Schwelle 2 hatte: weiterarbeiten in Repos,
    # die der Checkpoint schon als beschrieben vorfand — auch ohne sie zu nennen.
    p = _transcript(
        tmp_path,
        [
            *DREI_REPOS,
            _CHECKPOINT,
            _ARTEFAKT,
            _zeile_edit("/home/devuser/github/platform/tools/x.py"),
            _zeile_edit("/home/devuser/github/dev-hub/app/z2.py"),
        ],
    )
    _, antwort = _run(monkeypatch, capsys, p)
    assert _kontext(antwort) == ""


def test_should_flag_first_prod_step_after_a_repo_only_checkpoint(
    tmp_path, monkeypatch, capsys
):
    # Die Hausregel fuehrt Prod eigenstaendig neben der Repo-Zahl: ein Checkpoint
    # ueber drei Repos sagt nichts ueber einen spaeteren Prod-Schritt.
    p = _transcript(
        tmp_path,
        [*DREI_REPOS, _CHECKPOINT, _ARTEFAKT, _zeile_bash("bash deploy.sh risk-hub")],
    )
    _, antwort = _run(monkeypatch, capsys, p)
    kontext = _kontext(antwort)
    assert "Fehlerform C" in kontext
    assert "Prod-/Publish-Schritt NACH dem Checkpoint" in kontext


def test_should_not_flag_prod_that_already_ran_before_the_checkpoint(
    tmp_path, monkeypatch, capsys
):
    p = _transcript(
        tmp_path,
        [*DREI_REPOS, _zeile_bash("bash deploy.sh risk-hub"), _CHECKPOINT, _ARTEFAKT],
    )
    _, antwort = _run(monkeypatch, capsys, p)
    assert _kontext(antwort) == ""


def test_should_reset_the_duty_when_a_second_checkpoint_is_spoken(
    tmp_path, monkeypatch, capsys
):
    # Der zweite Checkpoint beschreibt die neue Reichweite — danach ist wieder Ruhe.
    p = _transcript(
        tmp_path,
        [
            *DREI_REPOS,
            _CHECKPOINT,
            _ARTEFAKT,
            _zeile_edit("/home/devuser/github/meiki-hub/app/a.py"),
            _zeile_edit("/home/devuser/github/writing-hub/app/b.py"),
            _zeile_text("Scope-Checkpoint: jetzt sind es fuenf Repos."),
            _zeile_bash("gh issue comment 151 --body 'zweiter Checkpoint'"),
        ],
    )
    _, antwort = _run(monkeypatch, capsys, p)
    assert _kontext(antwort) == ""


def test_should_report_each_growth_level_once(tmp_path, monkeypatch, capsys):
    # Entprellung haengt an der Reichweite, nicht an der Sitzung: derselbe Stand
    # meldet einmal, ein weiterer Sprung wieder. Waere sie sitzungsweit, waere
    # Fehlerform C selbst ein Melder, der nach dem ersten Mal verstummt.
    gewachsen = [
        *DREI_REPOS,
        _CHECKPOINT,
        _ARTEFAKT,
        _zeile_edit("/home/devuser/github/meiki-hub/app/a.py"),
        _zeile_edit("/home/devuser/github/writing-hub/app/b.py"),
    ]
    p1 = _transcript(tmp_path, gewachsen)
    _, erste = _run(monkeypatch, capsys, p1)
    assert "Fehlerform C" in _kontext(erste)

    # Gleicher Stand erneut -> still.
    _, zweite = _run(monkeypatch, capsys, p1)
    assert _kontext(zweite) == ""

    # Naechster Sprung -> wieder eine Meldung.
    p2 = _transcript(
        tmp_path,
        [*gewachsen, _zeile_edit("/home/devuser/github/chat-hub/app/c.py")],
    )
    _, dritte = _run(monkeypatch, capsys, p2)
    assert "Fehlerform C" in _kontext(dritte)


# --- Rev 5: Scharfschalten zaehlt wie Stilllegen (Retro 2026-09-09, Befund 11)


def test_should_flag_enabling_a_service_on_a_foreign_host():
    """`systemctl enable --now` auf prod ist ein Scope-Schritt wie `stop`."""
    treffer = scanner._FREMDE_RESSOURCE.search(
        "ssh hetzner-prod 'systemctl enable --now doc-hub-splitter.timer'"
    )
    assert treffer is not None


def test_should_flag_starting_a_service_on_a_foreign_host():
    treffer = scanner._FREMDE_RESSOURCE.search(
        "ssh hetzner-prod 'systemctl start doc-hub-splitter'"
    )
    assert treffer is not None


def test_should_not_flag_reading_a_service_state():
    """Positivkontrolle: Nachsehen ist kein Eingriff."""
    for harmlos in (
        "systemctl is-active doc-hub-splitter.timer",
        "systemctl list-timers --no-pager",
        "systemctl cat doc-hub-splitter.service",
    ):
        assert scanner._FREMDE_RESSOURCE.search(harmlos) is None, harmlos


# --- Rev 6 (2026-09-14, Retro b7822e B7): Optionen VOR dem Verb -------------
#
# Realfall: `systemctl --user enable --now todo-x.timer` auf dem als Prod
# deklarierten todo-board-Host loeste den Checkpoint nicht aus — Rev 5 kannte
# nur `systemctl <verb>` ohne Optionen dazwischen.


def test_should_flag_systemctl_user_enable_with_option_before_verb():
    treffer = scanner._FREMDE_RESSOURCE.search(
        "systemctl --user enable --now todo-x.timer"
    )
    assert treffer is not None


def test_should_still_not_flag_status_with_option_before_verb():
    """`status` steht nicht in der Verb-Liste — bleibt unerkannt, auch mit Option davor."""
    assert (
        scanner._FREMDE_RESSOURCE.search("systemctl --user status todo-x.timer") is None
    )


def test_should_still_flag_ssh_prefixed_case_from_rev5():
    """Bestehender Rev-5-Fall (ssh-Praefix, kein Optionen-vor-Verb-Fall) bleibt erkannt."""
    treffer = scanner._FREMDE_RESSOURCE.search(
        "ssh hetzner-prod 'systemctl enable --now doc-hub-splitter.timer'"
    )
    assert treffer is not None


# --- Fehlerform D (Rev 9): Frage nach einem Prod-Wort ohne Checkpoint -------
# Realfall Retro 02b7f5 (2026-09-24): Board-Zeile bat um „25 go" fuer einen Merge
# mit Prod-Deploy; der Owner klickte selbst, Tool-Evidenz gab es nie.

_OWNER = {"type": "user", "message": {"content": "25 go 26 go"}}
_PROD_BITTE = (
    "- **[25]** 🟢 Merge von #383 mit Prod-Deploy von dev-hub freigeben · du — "
    "https://github.com/achimdehnert/dev-hub/pull/383"
)


def test_should_fire_form_d_when_answer_asks_for_prod_word_without_checkpoint(
    tmp_path, monkeypatch, capsys
):
    path = _transcript(tmp_path, [_OWNER, _zeile_text(_PROD_BITTE)])
    _, antwort = _run(monkeypatch, capsys, path)
    assert "Fehlerform D" in _kontext(antwort)


def test_should_stay_silent_on_form_d_when_checkpoint_spoken_in_same_answer(
    tmp_path, monkeypatch, capsys
):
    text = "Scope-Checkpoint: wir sind jetzt 2 Repos und einen Prod-Schritt weiter.\n"
    path = _transcript(tmp_path, [_OWNER, _zeile_text(text + _PROD_BITTE)])
    _, antwort = _run(monkeypatch, capsys, path)
    assert "Fehlerform D" not in _kontext(antwort)


def test_should_stay_silent_on_form_d_when_checkpoint_fell_earlier_in_session(
    tmp_path, monkeypatch, capsys
):
    frueher = _zeile_text(
        "Scope-Checkpoint: Scope ist gewachsen, ist das noch gewollt?"
    )
    path = _transcript(tmp_path, [frueher, _OWNER, _zeile_text(_PROD_BITTE)])
    _, antwort = _run(monkeypatch, capsys, path)
    assert "Fehlerform D" not in _kontext(antwort)


def test_should_stay_silent_on_form_d_for_plain_merge_request(
    tmp_path, monkeypatch, capsys
):
    text = "- **[11]** 🟢 PR #3552 und #3553 mergen · platform · du"
    path = _transcript(tmp_path, [_OWNER, _zeile_text(text)])
    _, antwort = _run(monkeypatch, capsys, path)
    assert antwort == {}


def test_should_stay_silent_on_form_d_when_signals_sit_in_different_lines(
    tmp_path, monkeypatch, capsys
):
    text = "Der Deploy lief gestern durch.\n- **[3]** 🟢 Bericht lesen · du"
    path = _transcript(tmp_path, [_OWNER, _zeile_text(text)])
    _, antwort = _run(monkeypatch, capsys, path)
    assert antwort == {}


def test_should_report_form_d_only_once_per_session(tmp_path, monkeypatch, capsys):
    path = _transcript(tmp_path, [_OWNER, _zeile_text(_PROD_BITTE)])
    _run(monkeypatch, capsys, path)
    _, zweite = _run(monkeypatch, capsys, path)
    assert "Fehlerform D" not in _kontext(zweite)
