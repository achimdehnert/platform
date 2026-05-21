"""Smoke tests for iil-klickdummy package — every public surface importable + callable."""
from __future__ import annotations

import json
from importlib.resources import files


def test_package_version():
    import iil_klickdummy
    # Major bleibt 1; Minor wandert v1.0 → v1.1 → v1.2 …
    assert iil_klickdummy.__version__.startswith("1.")


def test_all_modules_present():
    import iil_klickdummy
    for mod in ("check_i1", "check_i2", "check_i3", "check_i4",
                "extract_requirements", "inventory", "install_snippets"):
        assert hasattr(iil_klickdummy, mod), f"missing module: {mod}"


def test_all_main_cli_endpoints():
    import iil_klickdummy
    for mod_name in ("check_i1", "check_i2", "check_i3", "check_i4",
                     "extract_requirements", "inventory", "install_snippets"):
        mod = getattr(iil_klickdummy, mod_name)
        assert callable(getattr(mod, "main_cli", None)), f"{mod_name}.main_cli missing"


def test_schemas_resource():
    names = sorted(p.name for p in files("iil_klickdummy.schemas").iterdir())
    assert {"screens-spec.schema.json", "module-manifest.schema.json",
            "feedback-payload.schema.json"}.issubset(set(names))


def test_screens_spec_schema_strict_mode():
    schema = json.loads(files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text())
    assert schema["properties"]["class"]["enum"] == ["mock", "stub-demo", "story", "spec-demo"]


def test_check_i2_strict_mode():
    from iil_klickdummy import check_i2
    assert check_i2.LEGACY == {}, "Strict-Mode: LEGACY must be empty per ADR-211 Rev 12/13"
    assert check_i2.ALLOWED == {"mock", "stub-demo", "story", "spec-demo"}


def test_snippets_resource():
    snippets = files("iil_klickdummy") / "snippets"
    names = []
    for d in snippets.iterdir():
        for f in d.iterdir():
            names.append(f.name)
    assert "widget.js" in names
    assert "klickdummy-feedback.md" in names
    assert "inject-widget.html" in names
    assert "screens-spec-template.yaml" in names


def test_widget_js_v05_features():
    """Widget v0.5 must have all v0.2-v0.4 features + GitHub-Direct-API."""
    js = (files("iil_klickdummy") / "snippets" / "feedback-widget" / "widget.js").read_text()
    # v0.2 features
    assert "populateRelated" in js
    assert "fb-rel-grid" in js
    # v0.3 features
    assert "domSnapshot" in js
    assert "FB_FILE_MAX_BYTES" in js
    assert "actionsInCurrentScreen" in js
    assert "fb-act-grid" in js
    # v0.4 features
    assert "feedback_scope" in js
    assert "fb-scope" in js
    assert "KLICKDUMMY_VERFAHREN_HOOK" in js
    # v0.5 (Rev 13 pivot B): GitHub-Direkt-API
    assert "submitGithub" in js
    assert "api.github.com" in js
    assert "klickdummy_github_token" in js
    # v0.5: Plugin-Hooks
    assert "KLICKDUMMY_CATEGORIES" in js
    assert "KLICKDUMMY_PERSONA_HOOK" in js


def test_inventory_runs_clean_on_nonexistent_base():
    from iil_klickdummy import inventory
    assert inventory.main(["--base", "/nonexistent/path"]) == 0


# --- v1.1 ------------------------------------------------------------------

def test_v11_registry_module_present():
    from iil_klickdummy import registry
    assert hasattr(registry, "discover_klickdummies")
    assert hasattr(registry, "discover_versions")
    assert hasattr(registry, "render_browser_html")
    assert hasattr(registry, "main_cli")


def test_v11_browser_template_present():
    tmpl = files("iil_klickdummy.snippets.browser").joinpath("browser.html.tmpl").read_text()
    assert "__KLICKDUMMIES_JSON__" in tmpl
    assert "__REPO_LABEL__" in tmpl


def test_v11_registry_discover_empty_repo(tmp_path):
    from iil_klickdummy import registry
    # leeres Verzeichnis → 0 Klickdummies
    result = registry.discover_klickdummies(tmp_path)
    assert result == []


def test_v11_registry_render_browser_html(tmp_path):
    from iil_klickdummy import registry
    fake = [registry.KlickdummyMeta(
        name="demo", path="klickdummy/demo/screens-spec.yaml",
        shell_path="klickdummy/demo/shell.html",
        spec_id="repo:klickdummy-spec-demo", spec_version="0.1",
        klickdummy_class="mock", title="Demo",
        adr_local="repo:ADR-100", sister_of=[],
    )]
    out = tmp_path / "browser.html"
    registry.render_browser_html(fake, out, repo_label="test-repo")
    html = out.read_text(encoding="utf-8")
    assert "test-repo" in html
    assert "Demo" in html
    assert "repo:klickdummy-spec-demo" in html
    assert "__KLICKDUMMIES_JSON__" not in html  # Template-Marker ersetzt


def test_v11_version_bumped():
    import iil_klickdummy
    assert iil_klickdummy.__version__ == "1.1.0"
