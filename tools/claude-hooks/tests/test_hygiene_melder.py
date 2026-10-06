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
import os
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "hygiene_melder.py"
_spec = importlib.util.spec_from_file_location("hygiene_melder", _SRC)
hm = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = hm
_spec.loader.exec_module(hm)

JETZT = dt.datetime(2026, 8, 2, 12, 0, tzinfo=dt.timezone.utc)

# Die echten Funktionen, bevor die autouse-Fixture sie fuer main() abklemmt.
KONTINGENT = hm.kontingent_befund
LANGLAEUFER = hm.langlaeufer


@pytest.fixture(autouse=True)
def ohne_host(monkeypatch, tmp_path):
    """main() darf in Tests weder gh rufen noch den echten Host lesen."""
    monkeypatch.setattr(hm, "SETTINGS", tmp_path / "keine-settings.json")
    monkeypatch.setattr(hm, "kontingent_befund", lambda: None)
    monkeypatch.setattr(hm, "langlaeufer", lambda: [])


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


_FOOTER = (
    "\n\n# MANAGED-BY: platform/tools/cc-skill-dist · generated=true · "
    "source=tools/claude-hooks/a.py · source_commit=9caf8a5b3950 · "
    "content_hash=sha256:549b35e9f2dd5536 · do_not_edit\n"
)


def test_should_not_count_the_managed_footer_as_drift(welt):
    """platform#3611: jede Lane-Kopie traegt den Footer, die Quelle nicht."""
    wurzel, quelle, kopien = welt
    (quelle / "a.py").write_text("gleich\n", encoding="utf-8")
    (kopien / "a.py").write_text("gleich" + _FOOTER, encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == []


def test_should_report_drift_behind_a_managed_footer(welt):
    wurzel, quelle, kopien = welt
    (quelle / "a.py").write_text("neu\n", encoding="utf-8")
    (kopien / "a.py").write_text("alt" + _FOOTER, encoding="utf-8")

    assert hm.driftende_kopien(wurzel, kopien) == ["a.py"]


def test_should_strip_the_footer_like_the_lane_doctor():
    """Gegenstueck zu doctor.py — beide muessen dieselbe Kopie gleich lesen."""
    doctor_pfad = _SRC.parents[1] / "cc-skill-dist" / "doctor.py"
    spec = importlib.util.spec_from_file_location("cc_doctor", doctor_pfad)
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    for kopie in ("x = 1" + _FOOTER, "x = 1\n", "#!/bin/bash\necho a" + _FOOTER):
        assert hm.ohne_managed_footer(kopie) == doctor.strip_managed_footer(kopie).rstrip(
            "\n"
        )


def test_should_find_drift_when_running_as_the_distributed_copy(tmp_path):
    """platform#3611 Kriterium 4: der Melder laeuft als Kopie unter
    ~/.claude/hooks — `__file__` zeigt dann nicht in den platform-Checkout."""
    import shutil
    import subprocess

    home = tmp_path / "home"
    kopien = home / ".claude" / "hooks"
    kopien.mkdir(parents=True)
    quelle = tmp_path / "github" / "platform" / "tools" / "claude-hooks"
    quelle.mkdir(parents=True)
    shutil.copy(_SRC, quelle / "hygiene_melder.py")
    kopie = kopien / "hygiene_melder.py"
    kopie.write_text(_SRC.read_text(encoding="utf-8").rstrip("\n") + _FOOTER, encoding="utf-8")
    (kopien / "zweiter.py").write_text("alt" + _FOOTER, encoding="utf-8")
    (quelle / "zweiter.py").write_text("neu\n", encoding="utf-8")

    ergebnis = subprocess.run(
        [
            sys.executable,
            str(kopie),
            "--leases",
            str(tmp_path / "leases"),
            "--settings",
            str(tmp_path / "settings.json"),
            "--ohne-kontingent",
        ],
        input="{}",
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home), "GITHUB_DIR": str(tmp_path / "github")},
    )

    assert ergebnis.returncode == 0, ergebnis.stderr
    kontext = json.loads(ergebnis.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "1 verteilte Hook-Kopie(n) weichen von der platform-Quelle ab: zweiter.py." in kontext


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


# --- Verschleiss ohne Zeugen (dev-hub#404 Baustein A) -------------------------


def _settings(d: pathlib.Path, *befehle: str) -> pathlib.Path:
    p = d / "settings.json"
    p.write_text(
        json.dumps(
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": b} for b in befehle]}]}}
        ),
        encoding="utf-8",
    )
    return p


def _skript(d: pathlib.Path, name: str, shebang: str, ausfuehrbar=True) -> pathlib.Path:
    p = d / name
    p.write_text(f"#!{shebang}\n", encoding="utf-8")
    p.chmod(0o755 if ausfuehrbar else 0o644)
    return p


def test_should_report_hook_whose_interpreter_is_a_self_link(tmp_path):
    # Realfall 2026-09-28: `.venv -> <selber Pfad>`, rc 126 ab 03:17.
    venv = tmp_path / ".venv"
    venv.symlink_to(venv)
    hook = _skript(tmp_path, "log_llm_call.py", f"{venv}/bin/python")

    befunde = hm.kaputte_hooks(_settings(tmp_path, str(hook)))

    assert len(befunde) == 1
    assert befunde[0].startswith("log_llm_call.py: Interpreter")


def test_should_accept_healthy_hooks(tmp_path):
    ok = _skript(tmp_path, "ok.py", "/usr/bin/env python3")
    direkt = _skript(tmp_path, "direkt.sh", "/bin/sh")

    befehle = (str(ok), str(direkt), f"python3 {ok} --hook")
    assert hm.kaputte_hooks(_settings(tmp_path, *befehle)) == []


def test_should_report_missing_and_non_executable_hooks(tmp_path):
    lahm = _skript(tmp_path, "lahm.py", "/usr/bin/env python3", ausfuehrbar=False)

    befunde = hm.kaputte_hooks(
        _settings(tmp_path, str(tmp_path / "weg.sh"), str(lahm), f"python3 {tmp_path}/fehlt.py")
    )

    assert befunde == ["weg.sh: Datei fehlt", "lahm.py: nicht ausfuehrbar", "fehlt.py: Datei fehlt"]


def test_should_return_no_hooks_for_missing_or_broken_settings(tmp_path):
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{{{", encoding="utf-8")

    assert hm.kaputte_hooks(tmp_path / "weg.json") == []
    assert hm.kaputte_hooks(kaputt) == []


def test_should_report_broken_hook_via_main(tmp_path, capsys, stdin_leer):
    (tmp_path / "leases").mkdir()
    settings = _settings(tmp_path, str(tmp_path / "weg.sh"))

    hm.main(
        ["--platform", str(tmp_path), "--leases", str(tmp_path / "leases"),
         "--settings", str(settings)]
    )

    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "koennen nicht starten: weg.sh: Datei fehlt" in text


def _rate(core: int, graphql: int = 5000) -> str:
    return json.dumps(
        {"resources": {"core": {"limit": 5000, "remaining": core},
                       "graphql": {"limit": 5000, "remaining": graphql}}}
    )


def _laeufer(probe_ok: bool, rate: str):
    def lauf(pfad: str):
        if pfad.startswith("repos/"):
            return (0, "achimdehnert/platform") if probe_ok else (1, "API rate limit exceeded")
        return 0, rate
    return lauf


def test_should_report_secondary_throttling_although_rate_limit_is_full():
    # platform#2735: rate_limit meldet 5000 frei, echte Abrufe scheitern.
    drossel = hm._drossel_modul()
    assert drossel is not None

    befund = KONTINGENT(laeufer=_laeufer(False, _rate(5000)), drossel=drossel)

    assert befund and "weist echte Abrufe ab" in befund


def test_should_report_primary_quota_below_threshold():
    befund = KONTINGENT(laeufer=_laeufer(True, _rate(5000, 900)), drossel=hm._drossel_modul())

    assert befund == "GitHub-Kontingent knapp: graphql 900/5000."


def test_should_stay_silent_on_healthy_quota_or_missing_gh():
    drossel = hm._drossel_modul()

    assert KONTINGENT(laeufer=_laeufer(True, _rate(4000)), drossel=drossel) is None
    assert KONTINGENT(laeufer=lambda p: (127, "gh: command not found"), drossel=drossel) is None
    assert KONTINGENT(laeufer=lambda p: (1, "HTTP 401: Bad credentials"), drossel=drossel) is None


def _proc(d: pathlib.Path, btime: int) -> pathlib.Path:
    d.mkdir()
    (d / "stat").write_text(f"cpu  1 2 3\nbtime {btime}\n", encoding="utf-8")
    return d


def _prozess(proc: pathlib.Path, pid: int, argv: list[str], start_ticks: int) -> None:
    p = proc / str(pid)
    p.mkdir()
    (p / "cmdline").write_bytes("\0".join(argv).encode() + b"\0")
    # Feld 22 = starttime; nach `)` ist es der 20. Eintrag (Index 19).
    (p / "stat").write_text(f"{pid} (x y) S" + " 0" * 18 + f" {start_ticks} 0 0\n")


def test_should_find_old_gh_loop_and_mcp_but_not_old_dev_server(tmp_path):
    takt = os.sysconf("SC_CLK_TCK")
    proc = _proc(tmp_path / "proc", btime=1_000_000)
    jetzt = 1_000_000 + 20 * 86400
    alt, frisch = 0, (19 * 86400) * takt  # Start bei Boot bzw. vor einem Tag
    geheim = "tok-nie-ins-log"
    _prozess(proc, 11, ["bash", "-c", f"until false; do gh pr view 1 --token {geheim}; sleep 60; done"], alt)
    _prozess(proc, 12, ["npm", "exec", "@modelcontextprotocol/server-github"], alt)
    _prozess(proc, 13, ["python3", "-m", "http.server", "--directory", "/home/x/github/repo"], alt)
    _prozess(proc, 14, ["gh", "run", "watch"], frisch)

    funde = LANGLAEUFER(tage=7, proc=proc, jetzt=jetzt, uid=os.getuid())

    assert [(pid, tage) for pid, tage, _ in funde] == [(11, 20), (12, 20)]
    assert funde[0][2] == "bash"
    assert all(geheim not in label for _, _, label in funde)


def test_should_skip_processes_of_other_users(tmp_path):
    proc = _proc(tmp_path / "proc", btime=1_000_000)
    _prozess(proc, 11, ["gh", "run", "watch"], 0)

    assert LANGLAEUFER(tage=7, proc=proc, jetzt=1_000_000 + 30 * 86400, uid=os.getuid() + 1) == []
