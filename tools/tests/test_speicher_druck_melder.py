"""Drill fuer tools/speicher_druck_melder.py (platform#3607).

Die Druck-Fixture bildet den OOM vom 2026-09-26 nach: 16 Worker je ~1,4 GB in einer
Login-Sitzung, daneben ein kleiner Runner-Prozess. Die Ruhe-Fixture ist die Messung auf
dev-desktop vom 2026-09-29 (PSI 0,00, 65 % verfuegbar, Swap 5 von 7 GB). Aus dem hohen
Swap darf der Melder KEINEN Befund machen (Negativkontrolle).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import melder_ergebnis  # noqa: E402
import speicher_druck_melder as sdm  # noqa: E402

JETZT = datetime(2026, 9, 26, 8, 6, tzinfo=timezone.utc)
SITZUNG = "/user.slice/user-1000.slice/session-34780.scope"
RUNNER = "/system.slice/actions.runner.achimdehnert-mcp-hub.mcp-hub-staging-ci.service"
GIB = 1024 * 1024  # kB


def _proc(
    tmp_path: Path,
    *,
    verfuegbar_kb: int,
    psi_some: float,
    oom_kill: int = 0,
    prozesse: list[tuple[int, str, str, int, int]] = (),
) -> Path:
    proc = tmp_path / "proc"
    (proc / "pressure").mkdir(parents=True)
    (proc / "meminfo").write_text(
        f"MemTotal:       {32 * GIB} kB\n"
        f"MemFree:          102144 kB\n"
        f"MemAvailable:   {verfuegbar_kb} kB\n"
        f"SwapTotal:      {7 * GIB} kB\n"
        f"SwapFree:       {2 * GIB} kB\n"
    )
    (proc / "pressure" / "memory").write_text(
        f"some avg10={psi_some:.2f} avg60={psi_some:.2f} avg300=0.00 total=1\n"
        "full avg10=0.00 avg60=0.00 avg300=0.00 total=1\n"
    )
    (proc / "vmstat").write_text(f"nr_free_pages 25536\noom_kill {oom_kill}\n")
    for pid, name, cgroup, anon_kb, swap_kb in prozesse:
        d = proc / str(pid)
        d.mkdir()
        (d / "status").write_text(
            f"Name:\t{name}\nRssAnon:\t{anon_kb} kB\nVmSwap:\t{swap_kb} kB\n"
        )
        (d / "cgroup").write_text(f"0::{cgroup}\n")
    return proc


def _druck(tmp_path: Path, oom_kill: int = 1) -> Path:
    worker = [(129822 + i, "python", SITZUNG, 1_000_000, 400_000) for i in range(16)]
    return _proc(
        tmp_path,
        verfuegbar_kb=300_000,
        psi_some=62.0,
        oom_kill=oom_kill,
        prozesse=[*worker, (3774066, "gpg-agent", RUNNER, 44, 0)],
    )


def test_should_stay_quiet_at_rest_despite_high_swap(tmp_path):
    proc = _proc(tmp_path, verfuegbar_kb=int(0.65 * 32 * GIB), psi_some=0.0)
    ergebnis, journal = sdm.messe(proc, None, JETZT)
    assert ergebnis["regeln"] == []
    assert ergebnis["swap_belegt_prozent"] > 70
    assert journal is None


def test_should_name_the_holding_cgroup_under_pressure(tmp_path):
    ergebnis, journal = sdm.messe(_druck(tmp_path), None, JETZT)
    assert any(r.startswith("psi-some-avg60") for r in ergebnis["regeln"])
    assert any(r.startswith("mem-verfuegbar") for r in ergebnis["regeln"])
    top = journal["gruppen"][0]
    assert top["cgroup"] == SITZUNG
    assert top["prozesse"] == 16
    assert top["name"] == "python"
    assert top["mb"] == round(16 * 1_400_000 / 1024)


def test_should_fire_each_rule_alone(tmp_path):
    gesamt = 32 * GIB
    assert sdm.bewerte({"MemTotal": gesamt, "MemAvailable": gesamt}, {"some": 10.0}, 0)
    assert sdm.bewerte(
        {"MemTotal": gesamt, "MemAvailable": gesamt // 20}, {"some": 0.0}, 0
    )
    assert sdm.bewerte({"MemTotal": gesamt, "MemAvailable": gesamt}, {"some": 0.0}, 1)
    assert not sdm.bewerte(
        {"MemTotal": gesamt, "MemAvailable": gesamt}, {"some": 9.9}, 0
    )


def test_should_count_kill_between_runs_but_not_across_reboot(tmp_path):
    proc = _proc(
        tmp_path, verfuegbar_kb=int(0.65 * 32 * GIB), psi_some=0.0, oom_kill=35
    )
    vorher = {"ergebnis": {"oom_kill_zaehler": 34}}
    assert sdm.messe(proc, vorher, JETZT)[0]["regeln"] == [
        "oom-kill +1 seit letztem Lauf"
    ]
    nach_neustart = {"ergebnis": {"oom_kill_zaehler": 40}}
    assert sdm.messe(proc, nach_neustart, JETZT)[0]["regeln"] == []


def test_should_rate_limit_snapshots_and_keep_last_finding(tmp_path):
    proc = _druck(tmp_path)
    e1, j1 = sdm.messe(proc, None, JETZT)
    e2, j2 = sdm.messe(proc, {"ergebnis": e1}, JETZT + timedelta(minutes=1))
    assert j1 is not None and j2 is None
    assert e2["letzter_befund"]["zeit"] == e1["letzter_befund"]["zeit"]
    _, j3 = sdm.messe(proc, {"ergebnis": e2}, JETZT + timedelta(minutes=5))
    assert j3 is not None


def test_should_report_finding_for_24h_then_clear(tmp_path):
    datei = tmp_path / "e.json"
    e, _ = sdm.messe(_druck(tmp_path), None, JETZT)
    ruhig = tmp_path / "ruhig"
    ruhig.mkdir()
    proc_ruhig = _proc(
        ruhig, verfuegbar_kb=int(0.65 * 32 * GIB), psi_some=0.0, oom_kill=1
    )
    e_spaeter, _ = sdm.messe(proc_ruhig, {"ergebnis": e}, JETZT + timedelta(hours=2))
    assert e_spaeter["regeln"] == [] and e_spaeter["letzter_befund"] is not None

    t = JETZT + timedelta(hours=2)
    melder_ergebnis.schreibe(datei, sdm.MELDER, e_spaeter, gemessen_am=t)
    rc, text = sdm.zeile_lesen(melder_ergebnis.lies(datei, jetzt=t), t)
    assert rc == 1 and SITZUNG in text and "16x python" in text

    t2 = JETZT + timedelta(hours=25)
    melder_ergebnis.schreibe(datei, sdm.MELDER, e_spaeter, gemessen_am=t2)
    rc, _ = sdm.zeile_lesen(melder_ergebnis.lies(datei, jetzt=t2), t2)
    assert rc == 0


def test_should_flag_stale_or_missing_result_as_blind(tmp_path):
    assert sdm.zeile_lesen(None, JETZT)[0] == 2
    alt = {"gemessen_am": "2026-09-26T07:30:00Z", "ergebnis": {}}
    assert sdm.zeile_lesen(alt, JETZT)[0] == 2


def test_should_write_result_and_journal_via_cli(tmp_path, capsys):
    proc = _druck(tmp_path)
    journal = tmp_path / "j.jsonl"
    ergebnis = tmp_path / "e.json"
    args = [
        "--proc",
        str(proc),
        "--journal",
        str(journal),
        "--ergebnis-datei",
        str(ergebnis),
    ]
    assert sdm.main(args) == 0  # Messen endet immer mit 0
    assert "BEFUND" in capsys.readouterr().out
    zeile = json.loads(journal.read_text().splitlines()[0])
    assert zeile["gruppen"][0]["cgroup"] == SITZUNG
    assert json.loads(ergebnis.read_text())["schema"] == melder_ergebnis.SCHEMA
    assert sdm.main([*args, "--lesen"]) == 1


def test_should_never_read_command_lines(tmp_path, monkeypatch):
    """Secrets koennen in /proc/<pid>/cmdline oder environ stehen: jeder Zugriff darauf
    laesst den Test scheitern, nicht erst ein Treffer in der Ausgabe."""
    proc = _druck(tmp_path)
    original = Path.read_text

    def wache(self, *a, **k):
        assert self.name not in {"cmdline", "environ"}, f"liest {self}"
        return original(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", wache)
    _, journal = sdm.messe(proc, None, JETZT)
    assert journal is not None
