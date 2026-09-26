"""Tests fuer tools/agent-handover/fragments.py (KONZ-platform-027, #1944 K6)."""

import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_PFAD = Path(__file__).resolve().parents[1] / "agent-handover" / "fragments.py"
_spec = importlib.util.spec_from_file_location("handover_fragments", _PFAD)
fr = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = fr  # dataclass braucht das Modul in sys.modules
_spec.loader.exec_module(fr)

JETZT = dt.datetime(2026, 9, 16, 10, 0, 0, tzinfo=dt.timezone.utc)
ISSUE = "https://github.com/achimdehnert/platform/issues/{}"


def _fragment(wurzel, sid, erstellt, offen=(), erledigt=("x",), log="Text."):
    pfad = fr.neu(wurzel, sid, f"Titel {sid}", None, erstellt)
    text = pfad.read_text()
    text = text.replace(
        "## Erledigt\n", "## Erledigt\n" + "".join(f"- {e}\n" for e in erledigt)
    )
    text = text.replace("## Offen\n", "## Offen\n" + "".join(f"- {o}\n" for o in offen))
    text = text.replace("## Log\n", f"## Log\n{log}\n")
    pfad.write_text(text)
    return pfad


def _zustand(zu):
    return lambda owner, repo, n: "zu" if n in zu else "offen"


def test_should_append_suffix_instead_of_overwriting_same_session(tmp_path):
    a = fr.neu(tmp_path, "s1", "T", None, JETZT)
    b = fr.neu(tmp_path, "s1", "T", None, JETZT)
    assert a != b and a.exists() and b.exists()
    assert b.name.endswith("-s1-2.md")


def test_should_reject_session_id_with_path_characters(tmp_path):
    with pytest.raises(ValueError):
        fr.neu(tmp_path, "../x", "T", None, JETZT)


def test_should_render_every_recent_fragment_regardless_of_count(tmp_path):
    # L6: kein festes N-Fenster — auch am Tag mit vielen Sitzungen fehlt keine
    for i in range(5):
        _fragment(tmp_path, f"s{i}", JETZT + dt.timedelta(minutes=i))
    text = fr.render(fr.alle(tmp_path), JETZT.date(), _zustand(set()))
    for i in range(5):
        assert f"(Sitzung s{i})" in text
    assert "aktive Fragmente 5 von 5" in text


def test_should_keep_old_fragment_while_its_issue_is_open(tmp_path):
    alt = JETZT - dt.timedelta(days=30)
    _fragment(tmp_path, "alt-offen", alt, offen=[f"Rest — {ISSUE.format(1)}"])
    _fragment(tmp_path, "alt-zu", alt, offen=[f"Rest — {ISSUE.format(2)}"])
    text = fr.render(fr.alle(tmp_path), JETZT.date(), _zustand({2}))
    assert "Sitzung alt-offen" in text
    assert "Sitzung alt-zu" not in text
    assert ISSUE.format(1) in text and ISSUE.format(2) not in text


def test_should_treat_unknown_issue_state_as_open(tmp_path):
    _fragment(
        tmp_path, "alt", JETZT - dt.timedelta(days=30), offen=[f"R — {ISSUE.format(3)}"]
    )
    text = fr.render(fr.alle(tmp_path), JETZT.date(), fr.offline_zustand)
    assert "Sitzung alt" in text


def test_should_list_each_open_url_once_newest_first(tmp_path):
    _fragment(tmp_path, "a", JETZT, offen=[f"erst — {ISSUE.format(5)}"])
    _fragment(
        tmp_path, "b", JETZT + dt.timedelta(hours=1), offen=[f"neu — {ISSUE.format(5)}"]
    )
    text = fr.render(fr.alle(tmp_path), JETZT.date(), _zustand(set()))
    assert text.count(ISSUE.format(5)) == 1
    assert "neu — " in text
    assert text.index("Sitzung b)") < text.index("Sitzung a)")


def test_should_flag_open_item_without_exactly_one_url(tmp_path):
    _fragment(
        tmp_path,
        "s",
        JETZT,
        offen=["ohne Link", f"zwei {ISSUE.format(1)} {ISSUE.format(2)}"],
    )
    fehler = fr.fehler(fr.alle(tmp_path)[0])
    assert sum("genau eine" in f for f in fehler) == 2


def test_should_accept_skeleton_written_by_neu(tmp_path):
    fr.neu(tmp_path, "s", "T", "Ziel", JETZT)
    assert fr.fehler(fr.alle(tmp_path)[0]) == []


def test_should_flag_edit_of_fragment_already_on_base(tmp_path):
    def git(*a):
        subprocess.run(
            ["git", "-C", str(tmp_path), *a], check=True, capture_output=True
        )

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    pfad = _fragment(tmp_path, "s", JETZT)
    git("add", "-A")
    git("commit", "-qm", "basis")
    git("switch", "-qc", "zweig")
    pfad.write_text(pfad.read_text() + "nachtraeglich\n")
    _fragment(tmp_path, "t", JETZT)
    git("add", "-A")
    git("commit", "-qm", "zweig")
    assert fr.geaenderte_bestandsfragmente(tmp_path, "main") == [
        str(pfad.relative_to(tmp_path))
    ]


def test_should_read_fragments_from_git_ref_not_worktree(tmp_path):
    def git(*a):
        subprocess.run(
            ["git", "-C", str(tmp_path), *a], check=True, capture_output=True
        )

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    _fragment(tmp_path, "gemergt", JETZT)
    git("add", "-A")
    git("commit", "-qm", "basis")
    _fragment(tmp_path, "nur-lokal", JETZT)
    ids = [f.kopf["session_id"] for f in fr.alle(tmp_path, "main")]
    assert ids == ["gemergt"]


def test_should_map_graphql_states_and_default_to_unknown(monkeypatch):
    antwort = {
        "data": {
            "r0": {"i1": {"state": "OPEN"}, "i2": {"state": "MERGED"}, "i3": None},
            "r1": None,
        }
    }

    def lauf(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(antwort))

    monkeypatch.setattr(fr.subprocess, "run", lauf)
    urls = [
        ISSUE.format(1),
        ISSUE.format(2),
        ISSUE.format(3),
        "https://github.com/o/x/issues/9",
    ]
    t = fr.gh_zustaende(urls)
    assert t[("achimdehnert", "platform", 1)] == "offen"
    assert t[("achimdehnert", "platform", 2)] == "zu"
    assert t[("achimdehnert", "platform", 3)] == "unbekannt"
    assert t[("o", "x", 9)] == "unbekannt"


def test_should_fall_back_to_unknown_when_gh_times_out(monkeypatch):
    def lauf(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)

    monkeypatch.setattr(fr.subprocess, "run", lauf)
    assert fr.gh_zustaende([ISSUE.format(1)]) == {
        ("achimdehnert", "platform", 1): "unbekannt"
    }


def test_should_flag_session_id_that_is_only_a_prefix_of_the_file_name(tmp_path):
    pfad = fr.neu(tmp_path, "auf-main", "T", None, JETZT)
    pfad.write_text(pfad.read_text().replace("session_id: auf-main", "session_id: auf"))
    assert "session_id im Kopf passt nicht zum Dateinamen" in fr.fehler(
        fr.alle(tmp_path)[0]
    )


def test_should_accept_suffixed_file_of_same_session(tmp_path):
    fr.neu(tmp_path, "s", "T", None, JETZT)
    fr.neu(tmp_path, "s", "T", None, JETZT)
    assert [fr.fehler(f) for f in fr.alle(tmp_path)] == [[], []]
