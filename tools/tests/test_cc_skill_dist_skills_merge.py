"""Drill fuer platform#3467 — Lane `skills` von `mode: swap` auf `mode: merge`.

Realfall (Issue #3467, Session-Melder 0.7.13 seit 2026-09-23): `~/.claude/skills` ist seit
dem claude.ai-Skill-Sync (2026-09-17) ein Mischverzeichnis — `synced/<bucket-id>/` +
`.bucket-*`-Marker liegen dort, dazu ein altes `MANAGED_BY` aus dem frueheren SWAP-Regime
(ohne `manifest.json`). Der Swap-Guard `pruefe_swap_ziel` brach deshalb zu Recht ab: ein
atomarer Verzeichnistausch haette `synced/` weggewischt. Die Lane `skills` laeuft seither im
Modus `merge` (Vorbild `claude-hooks`, #1989) — dieser Drill deckt genau den Uebergang:

(a) Ein altes Swap-Ziel MIT Fremdinhalt (`synced/`) UND Alt-`MANAGED_BY` (ohne
    `manifest.json`) laesst den Generator trotzdem durchlaufen — `synced/` bleibt
    unangetastet liegen, die Skill-Kopie wird aktualisiert.
(b) `doctor.py --kind skills` misst danach DRIFT-SCORE 0 — `synced/` ist dabei KEIN Befund
    (Parität zu #1508 bei `claude-hooks`).
(c) Die Swap-Guard-Drills der Nachbar-Lanes (`commands`, weiterhin `mode: swap`) bleiben von
    der Umstellung unberuehrt — ein Fremdverzeichnis dort wird weiterhin blockiert.

Run: `python3 -m pytest tools/tests/test_cc_skill_dist_skills_merge.py -q`
"""

import importlib.util
import json
import pathlib
import subprocess
import sys

_GEN = pathlib.Path(__file__).resolve().parents[1] / "cc-skill-dist" / "generate.py"
_DOC = pathlib.Path(__file__).resolve().parents[1] / "cc-skill-dist" / "doctor.py"

_spec_gen = importlib.util.spec_from_file_location("generate", _GEN)
gen = importlib.util.module_from_spec(_spec_gen)
_spec_gen.loader.exec_module(gen)


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _make_skills_repo(root, names=("schreibstil",)):
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    for n in names:
        (root / "skills" / n).mkdir(parents=True)
        (root / "skills" / n / "SKILL.md").write_text(f"---\nname: {n}\n---\n# {n}\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    _git(root, "remote", "add", "origin", str(root))
    _git(root, "fetch", "origin", "main", "-q")
    return root


def _generate(repo, target, kind="skills", extra=()):
    return subprocess.run(
        [
            sys.executable,
            str(_GEN),
            "--kind",
            kind,
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--target",
            str(target),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def _doctor_skills(repo, skills_dir):
    return subprocess.run(
        [
            sys.executable,
            str(_DOC),
            "--kind",
            "skills",
            "--platform",
            str(repo),
            "--ref",
            "HEAD",
            "--skills-dir",
            str(skills_dir),
        ],
        capture_output=True,
        text=True,
    )


def _score(stdout):
    line = next(ln for ln in stdout.splitlines() if "DRIFT-SCORE:" in ln)
    return int(line.split("DRIFT-SCORE:")[1].split()[0])


def _mischverzeichnis(tmp_path, name="schreibstil", stale_body="# alt\n"):
    """Realfall-Fixture: altes Swap-Ziel + claude.ai-Skill-Sync-Fremdinhalt.

    `synced/<bucket-id>/` + `.bucket-*` bilden den Sync-Fremdinhalt nach; `MANAGED_BY`
    ohne `manifest.json` bildet das alte Swap-Regime nach (genau der ABBRUCH-Fall aus
    dem Issue-Text)."""
    ziel = tmp_path / "skills"
    ziel.mkdir()
    (ziel / name).mkdir()
    (ziel / name / "SKILL.md").write_text(stale_body)
    (ziel / "MANAGED_BY").write_text(
        "managed_by: platform/tools/cc-skill-dist/generate.py (kind=skills)\n"
        "source: achimdehnert/platform @ deadbeef0000\n"
    )
    bucket = "676bd685-3bb0-4289-a58d-f181ce8b2d34_37096e48-dcee-49a7-b680-e7ee34181d4a"
    (ziel / "synced" / bucket).mkdir(parents=True)
    (ziel / "synced" / bucket / "eigenes-zeug.md").write_text("# claude.ai-Sync\n")
    (ziel / f".bucket-{bucket}").write_text("")
    return ziel


# --------------------------------------------------------------- (a) generate laeuft durch
def test_should_generate_through_mixed_target_with_synced_and_legacy_managed_by(
    tmp_path,
):
    repo = _make_skills_repo(tmp_path / "repo")
    ziel = _mischverzeichnis(tmp_path)

    r = _generate(repo, ziel)
    assert r.returncode == 0, r.stdout + r.stderr

    # synced/ + Marker unangetastet
    bucket = "676bd685-3bb0-4289-a58d-f181ce8b2d34_37096e48-dcee-49a7-b680-e7ee34181d4a"
    assert (
        ziel / "synced" / bucket / "eigenes-zeug.md"
    ).read_text() == "# claude.ai-Sync\n"
    assert (ziel / f".bucket-{bucket}").exists()

    # Skill-Kopie aktualisiert (nicht mehr der alte "# alt\n"-Stand)
    inhalt = (ziel / "schreibstil" / "SKILL.md").read_text()
    assert "# alt" not in inhalt
    assert "MANAGED-BY" in inhalt

    # Merge-Manifest geschrieben, altes Swap-Regime aufgeraeumt
    assert (ziel / ".cc-skill-dist-manifest.json").is_file()
    assert not (ziel / "MANAGED_BY").exists()
    assert not (ziel / "manifest.json").exists()


def test_should_report_merge_mode_not_swap_on_stdout(tmp_path):
    repo = _make_skills_repo(tmp_path / "repo")
    ziel = _mischverzeichnis(tmp_path)
    r = _generate(repo, ziel)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "merge" in r.stdout
    assert "kein Verzeichnis-Swap" in r.stdout


# --------------------------------------------------------------------- (b) doctor DRIFT 0
def test_should_measure_drift_score_zero_after_merge_run_with_synced_present(tmp_path):
    repo = _make_skills_repo(tmp_path / "repo")
    ziel = _mischverzeichnis(tmp_path)
    _generate(repo, ziel)

    r = _doctor_skills(repo, ziel)
    assert "DRIFT-SCORE: 0" in r.stdout, r.stdout
    assert r.returncode == 0, r.stdout + r.stderr
    # synced/ ist KEIN Befund (Parität zu claude-hooks, #1508)
    assert "synced" not in r.stdout


def test_should_still_detect_real_drift_with_synced_present(tmp_path):
    """Die Fremd-Toleranz darf nicht blind machen fuer echte Drift an EIGENEN Skills."""
    repo = _make_skills_repo(tmp_path / "repo")
    ziel = _mischverzeichnis(tmp_path)
    _generate(repo, ziel)

    (ziel / "schreibstil" / "SKILL.md").write_text("MANIPULIERT\n")

    r = _doctor_skills(repo, ziel)
    assert "DRIFT-SCORE: 0" not in r.stdout
    assert "copy-stale" in r.stdout, r.stdout
    assert r.returncode == 1


def test_should_add_a_second_skill_without_touching_synced(tmp_path):
    """Mehrere kanonische Skills, nur einer stand schon im Mischverzeichnis — der
    Generator ergaenzt den fehlenden, ruehrt `synced/` dabei nicht an."""
    repo = _make_skills_repo(tmp_path / "repo", names=("schreibstil", "next"))
    ziel = _mischverzeichnis(tmp_path)  # traegt nur "schreibstil" als Alt-Kopie

    r = _generate(repo, ziel)
    assert r.returncode == 0, r.stdout + r.stderr

    assert (ziel / "next" / "SKILL.md").is_file()
    bucket = "676bd685-3bb0-4289-a58d-f181ce8b2d34_37096e48-dcee-49a7-b680-e7ee34181d4a"
    assert (ziel / "synced" / bucket / "eigenes-zeug.md").is_file()

    doc = _doctor_skills(repo, ziel)
    assert "DRIFT-SCORE: 0" in doc.stdout, doc.stdout


# --------------------------------------------------------- (c) Swap-Guard-Nachbarn bleiben gruen
def _make_commands_repo(root):
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    (root / ".windsurf" / "workflows").mkdir(parents=True)
    (root / ".windsurf" / "workflows" / "foo.md").write_text("# foo\nbody\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    _git(root, "remote", "add", "origin", str(root))
    _git(root, "fetch", "origin", "main", "-q")
    return root


def test_should_still_block_swap_lane_on_foreign_directory(tmp_path):
    """`commands` bleibt `mode: swap` — ein Fremdverzeichnis im Ziel blockiert weiterhin
    (die Umstellung der `skills`-Lane darf die Nachbar-Lane nicht mitziehen)."""
    repo = _make_commands_repo(tmp_path / "repo")
    ziel = tmp_path / "commands"
    ziel.mkdir()
    (ziel / "fremd").mkdir()  # kein MANAGED_BY/manifest.json → sofortiger Fremd-Abbruch

    r = _generate(repo, ziel, kind="commands")
    assert r.returncode != 0
    assert "ABBRUCH" in r.stderr


def test_should_confirm_skills_lane_mode_is_merge():
    assert gen.lane_mode("skills") == "merge"
    assert gen.lane_mode("commands") == "swap"  # Gegenprobe: Nachbarn unveraendert
    assert gen.lane_mode("hooks") == "swap"
    assert gen.lane_mode("claude-hooks") == "merge"


# ----------------------------------------------------------- doctor: enumerate_skills_merge_lane
def _load_doctor():
    spec = importlib.util.spec_from_file_location("doctor", _DOC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_should_ignore_synced_dir_in_merge_lane_enumeration(tmp_path):
    doc = _load_doctor()
    ziel = _mischverzeichnis(tmp_path)
    manifest = {
        "files": [{"name": "schreibstil", "source_path": "skills/schreibstil/SKILL.md"}]
    }
    (ziel / doc.MERGE_MANIFEST).write_text(json.dumps(manifest))
    out = doc.enumerate_skills_merge_lane(str(ziel))
    assert set(out) == {"schreibstil"}  # synced/ + Bucket-Marker NICHT enthalten


def test_should_return_empty_without_merge_manifest():
    doc = _load_doctor()
    assert doc.enumerate_skills_merge_lane("/nonexistent/xyz/123") == {}
