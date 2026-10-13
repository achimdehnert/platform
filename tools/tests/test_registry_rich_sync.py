"""Tests für tools/registry_rich_sync.py (KONZ-070 WP0, #3903).

Invarianten: dry-run schreibt nichts · apply ist idempotent · ``deployed`` wird nie ohne
Beleg aus infra/ports.yaml gesetzt · jede Änderung trägt eine Quelle · Kommentare der
canonical.yaml überleben den textuellen Patch · Konflikte überschreiben nie.

Run: `python3 -m pytest tools/tests/test_registry_rich_sync.py -q`
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import registry_rich_sync as rrs  # noqa: E402

CANON_TEXT = """\
meta:
  server:
    github_org: achimdehnert
  repo_owner:
    frist-hub: meiki-lra
  owner_prefix_rules:
  - prefix: meiki-
    owner: meiki-lra
repos:
  # Kommentar vor dem ersten Eintrag
  dev-hub:
    in_flat: true
    in_rich: true
    flat:
      type: django
    rich:
      name: dev-hub
      github: achimdehnert/dev-hub
      deployed: true
      lifecycle: production
      # Kommentar im rich-Block
      type: django

  # Kommentar vor meiki-hub (gehört zum nächsten Eintrag)
  meiki-hub:
    in_flat: true
    in_rich: false
    flat:
      type: django
  frist-hub:
    in_flat: true
    in_rich: false
    flat:
      type: django
  aifw:
    in_flat: true
    in_rich: false
    flat:
      type: library
  old-tool:
    in_flat: false
    in_rich: false
    lifecycle: archived
    github: achimdehnert/old-tool
    description: tot
"""

PORTS = {
    "services": {
        "dev-hub": {"repo": "achimdehnert/dev-hub", "domain_prod": "dev-hub.iil.pet"},
        "frist-hub": {"domain_prod": "frist-hub.iil.pet", "betriebsstatus": "blockiert"},
    }
}

ANTWORTEN = {
    "achimdehnert/dev-hub": {
        "full_name": "achimdehnert/dev-hub",
        "visibility": "private",
        "archived": False,
        "default_branch": "main",
        "pushed_at": "2026-10-13T10:08:50Z",
    },
    "meiki-lra/meiki-hub": {
        "full_name": "meiki-lra/meiki-hub",
        "visibility": "private",
        "archived": False,
        "default_branch": "main",
        "pushed_at": "2026-10-13T10:08:50Z",
    },
    "meiki-lra/frist-hub": {
        "full_name": "meiki-lra/frist-hub",
        "visibility": "private",
        "archived": False,
        "default_branch": "main",
        "pushed_at": "2026-10-01T00:00:00Z",
    },
    # Default-Org-Fallback, GitHub leitet still nach iilgmbh um (ADR-297)
    "achimdehnert/aifw": {
        "full_name": "iilgmbh/aifw",
        "visibility": "public",
        "archived": False,
        "default_branch": "main",
        "pushed_at": "2026-09-01T00:00:00Z",
    },
    "achimdehnert/old-tool": {
        "full_name": "achimdehnert/old-tool",
        "visibility": "private",
        "archived": True,
        "default_branch": "master",
        "pushed_at": "2025-01-01T00:00:00Z",
    },
}


def _fetch(full: str) -> dict | None:
    return ANTWORTEN.get(full)


def _schreibe_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    canon = tmp_path / "canonical.yaml"
    canon.write_text(CANON_TEXT)
    ports = tmp_path / "ports.yaml"
    ports.write_text(yaml.safe_dump(PORTS))
    return canon, ports


def _lauf(tmp_path: Path, canon: Path, ports: Path, *extra: str, monkeypatch) -> int:
    monkeypatch.setattr(rrs, "gh_fetch", _fetch)
    return rrs.main(["--canonical", str(canon), "--ports", str(ports), *extra])


# --- dry-run / apply / idempotenz ----------------------------------------------


def test_should_not_write_anything_in_dry_run(tmp_path, monkeypatch, capsys):
    canon, ports = _schreibe_fixtures(tmp_path)
    assert _lauf(tmp_path, canon, ports, monkeypatch=monkeypatch) == 0
    assert canon.read_text() == CANON_TEXT
    assert "dry-run, nichts geschrieben" in capsys.readouterr().out


def test_should_apply_idempotently(tmp_path, monkeypatch, capsys):
    canon, ports = _schreibe_fixtures(tmp_path)
    _lauf(tmp_path, canon, ports, "--apply", monkeypatch=monkeypatch)
    nach_erstem = canon.read_text()
    assert nach_erstem != CANON_TEXT
    capsys.readouterr()
    _lauf(tmp_path, canon, ports, "--apply", monkeypatch=monkeypatch)
    assert canon.read_text() == nach_erstem
    assert "0 Änderung(en)" in capsys.readouterr().out


def test_should_keep_every_comment_line_after_apply(tmp_path, monkeypatch):
    canon, ports = _schreibe_fixtures(tmp_path)
    _lauf(tmp_path, canon, ports, "--apply", monkeypatch=monkeypatch)
    assert rrs._kommentarzeilen(canon.read_text()) == rrs._kommentarzeilen(CANON_TEXT)


def test_should_produce_text_equal_to_dict_mutation(tmp_path, monkeypatch):
    canon, ports = _schreibe_fixtures(tmp_path)
    before = yaml.safe_load(CANON_TEXT)
    rep = rrs.derive(before, PORTS, _fetch)
    _lauf(tmp_path, canon, ports, "--apply", monkeypatch=monkeypatch)
    assert yaml.safe_load(canon.read_text()) == rrs.erwartet(before, rep.changes)


# --- Feld-Ableitung und Quellen -------------------------------------------------


def _changes(name: str, rep: rrs.Report) -> dict[str, rrs.Change]:
    return {c.feld: c for c in rep.changes if c.repo == name}


def test_should_derive_github_from_prefix_rule_and_api_full_name():
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), PORTS, _fetch)
    c = _changes("meiki-hub", rep)
    assert c["github"].neu == "meiki-lra/meiki-hub"
    assert c["github"].quelle.startswith("gh api repos/meiki-lra/meiki-hub")
    assert c["github_meta"].neu == {
        "visibility": "private",
        "archived": False,
        "default_branch": "main",
        "pushed_at": "2026-10-13",
    }


def test_should_accept_redirect_when_owner_was_only_the_default_fallback():
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), PORTS, _fetch)
    c = _changes("aifw", rep)
    assert c["github"].neu == "iilgmbh/aifw"
    assert "Umleitung" in c["github"].quelle
    assert not [k for k in rep.konflikte if k[0] == "aifw"]


def test_should_report_conflict_instead_of_overwriting_declared_github():
    canon = yaml.safe_load(CANON_TEXT)
    canon["meta"]["repo_owner"]["aifw"] = "achimdehnert"  # explizit deklariert
    rep = rrs.derive(canon, PORTS, _fetch)
    assert "aifw" not in {c.repo for c in rep.changes}
    (k,) = [k for k in rep.konflikte if k[0] == "aifw"]
    assert k[1:4] == ("github", "achimdehnert/aifw", "iilgmbh/aifw")


def test_should_report_rename_as_conflict_even_for_default_fallback():
    antworten = dict(ANTWORTEN)
    antworten["achimdehnert/aifw"] = {**ANTWORTEN["achimdehnert/aifw"], "full_name": "iilgmbh/aifw-neu"}
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), PORTS, antworten.get)
    assert "aifw" not in {c.repo for c in rep.changes}
    assert [k for k in rep.konflikte if k[0] == "aifw"]


def test_should_set_lifecycle_archived_only_when_api_says_archived():
    canon = yaml.safe_load(CANON_TEXT)
    del canon["repos"]["old-tool"]["lifecycle"]
    rep = rrs.derive(canon, PORTS, _fetch)
    assert _changes("old-tool", rep)["lifecycle"].neu == "archived"
    assert _changes("old-tool", rep)["lifecycle"].ziel == rrs.ZIEL_TOP
    # nicht archiviert → lifecycle bleibt leer und steht in "offen"
    assert "lifecycle" not in _changes("meiki-hub", rep)
    assert "meiki-hub" in rep.lifecycle_offen


def test_should_report_lifecycle_conflict_without_overwriting():
    canon = yaml.safe_load(CANON_TEXT)
    canon["repos"]["old-tool"]["lifecycle"] = "frozen"
    rep = rrs.derive(canon, PORTS, _fetch)
    assert "lifecycle" not in _changes("old-tool", rep)
    assert ("old-tool", "lifecycle", "frozen", "archived") in {k[:4] for k in rep.konflikte}


# --- deployed: nie ohne Beleg ---------------------------------------------------


def test_should_never_set_deployed_without_ports_declaration():
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), {"services": {}}, _fetch)
    assert not [c for c in rep.changes if c.feld == "deployed"]
    assert {n for n, _ in rep.deployed_nicht_belegbar} == {"meiki-hub", "frist-hub", "aifw"}


def test_should_derive_deployed_false_from_blocked_service_and_cite_it():
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), PORTS, _fetch)
    c = _changes("frist-hub", rep)["deployed"]
    assert c.neu is False
    assert c.quelle == "infra/ports.yaml services.frist-hub.betriebsstatus=blockiert"
    assert ("meiki-hub", "kein Dienst mit domain_prod in infra/ports.yaml") in rep.deployed_nicht_belegbar


def test_should_derive_deployed_true_only_from_active_service_with_domain_prod():
    canon = yaml.safe_load(CANON_TEXT)
    del canon["repos"]["dev-hub"]["rich"]["deployed"]
    rep = rrs.derive(canon, PORTS, _fetch)
    c = _changes("dev-hub", rep)["deployed"]
    assert c.neu is True
    assert "services.dev-hub.domain_prod=dev-hub.iil.pet" in c.quelle


def test_should_leave_deployed_open_for_undefined_betriebsstatus():
    wert, grund = rrs.ports_beleg(
        {"services": {"x": {"domain_prod": "x.iil.pet", "betriebsstatus": "ruhend"}}}, "o/x", "x"
    )
    assert wert is None
    assert "ruhend" in grund


def test_should_report_deployed_conflict_without_overwriting():
    canon = yaml.safe_load(CANON_TEXT)
    canon["repos"]["dev-hub"]["rich"]["deployed"] = False
    rep = rrs.derive(canon, PORTS, _fetch)
    assert "deployed" not in _changes("dev-hub", rep)
    assert ("dev-hub", "deployed", False, True) in {k[:4] for k in rep.konflikte}


def test_should_skip_deployed_for_archived_entries():
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), PORTS, _fetch)
    assert "deployed" not in _changes("old-tool", rep)
    assert "old-tool" not in {n for n, _ in rep.deployed_nicht_belegbar}


def test_should_attach_a_source_to_every_change():
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), PORTS, _fetch)
    assert rep.changes
    for c in rep.changes:
        assert c.quelle.startswith(("gh api repos/", "infra/ports.yaml")), c


def test_should_record_api_failure_instead_of_guessing():
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), PORTS, lambda full: None)
    assert not rep.changes
    assert {n for n, _ in rep.fehler} == {"dev-hub", "meiki-hub", "frist-hub", "aifw", "old-tool"}


# --- textueller Patch -----------------------------------------------------------


def test_should_write_meta_top_level_for_lean_archived_entry_and_into_rich_otherwise():
    rep = rrs.derive(yaml.safe_load(CANON_TEXT), PORTS, _fetch)
    neu = yaml.safe_load(rrs.apply_text(CANON_TEXT, rep.changes))
    assert neu["repos"]["old-tool"]["github_meta"]["archived"] is True
    assert "rich" not in neu["repos"]["old-tool"]
    assert neu["repos"]["meiki-hub"]["rich"] == {
        "github": "meiki-lra/meiki-hub",
        "github_meta": {
            "visibility": "private",
            "archived": False,
            "default_branch": "main",
            "pushed_at": "2026-10-13",
        },
    }
    assert neu["repos"]["dev-hub"]["rich"]["type"] == "django"  # Bestand unangetastet


def test_should_refuse_to_write_when_patch_diverges_from_expected_dict(tmp_path):
    canon = tmp_path / "c.yaml"
    canon.write_text(CANON_TEXT)
    kaputt = rrs.Change("nicht-da", "github", None, "x/y", "q", rrs.ZIEL_RICH)
    try:
        rrs.schreibe(canon, CANON_TEXT, yaml.safe_load(CANON_TEXT), [kaputt])
    except KeyError:
        pass
    assert canon.read_text() == CANON_TEXT


def test_should_count_missing_fields_per_org_before_and_after():
    canon = yaml.safe_load(CANON_TEXT)
    rep = rrs.derive(canon, PORTS, _fetch)
    nachher = rrs.erwartet(canon, rep.changes)
    org_von = rrs.orgs(nachher)
    vorher = rrs.fehlstellen_je_org(canon, org_von)
    danach = rrs.fehlstellen_je_org(nachher, org_von)
    assert vorher["meiki-lra"] == {"gesamt": 2, "ohne_github": 2, "ohne_lifecycle": 2, "ohne_deployed": 2}
    assert danach["meiki-lra"] == {"gesamt": 2, "ohne_github": 0, "ohne_lifecycle": 2, "ohne_deployed": 1}
    assert org_von["aifw"] == "iilgmbh" and vorher["iilgmbh"]["ohne_github"] == 1
