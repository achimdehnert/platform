"""Unit-/E2E-Tests für cc-skill-dist/doctor.py (session-retro 2026-06-05, F-A/F-B).

Deckt die reinen Helfer (`strip_managed_footer`, `enumerate_commands`,
`enumerate_skills`) und den e2e-Round-Trip der skills-Lane: generate → doctor == Drift 0,
plus Drift-Erkennung bei manipulierter Kopie. Schließt F-A (skills-Lane war CI-blind).

Run: `python3 -m pytest tools/tests/test_doctor.py -q`
"""
import importlib.util
import pathlib
import subprocess
import sys

_DOC = pathlib.Path(__file__).resolve().parents[1] / "cc-skill-dist" / "doctor.py"
_GEN = pathlib.Path(__file__).resolve().parents[1] / "cc-skill-dist" / "generate.py"
_spec = importlib.util.spec_from_file_location("doctor", _DOC)
doc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(doc)

MARK_FOOTER = ("\n\n<!-- MANAGED-BY: platform/tools/cc-skill-dist · generated=true · "
               "source=skills/bar/SKILL.md · source_commit=abc123def456 · "
               "content_hash=sha256:0123456789abcdef · do_not_edit -->\n")


# ---------------------------------------------------------------- reine Helfer
def test_should_strip_managed_footer():
    assert doc.strip_managed_footer("content\n" + MARK_FOOTER).rstrip("\n") == "content"


def test_should_not_strip_when_no_footer():
    t = "plain content\nno footer\n"
    assert doc.strip_managed_footer(t) == t


def test_should_enumerate_only_dirs_with_skill_md(tmp_path):
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "SKILL.md").write_text("x")
    (tmp_path / "beta").mkdir()
    (tmp_path / "beta" / "SKILL.md").write_text("y")
    (tmp_path / "nope").mkdir()                              # kein SKILL.md
    assert set(doc.enumerate_skills(str(tmp_path))) == {"alpha", "beta"}


def test_should_enumerate_flat_md_only(tmp_path):
    (tmp_path / "a.md").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    assert set(doc.enumerate_commands(str(tmp_path))) == {"a.md"}


def test_should_return_empty_for_missing_dir():
    assert doc.enumerate_skills(str(pathlib.Path("/nonexistent/xyz/123"))) == {}


# ---------------------------------------------------------------- e2e round-trip
def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _make_repo(root):
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    (root / "skills" / "bar").mkdir(parents=True)
    (root / "skills" / "bar" / "SKILL.md").write_text("---\nname: bar\n---\n# bar\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    _git(root, "remote", "add", "origin", str(root))
    _git(root, "fetch", "origin", "main", "-q")
    return root


def _doctor_skills(repo, skills_dir):
    return subprocess.run(
        [sys.executable, str(_DOC), "--kind", "skills", "--platform", str(repo),
         "--ref", "HEAD", "--skills-dir", str(skills_dir)],
        capture_output=True, text=True)


def test_should_report_drift_zero_then_detect_tamper(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(_GEN), "--kind", "skills", "--platform", str(repo),
         "--ref", "HEAD", "--target", str(dist)],
        check=True, capture_output=True, text=True)

    # frisch generiert → Drift 0
    r = _doctor_skills(repo, dist)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DRIFT-SCORE: 0" in r.stdout

    # manipulierte Kopie → Drift erkannt (exit 1, score > 0)
    (dist / "bar" / "SKILL.md").write_text("TAMPERED\n")
    r2 = _doctor_skills(repo, dist)
    assert r2.returncode == 1
    assert "DRIFT-SCORE: 0" not in r2.stdout
