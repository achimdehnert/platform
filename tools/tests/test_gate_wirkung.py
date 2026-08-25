"""Drill fuer tools/gate_wirkung.py — das Rueckfall-Mass des Session-Loops.

Der wichtigste Test hier ist NICHT die Rueckfall-Erkennung, sondern die
Ehrlichkeits-Sperre: ein frisch gebautes Gate darf nicht als "wirksam" gelten,
nur weil hinter seinem Bau-Datum noch kaum Retros liegen. Ohne diesen Test waere
die Kennzahl durch blosses Neubauen von Gates steigerbar (Goodhart) — und damit
genau das Gegenteil dessen, wofuer sie gebaut wurde.

Run: `python3 -m pytest tools/tests/test_gate_wirkung.py -q`
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "gate_wirkung.py"
_spec = importlib.util.spec_from_file_location("gate_wirkung", _QUELLE)
gw = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gw)


def _retro(
    verzeichnis: Path, datum: str, kuerzel: str, slugs: list[str], inline: bool = True
) -> None:
    """Legt ein Retro mit `recurring_findings` an — inline oder als YAML-Block."""
    if inline:
        block = "recurring_findings: [" + ", ".join(slugs) + "]"
    else:
        block = "recurring_findings:\n" + "".join(f"  - {s}\n" for s in slugs).rstrip()
    (verzeichnis / f"session-retro-{datum}-platform-{kuerzel}.md").write_text(
        f"---\nretro_schema: 1\ndate: {datum}\n{block}\n---\n\n# Retro\n",
        encoding="utf-8",
    )


def _urteile(verzeichnis: Path, gates: list[dict]) -> dict[str, dict]:
    retros = gw.lies_retros([str(verzeichnis)])
    return {e["slug"]: e for e in gw.bewerte(gates, retros)}


def test_should_mark_gate_rueckfaellig_when_finding_recurs_after_build(tmp_path):
    for i, tag in enumerate(["10", "11", "12"]):
        _retro(tmp_path, f"2026-07-{tag}", f"a{i}", ["schludrigkeit"])
    urteile = _urteile(
        tmp_path, [{"slug": "schludrigkeit", "mode": "blocking", "built": "2026-07-01"}]
    )

    assert urteile["schludrigkeit"]["urteil"] == "RUECKFAELLIG"
    assert urteile["schludrigkeit"]["nachher"] == 3
    assert urteile["schludrigkeit"]["letzter_rueckfall"] == "2026-07-12"


def test_should_not_call_fresh_gate_wirksam_before_min_fenster(tmp_path):
    """Die Ehrlichkeits-Sperre: zu wenig Retros seit Bau ⇒ 'zu-frueh', nie 'wirksam'."""
    _retro(tmp_path, "2026-07-01", "alt", ["schludrigkeit"])
    _retro(tmp_path, "2026-07-02", "alt2", ["schludrigkeit"])
    # genau EIN Retro nach dem Bau-Datum — unter MIN_FENSTER
    _retro(tmp_path, "2026-07-20", "neu", ["anderes"])
    urteile = _urteile(
        tmp_path, [{"slug": "schludrigkeit", "mode": "blocking", "built": "2026-07-10"}]
    )

    assert gw.MIN_FENSTER > 1, "Sperre ist wirkungslos, wenn ein einziges Retro genuegt"
    assert urteile["schludrigkeit"]["urteil"] == "zu-frueh"
    assert urteile["schludrigkeit"]["vorher"] == 2


def test_should_call_gate_wirksam_only_with_before_after_evidence(tmp_path):
    _retro(tmp_path, "2026-07-01", "a", ["schludrigkeit"])
    _retro(tmp_path, "2026-07-02", "b", ["schludrigkeit"])
    for i, tag in enumerate(["20", "21", "22"]):
        _retro(tmp_path, f"2026-07-{tag}", f"c{i}", ["anderes"])
    urteile = _urteile(
        tmp_path, [{"slug": "schludrigkeit", "mode": "blocking", "built": "2026-07-10"}]
    )

    assert urteile["schludrigkeit"]["urteil"] == "wirksam"
    assert urteile["schludrigkeit"]["vorher_messbar"] is True


def test_should_flag_missing_before_window_for_gate_older_than_data(tmp_path):
    """Gate aelter als das aelteste Retro ⇒ 'vorher' ist Datenfenster-Ende, kein Messwert."""
    for i, tag in enumerate(["10", "11", "12"]):
        _retro(tmp_path, f"2026-07-{tag}", f"a{i}", ["anderes"])
    urteile = _urteile(
        tmp_path, [{"slug": "uralt", "mode": "process", "built": "2026-01-01"}]
    )

    assert urteile["uralt"]["vorher_messbar"] is False
    assert urteile["uralt"]["urteil"] == "kein-vorher-fenster"


def test_should_read_recurring_findings_from_block_and_inline_form(tmp_path):
    _retro(tmp_path, "2026-07-10", "inline", ["a-slug", "b-slug"], inline=True)
    _retro(tmp_path, "2026-07-11", "block", ["a-slug"], inline=False)
    retros = gw.lies_retros([str(tmp_path)])

    assert sorted(r[1] for r in retros) == [["a-slug"], ["a-slug", "b-slug"]]


def test_should_ignore_extern_briefings(tmp_path):
    _retro(tmp_path, "2026-07-10", "echt", ["a-slug"])
    (tmp_path / "session-retro-2026-07-11-extern-platform-x.md").write_text(
        "---\nrecurring_findings: [a-slug]\n---\n", encoding="utf-8"
    )
    assert len(gw.lies_retros([str(tmp_path)])) == 1


def test_should_print_nothing_in_kurz_mode_without_rueckfall(tmp_path):
    """Der Runner darf keine Zeile bekommen, wenn es nichts zu melden gibt."""
    for i, tag in enumerate(["10", "11", "12"]):
        _retro(tmp_path, f"2026-07-{tag}", f"a{i}", ["anderes"])
    registry = tmp_path / "reg.json"
    registry.write_text(
        json.dumps(
            {"gates": [{"slug": "ruhig", "mode": "advisory", "built": "2026-07-01"}]}
        ),
        encoding="utf-8",
    )
    lauf = subprocess.run(
        [
            sys.executable,
            str(_QUELLE),
            "--kurz",
            "--registry",
            str(registry),
            "--dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert lauf.returncode == 0
    assert lauf.stdout.strip() == ""


def test_should_stay_exit_zero_on_unreadable_registry(tmp_path):
    """Fail-open: ein Melder, der den Sitzungsstart aufhaelt, wird abgeschaltet.

    Fail-open heisst weiterlaufen, nicht schweigen. Die frueher hier stehende
    Zeile `assert lauf.stdout.strip() == ""` hielt genau den Defekt fest, den
    platform#2278 behebt: der Runner liest leere Ausgabe als PASS und behauptet
    dann "kein Gate rueckfaellig" ueber Gates, die nie gelesen wurden. Der
    Exit-Code-Vertrag bleibt (0), die Stille nicht.
    """
    lauf = subprocess.run(
        [
            sys.executable,
            str(_QUELLE),
            "--kurz",
            "--registry",
            str(tmp_path / "gibtsnicht.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert lauf.returncode == 0
    assert "misst nichts" in lauf.stdout


# --- Regressionen aus Retro beefc148 (2026-08-20) ----------------------------
# Beide Faelle wurden von einem fremden Pruefer reproduziert und von KEINEM der
# acht Tests darueber gefangen. Sie stehen hier bewusst als eigener Block: was
# ein Aussenstehender findet und die eigene Suite nicht, gehoert markiert.


def test_should_not_count_the_build_day_retro_as_a_relapse(tmp_path):
    """Das Retro des Bau-Tags ist der Ausloeser des Gates, nicht sein Rueckfall.

    Vorher zaehlte es als Rueckfall mit (`d >= gebaut`) — damit reichte EIN
    weiteres Vorkommen fuer das Urteil RUECKFAELLIG, obwohl die Schwelle 2 ist.
    """
    _retro(tmp_path, "2026-07-10", "bautag", ["schludrigkeit"])  # Bau-Tag selbst
    _retro(tmp_path, "2026-07-11", "danach", ["schludrigkeit"])  # ein echter Rueckfall
    urteile = _urteile(
        tmp_path, [{"slug": "schludrigkeit", "mode": "blocking", "built": "2026-07-10"}]
    )

    assert urteile["schludrigkeit"]["nachher"] == 1, "Bau-Tag darf nicht mitzaehlen"
    assert urteile["schludrigkeit"]["urteil"] != "RUECKFAELLIG"


def test_should_still_report_two_real_relapses_in_a_short_window(tmp_path):
    """Gegenprobe zur Sperre: zwei ECHTE Rueckfaelle bleiben RUECKFAELLIG.

    Die Fenster-Sperre schuetzt die positive Aussage ("wirksam") — sie darf
    beobachtete Rueckfaelle nicht verschlucken, auch nicht bei kurzem Fenster.
    """
    _retro(tmp_path, "2026-07-10", "bautag", ["schludrigkeit"])
    _retro(tmp_path, "2026-07-11", "r1", ["schludrigkeit"])
    _retro(tmp_path, "2026-07-12", "r2", ["schludrigkeit"])
    urteile = _urteile(
        tmp_path, [{"slug": "schludrigkeit", "mode": "blocking", "built": "2026-07-10"}]
    )

    assert urteile["schludrigkeit"]["nachher"] == 2
    assert urteile["schludrigkeit"]["urteil"] == "RUECKFAELLIG"


def test_should_keep_reading_slugs_after_an_inline_comment(tmp_path):
    """Ein `- slug  # Notiz` beendete die Liste und verschluckte alles danach.

    Die Fehlrichtung ist die gefaehrlichere: fehlende Slugs lassen ein Gate
    wirksam aussehen, obwohl es rueckfaellig ist.
    """
    (tmp_path / "session-retro-2026-07-10-platform-kommentar.md").write_text(
        "---\nretro_schema: 1\nrecurring_findings:\n"
        "  - erster-slug  # hier stand frueher der Abbruch\n"
        "  - zweiter-slug\n"
        "---\n",
        encoding="utf-8",
    )
    retros = gw.lies_retros([str(tmp_path)])

    assert retros[0][1] == ["erster-slug", "zweiter-slug"]


def test_should_not_end_the_block_on_a_blank_or_comment_line(tmp_path):
    (tmp_path / "session-retro-2026-07-10-platform-leer.md").write_text(
        "---\nrecurring_findings:\n  - a-slug\n\n  # Zwischenkommentar\n  - b-slug\n---\n",
        encoding="utf-8",
    )
    retros = gw.lies_retros([str(tmp_path)])

    assert retros[0][1] == ["a-slug", "b-slug"]


class TestUmbauDatum:
    """Ein umgebautes Gate wird ab seinem Umbau gemessen, nicht ab dem Erstbau."""

    def test_should_measure_from_revised_date(self):
        gates = [{"slug": "g", "built": "2026-06-01", "revised": "2026-08-01"}]
        retros = [
            ("2026-07-10", ["g"], "a"),
            ("2026-07-20", ["g"], "b"),
            ("2026-08-10", [], "c"),
            ("2026-08-12", [], "d"),
            ("2026-08-14", [], "e"),
        ]
        e = gw.bewerte(gates, retros)[0]
        assert e["nachher"] == 0, (
            "Vorkommen vor dem Umbau zaehlen nicht mehr als Rueckfall"
        )
        assert e["vorher"] == 2
        assert e["urteil"] != "RUECKFAELLIG"
        assert e["umgebaut"] is True

    def test_should_still_see_recurrence_after_the_rebuild(self):
        """Der Umbau ist kein Freibrief: was danach passiert, zaehlt weiter."""
        gates = [{"slug": "g", "built": "2026-06-01", "revised": "2026-08-01"}]
        retros = [
            ("2026-07-10", ["g"], "a"),
            ("2026-08-05", ["g"], "b"),
            ("2026-08-09", ["g"], "c"),
            ("2026-08-11", [], "d"),
            ("2026-08-13", [], "e"),
        ]
        e = gw.bewerte(gates, retros)[0]
        assert e["nachher"] == 2
        assert e["urteil"] == "RUECKFAELLIG"

    def test_should_fall_back_to_built_without_revised(self):
        gates = [{"slug": "g", "built": "2026-08-01"}]
        retros = [("2026-08-05", ["g"], "a"), ("2026-08-06", ["g"], "b")]
        e = gw.bewerte(gates, retros)[0]
        assert e["gebaut"] == "2026-08-01"
        assert e["umgebaut"] is False


class TestGefangenerBefund:
    """Ein Befund, den das Gate gefangen hat, zaehlt nicht gegen dieses Gate."""

    def test_should_not_count_a_caught_finding_as_recurrence(self):
        gates = [{"slug": "g", "built": "2026-08-01"}]
        retros = [
            ("2026-08-05", ["g"], "a", ["g"]),
            ("2026-08-06", ["g"], "b", ["g"]),
            ("2026-08-07", [], "c", []),
            ("2026-08-08", [], "d", []),
            ("2026-08-09", [], "e", []),
        ]
        e = gw.bewerte(gates, retros)[0]
        assert e["nachher"] == 0
        assert e["gefangen"] == 2
        assert e["urteil"] != "RUECKFAELLIG"

    def test_should_still_count_an_uncaught_finding(self):
        """Die Markierung gilt je Retro, nicht pauschal fuer den Slug."""
        gates = [{"slug": "g", "built": "2026-08-01"}]
        retros = [
            ("2026-08-05", ["g"], "a", ["g"]),
            ("2026-08-06", ["g"], "b", []),
            ("2026-08-07", ["g"], "c", []),
            ("2026-08-08", [], "d", []),
        ]
        e = gw.bewerte(gates, retros)[0]
        assert e["nachher"] == 2
        assert e["gefangen"] == 1
        assert e["urteil"] == "RUECKFAELLIG"

    def test_should_read_gates_caught_from_frontmatter(self, tmp_path):
        (tmp_path / "session-retro-2026-08-05-platform-x.md").write_text(
            "---\nrecurring_findings: [g-slug]\ngates_caught: [g-slug]\n---\n",
            encoding="utf-8",
        )
        retros = gw.lies_retros([str(tmp_path)])
        assert retros[0][1] == ["g-slug"]
        assert retros[0][3] == ["g-slug"]

    def test_should_accept_old_three_tuples(self):
        """Aeltere Aufrufer reichen Dreier-Tupel — die duerfen nicht brechen."""
        gates = [{"slug": "g", "built": "2026-08-01"}]
        e = gw.bewerte(gates, [("2026-08-05", ["g"], "a")])[0]
        assert e["nachher"] == 1
        assert e["gefangen"] == 0


# ── Kalibrierfenster ────────────────────────────────────────────────────────
# Die Zusage "spaeter scharf" ist eine Vertagung mit Datum. Sie war bis zum
# 2026-08-23 Prosa in `revision_note`, und die erste Frist verfiel unbemerkt:
# das Protokoll trug 59 Zeilen, aber KEINE davon war beurteilbar (leerer
# Ausschnitt) und nur EINE gehoerte ueberhaupt der Kalibrierklasse. Deshalb
# zaehlen diese Tests genau die Trennung, an der es scheiterte — Treffer ist
# nicht gleich Datenpunkt.


def _hits(pfad: Path, zeilen: list[dict]) -> str:
    pfad.write_text(
        "\n".join(json.dumps(z, ensure_ascii=False) for z in zeilen) + "\n",
        encoding="utf-8",
    )
    return str(pfad)


def _zeile(
    ausschnitt: str,
    *,
    klasse: str = "kinds=subjekt-unbelegt-kalibrierung",
    zeit: str = "2026-08-25T10:00:00+00:00",
    slug: str = "g",
) -> dict:
    return {"zeit": zeit, "slug": slug, "marker": klasse, "ausschnitt": ausschnitt}


_FENSTER = {
    "slug": "g",
    "kalibrierfenster": {
        "klasse": "kinds=subjekt-unbelegt-kalibrierung",
        "seit": "2026-08-23",
        "bis": "2026-09-20",
        "min_beurteilbar": 3,
    },
}


def test_should_not_count_a_hit_without_a_snippet_as_judgeable(tmp_path):
    """Der Realfall: zaehlbar, aber nicht beurteilbar — und damit wertlos."""
    datei = _hits(tmp_path / "hits.jsonl", [_zeile(""), _zeile(""), _zeile("")])
    stand = gw.kalibrier_stand(_FENSTER, "2026-08-26", datei)
    assert stand["gesamt"] == 3
    assert stand["beurteilbar"] == 0
    assert stand["zustand"] == "sammelt"


def test_should_ignore_hits_of_another_class_of_the_same_gate(tmp_path):
    """59 Zeilen im Protokoll gehoerten dem regulaeren Treffer, nicht dem Fenster."""
    datei = _hits(
        tmp_path / "hits.jsonl",
        [_zeile("belegt", klasse="kinds=published-body") for _ in range(59)]
        + [_zeile("belegt")],
    )
    stand = gw.kalibrier_stand(_FENSTER, "2026-08-26", datei)
    assert stand["gesamt"] == 1
    assert stand["beurteilbar"] == 1


def test_should_ignore_hits_from_before_the_window_started(tmp_path):
    datei = _hits(
        tmp_path / "hits.jsonl",
        [_zeile("belegt", zeit="2026-08-19T10:00:00+00:00"), _zeile("belegt")],
    )
    assert gw.kalibrier_stand(_FENSTER, "2026-08-26", datei)["gesamt"] == 1


def test_should_call_the_window_decidable_once_the_minimum_is_reached(tmp_path):
    datei = _hits(tmp_path / "hits.jsonl", [_zeile("belegt") for _ in range(3)])
    stand = gw.kalibrier_stand(_FENSTER, "2026-08-26", datei)
    assert stand["zustand"] == "entscheidungsreif"


def test_should_report_an_expired_window_that_never_gathered_enough(tmp_path):
    """Genau der Fall vom 2026-09-03, der stumm verfallen waere."""
    datei = _hits(tmp_path / "hits.jsonl", [_zeile("belegt")])
    stand = gw.kalibrier_stand(_FENSTER, "2026-09-21", datei)
    assert stand["zustand"] == "abgelaufen"
    assert "neu setzen oder Fenster aufgeben" in gw.kalibrier_zeile(stand)


def test_should_survive_a_missing_protocol_without_claiming_success(tmp_path):
    stand = gw.kalibrier_stand(_FENSTER, "2026-08-26", str(tmp_path / "fehlt.jsonl"))
    assert stand["beurteilbar"] == 0
    assert stand["zustand"] == "sammelt"


def test_should_return_none_for_a_gate_without_a_window():
    assert gw.kalibrier_stand({"slug": "g"}, "2026-08-26") is None


def test_should_flag_a_window_without_a_minimum_as_misconfigured(tmp_path):
    """Ohne Mindestzahl kann das Fenster nie entscheidungsreif werden.

    Der Rand war bis 2026-08-23 ungetestet und still: `mindest > 0` schlug fehl,
    das Fenster blieb in "sammelt" haengen und fiel bei Fristablauf durch, ohne
    dass jemand erfuhr, warum (Retro a84f71 Befund 4).
    """
    gate = {
        "slug": "g",
        "kalibrierfenster": {
            "klasse": "kinds=x",
            "seit": "2026-08-23",
            "bis": "2026-09-20",
        },
    }
    datei = _hits(tmp_path / "hits.jsonl", [_zeile("belegt", klasse="kinds=x")])
    stand = gw.kalibrier_stand(gate, "2026-08-26", datei)
    assert stand["zustand"] == "unbestimmt"
    assert "keine Mindestzahl gesetzt" in gw.kalibrier_zeile(stand)


def test_should_treat_an_explicit_zero_minimum_the_same_way(tmp_path):
    gate = {
        "slug": "g",
        "kalibrierfenster": {
            "klasse": "kinds=x",
            "seit": "2026-08-23",
            "bis": "2026-09-20",
            "min_beurteilbar": 0,
        },
    }
    datei = _hits(tmp_path / "hits.jsonl", [])
    assert gw.kalibrier_stand(gate, "2026-08-26", datei)["zustand"] == "unbestimmt"
