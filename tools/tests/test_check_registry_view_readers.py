"""R7 Fault-Injection für check_registry_view_readers (ADR-234 §11.1 REC-4, KONZ-001 R7).

+/-: API-only-Datei ist kein Reader; injizierter Direct-Read einer View wird geflaggt;
der klickdummy-`repos.yaml`-Basename (anderes File) wird NICHT fälschlich geflaggt;
Maschinerie (registry_api etc.) ist allowlisted.

Run: `python3 -m pytest tools/tests/test_check_registry_view_readers.py -q`
"""
import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "check_registry_view_readers.py"
_spec = importlib.util.spec_from_file_location("crvr", _SRC)
crvr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crvr)


def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_should_not_flag_api_consumer(tmp_path):
    _write(tmp_path, "scripts/good.py", "from registry_api import flat\nflat()\n")
    assert crvr.find_readers(tmp_path, ["scripts/good.py"]) == set()


def test_should_flag_new_direct_read_of_rich_view(tmp_path):
    _write(tmp_path, "scripts/bad.py", "open('registry/repos.yaml')\n")
    assert crvr.find_readers(tmp_path, ["scripts/bad.py"]) == {"scripts/bad.py"}


def test_should_flag_direct_read_of_flat_view(tmp_path):
    _write(tmp_path, "scripts/bad2.py", "yaml.safe_load(open('scripts/repo-registry.yaml'))\n")
    assert crvr.find_readers(tmp_path, ["scripts/bad2.py"]) == {"scripts/bad2.py"}


def test_should_not_flag_klickdummy_bare_repos_yaml(tmp_path):
    # infra/klickdummy-host nutzt /opt/klickdummy/repos.yaml — anderes File, kein registry/-Pfad.
    _write(tmp_path, "infra/klickdummy-host/sync.sh", 'REPOS_FILE="/opt/klickdummy/repos.yaml"\n')
    assert crvr.find_readers(tmp_path, ["infra/klickdummy-host/sync.sh"]) == set()


def test_should_ignore_allowed_machinery(tmp_path):
    _write(tmp_path, "tools/registry_api.py", "open('registry/repos.yaml')\n")
    assert crvr.find_readers(tmp_path, ["tools/registry_api.py"]) == set()
