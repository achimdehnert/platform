"""Unit-/E2E-Tests für cc-skill-dist/doctor.py (session-retro 2026-06-05, F-A/F-B).

Deckt die reinen Helfer (`strip_managed_footer`, `enumerate_commands`,
`enumerate_skills`) und den e2e-Round-Trip der skills-Lane: generate → doctor == Drift 0,
plus Drift-Erkennung bei manipulierter Kopie. Schließt F-A (skills-Lane war CI-blind).

Run: `python3 -m pytest tools/tests/test_doctor.py -q`
"""
import importlib.util
import pathlib
import shutil
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


def test_should_enumerate_dangling_directory_symlink(tmp_path):
    """ADR-281 §8.2 / #1332 — Form A: das Skill-VERZEICHNIS ist ein Symlink ins Leere.

    Genau die Form, die ADR-281 verwendet. Sie wurde vor dem Fix gar nicht erfasst,
    fiel damit aus target_files heraus und erreichte die dangling-Behandlung nie —
    der geforderte Negativtest waere stillschweigend durchgefallen.
    """
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "SKILL.md").write_text("x")
    (tmp_path / "kaputt").symlink_to(tmp_path / "gibt-es-nicht")
    assert set(doc.enumerate_skills(str(tmp_path))) == {"alpha", "kaputt"}


def test_should_enumerate_dangling_skill_md_symlink(tmp_path):
    """#1332 — Form B: die SKILL.md selbst ist ein toter Symlink (war schon vorher erfasst)."""
    (tmp_path / "gamma").mkdir()
    (tmp_path / "gamma" / "SKILL.md").symlink_to(tmp_path / "weg.md")
    assert set(doc.enumerate_skills(str(tmp_path))) == {"gamma"}


def test_should_not_enumerate_plain_dir_without_skill_md(tmp_path):
    """Gegenprobe zum Fix: ein normales Verzeichnis ohne SKILL.md bleibt draussen."""
    (tmp_path / "leer").mkdir()
    assert doc.enumerate_skills(str(tmp_path)) == {}


def test_should_enumerate_flat_md_only(tmp_path):
    (tmp_path / "a.md").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    assert set(doc.enumerate_commands(str(tmp_path))) == {"a.md"}


def test_should_return_empty_for_missing_dir():
    assert doc.enumerate_skills(str(pathlib.Path("/nonexistent/xyz/123"))) == {}


# ---------------------------------------------------------------- ADR-258 hooks-Lane
def test_should_strip_shell_footer_for_hooks():
    sh_footer = ("#!/bin/sh\nexit 0\n\n# MANAGED-BY: platform/tools/cc-skill-dist · "
                 "generated=true · source=tools/hooks/x.sh · do_not_edit\n")
    assert doc.strip_managed_footer(sh_footer).rstrip("\n") == "#!/bin/sh\nexit 0"


def test_should_enumerate_hooks_flat_sh(tmp_path):
    (tmp_path / "reap.sh").write_text("x")
    (tmp_path / "notes.md").write_text("y")           # nicht .sh
    assert set(doc.enumerate_hooks(str(tmp_path))) == {"reap.sh"}


def _wire_settings(home, command):
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    sj = home / ".claude" / "settings.json"
    import json as _json
    sj.write_text(_json.dumps({"hooks": {"SessionEnd": [
        {"matcher": "", "hooks": [{"type": "command", "command": command}]}]}}))


def test_should_flag_missing_hook_wiring(tmp_path, monkeypatch):
    """REC-3: Hook-Datei verteilt, aber settings.json verdrahtet ihn nicht → Drift-Befund."""
    monkeypatch.setenv("HOME", str(tmp_path))
    managed = tmp_path / ".claude" / "hooks" / "managed"
    managed.mkdir(parents=True)
    (managed / "reap_worktrees.sh").write_text("#!/bin/sh\n")
    (managed / "reap_worktrees.sh").chmod(0o755)
    _wire_settings(tmp_path, "/somewhere/else/other.sh")    # falscher Pfad
    issues = doc.check_hook_wiring(str(managed))
    assert any(k == "settings-wiring-missing" for k, _, _ in issues)


def test_should_pass_when_hook_wired_to_managed_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    managed = tmp_path / ".claude" / "hooks" / "managed"
    managed.mkdir(parents=True)
    hook = managed / "reap_worktrees.sh"
    hook.write_text("#!/bin/sh\n")
    hook.chmod(0o755)
    _wire_settings(tmp_path, str(hook))                     # exakter managed-Pfad
    issues = doc.check_hook_wiring(str(managed))
    assert not any(k == "settings-wiring-missing" for k, _, _ in issues)


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


def _make_commands_repo(root):
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    (root / ".windsurf" / "workflows").mkdir(parents=True)
    (root / ".windsurf" / "workflows" / "foo.md").write_text("# foo\nbody\n")
    (root / ".windsurf" / "workflows" / "_reviewer.md").write_text(
        "---\nprovider: openai\ndistribute: false\n---\n# reviewer\nsystem prompt\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    _git(root, "remote", "add", "origin", str(root))
    _git(root, "fetch", "origin", "main", "-q")
    return root


def test_should_not_count_distribute_false_as_missing_drift(tmp_path):
    """commands-Lane: ein distribute:false-Workflow wird nicht verteilt UND nicht als
    'fehlend' gewertet → Drift bleibt 0 (Parität zu generate.py)."""
    repo = _make_commands_repo(tmp_path / "repo")
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(_GEN), "--platform", str(repo), "--ref", "HEAD", "--target", str(dist)],
        check=True, capture_output=True, text=True)
    r = subprocess.run(
        [sys.executable, str(_DOC), "--kind", "commands", "--platform", str(repo),
         "--ref", "HEAD", "--commands", str(dist)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DRIFT-SCORE: 0" in r.stdout


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


def test_should_report_dangling_directory_symlink_as_drift(tmp_path):
    """ADR-281 §8.2 Negativtest (#1332): ein gebrochener Verzeichnis-Symlink MUSS rot werden.

    Vor dem Fix blieb dieser Fall vollstaendig unsichtbar — dangling=0, DRIFT-SCORE
    unveraendert, exit 0. Ein Gate darauf haette eine Garantie getragen, die er nicht
    einloest. Der Test deckt genau die von ADR-281 verwendete Symlink-Form ab.
    """
    repo = _make_repo(tmp_path / "repo")
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(_GEN), "--kind", "skills", "--platform", str(repo),
         "--ref", "HEAD", "--target", str(dist)],
        check=True, capture_output=True, text=True)
    assert "DRIFT-SCORE: 0" in _doctor_skills(repo, dist).stdout

    # kanonischen Skill durch einen Verzeichnis-Symlink ins Leere ersetzen
    shutil.rmtree(dist / "bar")
    (dist / "bar").symlink_to(tmp_path / "ziel-existiert-nicht")

    r = _doctor_skills(repo, dist)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "dangling=1" in r.stdout, r.stdout
    assert "DRIFT-SCORE: 0" not in r.stdout


def _make_commands_repo_with_content(root, workflow_content):
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    (root / ".windsurf" / "workflows").mkdir(parents=True)
    (root / ".windsurf" / "workflows" / "foo.md").write_text(workflow_content)
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    _git(root, "remote", "add", "origin", str(root))
    _git(root, "fetch", "origin", "main", "-q")
    return root


def _doctor_commands(repo, dist):
    return subprocess.run(
        [sys.executable, str(_DOC), "--kind", "commands", "--platform", str(repo),
         "--ref", "HEAD", "--commands", str(dist)],
        capture_output=True, text=True)


def test_should_suggest_legacy_mcp_tokens_without_affecting_drift_score(tmp_path):
    """SUGGEST-lint: mcp[0-9]_ in verteiltem Skill → SUGGEST im Output, DRIFT-SCORE bleibt 0."""
    repo = _make_commands_repo_with_content(
        tmp_path / "repo",
        "# foo\nmcp1_create_issue(owner=x, repo=y)\nmcp2_agent_plan_task(task=z)\n"
    )
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(_GEN), "--platform", str(repo), "--ref", "HEAD", "--target", str(dist)],
        check=True, capture_output=True, text=True)
    r = _doctor_commands(repo, dist)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DRIFT-SCORE: 0" in r.stdout
    assert "SUGGEST" in r.stdout
    assert "mcp1_create_issue" in r.stdout


def test_should_not_suggest_when_no_legacy_mcp_tokens(tmp_path):
    """SUGGEST-lint: keine mcp[0-9]_ → '0 legacy' Meldung, DRIFT-SCORE 0."""
    repo = _make_commands_repo_with_content(
        tmp_path / "repo",
        "# foo\nmcp__github__create_issue(owner=x, repo=y)\nmcp__orchestrator__deploy_check()\n"
    )
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(_GEN), "--platform", str(repo), "--ref", "HEAD", "--target", str(dist)],
        check=True, capture_output=True, text=True)
    r = _doctor_commands(repo, dist)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DRIFT-SCORE: 0" in r.stdout


def test_should_suggest_incomplete_kd_referenz_schema(tmp_path):
    """SUGGEST-lint (Issue #970): KD-Referenz-Block ohne alle 4 Felder → SUGGEST,
    DRIFT-SCORE bleibt unberuehrt."""
    repo = _make_commands_repo_with_content(
        tmp_path / "repo",
        "# foo\n## KD-Referenz\nSpec: x\nLokal: y\n"  # GitHub/iil.pet fehlen
    )
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(_GEN), "--platform", str(repo), "--ref", "HEAD", "--target", str(dist)],
        check=True, capture_output=True, text=True)
    r = _doctor_commands(repo, dist)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DRIFT-SCORE: 0" in r.stdout
    assert "unvollständigem KD-Referenz-Schema" in r.stdout
    assert "GitHub" in r.stdout and "iil.pet" in r.stdout


def test_should_not_suggest_when_kd_referenz_complete(tmp_path):
    """SUGGEST-lint (Issue #970): alle 4 Felder vorhanden → '0 Skills' Meldung."""
    repo = _make_commands_repo_with_content(
        tmp_path / "repo",
        "# foo\n## KD-Referenz\nSpec: x\nLokal: y\nGitHub: z\niil.pet: w\n"
    )
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(_GEN), "--platform", str(repo), "--ref", "HEAD", "--target", str(dist)],
        check=True, capture_output=True, text=True)
    r = _doctor_commands(repo, dist)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DRIFT-SCORE: 0" in r.stdout
    assert "0 Skills mit unvollständigem KD-Referenz-Schema" in r.stdout


def test_should_not_mention_kd_referenz_when_not_declared(tmp_path):
    """SUGGEST-lint (Issue #970): kein 'KD-Referenz'-Marker im Skill → keine Meldung."""
    repo = _make_commands_repo_with_content(tmp_path / "repo", "# foo\nplain content\n")
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(_GEN), "--platform", str(repo), "--ref", "HEAD", "--target", str(dist)],
        check=True, capture_output=True, text=True)
    r = _doctor_commands(repo, dist)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "KD-Referenz-Schema" not in r.stdout
    assert "0 legacy" in r.stdout
