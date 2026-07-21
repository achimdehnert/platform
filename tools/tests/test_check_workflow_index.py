"""Tests für check_workflow_index.py — Vollständigkeits-Gate Workflow-Index (#901 Spec B).

Deckt: Wortgrenze (/adr matcht nicht /adr-review), Allowlist, distribute:false-Ausnahme,
fehlender Skill → gemeldet, plus ein Live-Check gegen den echten Repo-Index (muss grün sein).

Run: `python3 -m pytest tools/tests/test_check_workflow_index.py -q`
"""
import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "check_workflow_index.py"
_spec = importlib.util.spec_from_file_location("cwi", _SRC)
cwi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cwi)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _wf(root, name, body="# body\n"):
    d = root / ".windsurf" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.md").write_text("---\ndescription: x\n---\n\n" + body)
    return d


def test_should_respect_word_boundary_between_commands():
    text = "| ADR reviewen | `/adr-review` |\n"
    # /adr darf NICHT über /adr-review als indexiert gelten
    assert cwi.command_indexed("adr-review", text) is True
    assert cwi.command_indexed("adr", text) is False


def test_should_match_plain_slash_command():
    text = "ADR anlegen | `/adr` |\n"
    assert cwi.command_indexed("adr", text) is True


def test_should_pass_when_all_skills_indexed(tmp_path):
    d = _wf(tmp_path, "session-start")
    _wf(tmp_path, "ship")
    index = d / "workflow-index.md"
    index.write_text("start `/session-start`, deploy `/ship`\n")
    missing, checked = cwi.check(str(d), str(index), allowlist=set())
    assert missing == []
    assert set(checked) == {"session-start", "ship"}


def test_should_report_missing_skill(tmp_path):
    d = _wf(tmp_path, "session-start")
    _wf(tmp_path, "orphan-skill")
    index = d / "workflow-index.md"
    index.write_text("only `/session-start` is here\n")
    missing, _ = cwi.check(str(d), str(index), allowlist=set())
    assert missing == ["orphan-skill"]


def test_should_honor_allowlist(tmp_path):
    d = _wf(tmp_path, "session-start")
    _wf(tmp_path, "internal-thing")
    index = d / "workflow-index.md"
    index.write_text("only `/session-start`\n")
    missing, checked = cwi.check(str(d), str(index), allowlist={"internal-thing"})
    assert missing == []
    assert "internal-thing" not in checked


def test_should_skip_distribute_false_workflows(tmp_path):
    d = _wf(tmp_path, "session-start")
    (d / "persona.md").write_text("---\ndistribute: false\ndescription: x\n---\n")
    index = d / "workflow-index.md"
    index.write_text("only `/session-start`\n")
    missing, checked = cwi.check(str(d), str(index), allowlist=set())
    assert missing == []
    assert "persona" not in checked


def test_should_have_complete_live_repo_index():
    """Der echte platform workflow-index.md muss jeden verteilten Skill referenzieren.

    Prüft BEIDE Lanes — ohne `skills_dir` wäre dieser Live-Test für migrierte
    Agent-Skills blind und bliebe grün, während die Deckung fehlt (#1287).
    """
    wf_dir = _REPO_ROOT / ".windsurf" / "workflows"
    index = wf_dir / "workflow-index.md"
    missing, checked = cwi.check(
        str(wf_dir), str(index),
        allowlist={"onboard-repo-testing-addendum"},
        skills_dir=str(_REPO_ROOT / "skills"),
    )
    assert missing == [], f"Skills fehlen im Index: {missing}"
    assert checked, "keine Skills geprüft — Pfad falsch?"


# ── Lane 2: Agent-Skills (skills/<name>/SKILL.md) ────────────────────────────

def _skill(root, name):
    d = root / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n\n# body\n")
    return root / "skills"


def test_should_report_missing_agent_skill(tmp_path):
    """Ein nach skills/ migrierter Skill ohne Index-Eintrag muss auffallen."""
    d = _wf(tmp_path, "irgendwas")
    _skill(tmp_path, "nur-in-skills")
    index = d / "workflow-index.md"
    index.write_text("| x | `/irgendwas` |\n")
    missing, checked = cwi.check(
        str(d), str(index), allowlist=set(), skills_dir=str(tmp_path / "skills"),
    )
    assert missing == ["nur-in-skills"]
    assert "nur-in-skills" in checked


def test_should_pass_when_agent_skill_is_indexed(tmp_path):
    d = _wf(tmp_path, "irgendwas")
    _skill(tmp_path, "migriert")
    index = d / "workflow-index.md"
    index.write_text("| x | `/irgendwas` |\n| y | `/migriert` |\n")
    missing, checked = cwi.check(
        str(d), str(index), allowlist=set(), skills_dir=str(tmp_path / "skills"),
    )
    assert missing == []
    assert "migriert" in checked


def test_should_not_double_count_name_present_in_both_lanes(tmp_path):
    """Während der Migration kann ein Name kurzzeitig in beiden Lanes liegen."""
    d = _wf(tmp_path, "doppelt")
    _skill(tmp_path, "doppelt")
    index = d / "workflow-index.md"
    index.write_text("| x | `/doppelt` |\n")
    missing, checked = cwi.check(
        str(d), str(index), allowlist=set(), skills_dir=str(tmp_path / "skills"),
    )
    assert missing == []
    assert checked.count("doppelt") == 1


def test_should_tolerate_absent_skills_dir(tmp_path):
    """Leere/fehlende skills/-Lane ist kein Fehler."""
    d = _wf(tmp_path, "irgendwas")
    index = d / "workflow-index.md"
    index.write_text("| x | `/irgendwas` |\n")
    missing, checked = cwi.check(
        str(d), str(index), allowlist=set(), skills_dir=str(tmp_path / "gibt-es-nicht"),
    )
    assert missing == []
    assert checked == ["irgendwas"]


def test_should_ignore_skills_dir_entry_without_skill_md(tmp_path):
    """Ein Verzeichnis ohne SKILL.md ist kein Skill (z. B. Asset-Ordner)."""
    d = _wf(tmp_path, "irgendwas")
    (tmp_path / "skills" / "nur-assets").mkdir(parents=True)
    (tmp_path / "skills" / "nur-assets" / "bild.png").write_text("x")
    index = d / "workflow-index.md"
    index.write_text("| x | `/irgendwas` |\n")
    missing, checked = cwi.check(
        str(d), str(index), allowlist=set(), skills_dir=str(tmp_path / "skills"),
    )
    assert missing == []
    assert checked == ["irgendwas"]
