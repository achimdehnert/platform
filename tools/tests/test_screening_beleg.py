"""Tests fuer die Beleg-Pruefung des Technologiescreenings (KONZ-063 Stufe 1).

Der Kern ist die **Positivkontrolle**: ein Pruefer, der nie anschlaegt, belegt
keine Abwesenheit. Die acht Proben unten sind dieselben, mit denen am
2026-09-22 die zuerst benutzte, laxe Fassung durchfiel (2 Fehlurteile) und die
verschaerfte bestand (0) — sie stehen hier, damit eine spaetere Lockerung der
Pruefung nicht unbemerkt durchgeht.
"""

import importlib.util
import json
import pathlib
import sys

_TOOLS = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "screening_beleg", _TOOLS / "screening_beleg.py"
)
sb = importlib.util.module_from_spec(_spec)
sys.modules["screening_beleg"] = sb
_spec.loader.exec_module(sb)

# Echte Schlagzeilen aus dem Fenster 2026-09-15…09-21 der Morgen-Zeitung.
STOFF = [
    sb.norm("World Labs' Atlas Model Rebuilds a Campus in Real Time"),
    sb.norm("Jev auto-routes GenAI models – OpenArt Arena debut creative leaderboard"),
    sb.norm("Two New OCR Models Land on Hugging Face – Jev Puts Encoder Models Center"),
    sb.norm("14,7 MB-Modell erkennt sensible Daten lokal – Open-Source-Alternative"),
]


def _kandidat(**kv):
    basis = {
        "name": "Jev",
        "topf": "kompetenz",
        "warum": "routet Modelle",
        "beleg": "Jev auto-routes GenAI models – OpenArt Arena debut creative leaderboard",
    }
    basis.update(kv)
    return basis


# --- Positivkontrolle: der Pruefer muss anschlagen koennen -------------------


def test_should_accept_verbatim_headline():
    assert sb.beleg_gilt(
        "World Labs' Atlas Model Rebuilds a Campus in Real Time", STOFF
    )


def test_should_accept_second_verbatim_headline():
    assert sb.beleg_gilt(
        "Two New OCR Models Land on Hugging Face – Jev Puts Encoder Models Center",
        STOFF,
    )


def test_should_reject_freely_invented_beleg():
    assert not sb.beleg_gilt(
        "Astra ist eine LLM-Variante fuer klinische Anwendungen in Kliniken", STOFF
    )


def test_should_reject_plausible_invention():
    # Der gefaehrliche Fall: echte Schlagzeile plus erfundener Nachsatz.
    assert not sb.beleg_gilt(
        "Two New OCR Models Land on Hugging Face and beat Google Cloud Vision", STOFF
    )


def test_should_reject_half_invented_beleg():
    # Ein Wort getauscht: Campus -> Hospital.
    assert not sb.beleg_gilt(
        "World Labs' Atlas Model Rebuilds a Hospital in Real Time", STOFF
    )


def test_should_reject_short_word_that_is_a_substring():
    # Genau hier fiel die zweiseitige Fassung um: „AI" steckt in jeder Zeile.
    assert not sb.beleg_gilt("AI", STOFF)


def test_should_reject_single_product_name_as_beleg():
    assert not sb.beleg_gilt("Astra", STOFF)


def test_should_reject_empty_beleg():
    assert not sb.beleg_gilt("", STOFF)


# --- Normalisierung ---------------------------------------------------------


def test_should_match_despite_unicode_dashes_and_quotes():
    # Das Modell gibt Striche und Anfuehrungszeichen nicht zeichengetreu zurueck.
    assert sb.beleg_gilt(
        "World Labs' Atlas Model Rebuilds a Campus in Real Time", STOFF
    )
    assert sb.beleg_gilt("Jev auto-routes GenAI models - OpenArt Arena debut", STOFF)


# --- Sieb -------------------------------------------------------------------


def test_should_keep_candidate_with_findable_beleg():
    behalten, verworfen = sb.pruefe([_kandidat()], STOFF)
    assert [k["name"] for k in behalten] == ["Jev"]
    assert verworfen == []


def test_should_drop_candidate_with_invented_beleg_and_name_the_reason():
    _, verworfen = sb.pruefe(
        [_kandidat(beleg="Jev heilt Krebs laut Studie von gestern")], STOFF
    )
    assert verworfen[0]["grund"] == "Beleg nicht im Stoff auffindbar"


def test_should_drop_duplicates():
    behalten, verworfen = sb.pruefe([_kandidat(), _kandidat()], STOFF)
    assert len(behalten) == 1
    assert verworfen[0]["grund"] == "Dublette"


def test_should_fall_back_to_offen_for_unknown_topf():
    behalten, _ = sb.pruefe([_kandidat(topf="marketing")], STOFF)
    assert behalten[0]["topf"] == "offen"


# --- Fragetext --------------------------------------------------------------


def test_should_stay_silent_without_candidates():
    # REC-22: lieber keine Meldung als eine Pflichtmeldung.
    assert sb.frage_text([]) == ""


def test_should_end_with_the_thumb_sentence():
    behalten, _ = sb.pruefe([_kandidat()], STOFF)
    assert sb.frage_text(behalten).endswith(sb.DAUMEN_SATZ)


def test_should_ask_at_most_one_per_message():
    zwei = [
        _kandidat(),
        _kandidat(
            name="Atlas", beleg="World Labs' Atlas Model Rebuilds a Campus in Real Time"
        ),
    ]
    behalten, _ = sb.pruefe(zwei, STOFF)
    text = sb.frage_text(behalten)
    assert "2." not in text


def test_should_not_reorder_candidates():
    # Die Auswahl ist der teure Schritt (D4) und passiert anderswo. Baute man
    # hier eine Rangfolge ein, waere er still durch den guenstigen ersetzt.
    zwei = [
        _kandidat(
            name="Atlas", beleg="World Labs' Atlas Model Rebuilds a Campus in Real Time"
        ),
        _kandidat(),
    ]
    behalten, _ = sb.pruefe(zwei, STOFF)
    assert [k["name"] for k in behalten] == ["Atlas", "Jev"]


def test_should_carry_the_beleg_into_the_message():
    behalten, _ = sb.pruefe([_kandidat()], STOFF)
    assert "Beleg:" in sb.frage_text(behalten)


# --- CLI --------------------------------------------------------------------


def _schreibe(tmp_path, kandidaten):
    k = tmp_path / "k.json"
    k.write_text(
        json.dumps({"kandidaten": kandidaten}, ensure_ascii=False), encoding="utf-8"
    )
    korpus = tmp_path / "korpus.tsv"
    korpus.write_text(
        "T\t2026-09-21\tJev auto-routes GenAI models – OpenArt Arena debut creative leaderboard\n",
        encoding="utf-8",
    )
    return str(k), str(korpus)


def test_should_exit_0_when_a_candidate_holds(tmp_path, capsys):
    k, korpus = _schreibe(tmp_path, [_kandidat()])
    assert sb.main(["--kandidaten", k, "--korpus", korpus]) == 0
    assert sb.DAUMEN_SATZ in capsys.readouterr().out


def test_should_exit_1_when_nothing_holds(tmp_path, capsys):
    k, korpus = _schreibe(
        tmp_path, [_kandidat(beleg="frei erfunden und lang genug gemacht")]
    )
    assert sb.main(["--kandidaten", k, "--korpus", korpus]) == 1
    assert capsys.readouterr().out.strip() == ""


def test_should_exit_2_on_unreadable_candidates(tmp_path):
    _, korpus = _schreibe(tmp_path, [])
    assert (
        sb.main(["--kandidaten", str(tmp_path / "fehlt.json"), "--korpus", korpus]) == 2
    )
