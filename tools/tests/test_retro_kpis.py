"""Tests für tools/retro_kpis.py (session-retro Längsschnitt-Hebel, v2.2)."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retro_kpis import (  # noqa: E402
    _create_gate_issue,
    _existing_gate_issue,
    _gate_issue_title,
    file_gate_issues,
    k1_auswertung,
    load_reports,
    load_woerterbuch,
    parse_frontmatter,
    registry_coverage,
    tool_sha256,
)

SAMPLE = """---
retro_schema: 1
date: 2026-06-14
repo_scope: [coach-hub, platform]
session_id: 2d7cd9
footprint: deep
findings_total: 12
findings_survived: 8
refuted_rate: 0.33
phase3_refuted: 2
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 3
  risiko_debt: 2
gate_candidates: [a-gate, b-gate]
recurring_findings: [stale-local-vs-origin, worktree-orphan-accumulation]
---

# Body, darf NICHT geparst werden
recurring_findings: [should-be-ignored]
"""


def test_should_parse_inline_list_and_scalars():
    fm = parse_frontmatter(SAMPLE)
    assert fm is not None
    assert fm["session_id"] == "2d7cd9"
    assert fm["refuted_rate"] == "0.33"
    assert fm["recurring_findings"] == [
        "stale-local-vs-origin",
        "worktree-orphan-accumulation",
    ]


def test_should_parse_nested_scores_block_as_ints():
    fm = parse_frontmatter(SAMPLE)
    assert fm["scores"] == {
        "zielerreichung": 4,
        "architektur_design": 3,
        "risiko_debt": 2,
    }


def test_should_not_leak_body_keys_into_frontmatter():
    # Der `recurring_findings`-Eintrag IM BODY darf den Frontmatter-Wert nicht überschreiben.
    fm = parse_frontmatter(SAMPLE)
    assert "should-be-ignored" not in fm["recurring_findings"]


def test_should_return_none_without_frontmatter():
    assert parse_frontmatter("kein Frontmatter hier\n") is None


def test_should_skip_extern_briefings_and_load_real_reports(tmp_path):
    (tmp_path / "session-retro-2026-06-14-x-aaa.md").write_text(
        SAMPLE, encoding="utf-8"
    )
    (tmp_path / "session-retro-extern-2026-06-14-x-aaa.md").write_text(
        SAMPLE, encoding="utf-8"
    )
    (tmp_path / "unrelated.md").write_text("nope", encoding="utf-8")
    reports = load_reports(str(tmp_path))
    assert len(reports) == 1  # -extern- + unrelated ausgeschlossen
    assert reports[0]["_path"] == "session-retro-2026-06-14-x-aaa.md"


class TestMultiDirLoadReports:
    """T-11 (repo-optimize 2026-07-03): load_reports() akzeptiert seit #891/#886
    eine LISTE von Verzeichnissen (git-durables docs/retros/ + Skill-Schreibpfad
    ~/shared/) und dedupliziert nach Dateiname — bislang war das nur per Code-
    Review verifiziert, kein Test rief die Multi-Dir-Variante auf."""

    SAMPLE_B = SAMPLE.replace("2d7cd9", "other-session-id")

    def test_should_accept_list_of_directories(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "session-retro-2026-06-14-x-aaa.md").write_text(
            SAMPLE, encoding="utf-8"
        )
        (dir_b / "session-retro-2026-06-15-y-bbb.md").write_text(
            self.SAMPLE_B, encoding="utf-8"
        )

        reports = load_reports([str(dir_a), str(dir_b)])

        assert len(reports) == 2
        assert {r["_path"] for r in reports} == {
            "session-retro-2026-06-14-x-aaa.md",
            "session-retro-2026-06-15-y-bbb.md",
        }

    def test_should_dedupe_same_filename_across_dirs_first_dir_wins(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        same_name = "session-retro-2026-06-14-x-aaa.md"
        (dir_a / same_name).write_text(SAMPLE, encoding="utf-8")
        # gleicher Dateiname in dir_b, aber INHALTLICH anders — first-dir-wins
        # muss die dir_a-Version behalten, nicht die aus dir_b nachladen.
        (dir_b / same_name).write_text(self.SAMPLE_B, encoding="utf-8")

        reports = load_reports([str(dir_a), str(dir_b)])

        assert len(reports) == 1  # kein Doppelzählen trotz zwei Fundstellen
        assert reports[0]["session_id"] == "2d7cd9"  # dir_a-Inhalt gewinnt

    def test_should_sum_totals_across_both_dirs_without_overlap(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "session-retro-2026-06-14-x-aaa.md").write_text(
            SAMPLE, encoding="utf-8"
        )
        (dir_a / "session-retro-extern-2026-06-14-x-aaa.md").write_text(
            SAMPLE, encoding="utf-8"
        )
        (dir_b / "session-retro-2026-06-15-y-bbb.md").write_text(
            self.SAMPLE_B, encoding="utf-8"
        )
        (dir_b / "unrelated.md").write_text("nope", encoding="utf-8")

        reports = load_reports([str(dir_a), str(dir_b)])

        # Gesamtzahl = 2 echte Retros; -extern- (dir_a) + unrelated.md (dir_b) ausgeschlossen.
        assert len(reports) == 2


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestFileIssues:
    """--file-issues (Retro d80d23/2026-07-16): GATE-PFLICHT-Slugs sollen als durables
    'Gate: <slug>'-Issue landen statt nur als Prosa im Report zu versanden — genau die
    Lücke, die `session-retro-2026-07-11-platform-d2522c-incr.md` für
    `handover-stale-vor-merge` explizit als "ohne systemisches Gate" vermerkte."""

    def test_should_format_gate_issue_title_from_slug(self):
        assert (
            _gate_issue_title("stale-local-clone-as-ground-truth")
            == "Gate: stale-local-clone-as-ground-truth"
        )

    def test_should_find_existing_gate_issue_by_exact_title_match(self):
        listing = _proc(
            stdout='[{"number": 42, "title": "Gate: my-slug", '
            '"state": "OPEN", "url": "https://x/42"}]'
        )
        with patch("retro_kpis.subprocess.run", return_value=listing) as run:
            found = _existing_gate_issue("owner/repo", "my-slug")
        assert found == {
            "number": 42,
            "title": "Gate: my-slug",
            "state": "OPEN",
            "url": "https://x/42",
        }
        run.assert_called_once()

    def test_should_ignore_substring_only_title_matches(self):
        # gh --search kann lose matchen; nur ein EXAKTER Titel-Treffer zaehlt,
        # sonst wuerde z.B. "Gate: my-slug-v2" faelschlich als Duplikat gelten.
        listing = _proc(
            stdout='[{"number": 1, "title": "Gate: my-slug-v2", '
            '"state": "OPEN", "url": "https://x/1"}]'
        )
        with patch("retro_kpis.subprocess.run", return_value=listing):
            found = _existing_gate_issue("owner/repo", "my-slug")
        assert found is None

    def test_should_fail_open_on_gh_error(self):
        with patch(
            "retro_kpis.subprocess.run", return_value=_proc(returncode=1, stderr="boom")
        ):
            assert _existing_gate_issue("owner/repo", "my-slug") is None

    def test_should_fail_open_on_missing_gh(self):
        with patch("retro_kpis.subprocess.run", side_effect=OSError("no gh")):
            assert _existing_gate_issue("owner/repo", "my-slug") is None

    def test_should_return_url_from_last_stdout_line_on_create(self):
        created = _proc(
            stdout="creating issue...\nhttps://github.com/owner/repo/issues/99\n"
        )
        with patch("retro_kpis.subprocess.run", return_value=created) as run:
            url = _create_gate_issue(
                "owner/repo", "my-slug", ["s1", "s2"], {"s1": "session-retro-a.md"}
            )
        assert url == "https://github.com/owner/repo/issues/99"
        args = run.call_args[0][0]
        assert args[:4] == ["gh", "issue", "create", "--repo"]
        assert "Gate: my-slug" in args

    def test_should_return_none_when_create_fails(self):
        with patch("retro_kpis.subprocess.run", return_value=_proc(returncode=1)):
            assert _create_gate_issue("owner/repo", "my-slug", ["s1"], {}) is None

    def test_should_skip_all_when_gh_not_authenticated(self, capsys):
        with patch(
            "retro_kpis.subprocess.run", return_value=_proc(returncode=1)
        ) as run:
            file_gate_issues({"my-slug": ["s1", "s2"]}, [], "owner/repo")
        out = capsys.readouterr().out
        assert "übersprungen" in out
        run.assert_called_once()  # nur der auth-status-Check, keine Such-/Create-Calls danach

    def test_should_create_missing_and_report_existing_gate_issues(self, capsys):
        reports = [
            {
                "session_id": "s1",
                "_path": "session-retro-a.md",
                "recurring_findings": ["missing-slug"],
            },
            {
                "session_id": "s2",
                "_path": "session-retro-b.md",
                "recurring_findings": ["existing-slug"],
            },
        ]

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["gh", "auth"]:
                return _proc(returncode=0)
            if cmd[:3] == ["gh", "issue", "list"]:
                if "existing-slug" in cmd[8]:
                    return _proc(
                        stdout='[{"number": 5, "title": "Gate: existing-slug", '
                        '"state": "CLOSED", "url": "https://x/5"}]'
                    )
                return _proc(stdout="[]")
            if cmd[:3] == ["gh", "issue", "create"]:
                return _proc(stdout="https://github.com/owner/repo/issues/77\n")
            raise AssertionError(f"unexpected call: {cmd}")

        gated = {"missing-slug": ["s1"], "existing-slug": ["s2"]}
        with patch("retro_kpis.subprocess.run", side_effect=fake_run):
            file_gate_issues(gated, reports, "owner/repo")

        out = capsys.readouterr().out
        assert "existing-slug: bereits vorhanden — CLOSED https://x/5" in out
        assert (
            "missing-slug: neu angelegt — https://github.com/owner/repo/issues/77"
            in out
        )


# --- D6 (KONZ-038): Golden-Fixtures aus ECHTEN Retros + Parser-Haertung ----------
# Der Zaehler ist der einzige Sensor des Regel-Lebenszyklus; vor der K1-Baseline
# wird er gegen reale Reports mit bekannter Soll-Zaehlung gedrillt. a50bc6 traegt
# den Realfall, der 3 Phantom-Slugs erzeugte (Inline-Kommentar hinter der Liste).

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "retro_kpis"
_TOOL = Path(__file__).resolve().parents[1] / "retro_kpis.py"


def _run_kpis(*args):
    out = subprocess.run(
        [sys.executable, str(_TOOL), "--dir", str(FIXTURES), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_should_goldene_soll_zaehlung_liefern():
    out = _run_kpis()
    assert "Längsschnitt über 3 Retro-Reports" in out
    assert "claim-before-cheapest-check  ×3" in out
    assert "deferred-item-no-tracking-issue  ×2" in out
    assert "lint-failure-no-local-gate  ×1" in out


def test_should_a50bc6_phantom_slugs_nicht_mehr_zaehlen():
    out = _run_kpis()
    assert "Zählregel" not in out
    assert "verifiziert)" not in out
    assert "handover-stale-vor-merge]" not in out
    assert "handover-stale-vor-merge  ×1" in out  # der echte letzte Slug zählt weiter


def test_should_fenster_filter_nach_dateinamens_datum():
    out = _run_kpis("--since", "2026-07-31")
    assert "Längsschnitt über 2 Retro-Reports" in out
    assert "Fenster 2026-07-31" in out
    assert "claim-before-cheapest-check  ×2" in out
    assert "lint-failure-no-local-gate" not in out  # a50bc6 (07-02) vor dem Fenster


def test_should_unbekanntes_schema_laut_ausschliessen(tmp_path):
    import shutil

    src = FIXTURES / "session-retro-2026-07-31-platform-ec0588a8.md"
    (tmp_path / src.name).write_text(
        src.read_text(encoding="utf-8").replace("retro_schema: 1", "retro_schema: 99"),
        encoding="utf-8",
    )
    shutil.copy(FIXTURES / "session-retro-2026-07-02-frist-hub-a50bc6.md", tmp_path)
    out = subprocess.run(
        [sys.executable, str(_TOOL), "--dir", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout
    assert "Längsschnitt über 1 Retro-Reports" in out
    assert "unbekannt" in out and "ec0588a8" in out.split("##")[1]


def test_should_nicht_slugfoermige_eintraege_warnen_statt_zaehlen():
    fm = parse_frontmatter(
        "---\nrecurring_findings: [echter-slug, Kaputt (x:1, UPPER-CASE]\ndate: 2026-08-02\n---\nBody"
    )
    assert fm["recurring_findings"] == ["echter-slug"]
    assert any("NICHT gezählt" in w for w in fm["_parse_warnings"])


def test_should_kommentar_hinter_der_liste_ignorieren():
    fm = parse_frontmatter(
        "---\nrecurring_findings: [a-b-c, d-e-f]  # Kommentar (mit:Doppelpunkt)\n---\nBody"
    )
    assert fm["recurring_findings"] == ["a-b-c", "d-e-f"]
    assert "_parse_warnings" not in fm


# --- D6-Rest (KONZ-038): K1-Auswertung liest das Woerterbuch ---------------------
# Vor diesem Block war slug-woerterbuch.yaml ein Dokument OHNE Konsument: weder
# der Instrument-Pin noch "unmappbar = nicht bewertbar" wurden je gerechnet.

REPO_ROOT = Path(__file__).resolve().parents[2]
WB_PFAD = REPO_ROOT / "docs" / "governance" / "k1-baseline" / "slug-woerterbuch.yaml"

_WB_MIN = """\
baseline_window: 2026-07-19..2026-08-01
tool_sha256: deadbeef

top3:
  - canonical: claim-before-cheapest-check
    aliases: [claim-vor-billigstem-check]
  - canonical: deferred-item-no-tracking-issue
    aliases: []
  - canonical: workaround-without-tracking-anchor
    aliases: []

schwellen:
  wirksam_max: 0.700
  kill_ueber: 1.000
  min_retros: 8
"""


def _wb(tmp_path, text=_WB_MIN):
    p = tmp_path / "wb.yaml"
    p.write_text(text, encoding="utf-8")
    return load_woerterbuch(str(p))


def _reports(slug_listen):
    return [
        {"recurring_findings": s, "_path": f"r{i}.md"}
        for i, s in enumerate(slug_listen)
    ]


class TestWoerterbuchParser:
    def test_should_kanonische_slugs_und_aliase_lesen(self, tmp_path):
        wb = _wb(tmp_path)
        assert [e["canonical"] for e in wb["top3"]] == [
            "claim-before-cheapest-check",
            "deferred-item-no-tracking-issue",
            "workaround-without-tracking-anchor",
        ]
        assert wb["top3"][0]["aliases"] == ["claim-vor-billigstem-check"]
        assert wb["schwellen"] == {
            "wirksam_max": 0.7,
            "kill_ueber": 1.0,
            "min_retros": 8,
        }

    def test_should_none_liefern_wenn_pflichtangabe_fehlt(self, tmp_path):
        # Ohne tool_sha256 ist der Instrument-Pin nicht pruefbar — dann darf die
        # Auswertung nicht "irgendwie" rechnen, sondern gar nicht.
        assert _wb(tmp_path, _WB_MIN.replace("tool_sha256: deadbeef\n", "")) is None

    def test_should_echtes_eingefrorenes_woerterbuch_lesen(self):
        wb = load_woerterbuch(str(WB_PFAD))
        assert wb is not None
        assert len(wb["top3"]) == 3
        assert wb["schwellen"]["min_retros"] == 8


class TestK1Auswertung:
    def test_should_baseline_rate_und_ausgang_kill_rechnen(self, tmp_path):
        wb = _wb(tmp_path)
        # 8 Retros, 8 Top-3-Treffer => Summen-Rate 1.000 => noch "unentschieden"
        out = "\n".join(
            k1_auswertung(
                _reports([["claim-before-cheapest-check"]] * 8), wb, "deadbeef"
            )
        )
        assert "Rate 1.000" in out
        assert "→ Ausgang: unentschieden" in out

    def test_should_wirksam_nur_unter_der_vorregistrierten_schwelle(self, tmp_path):
        wb = _wb(tmp_path)
        # 10 Retros, 7 Treffer => 0.700 => genau auf der Schwelle => wirksam
        out = "\n".join(
            k1_auswertung(
                _reports([["claim-before-cheapest-check"]] * 7 + [[]] * 3),
                wb,
                "deadbeef",
            )
        )
        assert "→ Ausgang: wirksam (Rate 0.700 ≤ 0.700)" in out

    def test_should_kill_ueber_der_baseline_rate(self, tmp_path):
        wb = _wb(tmp_path)
        out = "\n".join(
            k1_auswertung(
                _reports(
                    [["claim-before-cheapest-check", "deferred-item-no-tracking-issue"]]
                    * 8
                ),
                wb,
                "deadbeef",
            )
        )
        assert "Rate 2.000" in out
        assert "→ Ausgang: Kill" in out

    def test_should_alias_auf_kanonischen_slug_mappen(self, tmp_path):
        wb = _wb(tmp_path)
        out = "\n".join(
            k1_auswertung(
                _reports([["claim-vor-billigstem-check"]] * 8), wb, "deadbeef"
            )
        )
        assert "claim-before-cheapest-check" in out and "×8" in out
        assert "Rate 1.000" in out  # der Alias zaehlt voll auf den kanonischen Slug
        assert "Nicht bewertbar" not in out

    def test_should_unmappbaren_slug_nicht_als_neu_bei_null_zaehlen(self, tmp_path):
        # Kern von EXT2-AD-2: ein umbenannter Slug darf die Rate nicht schoenen.
        wb = _wb(tmp_path)
        out = "\n".join(
            k1_auswertung(_reports([["voellig-neuer-slug"]] * 8), wb, "deadbeef")
        )
        assert "Nicht bewertbar — 1 Slug(s)" in out
        assert "voellig-neuer-slug ×8" in out
        assert "Summe Top-3" in out and "Rate 0.000" in out
        # ... und der Ausgang darf daraus NICHT "wirksam" machen? Doch — die Rate ist
        # echt 0, aber der unmappbare Slug steht sichtbar daneben statt zu verschwinden.
        assert "→ Ausgang: wirksam" in out

    def test_should_instrumentenwechsel_als_nicht_bewertbar_melden(self, tmp_path):
        wb = _wb(tmp_path)
        out = "\n".join(
            k1_auswertung(
                _reports([["claim-before-cheapest-check"]] * 8), wb, "ANDERER-HASH"
            )
        )
        assert "INSTRUMENTENWECHSEL" in out
        assert "→ Ausgang: nicht bewertbar (Instrumentenwechsel" in out

    def test_should_zu_kleines_fenster_als_nicht_bewertbar_melden(self, tmp_path):
        wb = _wb(tmp_path)
        out = "\n".join(
            k1_auswertung(
                _reports([["claim-before-cheapest-check"]] * 7), wb, "deadbeef"
            )
        )
        assert "Input-Bedingung ≥8: NICHT erfüllt" in out
        assert "→ Ausgang: nicht bewertbar (nur 7 Retros" in out


def test_should_eingefrorenen_instrument_pin_einhalten():
    """Rot, sobald retro_kpis.py sich aendert, ohne dass die Baseline neu berechnet
    und der Pin nachgezogen wurde — genau die Pflicht aus KONZ-038 D6/EXT2-AD-3.
    Bis hierher war das eine Prosa-Zusage im YAML-Kopf ohne jeden Sensor."""
    wb = load_woerterbuch(str(WB_PFAD))
    assert wb is not None
    assert tool_sha256() == wb["tool_sha256"], (
        "retro_kpis.py wurde geaendert: Baseline mit dieser Version NEU berechnen "
        "und tool_sha256 in slug-woerterbuch.yaml nachziehen (KONZ-038 D6)."
    )


def test_should_k1_ueber_die_cli_erreichbar_sein():
    out = _run_kpis("--k1", "--k1-woerterbuch", str(WB_PFAD))
    assert "## K1-Auswertung" in out
    assert "→ Ausgang:" in out


def test_should_ohne_lesbares_woerterbuch_nicht_bewertbar_melden(tmp_path):
    fehlt = tmp_path / "gibtsnicht.yaml"
    out = _run_kpis("--k1", "--k1-woerterbuch", str(fehlt))
    assert "nicht lesbar/unvollständig" in out
    assert "nicht bewertbar" in out


class TestRegistryCoverage:
    """platform#1650 Kriterium 3: Registry-Abgleich der GATE-PFLICHT-Slugs.

    Erwähnung ≠ Erzwingung (Nachmessung 2026-08-10: zwei "ja" des Audits waren
    bloße Slug-Erwähnungen in Kommentaren) — gedeckt ist nur, was die
    Gate-Registry als Eintrags-Slug ODER in dessen `covers`-Liste führt.
    """

    def test_should_collect_entry_slugs_and_covers(self, tmp_path):
        reg = tmp_path / "gate-registry.json"
        reg.write_text(
            json.dumps(
                {
                    "gates": [
                        {"slug": "familien-gate", "covers": ["slug-b", "slug-c"]},
                        {"slug": "einzel-gate"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        assert registry_coverage(str(reg)) == {
            "familien-gate",
            "slug-b",
            "slug-c",
            "einzel-gate",
        }

    def test_should_return_none_on_missing_registry(self, tmp_path):
        assert registry_coverage(str(tmp_path / "fehlt.json")) is None

    def test_should_return_none_on_invalid_json(self, tmp_path):
        kaputt = tmp_path / "kaputt.json"
        kaputt.write_text("{nope", encoding="utf-8")
        assert registry_coverage(str(kaputt)) is None

    def test_should_ignore_non_string_covers_entries(self, tmp_path):
        reg = tmp_path / "gate-registry.json"
        reg.write_text(
            json.dumps({"gates": [{"slug": "g", "covers": ["ok", 42, None]}]}),
            encoding="utf-8",
        )
        assert registry_coverage(str(reg)) == {"g", "ok"}

    def test_should_real_registry_cover_the_1650_family(self):
        """Die echte Registry ist lesbar und deckt die Aufschub-Familie (covers)."""
        covered = registry_coverage()
        assert covered is not None
        assert "workaround-without-tracking-anchor" in covered
        assert "tracking-doc-stale-after-new-occurrence" in covered
        assert "lint-failure-no-local-gate" in covered
