"""Unit-/E2E-Tests für cc-skill-dist/generate.py (session-retro 2026-06-05, F-B).

Schließt die Test-Lücke: +121 LOC Verteil-Tooling (commands + skills Lane) waren
ungetestet. Deckt `collect()` (beide Lanes + Edge-Cases), den e2e-Generate (flach vs.
verschachtelt), den `--allow-live`-Guard und die F-D-Regression (regenerate-Zeile trägt
`--allow-live` bei Live-Ziel).

Run: `python3 -m pytest tools/tests/test_generate.py -q`
(generate.py über importlib geladen — collect() ist rein, der Rest via subprocess.)
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "cc-skill-dist" / "generate.py"
_spec = importlib.util.spec_from_file_location("generate", _SRC)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


# ---------------------------------------------------------------- collect() (rein)
def test_should_collect_commands_by_basename():
    listing = ("100644 blob aaa\t.windsurf/workflows/foo.md\n"
               "100644 blob bbb\t.windsurf/workflows/bar.md\n")
    out = gen.collect(listing, "commands")
    assert set(out) == {"foo.md", "bar.md"}
    assert out["foo.md"] == ("aaa", ".windsurf/workflows/foo.md")


def test_should_collect_skills_by_dirname():
    listing = ("100644 blob c1\tskills/alpha/SKILL.md\n"
               "100644 blob c2\tskills/beta/SKILL.md\n")
    out = gen.collect(listing, "skills")
    assert set(out) == {"alpha", "beta"}
    assert out["alpha"] == ("c1", "skills/alpha/SKILL.md")


def test_should_ignore_non_skill_files_in_skills_lane():
    listing = ("100644 blob c1\tskills/alpha/SKILL.md\n"
               "100644 blob c2\tskills/alpha/README.md\n")
    assert set(gen.collect(listing, "skills")) == {"alpha"}


def test_should_ignore_non_md_in_commands_lane():
    listing = ("100644 blob c1\t.windsurf/workflows/foo.md\n"
               "100644 blob c2\t.windsurf/workflows/logo.png\n")
    assert set(gen.collect(listing, "commands")) == {"foo.md"}


def test_should_ignore_tree_lines():
    listing = ("040000 tree ddd\tskills/alpha\n"
               "100644 blob c1\tskills/alpha/SKILL.md\n")
    assert set(gen.collect(listing, "skills")) == {"alpha"}


# ---------------------------------------------------------------- e2e helpers
def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _make_repo(root):
    """Minimal-Repo mit beiden Quellen + self-origin (generate.py fetcht origin main)."""
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    (root / ".windsurf" / "workflows").mkdir(parents=True)
    (root / ".windsurf" / "workflows" / "foo.md").write_text("# foo\nbody\n")
    # interner System-Prompt: distribute:false → darf NICHT als Slash-Command verteilt werden
    (root / ".windsurf" / "workflows" / "_reviewer.md").write_text(
        "---\nprovider: openai\ndistribute: false\n---\n# reviewer\nsystem prompt\n")
    (root / "skills" / "bar").mkdir(parents=True)
    (root / "skills" / "bar" / "SKILL.md").write_text("---\nname: bar\n---\n# bar\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    _git(root, "remote", "add", "origin", str(root))
    _git(root, "fetch", "origin", "main", "-q")
    return root


def _run(args, env=None):
    return subprocess.run([sys.executable, str(_SRC), *args],
                          capture_output=True, text=True, env=env)


def test_should_generate_commands_flat(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(out)])
    assert r.returncode == 0, r.stderr
    assert (out / "foo.md").is_file()                       # flach
    assert "MANAGED-BY" in (out / "foo.md").read_text()
    m = json.loads((out / "manifest.json").read_text())
    assert m["kind"] == "commands" and m["skill_count"] == 1


def test_should_skip_distribute_false_in_commands(tmp_path):
    """distribute:false-Workflow ist interner System-Prompt → kein Slash-Command,
    nicht im Ziel, nicht im skill_count, nicht im Manifest."""
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(out)])
    assert r.returncode == 0, r.stderr
    assert (out / "foo.md").is_file()                       # normaler Command verteilt
    assert not (out / "_reviewer.md").exists()              # interner System-Prompt NICHT
    m = json.loads((out / "manifest.json").read_text())
    assert m["skill_count"] == 1                            # nur foo.md gezählt (nicht len(blobs))
    assert all(f["name"] != "_reviewer.md" for f in m["files"])


def test_should_generate_skills_nested(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    r = _run(["--kind", "skills", "--platform", str(repo), "--ref", "HEAD", "--target", str(out)])
    assert r.returncode == 0, r.stderr
    assert (out / "bar" / "SKILL.md").is_file()             # verschachtelt <name>/SKILL.md
    assert "MANAGED-BY" in (out / "bar" / "SKILL.md").read_text()
    assert json.loads((out / "manifest.json").read_text())["kind"] == "skills"


def test_should_block_live_target_without_allow_live(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    env = dict(os.environ, HOME=str(home))
    live = home / ".claude" / "commands"                    # == lane["live"] unter HOME-Override
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(live)], env=env)
    assert r.returncode != 0
    assert "ABBRUCH" in r.stderr
    assert not live.exists()                                # nichts geschrieben


def test_should_carry_allow_live_in_regenerate_for_live_target(tmp_path):
    """F-D-Regression: Live-Ziel → regenerate-Zeile MUSS --allow-live tragen, sonst
    bricht ihr Copy-Paste am Guard ab."""
    repo = _make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    env = dict(os.environ, HOME=str(home))
    live = home / ".claude" / "skills"
    r = _run(["--kind", "skills", "--platform", str(repo), "--ref", "HEAD",
              "--target", str(live), "--allow-live"], env=env)
    assert r.returncode == 0, r.stderr
    assert "--allow-live" in (live / "MANAGED_BY").read_text()
    # Gegenprobe: ein Nicht-Live-Ziel trägt KEIN --allow-live.
    out = tmp_path / "staging"
    _run(["--kind", "skills", "--platform", str(repo), "--ref", "HEAD", "--target", str(out)], env=env)
    assert "--allow-live" not in (out / "MANAGED_BY").read_text()
