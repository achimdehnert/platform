"""Tests für tools/session-leases (C1 — Parallel-Session-Sichtbarkeit)."""

import datetime as dt
import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_loader(
    "session_leases",
    importlib.machinery.SourceFileLoader(
        "session_leases", str(Path(__file__).resolve().parents[1] / "session-leases")
    ),
)
session_leases = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(session_leases)

NOW = dt.datetime(2026, 7, 20, 12, 0, tzinfo=dt.timezone.utc)


def _lease(**kw):
    base = {
        "session_id": "s1",
        "owner": "achim-dehnert",
        "repo": "platform",
        "branch": "session/2026-07-20/achim-dehnert/demo",
        "worktree": "/tmp/wt",
        "created_at": "2026-07-20T08:00:00Z",
        "last_touch": "2026-07-20T08:00:00Z",
        "expires_at": "2026-07-27T08:00:00Z",
    }
    base.update(kw)
    return base


def test_should_classify_unexpired_lease_as_active():
    assert session_leases.classify(_lease(), NOW) == "aktiv"


def test_should_classify_expired_lease_as_expired():
    lease = _lease(expires_at="2026-07-01T08:00:00Z")
    assert session_leases.classify(lease, NOW) == "abgelaufen"


def test_should_classify_stale_but_unexpired_lease_as_dormant():
    """Kern des Echtlauf-Befunds: lange TTL machte 7 Tage alte Leases 'aktiv'."""
    lease = _lease(last_touch="2026-07-13T08:00:00Z", expires_at="2026-07-27T08:00:00Z")
    assert session_leases.classify(lease, NOW) == "ruhend"


def test_should_hide_dormant_leases_from_default_view():
    dormant = _lease(last_touch="2026-07-13T08:00:00Z")
    out = session_leases.render([dormant], NOW, repo_filter=None)
    assert "0 aktiv" in out
    assert "verborgen" in out


def test_should_classify_unreadable_lease_as_broken():
    assert session_leases.classify({"_error": "kaputt"}, NOW) == "defekt"


def test_should_treat_unparseable_expiry_as_active_not_silently_dropped():
    """Unlesbares Ablaufdatum darf die Session nicht unsichtbar machen."""
    assert session_leases.classify(_lease(expires_at="niemals"), NOW) == "aktiv"


def test_should_report_broken_lease_files_instead_of_skipping(tmp_path):
    (tmp_path / "ok.json").write_text(json.dumps(_lease()))
    (tmp_path / "kaputt.json").write_text("{nicht json")
    leases = session_leases.load_leases(tmp_path)
    assert len(leases) == 2
    assert any(lease.get("_error") for lease in leases)


def test_should_return_empty_list_for_missing_lease_dir(tmp_path):
    assert session_leases.load_leases(tmp_path / "gibtsnicht") == []


def test_should_say_so_when_no_leases_match_repo():
    out = session_leases.render([_lease()], NOW, repo_filter="anderes-repo")
    assert "Keine offenen Session-Leases" in out


def test_brief_should_emit_one_line_per_active_lease():
    out = session_leases.render_brief([_lease(), _lease(session_id="s2")], NOW)
    assert out.count("\n") == 2


def test_brief_should_be_empty_when_nobody_else_is_active():
    """Leere Ausgabe ist das Signal 'niemand sonst' — darf nie faelschlich leer sein."""
    dormant = _lease(last_touch="2026-07-13T08:00:00Z")
    assert session_leases.render_brief([dormant], NOW) == ""
    assert session_leases.render_brief([], NOW) == ""


def test_should_list_active_lease_with_repo_owner_and_branch():
    out = session_leases.render([_lease()], NOW, repo_filter=None)
    assert "platform" in out
    assert "achim-dehnert" in out
    assert "1 aktiv" in out
