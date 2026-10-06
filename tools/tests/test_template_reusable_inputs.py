"""Vertragspruefung: Workflow-Templates rufen Reusables nur mit deklarierten Inputs auf (#3406).

Befund #3398: `docs/templates/ci.yml` uebergab an `_deploy-hetzner.yml@v1.1.18` die
Inputs `repo_name` und `port`, die das Reusable nicht kennt, und liess die
Pflicht-Inputs `app_name`/`deploy_path`/`health_url` weg. Ein Consumer, der das
Template kopiert, bekommt einen Workflow, der beim Start scheitert.

Geprueft wird je Job mit `uses: <reusable>` in jedem Template:
  * jeder `with:`-Schluessel ist im `workflow_call.inputs` des Reusables deklariert,
  * jeder required-Input wird uebergeben,
  * dasselbe fuer `secrets:` — und `secrets: inherit` ist verboten, sobald das
    Reusable required-Secrets hat (cross-org reicht `inherit` sie nicht durch).

Vertragsquelle, offline:
  * `iilgmbh/shared-ci/...@<tag>` → Snapshot `fixtures/reusable_interfaces/shared_ci.yaml`
  * `achimdehnert/platform/...@<ref>` → die Datei im eigenen `.github/workflows/`
Ein Reusable ohne Vertragsquelle ist selbst ein Befund (Pin gehoben, Snapshot nicht).

Positivkontrolle: `fixtures/reusable_interfaces/bad_unknown_key.yml` traegt genau die
Form des Realfalls (`repo_name`/`port`, Pflicht-Inputs fehlen) und muss rot werden.

Run: `python3 -m pytest tools/tests/test_template_reusable_inputs.py -q`
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "reusable_interfaces"
_SNAPSHOT = _FIXTURES / "shared_ci.yaml"
_PLATFORM_PREFIX = "achimdehnert/platform/.github/workflows/"

TEMPLATE_GLOBS = ("docs/templates/*.yml", "deployment/workflows/*.yml")


def _templates() -> list[Path]:
    return sorted(p for g in TEMPLATE_GLOBS for p in _ROOT.glob(g))


def _interface_from_workflow(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    on = doc.get("on", doc.get(True))  # PyYAML liest `on:` als True
    call = on["workflow_call"] or {}
    out = {}
    for kind in ("inputs", "secrets"):
        decl = call.get(kind) or {}
        req = sorted(k for k, v in decl.items() if (v or {}).get("required", False))
        out[kind] = {"required": req, "optional": sorted(set(decl) - set(req))}
    return out


def _load_interfaces() -> dict:
    return yaml.safe_load(_SNAPSHOT.read_text(encoding="utf-8"))


def interface_for(uses: str, snapshot: dict) -> dict | None:
    if uses in snapshot:
        return snapshot[uses]
    if uses.startswith(_PLATFORM_PREFIX):
        local = (
            _ROOT
            / ".github"
            / "workflows"
            / uses[len(_PLATFORM_PREFIX) :].split("@")[0]
        )
        if local.is_file():
            return _interface_from_workflow(local)
    return None


def reusable_calls(template: Path) -> list[tuple[str, str, dict]]:
    """(job, uses, job-dict) fuer jeden Job, der ein Reusable aufruft."""
    doc = yaml.safe_load(template.read_text(encoding="utf-8")) or {}
    calls = []
    for name, job in (doc.get("jobs") or {}).items():
        uses = (job or {}).get("uses", "")
        if "/.github/workflows/" in uses:
            calls.append((name, uses, job))
    return calls


def check_template(template: Path, snapshot: dict) -> list[str]:
    befunde = []
    for job, uses, body in reusable_calls(template):
        iface = interface_for(uses, snapshot)
        where = f"{template.name}:{job} → {uses}"
        if iface is None:
            befunde.append(f"{where}: kein Vertrag (Snapshot fehlt fuer diesen Pin)")
            continue
        passed = {
            "inputs": set((body.get("with") or {}).keys()),
            "secrets": body.get("secrets") or {},
        }
        for kind in ("inputs", "secrets"):
            required = set(iface[kind]["required"])
            declared = required | set(iface[kind]["optional"])
            given = passed[kind]
            if given == "inherit":
                if required:
                    befunde.append(
                        f"{where}: `secrets: inherit` bei required-Secrets "
                        f"{sorted(required)} — cross-org nicht durchgereicht, explizit mappen"
                    )
                continue
            given = set(given)
            for key in sorted(given - declared):
                befunde.append(f"{where}: {kind}-Schluessel `{key}` nicht deklariert")
            for key in sorted(required - given):
                befunde.append(f"{where}: required-{kind} `{key}` fehlt")
    return befunde


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return _load_interfaces()


def test_should_find_the_known_reusable_call_sites():
    # Nicht-Leerheit: ohne Aufrufstellen waere der Vertragstest gruen, ohne zu pruefen.
    sites = {(t.name, j) for t in _templates() for j, _, _ in reusable_calls(t)}
    assert {
        ("ci.yml", "ci"),
        ("ci.yml", "build"),
        ("ci.yml", "deploy"),
        ("deploy-staging.yml", "deploy"),
    } <= sites


@pytest.mark.parametrize(
    "template", _templates(), ids=lambda p: str(p.relative_to(_ROOT))
)
def test_should_pass_only_declared_and_all_required_inputs(template, snapshot):
    assert check_template(template, snapshot) == []


def test_should_fail_on_fixture_with_unknown_key(snapshot):
    befunde = check_template(_FIXTURES / "bad_unknown_key.yml", snapshot)
    text = "\n".join(befunde)
    assert "inputs-Schluessel `repo_name` nicht deklariert" in text
    assert "inputs-Schluessel `port` nicht deklariert" in text
    for key in ("app_name", "deploy_path", "health_url"):
        assert f"required-inputs `{key}` fehlt" in text
    assert "`secrets: inherit` bei required-Secrets" in text


def test_should_fail_on_unknown_pin(tmp_path, snapshot):
    t = tmp_path / "t.yml"
    t.write_text(
        "jobs:\n  d:\n    uses: iilgmbh/shared-ci/.github/workflows/_deploy-hetzner.yml@v9.9.9\n",
        encoding="utf-8",
    )
    assert any("kein Vertrag" in b for b in check_template(t, snapshot))


def test_should_read_platform_reusable_contract_from_local_file():
    iface = interface_for(f"{_PLATFORM_PREFIX}_build-docker.yml@main", {})
    assert iface is not None
    assert "dockerfile" in iface["inputs"]["optional"]
    assert "repo_name" not in iface["inputs"]["optional"] + iface["inputs"]["required"]
