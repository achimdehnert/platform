"""Tests fuer tools/check_noop_changes.py — Diff-Aenderungen ohne semantischen Gehalt.

Die Tests bauen echte Wegwerf-Git-Repos (wie andere Tests hier auch — deshalb
laeuft tools-tests.yml mit fetch-depth: 0).
"""

import importlib.util
import pathlib
import subprocess
import sys

_SPEC = importlib.util.spec_from_file_location(
    "check_noop_changes",
    pathlib.Path(__file__).resolve().parents[1] / "check_noop_changes.py",
)
cnc = importlib.util.module_from_spec(_SPEC)
sys.modules["check_noop_changes"] = cnc  # noetig fuer @dataclass-Aufloesung
_SPEC.loader.exec_module(cnc)


def _git(repo, *args):
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _repo(tmp_path, files_before):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    for name, content in files_before.items():
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "branch", "-q", "base-ref")
    return repo


def _commit(repo, files_after, msg="change"):
    for name, content in files_after.items():
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", msg)


ORIGINAL = "def f(a, b):\n    return a + b\n"
# Gleicher AST, andere Formatierung (so wuerde ein Formatter umbrechen).
REFORMATTED = "def f(\n    a,\n    b,\n):\n    return a + b\n"
SEMANTIC = "def f(a, b):\n    return a - b\n"


def test_should_flag_reformatted_python_as_ast_only(tmp_path):
    repo = _repo(tmp_path, {"m.py": ORIGINAL})
    _commit(repo, {"m.py": REFORMATTED})
    findings, stats = cnc.run("base-ref...HEAD", repo)
    assert [f.kind for f in findings] == ["ast_only"]
    assert findings[0].path == "m.py"
    assert stats["py_compared"] == 1


def test_should_not_flag_real_code_change(tmp_path):
    repo = _repo(tmp_path, {"m.py": ORIGINAL})
    _commit(repo, {"m.py": SEMANTIC})
    findings, _ = cnc.run("base-ref...HEAD", repo)
    assert findings == []


def test_should_flag_whitespace_only_change_in_any_filetype(tmp_path):
    repo = _repo(tmp_path, {"a.md": "Hallo Welt\n"})
    _commit(repo, {"a.md": "Hallo   Welt\n"})
    findings, _ = cnc.run("base-ref...HEAD", repo)
    assert [f.kind for f in findings] == ["ws_only"]


def test_should_separate_wanted_change_from_swept_files(tmp_path):
    """Der reale Anlassfall: eine gewollte Aenderung, viele mitformatierte Dateien."""
    repo = _repo(
        tmp_path,
        {"wanted.py": ORIGINAL, "foreign1.py": ORIGINAL, "foreign2.py": ORIGINAL},
    )
    _commit(
        repo,
        {
            "wanted.py": SEMANTIC,
            "foreign1.py": REFORMATTED,
            "foreign2.py": REFORMATTED,
        },
    )
    findings, stats = cnc.run("base-ref...HEAD", repo)
    assert stats["changed"] == 3
    assert sorted(f.path for f in findings) == ["foreign1.py", "foreign2.py"]


def test_should_ignore_added_and_deleted_files(tmp_path):
    repo = _repo(tmp_path, {"keep.py": ORIGINAL, "gone.py": ORIGINAL})
    (repo / "gone.py").unlink()
    _commit(repo, {"new.py": ORIGINAL})
    findings, _ = cnc.run("base-ref...HEAD", repo)
    assert findings == []


def test_should_survive_unparsable_python(tmp_path):
    repo = _repo(tmp_path, {"broken.py": "def f(:\n"})
    _commit(repo, {"broken.py": "def f(:  \n"})
    findings, stats = cnc.run("base-ref...HEAD", repo)
    # Whitespace-Detektor greift trotzdem; der AST-Vergleich zaehlt als unlesbar.
    assert [f.kind for f in findings] == ["ws_only"]
    assert stats["unreadable"] == 0  # ws_only kommt vor dem Parse-Versuch


def test_should_count_unparsable_python_when_not_whitespace_only(tmp_path):
    repo = _repo(tmp_path, {"broken.py": "def f(:\n"})
    _commit(repo, {"broken.py": "def g(:\n"})
    findings, stats = cnc.run("base-ref...HEAD", repo)
    assert findings == []
    assert stats["unreadable"] == 1


def test_should_raise_lookup_error_for_missing_ref(tmp_path):
    repo = _repo(tmp_path, {"m.py": ORIGINAL})
    try:
        cnc.run("does-not-exist...HEAD", repo)
    except LookupError as exc:
        assert exc.args[0] == "does-not-exist"
    else:
        raise AssertionError("LookupError erwartet")


def test_should_exit_zero_on_missing_ref_instead_of_false_green(tmp_path, monkeypatch):
    repo = _repo(tmp_path, {"m.py": ORIGINAL})
    monkeypatch.chdir(repo)
    assert cnc.main(["--range", "nope...HEAD", "--format", "github"]) == 0


def test_should_exit_zero_in_suggest_mode_despite_findings(tmp_path, monkeypatch):
    repo = _repo(tmp_path, {"m.py": ORIGINAL})
    _commit(repo, {"m.py": REFORMATTED})
    monkeypatch.chdir(repo)
    assert cnc.main(["--range", "base-ref...HEAD"]) == 0


def test_should_exit_one_with_gate_flag(tmp_path, monkeypatch):
    repo = _repo(tmp_path, {"m.py": ORIGINAL})
    _commit(repo, {"m.py": REFORMATTED})
    monkeypatch.chdir(repo)
    assert cnc.main(["--range", "base-ref...HEAD", "--gate"]) == 1


def test_should_accept_two_dot_and_bare_ref_ranges(tmp_path):
    assert cnc._split_range("a...b") == ("a", "b")
    assert cnc._split_range("a..b") == ("a", "b")
    assert cnc._split_range("a") == ("a", "HEAD")
