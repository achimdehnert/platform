"""Tests fuer tools/flottenbild.py (KONZ-054, 178) — Rendern ohne Netz.

Der teuerste Fall: ein Knoten, der nicht antwortet, darf nicht fehlen. Er muss als
eigener Zustand auf der Seite stehen (K1 aus platform#2483).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flottenbild as fb  # noqa: E402


def _daten():
    return {
        "stand": "2026-08-30 12:00 UTC",
        "knoten": [
            {"knoten": "prod", "zustand": "gemessen", "load": "1.6 1.6 1.4", "kerne": 12, "ram_pct": 42,
             "swap_pct": 49, "swap_mb": 8191, "disk_pct": 70, "container": 63, "container_gesamt": 75,
             "unhealthy": [], "restarting": ["travel_beat_celery_beat"], "uptime_tage": 55,
             "rolle": "Prod", "auflage": {}, "historie": ["2026-08-30: Swap 8 GB"], "verified": "2026-08-30",
             "verified_bis": "", "ip": "88.198.191.108", "arch": "amd64", "provider": "Hetzner", "server_type": "cpx52"},
            {"knoten": "netcup", "zustand": "unerreichbar", "grund": "Connection timed out",
             "rolle": "Backup", "auflage": {"runner": False, "grund": "ADR-289"}, "historie": [], "verified": "2026-08-30",
             "verified_bis": "", "ip": "152.53.136.219", "arch": "amd64", "provider": "netcup", "server_type": ""},
            {"knoten": "gx10", "zustand": "geplant", "rolle": "Inferenz", "auflage": {}, "historie": [],
             "verified": "False", "verified_bis": "2026-09-30", "ip": None, "arch": "aarch64", "provider": "owner", "server_type": "gx10"},
        ],
        "dienste_je_host": {"prod": {"aktiv": ["risk-hub"], "stillgelegt": ["travel-beat"], "blockiert": []}},
        "prometheus": {"zustand": "gemessen",
                       "targets": [{"job": "fleet-node", "host": "prod-b", "health": "up"}],
                       "alerts": [{"name": "HostSwapHigh", "host": "prod", "name_": "", "state": "firing"}]},
        "melder": {"journal": {"gesamt": 2, "im_gate": 1, "ueberfaellig": 0, "mit_kommando": 0,
                               "eintraege": [{"id": "0.7.18 speicher::platform", "laeufe": 6, "im_gate": True, "ueberfaellig": False, "note": "Swap"}]},
                   "alarmwege": {"exit": 1, "kanaele": [{"kanal": "discord-owner", "ok": False, "blind": False, "grund": "letzte Probe failure"},
                                                         {"kanal": "github-issue-owner", "ok": True, "blind": False, "grund": "Erfolg vor 0 d"}]},
                   "erreichbarkeit": {"exit": 1, "kurz": "1 von 27"}, "hosts_audit": {"exit": 0, "kurz": "keine Findings"}},
    }


def test_should_render_unreachable_node_as_its_own_state_not_omit_it():
    seite = fb.render(_daten())
    assert "netcup" in seite and "unerreichbar" in seite and "Connection timed out" in seite


def test_should_put_the_denominator_from_hosts_yaml_in_the_first_kpi():
    seite = fb.render(_daten())
    assert "1 / 3" in seite  # 1 gemessen von 3 Knoten (geplant zaehlt im Nenner)


def test_should_mark_a_firing_alert_and_a_restart_loop_as_critical():
    seite = fb.render(_daten())
    assert 'class="node crit"' in seite
    assert "Restart-Schleife" in seite and "HostSwapHigh" in seite


def test_should_show_planned_node_with_deadline():
    seite = fb.render(_daten())
    assert "gx10" in seite and "2026-09-30" in seite and "geplant" in seite


def test_should_show_alarm_channels_and_journal_gate():
    seite = fb.render(_daten())
    assert "discord-owner" in seite and "fehlt" in seite and "belegt" in seite
    assert "0.7.18 speicher::platform" in seite and "im Gate" in seite


def test_should_escape_html_from_sources():
    d = _daten()
    d["knoten"][0]["rolle"] = "<script>alert(1)</script>"
    assert "<script>" not in fb.render(d)


def test_should_treat_missing_prometheus_as_no_all_clear():
    d = _daten()
    d["prometheus"] = {"zustand": "unerreichbar", "grund": "ssh"}
    seite = fb.render(d)
    assert "keine Entwarnung" in seite


def test_should_parse_probe_line_with_twelve_fields():
    zeile = "1.60 1.62 1.43|12|23456|9851|8191|4017|70|63|75|a,b|x|4776872"
    f = zeile.split("|")
    assert len(f) == 12
    assert fb.HOST_KOMMANDO.count("%s") == 12
