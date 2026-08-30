"""Tests für tools/backup_meter.py (ADR-241 §4)."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backup_meter import (  # noqa: E402
    evaluate_app,
    evaluate_drill,
    newest_snapshot_age_hours,
    render_report,
)

NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _snap(tag, hours_ago):
    t = NOW - timedelta(hours=hours_ago)
    return {"time": t.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00", "tags": [tag]}


ENTRY = {"app": "risk-hub", "tag": "risk-hub", "max_age_hours": 26}


def test_should_pass_when_fresh_snapshot_within_soll():
    result = evaluate_app(ENTRY, [_snap("risk-hub", 4)], NOW)
    assert result["status"] == "ok"
    assert result["reasons"] == []


def test_should_flag_violation_when_no_snapshot_for_tag():
    result = evaluate_app(ENTRY, [_snap("other-hub", 1)], NOW)
    assert result["status"] == "violation"
    assert "kein restic-Snapshot" in result["reasons"][0]


def test_should_flag_violation_when_snapshot_too_old():
    result = evaluate_app(ENTRY, [_snap("risk-hub", 30)], NOW)
    assert result["status"] == "violation"
    assert "alt" in result["reasons"][0]


def test_should_defer_in_scaffold_mode_when_snapshots_none():
    # Offsite noch nicht provisioniert → deferred, NICHT violation (CI bleibt grün)
    result = evaluate_app(ENTRY, None, NOW)
    assert result["status"] == "deferred"


def test_should_defer_explicitly_marked_entry():
    entry = {"app": "frozen-hub", "deferred": True, "reason": "eingefroren"}
    result = evaluate_app(entry, [], NOW)
    assert result["status"] == "deferred"
    assert result["reasons"] == ["eingefroren"]


def test_should_pick_most_recent_snapshot_of_tag():
    snaps = [_snap("risk-hub", 30), _snap("risk-hub", 3), _snap("risk-hub", 50)]
    age = newest_snapshot_age_hours(snaps, "risk-hub", NOW)
    assert abs(age - 3.0) < 0.01


def test_should_parse_nanosecond_restic_timestamp():
    snaps = [{"time": "2026-06-21T08:00:00.123456789+00:00", "tags": ["x"]}]
    age = newest_snapshot_age_hours(snaps, "x", NOW)
    assert abs(age - 4.0) < 0.01


def test_should_flag_missing_drill_when_enforced(tmp_path):
    result = evaluate_drill(tmp_path, NOW, enforce=True)
    assert result["status"] == "violation"


def test_should_defer_missing_drill_when_not_enforced(tmp_path):
    # Default bis G3: kein Protokoll → deferred, NICHT violation (kein Spam)
    result = evaluate_drill(tmp_path, NOW, enforce=False)
    assert result["status"] == "deferred"


def test_should_pass_drill_when_recent_protocol(tmp_path):
    (tmp_path / "2026-06-20-risk-hub.md").write_text("drill ok")
    result = evaluate_drill(tmp_path, NOW, enforce=True)
    assert result["status"] == "ok"


def test_should_defer_stale_drill_when_not_enforced(tmp_path):
    import os

    p = tmp_path / "2026-01-01-risk-hub.md"
    p.write_text("alt")
    old = NOW.timestamp() - 200 * 86400
    os.utime(p, (old, old))
    assert evaluate_drill(tmp_path, NOW, enforce=False)["status"] == "deferred"
    assert evaluate_drill(tmp_path, NOW, enforce=True)["status"] == "violation"


def test_should_ignore_readme_in_drills(tmp_path):
    (tmp_path / "README.md").write_text("nur Doku")
    result = evaluate_drill(tmp_path, NOW, enforce=True)
    assert result["status"] == "violation"


def test_should_count_each_bucket_in_report():
    results = [
        {"app": "a", "status": "ok", "reasons": []},
        {"app": "b", "status": "violation", "reasons": ["kaputt"]},
        {"app": "c", "status": "deferred", "reasons": ["scaffold"]},
    ]
    report = render_report(results)
    assert "1 konform · 1 Verletzungen · 1 deferred" in report
    assert "**b**: kaputt" in report


# ── Mehrteilige Apps + Pfad-Pruefung (Fehlalarm 2026-08-03) ────────────────
# risk-hub wird ueber ZWEI Snapshots gesichert: pgdump unter Tag `risk_hub_db`
# und die Volumes im Sammel-Snapshot `volumes`. Der Melder kannte nur einen Tag
# pro App und erwartete `risk-hub` — den vergibt der taegliche Job gar nicht.
# Ergebnis: "89.6 h alt" gemeldet, waehrend beide echten Snapshots 7,8 h alt
# waren. Der Sammel-Snapshot macht Tag-Frische allein wertlos, deshalb Pfade.


def _snap_pfade(tags, hours_ago, paths):
    t = NOW - timedelta(hours=hours_ago)
    return {
        "time": t.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00",
        "tags": list(tags),
        "paths": list(paths),
    }


RISK_ENTRY = {
    "app": "risk-hub",
    "max_age_hours": 26,
    "checks": [
        {"tag": "risk_hub_db", "label": "Datenbank"},
        {
            "tag": "volumes",
            "label": "Medien + MinIO",
            "paths_contain": [
                "risk-hub_risk_hub_media/_data",
                "risk-hub_risk_hub_minio_data/_data",
            ],
        },
    ],
}

VOLUME_PFADE = [
    "/mnt/HC_Volume_105908261/docker/volumes/devhub_media_prod/_data",
    "/mnt/HC_Volume_105908261/docker/volumes/risk-hub_risk_hub_media/_data",
    "/mnt/HC_Volume_105908261/docker/volumes/risk-hub_risk_hub_minio_data/_data",
]


def test_should_pass_when_all_parts_of_a_multipart_app_are_fresh():
    snaps = [
        _snap("risk_hub_db", 7.8),
        _snap_pfade(["volumes"], 7.8, VOLUME_PFADE),
    ]
    assert evaluate_app(RISK_ENTRY, snaps, NOW)["status"] == "ok"


def test_should_flag_violation_when_only_the_database_part_is_fresh():
    """Die Haelfte gesichert ist nicht gesichert."""
    result = evaluate_app(RISK_ENTRY, [_snap("risk_hub_db", 7.8)], NOW)
    assert result["status"] == "violation"
    assert any("Medien + MinIO" in r for r in result["reasons"])


def test_should_flag_violation_when_collective_snapshot_drops_the_app_paths():
    """Kern-Regression: frischer Sammel-Snapshot OHNE die Pfade der App.

    Ohne Pfad-Pruefung waere das gruen — der Tag `volumes` ist ja frisch. Genau
    diese Luecke soll der Melder nicht haben.
    """
    ohne_risk = [p for p in VOLUME_PFADE if "risk-hub" not in p]
    snaps = [
        _snap("risk_hub_db", 7.8),
        _snap_pfade(["volumes"], 1, ohne_risk),
    ]
    result = evaluate_app(RISK_ENTRY, snaps, NOW)
    assert result["status"] == "violation"
    assert any("enthaelt" in r for r in result["reasons"])


def test_should_flag_violation_when_only_minio_path_is_missing():
    """Auch ein einzelner fehlender Pfad zaehlt — nicht 'einer reicht'."""
    ohne_minio = [p for p in VOLUME_PFADE if "minio" not in p]
    snaps = [_snap("risk_hub_db", 7.8), _snap_pfade(["volumes"], 1, ohne_minio)]
    assert evaluate_app(RISK_ENTRY, snaps, NOW)["status"] == "violation"


def test_should_ignore_stale_snapshot_that_matches_paths():
    """Passende Pfade, aber zu alt — bleibt eine Verletzung."""
    snaps = [_snap("risk_hub_db", 7.8), _snap_pfade(["volumes"], 90, VOLUME_PFADE)]
    result = evaluate_app(RISK_ENTRY, snaps, NOW)
    assert result["status"] == "violation"
    assert any("90.0 h alt" in r for r in result["reasons"])


def test_should_keep_single_tag_entries_working():
    """Rueckwaertskompatibel: Eintraege ohne `checks` verhalten sich wie bisher."""
    assert evaluate_app(ENTRY, [_snap("risk-hub", 4)], NOW)["status"] == "ok"
    assert evaluate_app(ENTRY, [_snap("risk-hub", 30)], NOW)["status"] == "violation"


def test_should_match_paths_by_substring_not_exact():
    """Der Hetzner-Mountpoint darf sich aendern, ohne den Melder rot zu faerben."""
    umgezogen = [
        p.replace("HC_Volume_105908261", "HC_Volume_999") for p in VOLUME_PFADE
    ]
    snaps = [_snap("risk_hub_db", 7.8), _snap_pfade(["volumes"], 1, umgezogen)]
    assert evaluate_app(RISK_ENTRY, snaps, NOW)["status"] == "ok"


def test_should_treat_real_expected_apps_entry_as_multipart():
    """Ohne Test-Naht: die echte governance/backup/expected-apps.json."""
    import json

    pfad = Path(__file__).resolve().parents[2] / "governance/backup/expected-apps.json"
    eintrag = next(e for e in json.loads(pfad.read_text()) if e["app"] == "risk-hub")
    assert not eintrag.get("deferred")
    tags = {c["tag"] for c in eintrag["checks"]}
    assert tags == {"risk_hub_db", "volumes"}
    volumes = next(c for c in eintrag["checks"] if c["tag"] == "volumes")
    assert any("minio" in p for p in volumes["paths_contain"])


# ── KONZ-054 E3: der Nenner ist Teil der Meldung, deferred ist kein Gruen ─────


def _r(app, status):
    return {"app": app, "status": status, "reasons": ["x"] if status != "ok" else []}


def test_should_exit_3_when_nothing_violated_but_not_everything_measured():
    from backup_meter import exit_code

    assert exit_code([_r("a", "ok"), _r("b", "deferred")]) == 3


def test_should_exit_1_when_violations_outrank_scope_gap():
    from backup_meter import exit_code

    assert exit_code([_r("a", "violation"), _r("b", "deferred")]) == 1


def test_should_exit_0_only_when_everything_is_measured_and_ok():
    from backup_meter import exit_code

    assert exit_code([_r("a", "ok"), _r("b", "ok")]) == 0


def test_should_put_the_denominator_in_the_first_report_line():
    from backup_meter import deckungszeile, render_report

    results = [_r("a", "ok")] + [_r(f"d{i}", "deferred") for i in range(8)]
    zeile = deckungszeile(results)
    assert "1 von 9" in zeile and "Scope-Luecke" in zeile
    assert render_report(results).splitlines()[2] == zeile


def test_should_not_count_the_drill_as_an_app_in_the_denominator():
    from backup_meter import deckungszeile

    assert "2 von 2" in deckungszeile(
        [_r("a", "ok"), _r("b", "ok"), _r("restore-drill", "ok")]
    )
