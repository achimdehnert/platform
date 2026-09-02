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
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "check_publish_oidc_auth.py"
_spec = importlib.util.spec_from_file_location("check_publish_oidc_auth", _SRC)
gate = importlib.util.module_from_spec(_spec)
# Muss vor exec_module in sys.modules stehen: check_publish_oidc_auth.py
# definiert ein @dataclass, dessen Verarbeitung cls.__module__ über
# sys.modules nachschlägt — ohne diesen Eintrag crasht der Import mit
# 'NoneType' object has no attribute '__dict__'.
sys.modules[_spec.name] = gate
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

# Muster aus dem echten .github/workflows/publish-iil-testkit.yml (Ist-Beleg
# 2026-08-27, KONZ-052 V4): twine upload in einem run:-Block, TWINE_USERNAME/
# TWINE_PASSWORD im step-env — keine pypa-Action, also vom alten Guard (der nur
# with.password prüfte) komplett unsichtbar.
TWINE_UPLOAD_RUN_BLOCK = """\
jobs:
  publish:
    steps:
      - name: Upload to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
"""

# Muster aus dem echten .github/workflows/publish-iil-codeguard.yml —
# Positivkontrolle: OIDC-only, muss weiterhin sauber durchgehen.
OIDC_ONLY_CODEGUARD_PATTERN = """\
jobs:
  publish:
    permissions:
      contents: read
      id-token: write
    environment:
      name: pypi
    steps:
      - name: Build
        run: python -m hatchling build
      - name: Check
        run: twine check dist/*
      - name: Publish to PyPI (OIDC Trusted Publishing)
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/
          print-hash: true
"""

UV_PUBLISH_RUN_BLOCK = """\
jobs:
  publish:
    steps:
      - name: Publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
        run: uv publish
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
    inhalt = TESTPYPI.replace(
        "https://test.pypi.org/legacy/", "https://upload.pypi.org/legacy/"
    )

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


# --- Erweiterung KONZ-052 V4: twine/uv/hatch/flit/poetry-Publish + Token-Env ---


def test_should_flag_twine_upload_in_a_run_block_like_the_real_testkit_workflow(wf):
    pfad = wf(TWINE_UPLOAD_RUN_BLOCK, name="publish-iil-testkit.yml")

    verstoesse = gate.scan_file(pfad)
    gruende = " ".join(verstoesse)

    assert gate.main([str(pfad), "--block"]) == 1
    assert "twine upload" in gruende
    assert "ADR-278" in gruende


def test_should_pass_the_real_codeguard_oidc_pattern(wf):
    pfad = wf(OIDC_ONLY_CODEGUARD_PATTERN, name="publish-iil-codeguard.yml")

    assert gate.scan_file(pfad) == []
    assert gate.main([str(pfad), "--block"]) == 0


def test_should_flag_uv_publish_with_uv_publish_token_env(wf):
    verstoesse = gate.scan_file(wf(UV_PUBLISH_RUN_BLOCK))
    gruende = " ".join(verstoesse)

    assert "uv publish" in gruende
    assert "UV_PUBLISH_TOKEN" in gruende


def test_should_flag_a_bare_token_env_even_without_a_matching_run_command(wf):
    # Das Secret allein ist schon der Bruch (kein Token-Secret mehr noetig) —
    # unabhaengig davon, ob im selben Step ein Publish-Kommando steht.
    inhalt = (
        "jobs:\n"
        "  publish:\n"
        "    env:\n"
        "      POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_API_TOKEN }}\n"
        "    steps:\n"
        "      - name: Noop\n"
        "        run: echo hi\n"
    )

    verstoesse = gate.scan_file(wf(inhalt))

    assert len(verstoesse) == 1
    assert "POETRY_PYPI_TOKEN_PYPI" in verstoesse[0]


def test_should_not_flag_twine_upload_against_a_testpypi_target(wf):
    inhalt = (
        "jobs:\n"
        "  publish:\n"
        "    steps:\n"
        "      - name: Upload\n"
        "        run: twine upload --repository testpypi dist/*\n"
    )

    assert gate.scan_file(wf(inhalt)) == []


def test_should_not_flag_twine_upload_mentioned_only_in_a_yaml_comment(wf):
    # YAML-Kommentare landen nie im geparsten Dokument — ein Fund darf sich
    # nie aus Kommentartext ergeben (Realfall: publish-iil-ingest.yml/
    # publish-iil-codeguard.yml erwaehnen "twine upload" nur in einem Kommentar).
    inhalt = (
        "jobs:\n"
        "  publish:\n"
        "    steps:\n"
        "      # the irreversible event (twine upload) is actually blocked.\n"
        "      - name: Check\n"
        "        run: twine check dist/*\n"
    )

    assert gate.scan_file(wf(inhalt)) == []


# --- Allowlist (KONZ-052 V4): befristete Ausnahme, kein Sonderfall im Guard ---


def test_should_load_allowlist_entries_from_a_pipe_delimited_file(tmp_path):
    datei = tmp_path / "oidc_allowlist.txt"
    datei.write_text(
        "# Kommentar wird ignoriert\n"
        "\n"
        ".github/workflows/publish-iil-testkit.yml | 2026-10-19 | KONZ-052 V1\n",
        encoding="utf-8",
    )

    eintraege = gate.load_allowlist(datei)

    assert len(eintraege) == 1
    assert eintraege[0].file_path == ".github/workflows/publish-iil-testkit.yml"
    assert eintraege[0].until.isoformat() == "2026-10-19"
    assert eintraege[0].reference == "KONZ-052 V1"


def test_should_ignore_a_missing_allowlist_file(tmp_path):
    assert gate.load_allowlist(tmp_path / "does-not-exist.txt") == []


def test_should_treat_an_expired_allowlist_entry_as_inactive():
    import datetime as _dt

    eintraege = [
        gate.AllowlistEntry(
            file_path="x.yml", until=_dt.date(2026, 10, 19), reference="ref"
        )
    ]

    # Am Ablauftag selbst noch aktiv, einen Tag danach nicht mehr.
    assert "x.yml" in gate.active_allowlist(eintraege, _dt.date(2026, 10, 19))
    assert "x.yml" not in gate.active_allowlist(eintraege, _dt.date(2026, 10, 20))


def test_should_suppress_the_exit_code_for_an_actively_allowlisted_file(
    wf, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "oidc_allowlist.txt").write_text(
        "publish-iil-testkit.yml | 2099-01-01 | KONZ-052 V1\n", encoding="utf-8"
    )
    pfad = tmp_path / "publish-iil-testkit.yml"
    pfad.write_text(TWINE_UPLOAD_RUN_BLOCK, encoding="utf-8")

    assert gate.main([str(pfad.name), "--block"]) == 0


def test_should_stop_suppressing_once_the_allowlist_entry_expired(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "oidc_allowlist.txt").write_text(
        "publish-iil-testkit.yml | 2020-01-01 | KONZ-052 V1 (abgelaufen)\n",
        encoding="utf-8",
    )
    pfad = tmp_path / "publish-iil-testkit.yml"
    pfad.write_text(TWINE_UPLOAD_RUN_BLOCK, encoding="utf-8")

    assert gate.main([str(pfad.name), "--block"]) == 1
