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
    listing = (
        "100644 blob aaa\t.windsurf/workflows/foo.md\n"
        "100644 blob bbb\t.windsurf/workflows/bar.md\n"
    )
    out = gen.collect(listing, "commands")
    assert set(out) == {"foo.md", "bar.md"}
    assert out["foo.md"] == ("aaa", ".windsurf/workflows/foo.md")


def test_should_collect_skills_by_dirname():
    listing = (
        "100644 blob c1\tskills/alpha/SKILL.md\n100644 blob c2\tskills/beta/SKILL.md\n"
    )
    out = gen.collect(listing, "skills")
    assert set(out) == {"alpha", "beta"}
    assert out["alpha"] == ("c1", "skills/alpha/SKILL.md")


def test_should_ignore_non_skill_files_in_skills_lane():
    listing = (
        "100644 blob c1\tskills/alpha/SKILL.md\n"
        "100644 blob c2\tskills/alpha/README.md\n"
    )
    assert set(gen.collect(listing, "skills")) == {"alpha"}


def test_should_ignore_non_md_in_commands_lane():
    listing = (
        "100644 blob c1\t.windsurf/workflows/foo.md\n"
        "100644 blob c2\t.windsurf/workflows/logo.png\n"
    )
    assert set(gen.collect(listing, "commands")) == {"foo.md"}


def test_should_ignore_tree_lines():
    listing = "040000 tree ddd\tskills/alpha\n100644 blob c1\tskills/alpha/SKILL.md\n"
    assert set(gen.collect(listing, "skills")) == {"alpha"}


def test_should_collect_hooks_by_basename():
    listing = (
        "100644 blob h1\ttools/hooks/reap_worktrees.sh\n"
        "100644 blob h2\ttools/hooks/other.sh\n"
        "100644 blob h3\ttools/hooks/notes.md\n"
    )  # nicht .sh → ignoriert
    out = gen.collect(listing, "hooks")
    assert set(out) == {"reap_worktrees.sh", "other.sh"}
    assert out["reap_worktrees.sh"] == ("h1", "tools/hooks/reap_worktrees.sh")


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
        "---\nprovider: openai\ndistribute: false\n---\n# reviewer\nsystem prompt\n"
    )
    (root / "skills" / "bar").mkdir(parents=True)
    (root / "skills" / "bar" / "SKILL.md").write_text("---\nname: bar\n---\n# bar\n")
    # ADR-258 hooks-Lane: Hook-Script-Quelle
    (root / "tools" / "hooks").mkdir(parents=True)
    (root / "tools" / "hooks" / "reap_worktrees.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n"
    )
    # platform#1989 claude-hooks-Lane: flach verteilte Scanner + ein Drill, der
    # NICHT mitverteilt werden darf.
    (root / "tools" / "claude-hooks" / "tests").mkdir(parents=True)
    (root / "tools" / "claude-hooks" / "scanner.py").write_text(
        "#!/usr/bin/env python3\nprint('scan')\n"
    )
    (root / "tools" / "claude-hooks" / "guard.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n"
    )
    (root / "tools" / "claude-hooks" / "notizen.md").write_text("# keine Hook-Datei\n")
    (root / "tools" / "claude-hooks" / "tests" / "test_scanner.py").write_text(
        "def test_x():\n    assert True\n"
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    _git(root, "remote", "add", "origin", str(root))
    _git(root, "fetch", "origin", "main", "-q")
    return root


def _run(args, env=None):
    return subprocess.run(
        [sys.executable, str(_SRC), *args], capture_output=True, text=True, env=env
    )


def test_should_generate_commands_flat(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(out)])
    assert r.returncode == 0, r.stderr
    assert (out / "foo.md").is_file()  # flach
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
    assert (out / "foo.md").is_file()  # normaler Command verteilt
    assert not (out / "_reviewer.md").exists()  # interner System-Prompt NICHT
    m = json.loads((out / "manifest.json").read_text())
    assert m["skill_count"] == 1  # nur foo.md gezählt (nicht len(blobs))
    assert all(f["name"] != "_reviewer.md" for f in m["files"])


def test_should_generate_skills_nested(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    r = _run(
        [
            "--kind",
            "skills",
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--target",
            str(out),
        ]
    )
    assert r.returncode == 0, r.stderr
    assert (out / "bar" / "SKILL.md").is_file()  # verschachtelt <name>/SKILL.md
    assert "MANAGED-BY" in (out / "bar" / "SKILL.md").read_text()
    assert json.loads((out / "manifest.json").read_text())["kind"] == "skills"


def test_should_generate_hooks_flat_executable(tmp_path):
    """ADR-258 hooks-Lane: .sh flach, ausführbar (0755), Shell-#-Footer (kein HTML-Kommentar)."""
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    r = _run(
        [
            "--kind",
            "hooks",
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--target",
            str(out),
        ]
    )
    assert r.returncode == 0, r.stderr
    hook = out / "reap_worktrees.sh"
    assert hook.is_file()  # flach
    assert os.access(hook, os.X_OK)  # ausführbar
    text = hook.read_text()
    assert text.rstrip().endswith("do_not_edit")  # Footer ohne HTML-Kommentar-Klammer
    assert "<!--" not in text  # KEIN HTML-Footer in .sh
    assert "# MANAGED-BY" in text  # Shell-#-Footer
    assert json.loads((out / "manifest.json").read_text())["kind"] == "hooks"


def test_should_not_wipe_sibling_hooks_on_live_swap(tmp_path):
    """REGRESSION (Retro 2026-06-29 F1): die hooks-Lane swappt nur ihr managed/-Ziel —
    hand-gepflegte Geschwister-Hooks in ~/.claude/hooks/ dürfen NICHT weggewischt werden."""
    repo = _make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    env = dict(os.environ, HOME=str(home))
    hooks_dir = home / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    sibling = (
        hooks_dir / "block_stale_branch_commit.sh"
    )  # hand-gepflegt, NICHT lane-verwaltet
    sibling.write_text("#!/usr/bin/env bash\necho guard\n")
    live = hooks_dir / "managed"  # == LANES["hooks"]["live"]
    r = _run(
        [
            "--kind",
            "hooks",
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--target",
            str(live),
            "--allow-live",
        ],
        env=env,
    )
    assert r.returncode == 0, r.stderr
    assert (live / "reap_worktrees.sh").is_file()  # Hook verteilt
    assert sibling.is_file()  # Geschwister ÜBERLEBT (kein Wipe)
    assert sibling.read_text() == "#!/usr/bin/env bash\necho guard\n"


def test_should_block_live_target_without_allow_live(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    env = dict(os.environ, HOME=str(home))
    live = home / ".claude" / "commands"  # == lane["live"] unter HOME-Override
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(live)], env=env)
    assert r.returncode != 0
    assert "ABBRUCH" in r.stderr
    assert not live.exists()  # nichts geschrieben


def test_should_carry_allow_live_in_regenerate_for_live_target(tmp_path):
    """F-D-Regression: Live-Ziel → regenerate-Zeile MUSS --allow-live tragen, sonst
    bricht ihr Copy-Paste am Guard ab."""
    repo = _make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    env = dict(os.environ, HOME=str(home))
    live = home / ".claude" / "skills"
    r = _run(
        [
            "--kind",
            "skills",
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--target",
            str(live),
            "--allow-live",
        ],
        env=env,
    )
    assert r.returncode == 0, r.stderr
    assert "--allow-live" in (live / "MANAGED_BY").read_text()
    # Gegenprobe: ein Nicht-Live-Ziel trägt KEIN --allow-live.
    out = tmp_path / "staging"
    _run(
        [
            "--kind",
            "skills",
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--target",
            str(out),
        ],
        env=env,
    )
    assert "--allow-live" not in (out / "MANAGED_BY").read_text()


# ------------------------------------------------- Swap-Ziel-Guard (Realfall 2026-07-30)
def test_should_refuse_parent_directory_as_target(tmp_path):
    """`--target ~/.claude` statt `~/.claude/commands` darf NICHT durchlaufen.

    Realfall 2026-07-30: der atomare Swap schob das ganze `~/.claude` nach `.bak`
    und legte ein neues mit 51 flachen Dateien an — `commands/`, `policies/`,
    `hooks/`, `bin/`, `mail-*.env` und 41 Session-Verzeichnisse waren weg. Der
    `--allow-live`-Guard griff nicht: er prüft Gleichheit mit dem Live-Pfad, und
    das Elternverzeichnis ist nicht der Pfad selbst.
    """
    repo = _make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    eltern = home / ".claude"
    (eltern / "commands").mkdir(parents=True)
    (eltern / "commands" / "alt.md").write_text("bestehender Command")
    (eltern / "policies").mkdir()
    (eltern / "settings.json").write_text("{}")
    env = dict(os.environ, HOME=str(home))

    r = _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--target",
            str(eltern),
            "--allow-live",
        ],
        env=env,
    )
    assert r.returncode != 0
    assert "ABBRUCH" in r.stderr
    # Der Hinweis muss den gemeinten Pfad nennen, sonst hilft er nicht weiter.
    assert str(eltern / "commands") in r.stderr
    # Und nichts darf angefasst worden sein:
    assert (eltern / "commands" / "alt.md").is_file()
    assert (eltern / "settings.json").is_file()
    assert not (home / ".claude.bak").exists()


def test_should_allow_target_from_previous_run(tmp_path):
    """Ein Ziel mit MANAGED_BY ist ein Generator-Ziel — zweiter Lauf muss gehen."""
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    assert (
        _run(
            ["--platform", str(repo), "--ref", "HEAD", "--target", str(out)]
        ).returncode
        == 0
    )
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(out)])
    assert r.returncode == 0, r.stderr
    assert (out / "foo.md").is_file()


def test_should_allow_empty_existing_target(tmp_path):
    """Ein leeres, vorab angelegtes Staging-Verzeichnis ist kein Fremdverzeichnis."""
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "leer"
    out.mkdir()
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(out)])
    assert r.returncode == 0, r.stderr


# --- Guard gegen das eigene Unfall-Residuum (Retro-Befund 2026-07-31) -------


def _residuum_ziel(tmp_path, eigene_dateien, fremde_eintraege):
    """Verzeichnis mit Manifest + optional fremden Einträgen bauen."""
    ziel = tmp_path / "claude"
    ziel.mkdir()
    for name in eigene_dateien:
        (ziel / name).write_text("x")
    for name in fremde_eintraege:
        (ziel / name).mkdir() if name.endswith("/") else (ziel / name).write_text("x")
    (ziel / "MANAGED_BY").write_text("x")
    (ziel / "manifest.json").write_text(
        json.dumps({"files": [{"name": n} for n in eigene_dateien]})
    )
    return ziel


def test_should_refuse_target_with_manifest_but_foreign_entries(tmp_path):
    """Der Unfall schreibt MANAGED_BY/manifest.json ins FALSCHE Verzeichnis.

    Blieben sie liegen, hätte die reine Namens-Prüfung denselben Tippfehler beim
    zweiten Mal durchgewinkt — ein Guard, dessen Erkennungsmerkmal der Fehler
    selbst erzeugt, schützt nur einmal.
    """
    repo = _make_repo(tmp_path / "repo")
    ziel = _residuum_ziel(tmp_path, ["foo.md"], ["settings.json", "policies"])
    r = _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--target",
            str(ziel),
            "--allow-live",
        ]
    )
    assert r.returncode != 0
    assert "ABBRUCH" in r.stderr
    assert "settings.json" in r.stderr or "policies" in r.stderr
    assert (ziel / "settings.json").is_file()  # nichts angefasst
    assert not (tmp_path / "claude.bak").exists()


def test_should_allow_target_whose_content_matches_manifest(tmp_path):
    """Echter Zweitlauf: alles im Ziel steht im Manifest → darf durchlaufen."""
    repo = _make_repo(tmp_path / "repo")
    ziel = _residuum_ziel(tmp_path, ["foo.md"], [])
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(ziel)])
    assert r.returncode == 0, r.stderr


def test_should_refuse_managed_by_without_manifest(tmp_path):
    """Ohne Manifest ist der Inhalt nicht prüfbar — kein Freibrief."""
    repo = _make_repo(tmp_path / "repo")
    ziel = tmp_path / "halb"
    ziel.mkdir()
    (ziel / "MANAGED_BY").write_text("x")
    (ziel / "fremd.txt").write_text("x")
    r = _run(["--platform", str(repo), "--ref", "HEAD", "--target", str(ziel)])
    assert r.returncode != 0
    assert "nicht gegen die Generator-Dateiliste prüfbar" in r.stderr


# --------------------------------------------- claude-hooks-Lane (platform#1989)
# Der Merge-Modus existiert, weil ~/.claude/hooks/ dem Generator NICHT allein
# gehoert: dort liegen hand-gepflegte Hooks, Zustand, eine zweite Lane und das
# Treffer-Protokoll. Ein Swap wuerde sie loeschen. Die Drills pruefen deshalb
# vor allem, was NICHT passiert.


def test_should_distribute_py_and_sh_but_not_other_suffixes(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    r = _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    assert r.returncode == 0, r.stderr
    assert (out / "scanner.py").is_file()
    assert (out / "guard.sh").is_file()
    assert not (out / "notizen.md").exists(), "nur .py/.sh gehoeren in den Hook-Pfad"


def test_should_never_distribute_the_drills(tmp_path):
    """Ein Testfile im aktiven Hook-Pfad liefe bei JEDEM Stop-Event mit."""
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    assert not (out / "test_scanner.py").exists()
    assert not (out / "tests").exists()


def test_should_not_delete_foreign_entries_in_the_shared_target(tmp_path):
    """Der Kern des Merge-Modus. Faellt dieser Test um, loescht die Lane fremde Hooks."""
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    out.mkdir()
    (out / "inject_policies.py").write_text("# hand-gepflegt\n")
    (out / "gate-hits.jsonl").write_text('{"a":1}\n')
    (out / "state").mkdir()
    (out / "state" / "x.json").write_text("{}\n")
    (out / "managed").mkdir()

    r = _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    assert r.returncode == 0, r.stderr
    assert (out / "inject_policies.py").read_text() == "# hand-gepflegt\n"
    assert (out / "gate-hits.jsonl").read_text() == '{"a":1}\n'
    assert (out / "state" / "x.json").is_file()
    assert (out / "managed").is_dir()
    assert (out / "scanner.py").is_file(), "und die Lane hat trotzdem geschrieben"


def test_should_back_up_only_what_it_really_replaced(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    out.mkdir()
    (out / "scanner.py").write_text("#!/usr/bin/env python3\nprint('ALT')\n")
    r = _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    assert r.returncode == 0, r.stderr
    sicherungen = list(out.glob(".cc-dist-backup-*/scanner.py"))
    assert sicherungen, "die ersetzte Fassung ist der einzige Zeuge dessen, was lief"
    assert "ALT" in sicherungen[0].read_text()
    assert "scan" in (out / "scanner.py").read_text()


def test_should_not_create_an_empty_backup_on_a_no_op_run(tmp_path):
    """Zweitlauf ohne Aenderung darf kein Backup-Rauschen erzeugen."""
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    vorher = set(p.name for p in out.iterdir())
    _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    assert set(p.name for p in out.iterdir()) == vorher


def test_should_write_a_dotfile_manifest_not_the_swap_lane_name(tmp_path):
    """`manifest.json` im gemischten Ziel waere ein Fehlsignal fuer pruefe_swap_ziel."""
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    assert (out / ".cc-skill-dist-manifest.json").is_file()
    assert not (out / "manifest.json").exists()
    assert not (out / "MANAGED_BY").exists()


def test_should_make_distributed_hooks_executable(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    assert os.stat(out / "scanner.py").st_mode & 0o111


def test_should_footer_python_hooks_as_comment_not_html(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    out = tmp_path / "out"
    _run(
        [
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--kind",
            "claude-hooks",
            "--target",
            str(out),
        ]
    )
    inhalt = (out / "scanner.py").read_text()
    assert "# MANAGED-BY" in inhalt
    assert "<!--" not in inhalt, "HTML-Kommentar waere in .py ein Syntaxfehler"
    compile(inhalt, "scanner.py", "exec")  # muss weiterhin gueltiges Python sein
