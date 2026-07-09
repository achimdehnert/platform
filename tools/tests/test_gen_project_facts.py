"""Tests für scripts/gen_project_facts.py — prod_url-Auto-Detect (F-9).

Repro (repo-optimize 2026-07-03, skeptiker-verifiziert): die alte Regex
`[a-z0-9.-]+\\.(de|com|pet|io|net)` hat genau eine Capture-Group (die TLD-
Alternation selbst) — `re.findall` liefert bei genau einer Gruppe NUR die
Gruppen-Treffer zurück, nicht den vollen Match. Für eine Zeile mit
`frist-hub.pet` lieferte `detect_prod_url` also `'pet'` statt der vollen
Domain. Latent (0/86 Live-Dateien betroffen, weil die Registry meist Vorrang
hat), aber ein Zeitzünder für jedes Registry-lose Repo mit ALLOWED_HOSTS-Zeile.

Liegt unter tools/tests/ (nicht repo-root tests/) — der generische
`tools-tests.yml`-Gate deckt scripts/** mit ab.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "gen_project_facts.py"
_spec = importlib.util.spec_from_file_location("gen_project_facts", _SCRIPT)
gpf = importlib.util.module_from_spec(_spec)
sys.modules["gen_project_facts"] = gpf
_spec.loader.exec_module(gpf)


def test_should_return_full_domain_not_bare_tld(tmp_path):
    """Repro F-9: frist-hub-Fixture darf nie nur die TLD ('pet') liefern."""
    compose = tmp_path / "docker-compose.prod.yml"
    compose.write_text(
        "services:\n"
        "  web:\n"
        "    environment:\n"
        "      DJANGO_ALLOWED_HOSTS: frist-hub.pet,localhost\n"
    )
    url = gpf.detect_prod_url(tmp_path)
    assert url == "frist-hub.pet"
    assert url != "pet"


def test_should_match_all_supported_tlds(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        "services:\n"
        "  web:\n"
        "    environment:\n"
        "      CSRF_TRUSTED_ORIGINS: https://schutztat.de\n"
    )
    assert gpf.detect_prod_url(tmp_path) == "schutztat.de"


def test_should_skip_localhost_and_loopback_candidates(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        "services:\n"
        "  web:\n"
        "    environment:\n"
        "      ALLOWED_HOSTS: localhost,127.0.0.1,real-repo.iil.pet\n"
    )
    assert gpf.detect_prod_url(tmp_path) == "real-repo.iil.pet"


def test_should_return_empty_string_when_no_compose_or_env_example(tmp_path):
    assert gpf.detect_prod_url(tmp_path) == ""


def test_should_read_env_example_when_no_compose_matches(tmp_path):
    (tmp_path / ".env.example").write_text("DJANGO_ALLOWED_HOSTS=example-repo.io\n")
    assert gpf.detect_prod_url(tmp_path) == "example-repo.io"
