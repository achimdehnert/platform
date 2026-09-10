"""Drill fuer tools/session_abgleich.py — drei Slugs, drei Positivkontrollen.

Jede der drei Pruefungen bekommt hier (a) eine POSITIVKONTROLLE am
nachgebauten Realfall, an der die Fixture ROT wird, und (b) eine Gegenprobe,
die gruen bleibt. Ohne (b) belegt ein rotes Gate nur, dass es ueberhaupt
etwas meldet — nicht, dass es das Richtige meldet.

Die Kernfunktionen sind netzfrei (Listen von dicts in `gh --json`-Form), der
gh-Abruf liegt in einer eigenen Schicht — deshalb braucht dieser Drill weder
Netz noch Mock-Server.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import session_abgleich as sa  # noqa: E402


# ─────────────────────────── Kopf & Zuordnung ───────────────────────────────


class TestGateHeader:
    def test_should_carry_first_slug_and_own_drill_as_evidence(self):
        assert sa.GATE_HEADER["slug"] == "issue-offen-nach-gemergtem-fix"
        assert sa.GATE_HEADER["mode"] == "advisory"
        assert sa.GATE_HEADER["owner"] == "achim"
        assert sa.GATE_HEADER["evidence"] == "tools/tests/test_session_abgleich.py"

    def test_should_document_all_three_slugs_in_docstring(self):
        # Die Registry nennt das Modul dreimal — der Kopf traegt nur den ersten.
        # Ohne die Doku-Zeilen waere die Zuordnung Slug→Funktion unauffindbar.
        for slug in (sa.SLUG_ISSUES, sa.SLUG_BELEGE, sa.SLUG_SERIEN):
            assert slug in sa.__doc__


# ───────────────────────── Referenz-Erkennung (rein) ────────────────────────


class TestReferenzierteIssues:
    def test_should_read_closing_and_loose_keywords(self):
        treffer = sa.referenzierte_issues("Closes #12\nRefs #34\nBezug: #56")
        assert [(t["nummer"], t["schliessend"]) for t in treffer] == [
            (12, True),
            (34, False),
            (56, False),
        ]

    def test_should_read_cross_repo_and_chained_refs(self):
        treffer = sa.referenzierte_issues("Refs achimdehnert/chat-hub#27, #28")
        assert treffer[0]["repo"] == "achimdehnert/chat-hub"
        assert [t["nummer"] for t in treffer] == [27, 28]

    def test_should_ignore_bare_hash_without_keyword(self):
        assert sa.referenzierte_issues("Der Lauf #33644319863 war gruen") == []


class TestOffeneKaestchen:
    def test_should_detect_unchecked_box(self):
        assert sa.hat_offene_kaestchen("- [x] eins\n- [ ] zwei") is True

    def test_should_stay_quiet_when_all_boxes_checked(self):
        assert sa.hat_offene_kaestchen("- [x] eins\n- [x] zwei") is False


# ══════════════ (1) issue-offen-nach-gemergtem-fix ══════════════════════════


class TestBefundeIssues:
    def test_should_flag_issue_still_open_after_its_fix_merged(self):
        """POSITIVKONTROLLE ausschreibungs-hub #184: inhaltlich durch #195
        erfuellt, PR gemergt — und das Issue stand weiter auf OPEN."""
        prs = [
            {
                "number": 195,
                "repo": "achimdehnert/ausschreibungs-hub",
                "state": "MERGED",
                "body": "Closes #184 — Vergabeportal-Import nachgezogen.",
            }
        ]
        issues = [
            {
                "number": 184,
                "repo": "achimdehnert/ausschreibungs-hub",
                "state": "OPEN",
                "body": "Import fehlt",
            }
        ]
        befunde = sa.befunde_issues(prs, issues)
        assert len(befunde) == 1
        assert befunde[0]["art"] == "befund"
        assert befunde[0]["slug"] == sa.SLUG_ISSUES
        assert befunde[0]["ref"] == "achimdehnert/ausschreibungs-hub#184"
        assert "#195" in befunde[0]["text"]

    def test_should_flag_refs_instead_of_closes(self):
        """POSITIVKONTROLLE writing-hub: 9 von 10 PR-Texten schrieben `Refs #N`
        statt `Closes #N` — GitHub schliesst dabei nichts, fuenf geloeste
        Issues blieben OPEN."""
        prs = [
            {
                "number": 1008,
                "repo": "achimdehnert/writing-hub",
                "state": "MERGED",
                "body": "Refs #77",
            }
        ]
        issues = [{"number": 77, "repo": "achimdehnert/writing-hub", "state": "OPEN"}]
        befunde = sa.befunde_issues(prs, issues)
        assert len(befunde) == 1
        assert "schliesst nicht automatisch" in befunde[0]["text"]

    def test_should_flag_closed_issue_with_unchecked_dod_boxes(self):
        """POSITIVKONTROLLE chat-hub #27: `alle fuenf Punkte erledigt` stand nur
        im Text — der Issue-Body trug die Kaestchen weiter unangehakt."""
        prs = [
            {
                "number": 31,
                "repo": "achimdehnert/chat-hub",
                "state": "MERGED",
                "body": "Closes #27",
            }
        ]
        issues = [
            {
                "number": 27,
                "repo": "achimdehnert/chat-hub",
                "state": "CLOSED",
                "body": "- [x] eins\n- [x] zwei\n- [ ] drei\n- [ ] vier\n- [ ] fuenf",
            }
        ]
        befunde = sa.befunde_issues(prs, issues)
        assert len(befunde) == 1
        assert "unangehakte" in befunde[0]["text"]

    def test_should_stay_green_when_issue_closed_and_dod_complete(self):
        """GEGENPROBE: derselbe Aufbau, aber sauber gebucht — kein Befund."""
        prs = [
            {
                "number": 31,
                "repo": "achimdehnert/chat-hub",
                "state": "MERGED",
                "body": "Closes #27",
            }
        ]
        issues = [
            {
                "number": 27,
                "repo": "achimdehnert/chat-hub",
                "state": "CLOSED",
                "body": "- [x] eins\n- [x] zwei",
            }
        ]
        assert sa.befunde_issues(prs, issues) == []

    def test_should_stay_green_when_pr_is_not_merged(self):
        """GEGENPROBE: ein OFFENER PR darf sein Issue offen lassen."""
        prs = [
            {
                "number": 195,
                "repo": "r/x",
                "state": "OPEN",
                "body": "Closes #184",
            }
        ]
        issues = [{"number": 184, "repo": "r/x", "state": "OPEN"}]
        assert sa.befunde_issues(prs, issues) == []

    def test_should_report_hinweis_when_issue_state_unknown(self):
        prs = [{"number": 5, "repo": "r/x", "state": "MERGED", "body": "Closes #99"}]
        ergebnis = sa.befunde_issues(prs, [])
        assert len(ergebnis) == 1
        assert ergebnis[0]["art"] == "hinweis"
        assert "keine Entwarnung" in ergebnis[0]["text"]


# ══════════════════ (2) beleg-pr-nicht-gemergt ══════════════════════════════


class TestBefundeBelege:
    def test_should_flag_proof_pr_left_open(self):
        """POSITIVKONTROLLE `proof-artifact-left-unmerged`: der PR-Text nennt
        einen anderen PR als Nachweis — der ist nie gemergt worden."""
        texte = [
            {
                "quelle": "#2812",
                "repo": "achimdehnert/platform",
                "nummer": 2812,
                "body": "Nachweis: der Drill laeuft in #2799.",
            }
        ]
        befunde = sa.befunde_belege(texte, {"achimdehnert/platform#2799": "OPEN"})
        assert len(befunde) == 1
        assert befunde[0]["art"] == "befund"
        assert befunde[0]["slug"] == sa.SLUG_BELEGE
        assert befunde[0]["ref"] == "achimdehnert/platform#2799"

    def test_should_name_closed_without_merge_as_the_worse_case(self):
        texte = [
            {
                "quelle": "#2812",
                "repo": "r/x",
                "nummer": 2812,
                "body": "Positivkontrolle siehe #2799",
            }
        ]
        befunde = sa.befunde_belege(texte, {"r/x#2799": "CLOSED"})
        assert "CLOSED OHNE MERGE" in befunde[0]["text"]

    def test_should_stay_green_when_proof_pr_is_merged(self):
        """GEGENPROBE: derselbe Satz, aber der Beleg-PR ist gemergt."""
        texte = [
            {
                "quelle": "#2812",
                "repo": "r/x",
                "nummer": 2812,
                "body": "Verifiziert in #2799.",
            }
        ]
        assert sa.befunde_belege(texte, {"r/x#2799": "MERGED"}) == []

    def test_should_ignore_reference_outside_a_proof_line(self):
        """GEGENPROBE: eine Zeile ohne Beleg-Wort ist kein Beleg."""
        texte = [
            {
                "quelle": "#1",
                "repo": "r/x",
                "nummer": 1,
                "body": "Folgearbeit steht in #2799.",
            }
        ]
        assert sa.befunde_belege(texte, {"r/x#2799": "OPEN"}) == []

    def test_should_ignore_self_reference(self):
        texte = [
            {
                "quelle": "#7",
                "repo": "r/x",
                "nummer": 7,
                "body": "Beleg: dieser PR #7 selbst.",
            }
        ]
        assert sa.befunde_belege(texte, {"r/x#7": "OPEN"}) == []

    def test_should_report_hinweis_when_reference_is_not_resolvable(self):
        texte = [{"quelle": "#1", "repo": "r/x", "nummer": 1, "body": "Beleg: #4242"}]
        ergebnis = sa.befunde_belege(texte, {})
        assert ergebnis[0]["art"] == "hinweis"
        assert "nicht aufloesbar" in ergebnis[0]["text"]


# ════════════════ (3) serielle-prs-auf-derselben-datei ══════════════════════


def _serien_pr(nummer, zeit, hunks, pfad="tools/session_ende_checks.sh"):
    datei = {"path": pfad}
    if hunks is not None:
        datei["hunks"] = hunks
    return {
        "number": nummer,
        "repo": "achimdehnert/platform",
        "state": "MERGED",
        "author": {"login": "achimdehnert"},
        "mergedAt": zeit,
        "files": [datei],
    }


class TestBefundeSerien:
    def test_should_flag_two_merged_prs_touching_the_same_lines(self):
        """POSITIVKONTROLLE `same-file-serial-prs`: zwei gemergte PRs desselben
        Autors, dieselbe Datei, ueberlappende Zeilen, drei Stunden Abstand."""
        prs = [
            _serien_pr(2879, "2026-09-07T08:00:00Z", [[100, 140]]),
            _serien_pr(2882, "2026-09-07T11:00:00Z", [[120, 160]]),
        ]
        befunde = sa.befunde_serien(prs, stunden=24)
        assert len(befunde) == 1
        assert befunde[0]["art"] == "befund"
        assert befunde[0]["slug"] == sa.SLUG_SERIEN
        assert "#2879" in befunde[0]["text"] and "#2882" in befunde[0]["text"]

    def test_should_stay_green_when_hunks_are_disjoint(self):
        """GEGENPROBE (Pflicht-Falsifikation): dieselbe Datei, aber getrennte
        Zeilenbereiche — das ist der Normalfall einer aktiven Datei."""
        prs = [
            _serien_pr(2879, "2026-09-07T08:00:00Z", [[10, 20]]),
            _serien_pr(2882, "2026-09-07T11:00:00Z", [[300, 320]]),
        ]
        assert sa.befunde_serien(prs, stunden=24) == []

    def test_should_report_hinweis_when_hunks_are_unavailable(self):
        """Ohne Hunk-Information ist der Fall NICHT falsifizierbar — Hinweis,
        nie Befund und nie Entwarnung."""
        prs = [
            _serien_pr(2879, "2026-09-07T08:00:00Z", None),
            _serien_pr(2882, "2026-09-07T11:00:00Z", None),
        ]
        ergebnis = sa.befunde_serien(prs, stunden=24)
        assert len(ergebnis) == 1
        assert ergebnis[0]["art"] == "hinweis"
        assert "NICHT falsifizierbar" in ergebnis[0]["text"]

    def test_should_stay_green_outside_the_time_window(self):
        prs = [
            _serien_pr(2879, "2026-09-01T08:00:00Z", [[100, 140]]),
            _serien_pr(2882, "2026-09-07T11:00:00Z", [[120, 160]]),
        ]
        assert sa.befunde_serien(prs, stunden=24) == []

    def test_should_stay_green_for_different_authors(self):
        a = _serien_pr(1, "2026-09-07T08:00:00Z", [[100, 140]])
        b = _serien_pr(2, "2026-09-07T09:00:00Z", [[100, 140]])
        b["author"] = {"login": "dependabot"}
        assert sa.befunde_serien([a, b], stunden=24) == []

    def test_should_ignore_unmerged_prs(self):
        a = _serien_pr(1, "2026-09-07T08:00:00Z", [[100, 140]])
        b = _serien_pr(2, None, [[100, 140]])
        b["state"] = "OPEN"
        assert sa.befunde_serien([a, b], stunden=24) == []


def _pr(nummer, autor, zustand, mergedat, pfad, hunks, repo="achimdehnert/platform"):
    datei = {"path": pfad}
    if hunks is not None:
        datei["hunks"] = hunks
    return {
        "number": nummer,
        "repo": repo,
        "author": {"login": autor},
        "state": zustand,
        "mergedAt": mergedat,
        "files": [datei],
    }


class TestBefundeSerienFuerPr:
    def test_should_flag_overlapping_hunks_against_another_open_pr(self):
        """POSITIVKONTROLLE 2026-09-10: #3034 (bereits heute gemergt) und
        #3042 (offen) beruehren test_todo_board.py an ueberlappenden Zeilen
        (467-531 vs 526-542)."""
        prs = [
            _pr(
                3042,
                "achimdehnert",
                "OPEN",
                None,
                "tools/tests/test_todo_board.py",
                [[467, 531]],
            ),
            _pr(
                3034,
                "achimdehnert",
                "MERGED",
                "2026-09-10T08:00:00Z",
                "tools/tests/test_todo_board.py",
                [[526, 542]],
            ),
        ]
        befunde = sa.befunde_serien_fuer_pr(3042, prs, heute="2026-09-10")
        assert len(befunde) == 1
        assert befunde[0]["art"] == "befund"
        assert "#3034" in befunde[0]["text"] and "#3042" in befunde[0]["text"]

    def test_should_report_clean_line_when_hunks_are_disjoint(self):
        """GEGENPROBE (Pflicht-Falsifikation): disjunkte Bereiche sind kein
        Befund, aber eine eigene Zeile belegt, dass geprueft wurde."""
        prs = [
            _pr(10, "achimdehnert", "OPEN", None, "tools/x.py", [[1, 10]]),
            _pr(11, "achimdehnert", "OPEN", None, "tools/x.py", [[50, 60]]),
        ]
        ergebnis = sa.befunde_serien_fuer_pr(10, prs, heute="2026-09-10")
        assert [e["art"] for e in ergebnis] == ["sauber"]
        assert "disjunkte Bereiche — kein Befund" in ergebnis[0]["text"]

    def test_should_compare_only_the_named_pr_via_eingabe(self, tmp_path, capsys):
        """--pr mit --eingabe vergleicht NUR den benannten PR — ein dritter PR
        desselben Autors auf einer anderen Datei bleibt aussen vor."""
        daten = {
            "prs": [
                _pr(10, "achimdehnert", "OPEN", None, "tools/x.py", [[1, 10]]),
                _pr(11, "achimdehnert", "OPEN", None, "tools/x.py", [[5, 15]]),
                _pr(12, "achimdehnert", "OPEN", None, "tools/y.py", [[1, 10]]),
            ]
        }
        pfad = tmp_path / "eingabe.json"
        pfad.write_text(json.dumps(daten), encoding="utf-8")
        rc = sa.main(["--eingabe", str(pfad), "--pr", "10", "--heute", "2026-09-10"])
        out = capsys.readouterr().out
        assert rc == 1
        assert "#11" in out and "#12" not in out

    def test_should_stay_clean_without_a_second_pr_of_the_same_author(self):
        """(d) Ziel-PR ohne zweiten PR desselben Autors → kein Befund."""
        prs = [_pr(10, "achimdehnert", "OPEN", None, "tools/x.py", [[1, 10]])]
        assert sa.befunde_serien_fuer_pr(10, prs, heute="2026-09-10") == []

    def test_should_ignore_pr_not_found_in_the_population(self):
        prs = [_pr(10, "achimdehnert", "OPEN", None, "tools/x.py", [[1, 10]])]
        assert sa.befunde_serien_fuer_pr(999, prs, heute="2026-09-10") == []


class TestBereicheUeberlappen:
    def test_should_detect_touching_ranges(self):
        assert sa.bereiche_ueberlappen([(1, 10)], [(10, 12)]) is True

    def test_should_separate_disjoint_ranges(self):
        assert sa.bereiche_ueberlappen([(1, 9)], [(10, 12)]) is False


class TestHunksAusPatch:
    def test_should_parse_paths_and_new_side_ranges(self):
        patch = (
            "diff --git a/tools/x.py b/tools/x.py\n"
            "--- a/tools/x.py\n"
            "+++ b/tools/x.py\n"
            "@@ -10,4 +12,6 @@ def f():\n"
            " kontext\n"
            "@@ -80 +90 @@\n"
            " kontext\n"
        )
        assert sa.hunks_aus_patch(patch) == {"tools/x.py": [(12, 17), (90, 90)]}

    def test_should_return_empty_for_empty_patch(self):
        assert sa.hunks_aus_patch("") == {}


# ──────────────────────────────── CLI ───────────────────────────────────────


class TestCli:
    def _eingabe(self, tmp_path, daten):
        p = tmp_path / "eingabe.json"
        p.write_text(json.dumps(daten), encoding="utf-8")
        return str(p)

    def test_should_exit_1_on_finding_from_input_file(self, tmp_path, capsys):
        pfad = self._eingabe(
            tmp_path,
            {
                "prs": [
                    {
                        "number": 195,
                        "repo": "r/x",
                        "state": "MERGED",
                        "body": "Closes #184",
                    }
                ],
                "issues": [{"number": 184, "repo": "r/x", "state": "OPEN"}],
            },
        )
        rc = sa.main(["--eingabe", pfad, "--issues"])
        assert rc == 1
        assert "RESULT: BEFUND" in capsys.readouterr().out

    def test_should_exit_0_when_input_is_clean(self, tmp_path, capsys):
        pfad = self._eingabe(tmp_path, {"prs": [], "issues": []})
        rc = sa.main(["--eingabe", pfad])
        assert rc == 0
        assert "RESULT: OK" in capsys.readouterr().out

    def test_should_exit_0_but_report_hinweis(self, tmp_path, capsys):
        pfad = self._eingabe(
            tmp_path,
            {
                "prs": [
                    {
                        "number": 5,
                        "repo": "r/x",
                        "state": "MERGED",
                        "body": "Closes #99",
                    }
                ]
            },
        )
        rc = sa.main(["--eingabe", pfad, "--issues"])
        assert rc == 0
        assert "RESULT: HINWEIS" in capsys.readouterr().out

    def test_should_exit_2_without_repo_and_without_input(self, capsys):
        assert sa.main([]) == 2
        assert "RESULT: FEHLER" in capsys.readouterr().out

    def test_should_exit_2_when_input_file_is_missing(self, capsys):
        assert sa.main(["--eingabe", "/nicht/vorhanden.json"]) == 2
        assert "RESULT: FEHLER" in capsys.readouterr().out

    def test_should_emit_json_when_asked(self, tmp_path, capsys):
        pfad = self._eingabe(tmp_path, {"prs": [], "issues": []})
        sa.main(["--eingabe", pfad, "--json"])
        zeilen = capsys.readouterr().out.split("RESULT:")[0]
        assert json.loads(zeilen)["result"] == "OK"

    def test_should_run_only_the_selected_check(self, tmp_path, capsys):
        # Serien-Befund vorhanden, aber nur --issues gewaehlt → sauber.
        pfad = self._eingabe(
            tmp_path,
            {
                "prs": [
                    _serien_pr(1, "2026-09-07T08:00:00Z", [[1, 10]]),
                    _serien_pr(2, "2026-09-07T09:00:00Z", [[5, 15]]),
                ]
            },
        )
        assert sa.main(["--eingabe", pfad, "--issues"]) == 0
        assert sa.main(["--eingabe", pfad, "--serien"]) == 1
        capsys.readouterr()


class TestGhSchicht:
    def test_should_raise_when_gh_is_missing(self, monkeypatch):
        def kein_gh(*a, **k):
            raise FileNotFoundError("gh")

        monkeypatch.setattr(sa.subprocess, "run", kein_gh)
        try:
            sa._gh(["pr", "list"])
        except sa.GhFehler as exc:
            assert "nicht verfuegbar" in str(exc)
        else:
            raise AssertionError("GhFehler erwartet")
