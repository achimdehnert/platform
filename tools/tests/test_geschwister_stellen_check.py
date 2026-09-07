"""Drill fuer tools/geschwister_stellen_check.py (geschwister-stellen-nicht-mitgezogen).

Die Kernlogik ist git-frei (`befunde_fuer` arbeitet auf Zeilenlisten) — der Drill
baut die Fixtures direkt, statt echte Diffs zu brauchen.

Positivkontrolle: Realfall (a) aus Retro a84f71 (2026-08-23) — ein Default-Flip
wurde nur an den WARN-Zweigen nachgezogen, die zwei praktisch identischen
PASS-Zweige derselben Datei blieben stehen und etikettierten fremde Repos
weiter als `platform`. Die Fixture bildet genau das ab: vier fast gleiche
Zweige, zwei geaendert, zwei stehengeblieben -> zwei Befunde.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import geschwister_stellen_check as gsc  # noqa: E402

# --- Fixture Realfall (a): record() mit vier fast identischen Zweigen ---------
_VORHER = '        etikett = "platform"  # Default fuer unbekannte Herkunft'
_NACHHER = '        etikett = herkunft(repo) or "unbekannt-fremd"'

_RECORD_TEILFIX = [
    "def record(repo, status):",
    '    if status == "WARN" and repo is None:',
    _NACHHER,
    '    if status == "WARN" and repo == "":',
    _NACHHER,
    '    if status == "PASS" and repo is None:',
    _VORHER,
    '    if status == "PASS" and repo == "":',
    _VORHER,
]
_RECORD_VOLLFIX = [z if z != _VORHER else _NACHHER for z in _RECORD_TEILFIX]


class TestNormalisierungUndRauschen:
    def test_should_collapse_whitespace_before_comparing(self):
        assert gsc.normalisieren("  a   =   1  ") == "a = 1"

    def test_should_treat_short_lines_as_noise(self):
        assert gsc.ist_rauschen("return None") is True

    def test_should_treat_comment_and_symbol_only_lines_as_noise(self):
        assert gsc.ist_rauschen("# ein ausreichend langer Kommentar hier") is True
        assert gsc.ist_rauschen("// noch ein langer Kommentar ohne Code") is True
        assert gsc.ist_rauschen("--------------------------------") is True

    def test_should_keep_real_code_lines(self):
        assert gsc.ist_rauschen(gsc.normalisieren(_VORHER)) is False

    def test_should_only_check_text_extensions(self):
        assert gsc.ist_pruefpflichtig("paket/modul.py") is True
        assert gsc.ist_pruefpflichtig("paket/ablauf.yml") is True
        assert gsc.ist_pruefpflichtig("paket/bild.png") is False


class TestPositivkontrolleRealfallA:
    """Retro a84f71 (a): zwei PASS-Zweige blieben beim Default-Flip stehen."""

    def test_should_report_the_two_untouched_sibling_branches(self):
        befunde = gsc.befunde_fuer(
            entfernte_zeilen=[_VORHER, _VORHER],
            neue_zeilen=_RECORD_TEILFIX,
            geaenderte_nummern={3, 5},
            pfad="paket/melder.py",
        )
        assert [b.zeile for b in befunde] == [7, 9]
        assert all(b.ratio >= gsc.AEHNLICHKEIT for b in befunde)
        assert all(b.pfad == "paket/melder.py" for b in befunde)

    def test_should_be_clean_when_all_four_branches_were_changed(self):
        """Gegenprobe: derselbe Fix vollstaendig gezogen -> kein Befund."""
        befunde = gsc.befunde_fuer(
            entfernte_zeilen=[_VORHER] * 4,
            neue_zeilen=_RECORD_VOLLFIX,
            geaenderte_nummern={3, 5, 7, 9},
        )
        assert befunde == []


class TestDeckelGegenStrukturen:
    """Mehr als MAX_GESCHWISTER Zwillinge = Struktur, kein vergessener Fix.

    Kalibriert an 150 Nicht-Merge-Commits von main: jede Gruppe ab drei
    gleichartigen Zeilen war dort eine Tabellen-/Listenstruktur.
    """

    @staticmethod
    def _tabelle(anzahl: int) -> list[str]:
        return [
            f'    record(melder_{i:02d}, mode="advisory", owner="achim")'
            for i in range(anzahl)
        ]

    _ENTFERNT = '    record(melder_99, mode="advisory", owner="achim")'

    def test_should_stay_silent_on_table_like_structures(self):
        neu = self._tabelle(12)
        assert len(neu) > gsc.MAX_GESCHWISTER
        assert gsc.befunde_fuer([self._ENTFERNT], neu, geaenderte_nummern=set()) == []

    def test_should_still_report_a_small_group_of_siblings(self):
        """Gegenprobe zum Deckel: unterhalb der Grenze wird gemeldet."""
        neu = self._tabelle(gsc.MAX_GESCHWISTER)
        befunde = gsc.befunde_fuer([self._ENTFERNT], neu, geaenderte_nummern=set())
        assert [b.zeile for b in befunde] == list(range(1, gsc.MAX_GESCHWISTER + 1))

    def test_should_cap_findings_per_file_and_count_the_rest(self):
        """Drei unabhaengige Stellen mit je zwei Zwillingen = 6 Befunde, 5 sichtbar."""
        stellen = [
            "    ergebnis = pruefe_erste_bedingung(wert, schwelle=12)",
            "    meldung = formatiere_zweite_ausgabe(text, breite=80)",
            "    zaehler = summiere_dritte_menge(eintraege, faktor=3)",
        ]
        neu = [z for z in stellen for _ in range(2)]
        befunde = gsc.befunde_fuer(stellen, neu, geaenderte_nummern=set())
        assert len(befunde) == 6
        sichtbar = befunde[: gsc.MAX_BEFUNDE_JE_DATEI]
        assert len(sichtbar) == 5
        assert len(befunde) - len(sichtbar) == 1


class TestDatenzeilenFilter:
    """Zeilen ohne Aufruf und ohne Zuweisung sind Daten — Wiederholung ist dort
    Struktur. Gemessen: Port-Tabellen, Secret-Inventar-Refs, Markdown-Tabellen
    lieferten so ausschliesslich Fehlalarme."""

    def test_should_treat_data_rows_as_noise(self):
        assert (
            gsc.ist_rauschen('betriebsstatus_grund: "laeuft auf dev-desktop"') is True
        )
        assert gsc.ist_rauschen('"dependabot-security-updates",') is True

    def test_should_keep_lines_with_a_call_or_an_assignment(self):
        assert gsc.ist_rauschen("ergebnis = pruefe_die_bedingung(wert)") is False
        assert gsc.ist_rauschen("_attach_files(tok, msg_id, anhaenge_liste)") is False

    def test_should_not_report_repeated_data_rows(self):
        neu = ["  ref: beispielorg/beispiel-hub"] * 2
        assert gsc.befunde_fuer(["  ref: beispielorg/beispiel-hub"], neu, set()) == []


class TestTestdateienAusgenommen:
    """Wiederholte assert-/Fixture-Zeilen waren die groesste Fehlalarm-Quelle."""

    def test_should_skip_test_and_fixture_files(self):
        assert gsc.ist_pruefpflichtig("paket/tests/test_modul.py") is False
        assert gsc.ist_pruefpflichtig("paket/test_modul.py") is False
        assert gsc.ist_pruefpflichtig("paket/conftest.py") is False
        assert gsc.ist_pruefpflichtig("paket/fixtures/daten.json") is False

    def test_should_keep_production_modules(self):
        assert gsc.ist_pruefpflichtig("paket/modul.py") is True


class TestDiffParsen:
    def test_should_collect_removed_lines_and_changed_new_line_numbers(self):
        diff = (
            "diff --git a/paket/modul.py b/paket/modul.py\n"
            "--- a/paket/modul.py\n"
            "+++ b/paket/modul.py\n"
            "@@ -3,2 +3,2 @@ def record():\n"
            "-        etikett = alt_und_lang_genug_fuer_die_pruefung()\n"
            "-        etikett = alt_und_lang_genug_fuer_die_pruefung()\n"
            "+        etikett = neu_und_lang_genug_fuer_die_pruefung()\n"
            "+        etikett = neu_und_lang_genug_fuer_die_pruefung()\n"
        )
        dateien = gsc.diff_parsen(diff)
        assert len(dateien) == 1
        assert dateien[0].pfad == "paket/modul.py"
        assert dateien[0].geaenderte_nummern == {3, 4}
        assert len(dateien[0].entfernte) == 2

    def test_should_default_hunk_count_to_one(self):
        diff = "+++ b/paket/modul.py\n@@ -7 +7 @@\n-alte zeile\n+neue zeile\n"
        assert gsc.diff_parsen(diff)[0].geaenderte_nummern == {7}

    def test_should_skip_deleted_files_without_new_version(self):
        diff = "--- a/paket/weg.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-eine zeile\n"
        assert gsc.diff_parsen(diff) == []


class TestMainExitVertrag:
    """0 sauber · 1 Befund (advisory) · 2 Werkzeugfehler (nie still)."""

    def _lauf(self, dateien, fassung=None):
        with patch.object(gsc, "diff_dateien", return_value=dateien):
            with patch.object(gsc, "neue_fassung", return_value=fassung):
                with patch.object(sys, "argv", ["x", "--range", "a...b"]):
                    return gsc.main()

    def test_should_exit_0_when_clean(self):
        assert self._lauf([]) == 0

    def test_should_exit_1_on_finding(self):
        datei = gsc.DateiDiff(
            pfad="paket/melder.py",
            entfernte=[_VORHER],
            geaenderte_nummern={3, 5},
        )
        assert self._lauf([datei], fassung=_RECORD_TEILFIX) == 1

    def test_should_exit_0_when_the_new_version_is_unreadable(self):
        """Geloescht/umbenannt/binaer ist kein Befund — und kein Werkzeugfehler."""
        datei = gsc.DateiDiff(pfad="paket/fehlt.py", entfernte=[_VORHER])
        assert self._lauf([datei], fassung=None) == 0

    def test_should_exit_2_when_git_fails(self):
        """git-Fehler ist kein sauberer Zustand (nie als gruen werten)."""
        assert self._lauf(None) == 2


class TestBereichsEndpunkt:
    """Die neue Fassung kommt vom Endpunkt des Bereichs, nicht vom Arbeitsbaum.

    Realfall 2026-09-07 beim Kalibrieren: `origin/main` war dem ausgecheckten
    HEAD voraus; die Zeilennummern aus dem Diff trafen eine andere Datei und der
    Melder erfand drei Befunde in `tools/schleuse.py`.
    """

    def test_should_take_the_part_after_the_last_separator(self):
        assert gsc.bereichs_endpunkt("origin/main...HEAD") == "HEAD"
        assert gsc.bereichs_endpunkt("abc123..def456") == "def456"

    def test_should_default_to_head(self):
        assert gsc.bereichs_endpunkt("origin/main...") == "HEAD"
        assert gsc.bereichs_endpunkt("") == "HEAD"

    def test_should_read_the_version_at_that_endpoint(self):
        out = subprocess.CompletedProcess([], 0, "erste zeile\nzweite zeile\n", "")
        with patch.object(gsc.subprocess, "run", return_value=out) as lauf:
            assert gsc.neue_fassung("paket/modul.py", Path("."), "abc123") == [
                "erste zeile",
                "zweite zeile",
            ]
        assert "abc123:paket/modul.py" in lauf.call_args[0][0]

    def test_should_return_none_when_the_path_is_absent_at_the_endpoint(self):
        out = subprocess.CompletedProcess([], 128, "", "fatal: path does not exist")
        with patch.object(gsc.subprocess, "run", return_value=out):
            assert gsc.neue_fassung("paket/weg.py", Path("."), "abc123") is None


class TestDiffDateien:
    def test_should_return_none_on_git_error(self):
        out = subprocess.CompletedProcess([], 128, "", "fatal")
        with patch.object(gsc.subprocess, "run", return_value=out):
            assert gsc.diff_dateien("a...b", Path(".")) is None

    def test_should_return_none_when_git_is_unavailable(self):
        with patch.object(gsc.subprocess, "run", side_effect=OSError("kein git")):
            assert gsc.diff_dateien("a...b", Path(".")) is None


class TestGateHeader:
    def test_should_carry_the_machine_readable_head(self):
        assert gsc.GATE_HEADER["slug"] == "geschwister-stellen-nicht-mitgezogen"
        assert gsc.GATE_HEADER["mode"] == "advisory"
        assert gsc.GATE_HEADER["evidence"].endswith(Path(__file__).name)
