"""Drill fuer tools/verankerung_pruefer.py (Gate `zusage-ohne-verankerung`, platform#2211).

Der Klassifikator laeuft ueber ein lokales Modell und ist damit in CI nicht
verfuegbar. Deshalb ist die Arbeitsteilung hier bewusst scharf:

* Alles Deterministische — Normalisierung, Segmentierung, Anker-Zustaendigkeit,
  Bericht, Ehrlichkeits-Sperre — wird **echt** geprueft, ohne Modell.
* Die Klassifikation selbst wird ueber einen eingesetzten Stub geprueft; ihre
  Guete ist **gemessen**, nicht behauptet, und steht in
  ``docs/governance/verankerung-kalibrierung-2026-08-23.md``. Ein
  ``pytest.importorskip``-artiges Stillschweigen waere hier die falsche Antwort:
  ein uebersprungener Test sieht gruen aus und prueft nichts.

Der wichtigste Test ist ``test_should_realfall_pr2007_finden``: er faehrt den
Wortlaut, an dem beide bestehenden Muster-Scanner nachweislich vorbeisehen.
"""

import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))
sys.path.insert(0, str(TOOL_DIR / "claude-hooks"))

import verankerung_pruefer  # noqa: E402
from verankerung_pruefer import (  # noqa: E402
    GATE_HEADER,
    GEGENPROBE,
    Ankerurteil,
    bericht,
    normalisiere,
    pruefe,
    pruefe_anker,
    segmentiere,
)

# Der echte Absatz aus PR platform#2007 — Retro 9d861a Befund #3.
PR2007_ABSATZ = (
    "## Bewusste Restüberschneidung\n\n"
    "Es gibt jetzt zwei Befund-Gedächtnisse: `befund_journal.py` (Runner-WARN-Zeilen, "
    "aus [#2005](https://github.com/achimdehnert/platform/pull/2005)) und "
    "`befund_leseflaeche.py` (nächtlicher Workflow-Report). Verschiedene Quellen, "
    "verschiedene Lebenszyklen — eine Zusammenlegung wäre ein eigener Umbau und ist "
    "hier bewusst **nicht** mitgemacht. Sichtbar wird sie sofort.\n\n"
    "Closes #2006\n\n"
    "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
)


def _stub(klasse: str, zitat: str = "z"):
    """Klassifikator-Attrappe: entscheidet nach einem Merkmal des Textes.

    Bewusst KEINE Attrappe, die immer dasselbe liefert — sonst prueft der Test
    die Verdrahtung nicht, sondern nur sich selbst.
    """

    def klassifiziere(text: str) -> dict:
        if "mitgemacht" in text:
            return {"klasse": klasse, "zitat": zitat, "begruendung": "stub"}
        return {"klasse": "keine", "zitat": "", "begruendung": "stub"}

    return klassifiziere


# ── Fehlermodus A: Auszeichnung zerreisst den Wortlaut ───────────────────────


def test_should_fettschrift_aus_dem_wortlaut_nehmen():
    assert "bewusst nicht mitgemacht" in normalisiere("bewusst **nicht** mitgemacht")


def test_should_belegen_dass_der_alte_scanner_erst_nach_normalisierung_sieht():
    """Der Beleg fuer den Umbau: dasselbe Muster, einmal blind, einmal sehend.

    Ohne diesen Test bliebe „der Regex sieht es nicht" eine Behauptung.
    """
    from deferred_item_scanner import DEFERRAL_PATTERNS

    roh = "eine Zusammenlegung ist hier bewusst **nicht** mitgemacht"
    assert DEFERRAL_PATTERNS.search(roh) is None
    assert DEFERRAL_PATTERNS.search(normalisiere(roh)) is not None


def test_should_link_ziel_beim_normalisieren_behalten():
    text = normalisiere("aus [#2005](https://github.com/a/b/pull/2005)")
    assert "pull/2005" in text and "#2005" in text


# ── Segmentierung ────────────────────────────────────────────────────────────


def test_should_ueberschrift_als_kontext_an_das_segment_haengen():
    segmente = segmentiere(normalisiere(PR2007_ABSATZ))
    assert len(segmente) == 1, [s.text[:40] for s in segmente]
    assert segmente[0].ueberschrift == "Bewusste Restüberschneidung"
    assert "Bewusste Restüberschneidung" in segmente[0].volltext


def test_should_beiwerk_und_schliess_zeile_nicht_als_segment_fuehren():
    """Signatur und `Closes #N` erben sonst die letzte Ueberschrift.

    Genau so entstand im Kalibrierlauf ein Fehlalarm „restarbeit" auf der
    Claude-Code-Signatur.
    """
    texte = [s.text for s in segmentiere(normalisiere(PR2007_ABSATZ))]
    assert not any("Generated with" in t for t in texte)
    assert not any(t.strip().startswith("Closes") for t in texte)


def test_should_codebloecke_ueberspringen():
    text = "## H\n\nEin Satz der lang genug ist um als Segment zu zaehlen hier.\n\n```\nbewusst vertagt und ausgelassen fuer immer und ewig ohne Anker\n```\n"
    assert all("bewusst vertagt" not in s.text for s in segmentiere(text))


def test_should_zu_kurze_absaetze_nicht_pruefen():
    assert segmentiere("## H\n\nzu kurz.\n") == []


# ── Fehlermodus B: Naehe ist keine Zustaendigkeit ────────────────────────────


def test_should_pr_link_nicht_als_anker_gelten_lassen():
    urteil = pruefe_anker(
        "aus [#2005](https://github.com/achimdehnert/platform/pull/2005)",
        mit_github=False,
    )
    assert urteil.verankert is False
    assert "Pull Request" in urteil.grund or "PR-Link" in urteil.grund


def test_should_issue_link_als_anker_gelten_lassen():
    urteil = pruefe_anker(
        "getrackt in https://github.com/achimdehnert/platform/issues/2006",
        mit_github=False,
    )
    assert urteil.verankert is True


def test_should_ohne_referenz_nicht_verankert_sein():
    assert (
        pruefe_anker("nur Prosa ohne jede Referenz", mit_github=False).verankert
        is False
    )


def test_should_blosse_nummer_offline_als_unsicher_werten():
    urteil = pruefe_anker("getrackt in #4711", mit_github=False)
    assert urteil.verankert is True and urteil.unsicher is True


# ── Zusammenspiel ────────────────────────────────────────────────────────────


def test_should_realfall_pr2007_finden():
    """Positivkontrolle am echten Rueckfall (Retro 9d861a #3)."""
    befunde, segmente, _ = pruefe(
        PR2007_ABSATZ, _stub("vertagung"), mit_github=False, klassen=("vertagung",)
    )
    assert len(befunde) == 1, [b.segment.text[:60] for b in befunde]
    assert befunde[0].klasse == "vertagung"
    assert (
        "Pull Request" in befunde[0].anker.grund or "PR-Link" in befunde[0].anker.grund
    )


def test_should_bei_issue_anker_schweigen():
    """Gegenprobe gegen Rauschen: dieselbe Zusage, aber mit Tracking-Issue."""
    mit_anker = PR2007_ABSATZ.replace(
        "Sichtbar wird sie sofort.",
        "Getrackt in https://github.com/achimdehnert/platform/issues/2099.",
    )
    befunde, _, _ = pruefe(
        mit_anker, _stub("vertagung"), mit_github=False, klassen=("vertagung",)
    )
    assert befunde == []


def test_should_nur_die_gewaehlten_klassen_melden():
    befunde, _, _ = pruefe(
        PR2007_ABSATZ, _stub("restarbeit"), mit_github=False, klassen=("vertagung",)
    )
    assert befunde == []


def test_should_gegenprobe_einen_kandidaten_verwerfen_koennen():
    befunde, _, _ = pruefe(
        PR2007_ABSATZ,
        _stub("vertagung"),
        mit_github=False,
        klassen=("vertagung",),
        bestaetiger=lambda text, klasse, zitat: False,
    )
    assert befunde == []


# ── Bericht + Ehrlichkeits-Sperre ────────────────────────────────────────────


def test_should_leere_pruefung_nicht_als_sauber_ausgeben():
    assert "kein pruefbares Segment" in bericht([], [], "x", block=False)


def test_should_sauberen_lauf_als_solchen_ausweisen():
    segmente = segmentiere(normalisiere(PR2007_ABSATZ))
    assert "✅" in bericht([], segmente, "x", block=False)


def test_should_gegenprobe_nach_dem_typ_fragen_nicht_nach_dem_zustand():
    """Die zwei Stufen muessen dieselbe Frage stellen — sonst hebt die zweite die erste auf.

    Gemessen am 2026-08-28: der frueher hier stehende Wortlaut („Steht die
    genannte Arbeit NOCH AUS?") liess den dokumentierten Zielfall aus PR #2007
    durchfallen. Das Modell antwortete `false` und begruendete das mit
    „Zusammenlegung ausgeschlagen" — eine abgelehnte Arbeit steht tatsaechlich
    nicht mehr aus. Der Klassifikator fragt aber nach dem TYP (wird Arbeit
    ausgelassen?), nicht nach dem ZUSTAND. Dieser Test haelt die Definitionen
    zusammen; er ersetzt keinen Modelllauf, aber er faengt das Zurueckdrehen.
    """
    assert "NOCH AUS" not in GEGENPROBE
    assert "AUSGELASSEN" in GEGENPROBE
    assert "trifft_zu" in GEGENPROBE
    # Der Verzicht darf nicht als Erledigung durchgehen — genau daran scheiterte es.
    assert "erledigt-durch-Verzicht" in GEGENPROBE


def test_should_nicht_erreichbares_modell_als_nicht_pruefbar_melden():
    """„Nichts gefunden" und „nichts pruefen koennen" sind zwei Aussagen."""
    lauf = subprocess.run(
        [
            sys.executable,
            str(TOOL_DIR / "verankerung_pruefer.py"),
            "--host",
            "http://127.0.0.1:1",
            "--ohne-github",
        ],
        input=PR2007_ABSATZ,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert lauf.returncode == 2, lauf.stdout
    assert "NICHT PRUEFBAR" in lauf.stderr
    assert "✅" not in lauf.stdout


# ── Kopf-Konsistenz (KONZ-038 D8) ────────────────────────────────────────────


@pytest.mark.parametrize("feld", ["slug", "mode", "owner", "last_drill_pass"])
def test_should_gate_header_pflichtfelder_tragen(feld):
    assert feld in GATE_HEADER


def test_should_advisory_bleiben_bis_das_kalibrierfenster_ausgewertet_ist():
    """Scharfschaltung ist eine Entscheidung, kein Nebeneffekt eines Edits."""
    assert GATE_HEADER["mode"] == "advisory"


def test_should_nur_gemessene_slugs_beanspruchen():
    """`covers` ist eine Behauptung ueber Wirkung — sie braucht eine Messung.

    Nur `deferred-item-no-tracking-issue` ist am Realfall belegt; jede weitere
    Zeile hier muesste einen eigenen Positivbeleg mitbringen.
    """
    assert GATE_HEADER["covers"] == ["deferred-item-no-tracking-issue"]


def test_should_ankerurteil_default_nicht_verankert_sein():
    assert Ankerurteil(False, "").verankert is False


def test_should_belegen_dass_beide_musterlisten_bei_neuer_formulierung_schweigen():
    """Der Generalisierungs-Beleg, deterministisch gefasst.

    Wortlaut: „Das Aufraeumen der Altlast hebe ich mir fuer den naechsten
    Durchgang auf." Eine gewoehnliche Vertagung — und in **keiner** der beiden
    Musterlisten enthalten. Der Typ-Pruefer meldet sie im Lauf vom 2026-08-23
    korrekt als `vertagung` (Zitat „hebe ich mir fuer den naechsten Durchgang
    auf", siehe Kalibrier-Datei); dieser Test haelt die andere Haelfte fest,
    die ohne Modell pruefbar ist: dass die Muster schweigen.

    Faellt er, weil jemand das Muster nachtraegt, ist das die Rueckkehr genau
    des Verfahrens, das 9 Rueckfaelle erzeugt hat — dann gehoert die Aufzaehlung
    besprochen, nicht der Test angepasst.
    """
    from deferral_anchor_check import AUFSCHUB
    from deferred_item_scanner import DEFERRAL_PATTERNS

    satz = (
        "Das Aufraeumen der Altlast in der alten Struktur hebe ich mir fuer den "
        "naechsten Durchgang auf."
    )
    assert DEFERRAL_PATTERNS.search(satz) is None
    assert AUFSCHUB.search(satz) is None


# ── Zeitbudget (#2469) ───────────────────────────────────────────────────────


def _langer_text(n: int) -> str:
    """n Absaetze, damit segmentiere() n Segmente liefert."""
    return "\n\n".join(
        f"Absatz {i}: Das machen wir spaeter, sobald die Migration steht."
        for i in range(n)
    )


def test_should_stop_when_the_overall_budget_is_used_up():
    """Der Pro-Anfrage-Timeout begrenzt EINE Anfrage, nicht den Lauf.

    Gemessen 2026-08-30: rund 8 s je Aufruf; bei vielen Segmenten laeuft das
    Werkzeug minutenlang, und die Sitzung bricht es ab — dann liegt GAR KEIN
    Ergebnis vor. Mit Budget liefert es das bis dahin Gepruefte.
    """
    text = _langer_text(10)
    uhr = iter([0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0])
    befunde, geprueft, ungeprueft = pruefe(
        text,
        _stub("vertagung"),
        mit_github=False,
        klassen=("vertagung",),
        budget_sekunden=3.0,
        uhr=lambda: next(uhr),
    )
    assert ungeprueft, "Budget hat nicht gegriffen"
    assert len(geprueft) + len(ungeprueft) == 10
    assert len(geprueft) < 10


def test_should_check_everything_when_budget_is_generous():
    """Positivkontrolle: ohne Druck bleibt nichts ungeprueft."""
    text = _langer_text(5)
    befunde, geprueft, ungeprueft = pruefe(
        text,
        _stub("vertagung"),
        mit_github=False,
        klassen=("vertagung",),
        budget_sekunden=3600.0,
    )
    assert ungeprueft == []
    assert len(geprueft) == 5


def test_should_not_call_a_partial_run_clean():
    """Ein Teillauf darf sich NIE wie ein Freispruch lesen — das ist der Kern.

    Ohne eigene Klasse wuerde ein abgebrochener Lauf mit dem gruenen Haken
    enden und genau die Zusagen decken, die er nie gesehen hat.
    """
    segmente = segmentiere(normalisiere(PR2007_ABSATZ))
    text = bericht([], segmente, "x", block=False, ungeprueft=7)
    assert "✅" not in text
    assert "UNGEPRUEFT" in text and "7" in text
    assert "keine Entwarnung" in text


def test_should_still_mark_a_complete_clean_run_green():
    """Gegenprobe: ohne Rest bleibt der gruene Haken gruen."""
    segmente = segmentiere(normalisiere(PR2007_ABSATZ))
    assert "✅" in bericht([], segmente, "x", block=False, ungeprueft=0)


def test_should_append_the_rest_note_to_a_finding_report():
    """Auch mit Befund muss der ungepruefte Rest sichtbar bleiben."""
    befunde, segmente, _ = pruefe(
        PR2007_ABSATZ, _stub("vertagung"), mit_github=False, klassen=("vertagung",)
    )
    text = bericht(befunde, segmente, "x", block=False, ungeprueft=3)
    assert "UNGEPRUEFT" in text


# ── Fehlerpfad: Zeitueberschreitung ist kein Ausfall (platform#2456) ─────────
#
# Beide Faelle liefen bisher in dieselbe Meldung »nicht erreichbar«. Die hat die
# Diagnose zweimal in die falsche Richtung geschickt (#2456, #2436): gesucht
# wurde bei ollama, obwohl der Host antwortete und nur laenger rechnete als der
# Timeout. Die Tests unterscheiden genau das — ohne den Fix faellt der erste
# durch, weil die Meldung »nicht erreichbar« lautet.


def _urlopen_wirft(exc):
    """Ersetzt urlopen im Modul durch einen Werfer — kein Netz, kein Modell."""

    def wirf(*_a, **_k):
        raise exc

    return wirf


@pytest.mark.parametrize(
    "exc",
    [
        TimeoutError("timed out"),
        # Beim Verbindungsaufbau verpackt urllib denselben Fall in URLError.
        urllib.error.URLError(TimeoutError("timed out")),
    ],
    ids=["lesetimeout", "verbindungstimeout"],
)
def test_should_name_a_timeout_a_timeout_not_an_outage(monkeypatch, exc):
    monkeypatch.setattr(
        verankerung_pruefer.urllib.request, "urlopen", _urlopen_wirft(exc)
    )
    klassifiziere = verankerung_pruefer.ollama_klassifikator(timeout=90)
    with pytest.raises(verankerung_pruefer.NichtPruefbar) as fehler:
        klassifiziere("Das mache ich spaeter.")
    meldung = str(fehler.value)
    assert "Zeitueberschreitung" in meldung, meldung
    assert "90 s" in meldung, meldung
    assert "Zeichen Prompt" in meldung, meldung
    assert "nicht erreichbar" not in meldung, meldung


def test_should_still_call_a_real_outage_unreachable(monkeypatch):
    """Gegenprobe: ein echter Verbindungsfehler behaelt seinen Namen."""
    monkeypatch.setattr(
        verankerung_pruefer.urllib.request,
        "urlopen",
        _urlopen_wirft(urllib.error.URLError(ConnectionRefusedError(111, "refused"))),
    )
    klassifiziere = verankerung_pruefer.ollama_klassifikator()
    with pytest.raises(verankerung_pruefer.NichtPruefbar) as fehler:
        klassifiziere("Das mache ich spaeter.")
    meldung = str(fehler.value)
    assert "nicht erreichbar" in meldung, meldung
    assert "Zeitueberschreitung" not in meldung, meldung


def test_should_name_the_countercheck_when_it_times_out(monkeypatch):
    """Auch die Gegenprobe nennt die Zeit — sie lief in dieselbe Sammelmeldung."""
    monkeypatch.setattr(
        verankerung_pruefer.urllib.request,
        "urlopen",
        _urlopen_wirft(TimeoutError("timed out")),
    )
    bestaetige = verankerung_pruefer.ollama_bestaetiger(timeout=45)
    with pytest.raises(verankerung_pruefer.NichtPruefbar) as fehler:
        bestaetige("Das mache ich spaeter.", "vertagung", "spaeter")
    meldung = str(fehler.value)
    assert "Gegenprobe" in meldung, meldung
    assert "Zeitueberschreitung nach 45 s" in meldung, meldung
