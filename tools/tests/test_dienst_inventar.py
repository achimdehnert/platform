"""Tests fuer tools/dienst_inventar.py (platform#3011, Kriterium 1)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dienst_inventar as di  # noqa: E402


def _repo(tmp_path: Path, name: str) -> Path:
    wurzel = tmp_path / name
    (wurzel / ".git").mkdir(parents=True)
    return wurzel


def _schreibe(pfad: Path, text: str) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text, encoding="utf-8")


@pytest.fixture
def bestand(tmp_path, monkeypatch):
    monkeypatch.setattr(di, "GITHUB_DIR", tmp_path)
    monkeypatch.setattr(di, "archivierte_repos", lambda: {"alt-hub"})
    hub = _repo(tmp_path, "demo-hub")
    _schreibe(hub / "apps/x/agent/toolkit.py", "class DemoToolkit(DomainToolkit):\n    pass\n")
    _schreibe(hub / "apps/x/management/commands/sync_all.py",
              "class Command(BaseCommand):\n    help = \"Alles synchronisieren\"\n")
    _schreibe(hub / "apps/x/management/commands/seed_musterkunde_org.py",
              "class Command(BaseCommand):\n    help = \"Org Musterkunde anlegen\"\n")
    _schreibe(hub / "apps/x/services.py",
              "def _intern():\n    pass\n\ndef berechne(a):\n    \"\"\"Rechnet etwas aus.\"\"\"\n    return a\n")
    _schreibe(hub / "src/mcp/server.py", "@mcp.tool()\nasync def suche(q):\n    pass\n")
    _schreibe(hub / "tests/test_x.py", "def helfer():\n    pass\n")
    _schreibe(hub / "vendor/chat_agent/toolkit.py", "class FremdToolkit(DomainToolkit):\n    pass\n")
    kern = _repo(tmp_path, "iil-assist-core")
    _schreibe(kern / "assist_core/models.py",
              "class Mandant(models.Model):\n    \"\"\"Ein Haus.\"\"\"\n\ndef nicht_zaehlen():\n    pass\n")
    return tmp_path


def test_should_find_one_entry_per_source(bestand):
    inv = di.inventar(["demo-hub", "iil-assist-core"])
    assert inv["je_quelle"] == {"mcp": 1, "mgmt": 2, "modell": 1, "service": 1, "toolkit": 1}
    namen = {(f["quelle"], f["name"]) for f in inv["funde"]}
    assert ("service", "berechne") in namen and ("service", "_intern") not in namen
    assert ("mcp", "suche") in namen
    assert inv["repos_fehlt"] == []
    assert inv["repos_archiviert"] == ["alt-hub"]


def test_should_skip_tests_and_vendor(bestand):
    inv = di.inventar(["demo-hub"])
    pfade = [f["pfad"] for f in inv["funde"]]
    assert not any(p.startswith(("tests/", "vendor/")) for p in pfade)


def test_should_report_missing_clone_instead_of_silent_zero(bestand):
    inv = di.inventar(["demo-hub", "gibt-es-nicht"])
    assert inv["repos_fehlt"] == ["gibt-es-nicht"]
    assert "gibt-es-nicht" not in inv["repos_geprueft"]


def test_should_carry_help_and_docstring_as_hint(bestand):
    inv = di.inventar(["demo-hub", "iil-assist-core"])
    hinweise = {f["name"]: f["hinweis"] for f in inv["funde"]}
    assert hinweise["sync_all"] == "Alles synchronisieren"
    assert hinweise["berechne"] == "Rechnet etwas aus."
    assert hinweise["Mandant"] == "Ein Haus."


def test_should_mask_protected_terms_in_name_path_and_hint(bestand):
    inv = di.inventar(["demo-hub"], begriffe={"musterkunde"})
    treffer = [f for f in inv["funde"] if f["quelle"] == "mgmt" and "seed_" in f["name"]]
    assert len(treffer) == 1
    f = treffer[0]
    assert f["name"] == "seed_[mandant]_org"
    assert "[mandant]" in f["pfad"] and "musterkunde" not in f["pfad"].lower()
    assert f["hinweis"] == "Org [mandant] anlegen"
    assert inv["schutz"] == {"cache": True, "maskiert": 3}
    assert "musterkunde" not in json.dumps(inv).lower()


def test_should_flag_missing_protection_cache(bestand):
    inv = di.inventar(["demo-hub"], begriffe=None)
    assert inv["schutz"] == {"cache": False, "maskiert": 0}
    assert "OHNE CACHE" in di.als_markdown(inv)


def test_should_be_byte_identical_across_two_runs(bestand):
    a = json.dumps(di.inventar(["demo-hub", "iil-assist-core"]), sort_keys=True)
    b = json.dumps(di.inventar(["demo-hub", "iil-assist-core"]), sort_keys=True)
    assert a == b
    assert "zeit" not in a.lower()
