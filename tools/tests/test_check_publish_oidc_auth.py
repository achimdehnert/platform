"""ADR-278-Gate: PyPI-Publish muss OIDC sein, kein password-Input.

Zwei Fehlrichtungen kosten hier unterschiedlich viel. Ein Fehlalarm blockiert einen
Release. Ein uebersehener `password:`-Input laesst Token-Publishing durchgehen,
obwohl ADR-278 es verbietet — der Fehler faellt dann erst auf, wenn ein Token leckt.
Der zweite ist der teurere, deshalb sichern die Faelle unten vor allem ab, dass der
Scanner den Verstoss wirklich sieht und ihn nicht an einer Formvariante verliert.

TestPyPI ist bewusst ausgenommen; dass diese Ausnahme nicht zu breit greift, ist ein
eigener Fall.
"""

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "check_publish_oidc_auth.py"
_spec = importlib.util.spec_from_file_location("check_publish_oidc_auth", _SRC)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

OIDC = """\
jobs:
  publish:
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

MIT_PASSWORT = """\
jobs:
  publish:
    steps:
      - name: Upload
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_TOKEN }}
"""

TESTPYPI = """\
jobs:
  publish:
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/
          password: ${{ secrets.TEST_PYPI_TOKEN }}
"""


@pytest.fixture()
def wf(tmp_path: pathlib.Path):
    def _schreibe(inhalt: str, name: str = "publish.yml") -> pathlib.Path:
        p = tmp_path / name
        p.write_text(inhalt, encoding="utf-8")
        return p

    return _schreibe


def test_should_pass_a_workflow_without_password_input(wf):
    assert gate.scan_file(wf(OIDC)) == []


def test_should_flag_a_password_input_on_the_pypi_upload(wf):
    verstoesse = gate.scan_file(wf(MIT_PASSWORT))

    assert len(verstoesse) == 1
    assert "password-Input" in verstoesse[0]
    assert "ADR-278" in verstoesse[0]


def test_should_allow_password_for_testpypi(wf):
    assert gate.scan_file(wf(TESTPYPI)) == []


def test_should_still_flag_pypi_when_repository_url_points_at_real_pypi(wf):
    # die TestPyPI-Ausnahme darf nicht auf upload.pypi.org durchschlagen
    inhalt = TESTPYPI.replace("https://test.pypi.org/legacy/", "https://upload.pypi.org/legacy/")

    assert len(gate.scan_file(wf(inhalt))) == 1


def test_should_report_unparsable_yaml_as_a_finding(wf):
    verstoesse = gate.scan_file(wf("jobs: [unbalanced\n"))

    assert len(verstoesse) == 1
    assert "nicht parsebar" in verstoesse[0]


def test_should_ignore_steps_of_other_actions(wf):
    inhalt = "jobs:\n  build:\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          password: x\n"

    assert gate.scan_file(wf(inhalt)) == []


def test_should_tolerate_a_yaml_document_that_is_not_a_mapping(wf):
    assert gate.scan_file(wf("- nur\n- eine\n- liste\n")) == []


def test_should_take_explicit_paths_over_the_default_glob():
    ziele = gate.collect_targets(["--block", "a/publish.yml", "b/publish.yml"])

    assert [str(p) for p in ziele] == ["a/publish.yml", "b/publish.yml"]


def test_should_exit_1_only_in_block_mode(wf):
    pfad = str(wf(MIT_PASSWORT))

    assert gate.main([pfad]) == 0  # warn-Modus meldet, blockiert aber nicht
    assert gate.main([pfad, "--block"]) == 1


def test_should_exit_0_when_no_publish_workflow_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert gate.main(["--block"]) == 0
