"""Tests für die drei ADR-265-Guards in scripts/gen_project_facts.py::gen_facts().

Kontext (Issue #931): gen_facts() ist neben scripts/sync-workflows.sh (#907,
getestet seit #950) ein zweiter Distributor von GLOBAL_RULES-Symlinks +
run-*.md-Workflow-Kopien — lief bisher aber OHNE die drei ADR-265-Guards.
Folgen (2026-07-04 reproduziert): Typechanges in platform-pinned (SSoT-Skip
fehlte, Namensvergleich `repo != "platform"` verfehlt Pins/Worktrees), ??-
Symlink-Noise in Repos ohne wirksamen `.windsurf/`-Ignore (Ignore-Guard
fehlte), leere `.windsurf/`-Dirs in geskippten Repos (mkdir lief vor jedem
Guard).

Diese Tests bauen echte, temporäre Git-Repos unter tmp_path (kein Netz, kein
echter Fleet-Lauf) und rufen `gen_facts()` read-only-artig gegen diese
Fixtures auf — GITHUB/WORKFLOWS_SRC/RULES_SRC werden je Test auf
tmp_path-Fixtures umgebogen (monkeypatch), damit niemals der echte
~/github-Baum berührt wird.

Liegt unter tools/tests/ (nicht repo-root tests/) — der generische
`tools-tests.yml`-Gate deckt scripts/** + tools/** mit ab.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "gen_project_facts.py"
_spec = importlib.util.spec_from_file_location("gen_project_facts_guards_test", _SCRIPT)
gpf = importlib.util.module_from_spec(_spec)
sys.modules["gen_project_facts_guards_test"] = gpf
_spec.loader.exec_module(gpf)


def _git(repo_path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo_path), *args], check=True, capture_output=True)


def _init_repo(repo_path: Path, origin: str | None = None, ignore_windsurf: bool = False) -> None:
    repo_path.mkdir(parents=True, exist_ok=True)
    _git(repo_path, "init", "-q")
    _git(repo_path, "config", "user.email", "test@example.com")
    _git(repo_path, "config", "user.name", "Test")
    if ignore_windsurf:
        (repo_path / ".gitignore").write_text(".windsurf/\n")
        _git(repo_path, "add", ".gitignore")
        _git(repo_path, "commit", "-q", "-m", "init")
    if origin is not None:
        _git(repo_path, "remote", "add", "origin", origin)


def _make_rules_and_workflows_src(base: Path) -> tuple[Path, Path]:
    """Fixture-SSoT analog platform/.windsurf/{rules,workflows} — nur die
    Dateien, die für die Tests gebraucht werden."""
    rules_src = base / "platform-src" / "rules"
    wf_src = base / "platform-src" / "workflows"
    rules_src.mkdir(parents=True)
    wf_src.mkdir(parents=True)
    (rules_src / "mcp-tools.md").write_text("SSoT mcp-tools content\n")
    (rules_src / "reviewer.md").write_text("SSoT reviewer content\n")
    for wf in ("run-local.md", "run-staging.md", "run-prod.md"):
        (wf_src / wf).write_text(f"SSoT {wf} content\n")
    return rules_src, wf_src


def _patch_sources(monkeypatch, tmp_path: Path, rules_src: Path, wf_src: Path) -> None:
    # gen_facts() rechnet `repo_path = GITHUB / repo` — GITHUB muss auf die
    # tmp_path-Fixture zeigen, sonst landet jeder Aufruf im echten ~/github.
    monkeypatch.setattr(gpf, "GITHUB", tmp_path)
    monkeypatch.setattr(gpf, "RULES_SRC", rules_src)
    monkeypatch.setattr(gpf, "WORKFLOWS_SRC", wf_src)
    monkeypatch.setattr(gpf, "GLOBAL_RULES", ["mcp-tools.md", "reviewer.md"])


# ── Guard 1: SSoT-Skip per git-ORIGIN ────────────────────────────────────────

def test_should_skip_entirely_when_origin_is_platform(tmp_path, monkeypatch):
    """origin endet auf /platform(.git) → Repo komplett unberührt lassen,
    auch project-facts.md wird NICHT geschrieben (deckt platform-pinned ab,
    das der Namensvergleich `repo != "platform"` verfehlt)."""
    rules_src, wf_src = _make_rules_and_workflows_src(tmp_path)
    _patch_sources(monkeypatch, tmp_path, rules_src, wf_src)

    repo_path = tmp_path / "platform-pinned"
    _init_repo(repo_path, origin="git@github.com:achimdehnert/platform.git")

    result = gpf.gen_facts("platform-pinned", {}, force=False)

    assert "SKIP" in result
    assert not (repo_path / ".windsurf").exists(), (
        "SSoT-Skip darf gar kein .windsurf/ anlegen — auch keine leere Rules-Dir"
    )


def test_should_skip_when_origin_is_platform_https_no_git_suffix(tmp_path, monkeypatch):
    """Auch ohne .git-Suffix (https-Remote) muss der Origin-Check greifen."""
    rules_src, wf_src = _make_rules_and_workflows_src(tmp_path)
    _patch_sources(monkeypatch, tmp_path, rules_src, wf_src)

    repo_path = tmp_path / "platform"
    _init_repo(repo_path, origin="https://github.com/achimdehnert/platform")

    result = gpf.gen_facts("platform", {}, force=False)

    assert "SKIP" in result
    assert not (repo_path / ".windsurf").exists()


# ── Guard 2: Ignore-Guard ────────────────────────────────────────────────────

def test_should_skip_distribution_when_windsurf_not_gitignored(tmp_path, monkeypatch):
    """Ohne wirksamen `.windsurf/`-Ignore darf gen_facts() weder Rules-Symlinks
    noch Workflow-Kopien anlegen (verhindert ??-Noise). project-facts.md
    bleibt legitimer Per-Repo-Inhalt und wird trotzdem geschrieben."""
    rules_src, wf_src = _make_rules_and_workflows_src(tmp_path)
    _patch_sources(monkeypatch, tmp_path, rules_src, wf_src)

    repo_path = tmp_path / "some-hub"
    _init_repo(repo_path, origin="git@github.com:achimdehnert/some-hub.git", ignore_windsurf=False)

    result = gpf.gen_facts("some-hub", {}, force=False)

    assert result.startswith("✅")
    facts_file = repo_path / ".windsurf" / "rules" / "project-facts.md"
    assert facts_file.exists(), "project-facts.md ist Per-Repo-Inhalt und bleibt vom Ignore-Guard unberührt"

    # Keine Distribution: weder Workflow-Kopien noch Rules-Symlinks
    assert not (repo_path / ".windsurf" / "workflows").exists(), (
        "Ohne Ignore-Guard darf .windsurf/workflows/ gar nicht erst angelegt werden"
    )
    for rule in ("mcp-tools.md", "reviewer.md"):
        assert not (repo_path / ".windsurf" / "rules" / rule).exists(), (
            f"Ohne Ignore-Guard darf kein Symlink für {rule} entstehen"
        )
    # .windsurf/rules darf ausschließlich project-facts.md enthalten
    assert sorted(p.name for p in (repo_path / ".windsurf" / "rules").iterdir()) == [
        "project-facts.md"
    ]


def test_should_distribute_when_windsurf_is_gitignored(tmp_path, monkeypatch):
    """Positiv-Kontrolle: MIT wirksamem Ignore laufen Workflow-Kopien +
    Rules-Symlinks wie gewohnt."""
    rules_src, wf_src = _make_rules_and_workflows_src(tmp_path)
    _patch_sources(monkeypatch, tmp_path, rules_src, wf_src)

    repo_path = tmp_path / "other-hub"
    _init_repo(repo_path, origin="git@github.com:achimdehnert/other-hub.git", ignore_windsurf=True)

    result = gpf.gen_facts("other-hub", {}, force=False)

    assert result.startswith("✅")
    assert (repo_path / ".windsurf" / "workflows" / "run-local.md").exists()
    link = repo_path / ".windsurf" / "rules" / "mcp-tools.md"
    assert link.is_symlink()
    assert link.resolve() == (rules_src / "mcp-tools.md").resolve()


# ── --dry-run Safety-Guard (#931-Abnahme, Incident 2026-07-05) ────────────────

def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    """--dry-run darf KEINERLEI Schreib-/mkdir-/Symlink-Operation ausführen —
    Schutz gegen versehentliche Fleet-Writes (der Incident 2026-07-05 entstand,
    weil ein `--help`-Aufruf auf einen echten Vollauf durchfiel)."""
    rules_src, wf_src = _make_rules_and_workflows_src(tmp_path)
    _patch_sources(monkeypatch, tmp_path, rules_src, wf_src)

    repo_path = tmp_path / "dry-hub"
    _init_repo(repo_path, origin="git@github.com:achimdehnert/dry-hub.git", ignore_windsurf=True)

    result = gpf.gen_facts("dry-hub", {}, force=True, dry_run=True)

    assert result.startswith("DRY-RUN")
    # Nichts angefasst: kein .windsurf/, keine project-facts.md, keine Symlinks.
    assert not (repo_path / ".windsurf").exists(), (
        "--dry-run darf nicht einmal .windsurf/ anlegen"
    )


def test_help_flag_does_not_run_fleet(tmp_path):
    """`--help` muss VOR jeder Registry-/Schreiboperation abbrechen (Exit 0,
    Usage) — nicht auf einen Fleet-Lauf durchfallen (Root-Cause des Incidents)."""
    env = dict(os.environ)
    env["GITHUB_DIR"] = str(tmp_path)  # leerer Sandbox-Fleet-Dir
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert r.returncode == 0
    assert "Usage:" in r.stdout and "--dry-run" in r.stdout
    assert "=== Done" not in r.stdout, "--help darf keinen Generierungslauf starten"


# ── Guard 3: Tracked-Guard ───────────────────────────────────────────────────

def test_should_not_replace_tracked_rule_file_with_symlink(tmp_path, monkeypatch):
    """Eine im Ziel-Repo-Index getrackte Rules-Datei darf NIE durch einen
    Symlink ersetzt werden (permanenter Typechange-Dirt). Andere,
    ungetrackte Rules werden weiterhin normal gesynct."""
    rules_src, wf_src = _make_rules_and_workflows_src(tmp_path)
    _patch_sources(monkeypatch, tmp_path, rules_src, wf_src)

    repo_path = tmp_path / "tracked-hub"
    _init_repo(repo_path, origin="git@github.com:achimdehnert/tracked-hub.git", ignore_windsurf=True)

    tracked_rule = repo_path / ".windsurf" / "rules" / "mcp-tools.md"
    tracked_rule.parent.mkdir(parents=True, exist_ok=True)
    tracked_rule.write_text("REPO-EIGENE Version — bewusst abweichend\n")
    _git(repo_path, "add", "-f", ".windsurf/rules/mcp-tools.md")
    _git(repo_path, "commit", "-q", "-m", "tracked own rule")

    result = gpf.gen_facts("tracked-hub", {}, force=False)

    assert result.startswith("✅")
    assert not tracked_rule.is_symlink(), "getrackte Datei darf nicht durch Symlink ersetzt werden"
    assert tracked_rule.read_text() == "REPO-EIGENE Version — bewusst abweichend\n"

    # Die NICHT getrackte zweite Rule wird ganz normal gesynct (Guard ist
    # selektiv, kein Blanket-Skip des ganzen Repos).
    other_link = repo_path / ".windsurf" / "rules" / "reviewer.md"
    assert other_link.is_symlink()
    assert other_link.resolve() == (rules_src / "reviewer.md").resolve()


def test_should_not_overwrite_tracked_workflow_copy(tmp_path, monkeypatch):
    """Tracked-Guard auch auf dem Kopie-Pfad: eine im Ziel-Repo getrackte
    reguläre run-*.md darf NICHT via shutil.copy2 überschrieben werden —
    genau dieser Pfad überschrieb im Incident 2026-07-05 billing-hub."""
    rules_src, wf_src = _make_rules_and_workflows_src(tmp_path)
    _patch_sources(monkeypatch, tmp_path, rules_src, wf_src)

    repo_path = tmp_path / "wf-tracked-hub"
    _init_repo(repo_path, origin="git@github.com:achimdehnert/wf-tracked-hub.git", ignore_windsurf=True)

    tracked_wf = repo_path / ".windsurf" / "workflows" / "run-local.md"
    tracked_wf.parent.mkdir(parents=True, exist_ok=True)
    tracked_wf.write_text("REPO-EIGENE run-local — bewusst abweichend\n")
    _git(repo_path, "add", "-f", ".windsurf/workflows/run-local.md")
    _git(repo_path, "commit", "-q", "-m", "tracked own run-local")

    result = gpf.gen_facts("wf-tracked-hub", {}, force=False)

    assert result.startswith("✅")
    assert tracked_wf.read_text() == "REPO-EIGENE run-local — bewusst abweichend\n", (
        "getrackte run-*.md darf nicht durch die Distribution überschrieben werden"
    )
    # Eine NICHT getrackte run-*.md wird normal kopiert (Guard selektiv).
    other_wf = repo_path / ".windsurf" / "workflows" / "run-prod.md"
    assert other_wf.exists() and not other_wf.is_symlink()


def test_should_replace_symlink_pointing_elsewhere_even_if_untracked(tmp_path, monkeypatch):
    """Ein bereits existierender (aber falscher) Symlink ist per Definition
    nicht 'getrackt wie eine reguläre Datei' im Tracked-Guard-Sinn — er wird
    weiterhin korrigiert (kein Typechange, da schon ein Symlink)."""
    rules_src, wf_src = _make_rules_and_workflows_src(tmp_path)
    _patch_sources(monkeypatch, tmp_path, rules_src, wf_src)

    repo_path = tmp_path / "stale-link-hub"
    _init_repo(repo_path, origin="git@github.com:achimdehnert/stale-link-hub.git", ignore_windsurf=True)

    rules_dest = repo_path / ".windsurf" / "rules"
    rules_dest.mkdir(parents=True, exist_ok=True)
    stale_target = tmp_path / "somewhere-else.md"
    stale_target.write_text("elsewhere\n")
    (rules_dest / "mcp-tools.md").symlink_to(stale_target)

    gpf.gen_facts("stale-link-hub", {}, force=False)

    link = rules_dest / "mcp-tools.md"
    assert link.is_symlink()
    assert link.resolve() == (rules_src / "mcp-tools.md").resolve()
