"""Tests fuer den hygiene-melder.

Ein SessionStart-Melder darf unter keinen Umstaenden blockieren und im Normalfall
nichts sagen — sonst wird er nach drei Tagen ignoriert. Die Faelle unten pruefen
deshalb vor allem: schweigt er, wenn alles in Ordnung ist, und ueberlebt er
kaputte Eingaben.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "hygiene_melder.py"
_spec = importlib.util.spec_from_file_location("hygiene_melder", _SRC)
hm = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = hm
_spec.loader.exec_module(hm)

JETZT = dt.datetime(2026, 8, 2, 12, 0, tzinfo=dt.timezone.utc)


def lease(d: pathlib.Path, name: str, expires: str | None) -> pathlib.Path:
    p = d / f"{name}.json"
    p.write_text(json.dumps({"repo": "x", "expires_at": expires}), encoding="utf-8")
    return p


@pytest.fixture()
def stdin_leer(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))


# --- Leases ------------------------------------------------------------------


def test_should_find_no_expired_lease_in_an_empty_dir(tmp_path):
    assert hm.abgelaufene_leases(JETZT, tmp_path) == []


def test_should_report_an_expired_lease_with_its_age(tmp_path):
    lease(tmp_path, "alt", "2026-07-26T12:00:00+00:00")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == [("alt", 7)]


def test_should_ignore_a_lease_that_is_still_valid(tmp_path):
    lease(tmp_path, "frisch", "2026-08-09T12:00:00+00:00")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == []


def test_should_sort_the_oldest_lease_first(tmp_path):
    lease(tmp_path, "a", "2026-07-30T12:00:00+00:00")
    lease(tmp_path, "b", "2026-06-01T12:00:00+00:00")

    assert [n for n, _ in hm.abgelaufene_leases(JETZT, tmp_path)] == ["b", "a"]


def test_should_accept_a_zulu_timestamp(tmp_path):
    lease(tmp_path, "z", "2026-07-26T12:00:00Z")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == [("z", 7)]


def test_should_treat_a_naive_timestamp_as_utc(tmp_path):
    lease(tmp_path, "naiv", "2026-07-26T12:00:00")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == [("naiv", 7)]


@pytest.mark.parametrize("wert", [None, "", "kein-datum"])
def test_should_skip_a_lease_without_a_usable_expiry(tmp_path, wert):
    lease(tmp_path, "kaputt", wert)

    assert hm.abgelaufene_leases(JETZT, tmp_path) == []


def test_should_skip_unreadable_json(tmp_path):
    (tmp_path / "muell.json").write_text("{{{", encoding="utf-8")

    assert hm.abgelaufene_leases(JETZT, tmp_path) == []


def test_should_return_empty_for_a_missing_lease_dir(tmp_path):
    assert hm.abgelaufene_leases(JETZT, tmp_path / "gibtsnicht") == []


# --- Kopien-Drift ------------------------------------------------------------


@pytest.fixture()
def welt(tmp_path):
    platform = tmp_path / "platform" / "tools" / "claude-hooks"
    platform.mkdir(parents=True)
    kopien = tmp_path / "hooks"
    kopien.mkdir()
    return tmp_path / "platform", platform, kopien


def test_should_report_no_drift_for_identical_files(welt):
    wurzel, quelle, kopien = welt
    (quelle / "a.py").write_text("gleich\n", encoding="utf-8")
    (kopien / "a.py").write_text("gleich\n", encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == []


def test_should_report_a_diverging_copy(welt):
    wurzel, quelle, kopien = welt
    (quelle / "a.py").write_text("neu\n", encoding="utf-8")
    (kopien / "a.py").write_text("alt\n", encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == ["a.py"]


def test_should_ignore_a_copy_without_a_source(welt):
    """Nur lokal vorhandene Hooks sind kein Drift — sie haben keine Quelle."""
    wurzel, _, kopien = welt
    (kopien / "nur-lokal.py").write_text("x\n", encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == []


def test_should_also_look_in_the_second_source_dir(welt):
    wurzel, _, kopien = welt
    zweite = wurzel / "tools" / "hooks"
    zweite.mkdir(parents=True)
    (zweite / "b.sh").write_text("neu\n", encoding="utf-8")
    (kopien / "b.sh").write_text("alt\n", encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == ["b.sh"]


def test_should_return_empty_when_the_copy_dir_is_missing(welt):
    wurzel, _, _ = welt

    assert hm.driftende_kopien(wurzel, wurzel / "gibtsnicht") == []


# --- main(): schweigen im Normalfall, nie blockieren -------------------------


def test_should_stay_silent_when_everything_is_healthy(tmp_path, capsys, stdin_leer):
    (tmp_path / "leases").mkdir()

    rc = hm.main(["--platform", str(tmp_path), "--leases", str(tmp_path / "leases")])

    assert rc == 0
    assert capsys.readouterr().out == ""


def test_should_report_expired_leases_via_additional_context(
    tmp_path, capsys, stdin_leer
):
    d = tmp_path / "leases"
    d.mkdir()
    lease(d, "alt", "2026-01-01T00:00:00+00:00")

    hm.main(["--platform", str(tmp_path), "--leases", str(d)])

    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"][
        "additionalContext"
    ]
    assert "abgelaufene repo-session-Leases" in text
    # Seit #1866 nennt der Melder zwei Klassen statt einer Zahl. Dieses Lease hat
    # keinen Worktree und faellt damit in die Sicht-Klasse.
    assert "Kandidat(en)" in text and "zum Sichten" in text
    assert "wollen angesehen, nicht entfernt werden" in text


def test_should_exit_0_on_broken_stdin(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("kein json {{{"))
    (tmp_path / "leases").mkdir()

    assert (
        hm.main(["--platform", str(tmp_path), "--leases", str(tmp_path / "leases")])
        == 0
    )


def test_should_exit_0_when_nothing_exists_at_all(tmp_path, stdin_leer):
    assert (
        hm.main(
            ["--platform", str(tmp_path / "weg"), "--leases", str(tmp_path / "weg")]
        )
        == 0
    )


# --- Klassentrennung (#1866) -------------------------------------------------


def _worktree(basis: pathlib.Path, name: str, *, dirty=False, detached=False):
    """Ein echter git-Worktree — die Klassifikation ruft echtes git auf."""
    import subprocess

    d = basis / name
    d.mkdir(parents=True)
    lauf = lambda *a: subprocess.run(  # noqa: E731
        ["git", "-C", str(d), *a], capture_output=True, check=True
    )
    lauf("init", "-q", "-b", "main")
    lauf("config", "user.email", "t@example.org")
    lauf("config", "user.name", "T")
    (d / "datei.txt").write_text("eins", encoding="utf-8")
    lauf("add", "-A")
    lauf("commit", "-qm", "erster")
    if detached:
        sha = subprocess.run(
            ["git", "-C", str(d), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        lauf("checkout", "-q", sha)
    if dirty:
        (d / "datei.txt").write_text("zwei", encoding="utf-8")
    return d


def _lease_mit_baum(d: pathlib.Path, name: str, baum: pathlib.Path):
    (d / f"{name}.json").write_text(
        json.dumps(
            {"repo": "x", "expires_at": "2026-01-01T00:00:00Z", "worktree": str(baum)}
        ),
        encoding="utf-8",
    )


def test_should_call_a_clean_worktree_a_candidate(tmp_path):
    leases, baeume = tmp_path / "l", tmp_path / "b"
    leases.mkdir()
    _lease_mit_baum(leases, "sauber", _worktree(baeume, "sauber"))

    k = hm.lease_klassen(JETZT, leases)

    assert k["kandidat"] == ["sauber"]
    assert k["dirty"] == [] and k["detached"] == []


def test_should_not_call_a_dirty_worktree_a_candidate(tmp_path):
    """Dirty heisst: da haengt jemandes unfertige Arbeit dran, das ist keine Aufgabe."""
    leases, baeume = tmp_path / "l", tmp_path / "b"
    leases.mkdir()
    _lease_mit_baum(leases, "schmutzig", _worktree(baeume, "schmutzig", dirty=True))

    k = hm.lease_klassen(JETZT, leases)

    assert k["dirty"] == ["schmutzig"]
    assert k["kandidat"] == []


def test_should_not_call_a_detached_worktree_a_candidate(tmp_path):
    leases, baeume = tmp_path / "l", tmp_path / "b"
    leases.mkdir()
    _lease_mit_baum(leases, "los", _worktree(baeume, "los", detached=True))

    k = hm.lease_klassen(JETZT, leases)

    assert k["detached"] == ["los"]
    assert k["kandidat"] == []


def test_should_flag_a_lease_whose_worktree_is_gone(tmp_path):
    leases = tmp_path / "l"
    leases.mkdir()
    _lease_mit_baum(leases, "weg", tmp_path / "gibtsnicht")

    assert hm.lease_klassen(JETZT, leases)["ohne_worktree"] == ["weg"]


def test_should_ignore_leases_that_are_still_valid(tmp_path):
    leases, baeume = tmp_path / "l", tmp_path / "b"
    leases.mkdir()
    baum = _worktree(baeume, "aktiv")
    (leases / "aktiv.json").write_text(
        json.dumps(
            {"repo": "x", "expires_at": "2099-01-01T00:00:00Z", "worktree": str(baum)}
        ),
        encoding="utf-8",
    )

    k = hm.lease_klassen(JETZT, leases)

    assert k["kandidat"] == [] and k["dirty"] == []


def test_should_report_the_rest_as_unclassified_when_the_budget_runs_out(tmp_path):
    """Zeitbudget gerissen ⇒ ehrlich unklassifiziert, nie stillschweigend 'in Ordnung'."""
    leases, baeume = tmp_path / "l", tmp_path / "b"
    leases.mkdir()
    for i in range(3):
        _lease_mit_baum(leases, f"w{i}", _worktree(baeume, f"w{i}"))

    ticks = iter([0.0] + [99.0] * 20)  # erster Blick ok, danach Budget gerissen
    k = hm.lease_klassen(JETZT, leases, zeitbudget=1.0, _uhr=lambda: next(ticks))

    assert k["unklassifiziert"] == 3
    assert k["kandidat"] == []


# --- Gemergt, aber offen (Umbau 2026-09-07, platform#2374) -------------------
#
# Die Klasse misst absichtlich NICHT die Lease-Uhr: der Realfall 0f59ce hatte
# sechs Baeume gemergter PRs offen, alle mit gueltigem Lease. Genau deshalb war
# das Gate blind — die alte Klasse wartet sieben Tage auf einen Ablauf, der
# Fehler passiert in Minuten.


def _lease_gueltig_mit_branch(
    d: pathlib.Path, name: str, branch: str, baum: pathlib.Path
) -> None:
    d.mkdir(exist_ok=True)
    (d / f"{name}.json").write_text(
        json.dumps(
            {
                "repo": "achimdehnert/platform",
                "branch": branch,
                "worktree": str(baum),
                # Bewusst weit in der Zukunft: ein GUELTIGES Lease.
                "expires_at": "2099-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def test_should_flag_a_merged_branch_whose_worktree_is_still_open(tmp_path):
    # POSITIVKONTROLLE am Realfall 0f59ce: gueltiges Lease, PR gemergt, Baum da.
    leases, baum = tmp_path / "l", tmp_path / "baum"
    baum.mkdir()
    _lease_gueltig_mit_branch(leases, "a", "session/2026-09-03/x/y", baum)

    ergebnis = hm.gemergt_aber_offen(leases, pr_state=lambda b, r: "merged")

    assert ergebnis["offen"] == [("session/2026-09-03/x/y", str(baum))]
    assert ergebnis["unklar"] == 0


def test_should_stay_silent_for_an_open_pr(tmp_path):
    leases, baum = tmp_path / "l", tmp_path / "baum"
    baum.mkdir()
    _lease_gueltig_mit_branch(leases, "a", "session/2026-09-03/x/y", baum)

    assert hm.gemergt_aber_offen(leases, pr_state=lambda b, r: "open")["offen"] == []


def test_should_ignore_a_lease_whose_worktree_is_already_gone(tmp_path):
    # Kein Baum = nichts, was hier offen waere; das ist Sache der Alt-Klasse.
    leases = tmp_path / "l"
    _lease_gueltig_mit_branch(leases, "a", "b", tmp_path / "weg")

    assert hm.gemergt_aber_offen(leases, pr_state=lambda b, r: "merged")["offen"] == []


def test_should_count_unjudgeable_leases_instead_of_calling_them_healthy(tmp_path):
    leases, baum = tmp_path / "l", tmp_path / "baum"
    baum.mkdir()
    _lease_gueltig_mit_branch(leases, "a", "b", baum)

    def _wirft(branch, repo):
        raise RuntimeError("gh weg")

    ergebnis = hm.gemergt_aber_offen(leases, pr_state=_wirft)
    assert ergebnis["offen"] == [] and ergebnis["unklar"] == 1


def test_should_count_leases_beyond_the_time_budget_as_unjudgeable(tmp_path):
    leases, baum = tmp_path / "l", tmp_path / "baum"
    baum.mkdir()
    for i in range(3):
        _lease_gueltig_mit_branch(leases, f"a{i}", f"b{i}", baum)

    uhr = iter([0.0, 1.0, 99.0, 99.0, 99.0, 99.0])
    ergebnis = hm.gemergt_aber_offen(
        leases, pr_state=lambda b, r: "merged", zeitbudget=5.0, _uhr=lambda: next(uhr)
    )
    assert ergebnis["unklar"] >= 1


def test_should_stay_silent_without_a_merge_probe(tmp_path):
    # Kein pr_state (Reaper nicht importierbar, gh fehlt) = Klasse uebersprungen,
    # nicht "alles in Ordnung" behauptet und nicht abgestuerzt.
    leases, baum = tmp_path / "l", tmp_path / "baum"
    baum.mkdir()
    _lease_gueltig_mit_branch(leases, "a", "b", baum)

    assert hm.gemergt_aber_offen(leases, pr_state=None)["offen"] == []


def test_should_report_merged_open_worktrees_in_the_session_start_output(
    tmp_path, capsys, stdin_leer, monkeypatch
):
    leases, baum = tmp_path / "l", tmp_path / "baum"
    baum.mkdir()
    _lease_gueltig_mit_branch(leases, "a", "session/2026-09-03/x/y", baum)
    monkeypatch.setattr(hm, "_reaper_pr_state", lambda: lambda b, r: "merged")

    rc = hm.main(["--platform", str(tmp_path / "leer"), "--leases", str(leases)])
    ausgabe = capsys.readouterr().out

    assert rc == 0
    assert "BEREITS GEMERGTEM PR" in ausgabe
    assert "repo-session.sh end" in ausgabe


def test_should_count_unknown_pr_state_as_unjudgeable(tmp_path):
    # Der Fehlermodus, an dem die Klasse im ersten Anlauf selbst scheiterte:
    # `pr_state` antwortet 'unknown' (gh-Aufruf gescheitert), und die Klasse
    # meldete nichts — 85 Leases, 0 Befunde, 3,8 s. Still gruen ist kein Ergebnis.
    leases, baum = tmp_path / "l", tmp_path / "baum"
    baum.mkdir()
    _lease_gueltig_mit_branch(leases, "a", "b", baum)

    ergebnis = hm.gemergt_aber_offen(leases, pr_state=lambda b, r: "unknown")
    assert ergebnis["offen"] == [] and ergebnis["unklar"] == 1


def test_should_expand_a_bare_repo_name_via_the_worktree_remote(tmp_path):
    # Realfall: das Lease traegt `wedding-hub`, `gh --repo wedding-hub` scheitert.
    baum = tmp_path / "baum"
    baum.mkdir()
    import subprocess as sp

    sp.run(["git", "init", "-q"], cwd=baum, check=True)
    sp.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            "git@github.com:achimdehnert/wedding-hub.git",
        ],
        cwd=baum,
        check=True,
    )
    assert hm.voller_repo_name("wedding-hub", str(baum)) == "achimdehnert/wedding-hub"


def test_should_expand_an_https_remote_too(tmp_path):
    baum = tmp_path / "baum"
    baum.mkdir()
    import subprocess as sp

    sp.run(["git", "init", "-q"], cwd=baum, check=True)
    sp.run(
        ["git", "remote", "add", "origin", "https://github.com/meiki-lra/meiki-hub"],
        cwd=baum,
        check=True,
    )
    assert hm.voller_repo_name("meiki-hub", str(baum)) == "meiki-lra/meiki-hub"


def test_should_keep_an_already_qualified_repo_name(tmp_path):
    assert (
        hm.voller_repo_name("achimdehnert/platform", str(tmp_path))
        == "achimdehnert/platform"
    )


def test_should_skip_leases_older_than_the_freshness_window(tmp_path):
    jetzt = dt.datetime(2026, 9, 7, 12, 0, tzinfo=dt.timezone.utc)
    alt = {"last_touch": "2026-07-08T10:00:00Z"}
    frisch = {"last_touch": "2026-09-06T10:00:00Z"}
    assert hm.ist_frisch(alt, jetzt, 3) is False
    assert hm.ist_frisch(frisch, jetzt, 3) is True
    # Ohne lesbaren Zeitstempel wird geprueft, nicht uebersprungen.
    assert hm.ist_frisch({}, jetzt, 3) is True
    assert hm.ist_frisch({"last_touch": "kaputt"}, jetzt, 3) is True
