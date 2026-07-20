"""Tests fuer tools/iil_migration_check.py (ADR-255 REC-3 Reality-Checker).

Fokus (Issue #819 Haeppchen 2): --offline-Modus (kein Netzzugriff) + Drift-
Erkennung gegen eine gefaelschte registry/iil-migration.yaml. Der Online-Pfad
(gh_repo_full_name) wird nur mit gemonkeypatchter Funktion getestet -- nie ein
echter `gh`/Netzaufruf.

REGISTRY und CANONICAL_GEN sind Modul-globale Path-Konstanten (fix auf den
echten Repo-Pfad) -- fuer Isolation von der echten registry/-Datei werden sie
pro Test auf tmp_path-Fixtures gemonkeypatcht.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

_SPEC = importlib.util.spec_from_file_location(
    "iil_migration_check",
    pathlib.Path(__file__).resolve().parents[1] / "iil_migration_check.py",
)
imc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(imc)


def _write_registry(tmp_path, packages_yaml: str) -> pathlib.Path:
    reg = tmp_path / "iil-migration.yaml"
    reg.write_text(f"packages:\n{packages_yaml}\n", encoding="utf-8")
    return reg


def _write_canonical_gen(tmp_path, repo_owner_entries: dict[str, str]) -> pathlib.Path:
    body = "\n".join(f'        "{k}": "{v}",' for k, v in repo_owner_entries.items())
    gen = tmp_path / "registry-canonical.py"
    gen.write_text(
        "SOME_MAP = {\n"
        '    "repo_owner": {\n'
        f"{body}\n"
        "    },\n"
        "}\n",
        encoding="utf-8",
    )
    return gen


# ─────────────────────────────────────────────────────────────────────────────
# check() — offline (Standardfall des Haeppchens)
# ─────────────────────────────────────────────────────────────────────────────


def test_should_report_no_drift_for_clean_registry_offline(tmp_path, monkeypatch):
    reg = _write_registry(
        tmp_path,
        "  iil-adrfw:\n"
        "    repo_current: iilgmbh/iil-adrfw\n"
        "    status: done\n",
    )
    gen = _write_canonical_gen(tmp_path, {"iil-adrfw": "iilgmbh"})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)

    findings, summary = imc.check(offline=True)

    assert findings == []
    assert summary == {"packages": 1, "drift": 0, "warn": 0, "offline": True}


def test_should_flag_canonical_vs_migration_owner_mismatch(tmp_path, monkeypatch):
    reg = _write_registry(
        tmp_path,
        "  iil-testkit:\n"
        "    repo_current: achimdehnert/iil-testkit\n"
        "    status: pending\n",
    )
    # registry-canonical.py behauptet iilgmbh, iil-migration.yaml sagt noch achimdehnert.
    gen = _write_canonical_gen(tmp_path, {"iil-testkit": "iilgmbh"})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)

    findings, summary = imc.check(offline=True)

    assert summary["drift"] == 1
    assert summary["warn"] == 0
    assert findings[0]["level"] == "DRIFT"
    assert findings[0]["package"] == "iil-testkit"
    assert "repo_owner claims" in findings[0]["message"]


def test_should_flag_status_done_outside_target_org(tmp_path, monkeypatch):
    reg = _write_registry(
        tmp_path,
        "  iil-ghost:\n"
        "    repo_current: achimdehnert/iil-ghost\n"
        "    status: done\n",
    )
    gen = _write_canonical_gen(tmp_path, {})  # keine Canonical-Aussage -> Befund #1 entfaellt
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)

    findings, summary = imc.check(offline=True)

    assert summary["drift"] == 1
    assert findings[0]["level"] == "DRIFT"
    assert "status=done" in findings[0]["message"]


def test_should_not_flag_status_pending_outside_target_org(tmp_path, monkeypatch):
    # status != done -> Befund #2 greift NICHT, auch wenn repo noch bei achimdehnert liegt.
    reg = _write_registry(
        tmp_path,
        "  iil-notyet:\n"
        "    repo_current: achimdehnert/iil-notyet\n"
        "    status: pending\n",
    )
    gen = _write_canonical_gen(tmp_path, {})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)

    findings, summary = imc.check(offline=True)

    assert summary["drift"] == 0
    assert findings == []


def test_should_skip_gh_reality_check_when_offline(tmp_path, monkeypatch):
    reg = _write_registry(
        tmp_path,
        "  iil-adrfw:\n"
        "    repo_current: iilgmbh/iil-adrfw\n"
        "    status: done\n",
    )
    gen = _write_canonical_gen(tmp_path, {})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)

    def _boom(owner_name):
        raise AssertionError("gh_repo_full_name darf im --offline-Modus NICHT aufgerufen werden")

    monkeypatch.setattr(imc, "gh_repo_full_name", _boom)

    findings, summary = imc.check(offline=True)  # muss NICHT raisen
    assert summary["offline"] is True


# ─────────────────────────────────────────────────────────────────────────────
# check() — online-Pfad, gh_repo_full_name gemonkeypatcht (kein echter Netzzugriff)
# ─────────────────────────────────────────────────────────────────────────────


def test_should_flag_drift_when_gh_resolves_to_different_repo(tmp_path, monkeypatch):
    reg = _write_registry(
        tmp_path,
        "  iil-renamed:\n"
        "    repo_current: iilgmbh/iil-renamed\n"
        "    status: pending\n",
    )
    gen = _write_canonical_gen(tmp_path, {})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)
    monkeypatch.setattr(
        imc, "gh_repo_full_name", lambda owner_name: "iilgmbh/iil-renamed-new"
    )

    findings, summary = imc.check(offline=False)

    assert summary["drift"] == 1
    assert findings[0]["level"] == "DRIFT"
    assert "gh resolves to" in findings[0]["message"]


def test_should_warn_when_gh_cannot_resolve_repo(tmp_path, monkeypatch):
    reg = _write_registry(
        tmp_path,
        "  iil-missing:\n"
        "    repo_current: iilgmbh/iil-missing\n"
        "    status: pending\n",
    )
    gen = _write_canonical_gen(tmp_path, {})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)
    monkeypatch.setattr(imc, "gh_repo_full_name", lambda owner_name: None)

    findings, summary = imc.check(offline=False)

    assert summary["drift"] == 0
    assert summary["warn"] == 1
    assert findings[0]["level"] == "WARN"


def test_should_report_no_drift_when_gh_confirms_repo_current(tmp_path, monkeypatch):
    reg = _write_registry(
        tmp_path,
        "  iil-stable:\n"
        "    repo_current: iilgmbh/iil-stable\n"
        "    status: done\n",
    )
    gen = _write_canonical_gen(tmp_path, {})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)
    monkeypatch.setattr(imc, "gh_repo_full_name", lambda owner_name: "iilgmbh/iil-stable")

    findings, summary = imc.check(offline=False)

    assert findings == []
    assert summary["drift"] == 0
    assert summary["warn"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# main() — CLI (Exit-Codes, --json, fehlende Registry)
# ─────────────────────────────────────────────────────────────────────────────


def test_should_exit_2_when_registry_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(imc, "REGISTRY", tmp_path / "does-not-exist.yaml")
    monkeypatch.setattr("sys.argv", ["iil_migration_check.py", "--offline"])

    rc = imc.main()

    assert rc == 2
    assert "registry not found" in capsys.readouterr().err


def test_should_exit_1_when_drift_found_offline(tmp_path, monkeypatch, capsys):
    reg = _write_registry(
        tmp_path,
        "  iil-ghost:\n"
        "    repo_current: achimdehnert/iil-ghost\n"
        "    status: done\n",
    )
    gen = _write_canonical_gen(tmp_path, {})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)
    monkeypatch.setattr("sys.argv", ["iil_migration_check.py", "--offline"])

    rc = imc.main()

    assert rc == 1
    out = capsys.readouterr().out
    assert "1 drift" in out
    assert "(offline)" in out


def test_should_exit_0_when_no_drift_offline(tmp_path, monkeypatch, capsys):
    reg = _write_registry(
        tmp_path,
        "  iil-adrfw:\n"
        "    repo_current: iilgmbh/iil-adrfw\n"
        "    status: done\n",
    )
    gen = _write_canonical_gen(tmp_path, {})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)
    monkeypatch.setattr("sys.argv", ["iil_migration_check.py", "--offline"])

    rc = imc.main()

    assert rc == 0
    assert "no drift" in capsys.readouterr().out


def test_should_emit_valid_json_report(tmp_path, monkeypatch, capsys):
    reg = _write_registry(
        tmp_path,
        "  iil-ghost:\n"
        "    repo_current: achimdehnert/iil-ghost\n"
        "    status: done\n",
    )
    gen = _write_canonical_gen(tmp_path, {})
    monkeypatch.setattr(imc, "REGISTRY", reg)
    monkeypatch.setattr(imc, "CANONICAL_GEN", gen)
    monkeypatch.setattr("sys.argv", ["iil_migration_check.py", "--offline", "--json"])

    rc = imc.main()

    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["drift"] == 1
    assert data["findings"][0]["package"] == "iil-ghost"
