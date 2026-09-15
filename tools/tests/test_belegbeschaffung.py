"""Tests für tools/sevdesk/belegbeschaffung.py — Belegbeschaffung (K9, platform#3102).

Postfach (Microsoft Graph) und sevdesk kommen ausschließlich über injizierte
Fakes herein — keine Anfrage verlässt den Prozess, kein Zugang wird gebraucht.
Alle PDF-Texte, Namen, Nummern und Beträge sind synthetisch (platform ist ein
öffentliches Repo, s. CLAUDE.md).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import belegbeschaffung as bb  # noqa: E402

HEUTE = dt.date(2026, 4, 15)


# ── synthetische PDF-Texte ─────────────────────────────────────────────────

PDF_RECEIPT_USD = """
Beispiel Plattform Inc.
Payment Receipt
Date 2026-04-07 10:32AM PDT
Account billed testkonto (rechnung@example.invalid)
Transaction ID ch_synthetisch123
Team Plan                                    $36.98 USD
Extra                                        $10.00 USD
Total $46.98 USD*
* VAT/GST paid directly by Beispiel Plattform
"""

PDF_RECHNUNG_EUR_EDV = """
Beispiel Cloud Europe
Abrechnungsprofil Synthetik-Profil
Abrechnungsnummer S999000111
Belegdatum 07/04/2026
Käufer Rechnungsempfänger:
Beispiel EDV Beratung
Zwischensumme 624.00
Steuer 118.56
Gesamtbetrag (nach Steuern) EUR 742.56
"""

# Hoster-Muster nach Echtprobe 2026-09-13: Summe heisst "Zu zahlender Betrag",
# und die Fusszeile traegt eine USt-IdNr. — beides hat den Parser zunaechst
# ueberfordert (kein Betrag, Identifikationsnummer als Steuerbetrag).
PDF_RECHNUNG_EUR_KOMMA = """
Beispiel Hosting SE
Rechnungsnummer: 100000000001
Rechnungsdatum: 05.04.2026
Kunde: IIL GmbH
Zwischensumme Netto (19,0 %) 100,00 EUR
+ Mehrwertsteuer (19,0 %) 19,00 EUR
Zu zahlender Betrag 119,00 EUR
Hauptsitz Musterstadt, HRB 00000 · USt-IdNr.: DE000000000
"""


PDF_RECHNUNG_NUR_DOMAIN = """
Beispiel Modelle Inc.
Receipt
Date 2026-04-06
Bill to: rechnung@iil.gmbh
Amount paid $25.00 USD
Total $25.00 USD
"""


# ── Register ───────────────────────────────────────────────────────────────


@pytest.fixture()
def register_datei(tmp_path) -> Path:
    pfad = tmp_path / "bezugswege.json"
    pfad.write_text(
        json.dumps(
            {
                "eintraege": [
                    {
                        "muster": "beispiel plattform",
                        "weg": "mail",
                        "lieferant": "Beispiel Plattform Inc.",
                        "absender": "noreply@example.invalid",
                        "betreff": "Payment Receipt",
                        "ordner": ["Beispielordner"],
                        "logins": {"testkonto": "iil", "privatkonto": "edv"},
                        "taxrule": "12",
                        "waehrung": "USD",
                    },
                    {
                        # Muster toleriert Bindestrich: Dateinamen aus der
                        # Owner-Ablage schreiben den Lieferanten so.
                        "muster": "beispiel[ -]?cloud",
                        "weg": "mail",
                        "lieferant": "Beispiel Cloud",
                        "absender": "noreply@cloud.invalid",
                        "betreff": "Rechnung",
                        "ordner": ["inbox"],
                        "taxrule": "9",
                    },
                    {
                        "muster": "beispiel modelle",
                        "weg": "mail",
                        "lieferant": "Beispiel Modelle Inc.",
                        "absender": "invoice@modelle.invalid",
                        "betreff": "Your receipt",
                        "ordner": ["Modellordner"],
                        "ohne_abgang": True,
                        "taxrule": "12",
                    },
                    {
                        "muster": "beispiel abo",
                        "weg": "portal",
                        "lieferant": "Beispiel Abo",
                        "url": "https://portal.example.invalid/",
                    },
                    {
                        "muster": "lohn|minijob",
                        "weg": "intern",
                        "lieferant": "Lohn",
                        "grund": "Lohnabrechnung, kein Lieferantenbeleg",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return pfad


def _abgang(datum: str, zahler: str, betrag: float, zweck: str = "") -> dict:
    return {
        "datum": datum,
        "zahler": zahler,
        "zweck": zweck,
        "betrag": betrag,
        "konto_vorschlag": "6837 — Lizenzen",
        "konto_grund": "Regel",
    }


def test_should_match_register_entry_via_zweck_when_zahler_is_dash(register_datei):
    """Lastschrift ohne geparsten Namen: nur der Verwendungszweck trägt den
    Lieferanten — das Register muss trotzdem greifen."""
    register = bb.register_laden(register_datei)
    treffer = bb.eintrag_fuer(
        _abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC MTHLY"), register
    )
    assert treffer is not None
    assert treffer["lieferant"] == "Beispiel Plattform Inc."


def test_should_return_none_when_no_register_entry_matches(register_datei):
    register = bb.register_laden(register_datei)
    assert (
        bb.eintrag_fuer(_abgang("2026-04-10", "Unbekannt AG", 10.0), register) is None
    )


def test_should_exit_3_when_register_file_is_missing(tmp_path, capsys):
    code = bb.main(
        [
            "--register",
            str(tmp_path / "gibtsnicht.json"),
            "--eingabe",
            str(_eingabe_datei(tmp_path, [])),
            "--heute",
            "2026-04-15",
        ]
    )
    assert code == 3
    assert "Bezugswege-Register fehlt" in capsys.readouterr().out


# ── PDF-Parser ─────────────────────────────────────────────────────────────


def test_should_read_usd_receipt_without_tax():
    feld = bb.pdf_lesen(PDF_RECEIPT_USD, "beleg-2026-04-07.pdf", ["testkonto"])
    assert feld["datum"] == "2026-04-07"
    assert feld["brutto"] == 46.98
    assert feld["steuer"] == 0.00
    assert feld["waehrung"] == "USD"
    assert feld["nummer"] == "ch_synthetisch123"


def test_should_read_eur_invoice_with_tax_and_slash_date():
    feld = bb.pdf_lesen(PDF_RECHNUNG_EUR_EDV, "S999000111.pdf")
    assert feld["datum"] == "2026-04-07"
    assert feld["brutto"] == 742.56
    assert feld["steuer"] == 118.56
    assert feld["waehrung"] == "EUR"
    assert feld["nummer"] == "S999000111"


def test_should_read_german_decimal_comma_and_dotted_date():
    feld = bb.pdf_lesen(PDF_RECHNUNG_EUR_KOMMA, "rechnung.pdf")
    assert feld["datum"] == "2026-04-05"
    assert feld["brutto"] == 119.00
    assert feld["steuer"] == 19.00
    assert feld["waehrung"] == "EUR"
    assert feld["nummer"] == "100000000001"


def test_should_ignore_vat_id_line_when_reading_the_tax_amount():
    """Die Fusszeile mit der USt-IdNr. ist der letzte Treffer auf 'ust' — ohne
    Ausnahme wuerde die Identifikationsnummer zum Steuerbetrag."""
    feld = bb.pdf_lesen(PDF_RECHNUNG_EUR_KOMMA, "rechnung.pdf")
    assert feld["steuer"] == 19.00


def test_should_read_spelled_out_month_dates():
    """Rechnungen aus dem englischen Sprachraum schreiben den Monat aus; ohne
    diese Schreibweise blieben sie ohne Datum und damit ohne Entwurf."""
    englisch = (
        "Invoice\nDate of issue May 13, 2026\nDate due June 12, 2026\nAmount due €12.00"
    )
    deutsch = "Rechnung\nRechnungsdatum 13. Mai 2026\nGesamtbetrag 12,00 EUR"
    assert bb.pdf_lesen(englisch, "a.pdf")["datum"] == "2026-05-13"
    assert bb.pdf_lesen(deutsch, "b.pdf")["datum"] == "2026-05-13"


def test_should_parse_year_first_slash_date():
    """JJJJ/MM/TT (BiblioCAD-Quittungen) — und DD/MM/YYYY bleibt unveraendert
    erkannt (2026-09-13)."""
    assert bb._datum_aus("Stripe recurrent 2026/01/13 USD $18.82") == "2026-01-13"
    assert bb._datum_aus("Rechnungsdatum 07/09/2025") == "2025-09-07"


def test_should_fall_back_to_filename_when_no_invoice_number_in_text():
    feld = bb.pdf_lesen("Irgendein Text ohne Nummer\nGesamt 10,00 €", "beleg-4711.pdf")
    assert feld["nummer"] == "beleg-4711"


def test_should_detect_own_mandant_from_account_billed_login():
    assert bb.empfaenger_bestimmen(PDF_RECEIPT_USD, ["testkonto"]) == "iil"


def test_should_flag_unklar_when_account_billed_login_is_foreign():
    assert bb.empfaenger_bestimmen(PDF_RECEIPT_USD, ["andereslogin"]) == "unklar"


def test_should_detect_edv_mandant_from_invoice_text():
    assert bb.empfaenger_bestimmen(PDF_RECHNUNG_EUR_EDV) == "edv"


def test_should_detect_iil_mandant_from_invoice_text():
    assert bb.empfaenger_bestimmen(PDF_RECHNUNG_EUR_KOMMA) == "iil"


# ── Zuordnung ──────────────────────────────────────────────────────────────


def _beleg(
    datum: str, brutto: float, waehrung: str = "EUR", nummer: str = "N1"
) -> dict:
    return {
        "datum": datum,
        "brutto": brutto,
        "steuer": 0.00,
        "waehrung": waehrung,
        "nummer": nummer,
        "empfaenger": "iil",
        "pfad": f"/tmp/synthetisch/{nummer}.pdf",
        "lieferant": "Beispiel",
    }


def test_should_match_exact_eur_amount_within_date_window():
    paare, ohne_pdf, ohne_abgang = bb.zuordnen(
        [_abgang("2026-04-10", "Beispiel", 119.00)], [_beleg("2026-04-05", 119.00)]
    )
    assert len(paare) == 1
    assert paare[0]["art"] == "sicher"
    assert not ohne_pdf and not ohne_abgang


def test_should_match_foreign_currency_only_inside_the_rate_band():
    """EUR-Abgang gegen USD-Receipt: Quotient 43.05/46.98 = 0.92 — Kandidat,
    aber nie 'sicher'."""
    paare, _, _ = bb.zuordnen(
        [_abgang("2026-04-10", "Beispiel", 43.05)],
        [_beleg("2026-04-07", 46.98, waehrung="USD")],
    )
    assert len(paare) == 1
    assert paare[0]["art"] == "fremdwaehrung"


def test_should_not_match_foreign_currency_outside_the_rate_band():
    paare, ohne_pdf, _ = bb.zuordnen(
        [_abgang("2026-04-10", "Beispiel", 20.00)],
        [_beleg("2026-04-07", 46.98, waehrung="USD")],
    )
    assert paare == []
    assert len(ohne_pdf) == 1


def test_should_not_match_when_date_window_is_violated():
    paare, ohne_pdf, ohne_abgang = bb.zuordnen(
        [_abgang("2026-04-10", "Beispiel", 119.00)], [_beleg("2026-01-05", 119.00)]
    )
    assert paare == []
    assert len(ohne_pdf) == 1 and len(ohne_abgang) == 1


def test_should_assign_each_pdf_to_at_most_one_abgang():
    """Zwei gleich hohe Abgänge, ein PDF: der datumsnähere gewinnt, der andere
    bleibt ohne Beleg — nie beide auf dasselbe PDF."""
    paare, ohne_pdf, _ = bb.zuordnen(
        [
            _abgang("2026-04-10", "Beispiel", 119.00),
            _abgang("2026-04-25", "Beispiel", 119.00),
        ],
        [_beleg("2026-04-09", 119.00)],
    )
    assert len(paare) == 1
    assert paare[0]["abgang"]["datum"] == "2026-04-10"
    assert len(ohne_pdf) == 1


# ── Lauf: Postfach-Fakes, Entwürfe, Idempotenz ─────────────────────────────


class _Postfach:
    """Minimales Fake-Postfach: eine Nachricht je Lieferant, PDF-Text wird beim
    'Download' als Datei geschrieben."""

    def __init__(self, nachrichten: dict[str, tuple[str, str, str]]):
        # id -> (ordner, dateiname, text)
        self.nachrichten = nachrichten
        self.downloads: list[str] = []
        self.suchen: list[tuple[str, str, int, str]] = []

    def suche_fn(self, absender, betreff, tage, ordner):
        self.suchen.append((absender, betreff, tage, ordner))
        return [
            {"id": mid, "subject": "Synthetische Rechnung"}
            for mid, (ord_, _name, _text) in self.nachrichten.items()
            if ord_ == ordner
        ]

    def download_fn(self, msg_id, ziel):
        self.downloads.append(msg_id)
        _ordner, name, text = self.nachrichten[msg_id]
        Path(ziel).mkdir(parents=True, exist_ok=True)
        (Path(ziel) / name).write_text(text, encoding="utf-8")
        return [name]


class _Anleger:
    """Fake für beleg_entwurf.anlegen — schreibt dasselbe JSON auf stdout."""

    def __init__(self, duplikat: bool = False):
        self.aufrufe: list[argparse.Namespace] = []
        self.duplikat = duplikat
        self.zaehler = 0

    def __call__(self, ns) -> int:
        self.aufrufe.append(ns)
        print("Kontovorschläge (Bestätigung nötig — nie automatisch gesetzt):")
        print("  1. Konto 6837 (Lizenzen) — Regel 'beispiel' trifft [Regel]")
        if self.duplikat:
            print(
                f"DUPLIKAT: description '{ns.beschreibung}' existiert als Beleg "
                "v-alt — nichts angelegt."
            )
            return 0
        if ns.dry_run:
            print(json.dumps({"dry_run": True, "beschreibung": ns.beschreibung}))
            return 0
        self.zaehler += 1
        print(json.dumps({"beleg_id": f"v-{self.zaehler}", "status": "50"}))
        return 0


def _lese_fn(pfad) -> str:
    """PDF-Text-Ersatz: die Fixture-Dateien tragen den Text im Klartext — so
    braucht der Test weder ``pdftotext`` noch eine echte PDF-Struktur."""
    return Path(pfad).read_text(encoding="utf-8")


def _eingabe_datei(tmp_path: Path, abgaenge: list[dict]) -> Path:
    pfad = tmp_path / "kostenabgleich.json"
    pfad.write_text(
        json.dumps({"kennzahlen": {}, "beleg_fehlt": abgaenge}), encoding="utf-8"
    )
    return pfad


def _args(tmp_path: Path, register_datei: Path, abgaenge: list[dict], **extra):
    daten = {
        "mandant": "iil",
        "tage": 120,
        "eingabe": str(_eingabe_datei(tmp_path, abgaenge)),
        "register": register_datei,
        "ablage": tmp_path / "ablage",
        # Standard im Test: Ordner existiert nicht — die Owner-Ablage ist
        # dann schlicht leer (kein Fehler).
        "ablage_inbox": tmp_path / "inbox",
        "index": tmp_path / "index.json",
        "journal": tmp_path / "journal.jsonl",
        "konten": tmp_path / "konten.json",
        "konto": None,
        "anlegen": False,
        "json": False,
        "heute": "2026-04-15",
        "ziel": tmp_path / "board.md",
    }
    daten.update(extra)
    return argparse.Namespace(**daten)


def test_should_call_anlegen_with_dry_run_true_in_preview(tmp_path, register_datei):
    postfach = _Postfach({"m1": ("Beispielordner", "receipt.pdf", PDF_RECEIPT_USD)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert len(anleger.aufrufe) == 1
    assert anleger.aufrufe[0].dry_run is True
    assert anleger.aufrufe[0].konto is None
    assert anleger.aufrufe[0].waehrung == "USD"
    assert anleger.aufrufe[0].taxrule == "12"
    assert ergebnis["entwuerfe"][0]["ergebnis"] == "VORSCHAU"
    assert ergebnis["entwuerfe"][0]["art"] == "fremdwaehrung"
    assert ergebnis["kennzahlen"]["vorschau"] == 1


def test_should_create_draft_when_anlegen_is_set(tmp_path, register_datei):
    postfach = _Postfach({"m1": ("Beispielordner", "receipt.pdf", PDF_RECEIPT_USD)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert anleger.aufrufe[0].dry_run is False
    assert ergebnis["entwuerfe"][0]["beleg_id"] == "v-1"
    assert ergebnis["entwuerfe"][0]["konto_vorschlag"] == "6837"
    assert ergebnis["kennzahlen"]["entwuerfe_angelegt"] == 1


def test_should_count_duplikat_instead_of_new_draft(tmp_path, register_datei):
    postfach = _Postfach({"m1": ("Beispielordner", "receipt.pdf", PDF_RECEIPT_USD)})
    anleger = _Anleger(duplikat=True)
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert ergebnis["kennzahlen"]["duplikate"] == 1
    assert ergebnis["kennzahlen"]["entwuerfe_angelegt"] == 0


def test_should_not_download_message_twice_when_index_knows_it(
    tmp_path, register_datei
):
    """Idempotenz auf Postfach-Seite: der zweite Lauf lädt nichts nach, liest
    die abgelegte Datei aber weiterhin."""
    postfach = _Postfach({"m1": ("Beispielordner", "receipt.pdf", PDF_RECEIPT_USD)})
    anleger = _Anleger()
    args = _args(
        tmp_path,
        register_datei,
        [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
    )
    bb.lauf(
        args,
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert postfach.downloads == ["m1"]
    zweiter = bb.lauf(
        args,
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert postfach.downloads == ["m1"]  # kein zweiter Download
    assert zweiter["kennzahlen"]["pdf_gefunden"] == 1


def test_should_list_edv_invoice_as_owner_move_without_creating_a_draft(
    tmp_path, register_datei
):
    postfach = _Postfach({"m1": ("inbox", "S999000111.pdf", PDF_RECHNUNG_EUR_EDV)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "Beispiel Cloud Europe", 742.56)],
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert anleger.aufrufe == []
    arten = [z["art"] for z in ergebnis["owner"]]
    assert "anderer Mandant (edv)" in arten
    assert "Beleg nicht im Postfach" in arten


def test_should_report_missing_folder_as_owner_move(tmp_path, register_datei):
    def suche_fn(absender, betreff, tage, ordner):
        raise SystemExit(f"FEHLER: Quellordner '{ordner}' nicht gefunden.")

    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
        ),
        HEUTE,
        suche_fn=suche_fn,
        download_fn=lambda *a, **k: [],
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    assert any("nicht lesbar" in str(z["hinweis"]) for z in ergebnis["owner"])


def test_should_create_draft_for_pdf_without_abgang(tmp_path, register_datei):
    """Ein echter Beleg ohne passenden Abgang wird trotzdem angelegt — der
    Abgang kann später kommen oder über ein anderes Konto laufen."""
    postfach = _Postfach(
        {
            "m1": ("Beispielordner", "receipt.pdf", PDF_RECEIPT_USD),
            "m2": ("Beispielordner", "receipt2.pdf", PDF_RECHNUNG_EUR_KOMMA),
        }
    )
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert len(ergebnis["pdf_ohne_abgang"]) == 1
    assert ergebnis["pdf_ohne_abgang"][0]["beleg_id"] is not None
    assert ergebnis["kennzahlen"]["entwuerfe_angelegt"] == 2


def test_should_render_all_four_lists_in_the_board(tmp_path, register_datei):
    postfach = _Postfach({"m1": ("Beispielordner", "receipt.pdf", PDF_RECEIPT_USD)})
    args = _args(
        tmp_path,
        register_datei,
        [
            _abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC"),
            _abgang("2026-04-02", "Beispiel Abo", 9.99),
            _abgang("2026-04-01", "—", 850.00, "LOHN APRIL"),
            _abgang("2026-04-03", "Voellig Unbekannt", 12.34),
        ],
    )
    ergebnis = bb.lauf(
        args,
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    text = bb.render_markdown(ergebnis, args)
    assert "## 1. Entwuerfe angelegt / Vorschau (1)" in text
    assert "## 2. Owner-Zug (" in text
    assert "## 3. intern (kein Lieferantenbeleg) (1)" in text
    assert "## 4. PDF ohne Abgang (0)" in text
    assert "https://portal.example.invalid/" in text
    arten = [z["art"] for z in ergebnis["owner"]]
    assert "Portal" in arten and "kein Bezugsweg" in arten
    assert ergebnis["kennzahlen"]["intern"] == 1


def test_should_exit_2_and_write_journal_when_owner_move_is_open(
    tmp_path, register_datei, monkeypatch
):
    # Kein Netz: der CLI-Pfad holt sich seine Postfach-Funktionen selbst —
    # hier ein stummes Postfach ohne Treffer (der Register-Eintrag mit
    # ohne_abgang wird trotzdem abgesucht).
    monkeypatch.setattr(
        bb,
        "graph_funktionen",
        lambda konto: ((lambda *a, **k: []), (lambda *a, **k: [])),
    )
    code = bb.main(
        [
            "--register",
            str(register_datei),
            "--eingabe",
            str(
                _eingabe_datei(tmp_path, [_abgang("2026-04-02", "Beispiel Abo", 9.99)])
            ),
            "--index",
            str(tmp_path / "index.json"),
            "--journal",
            str(tmp_path / "journal.jsonl"),
            "--ablage",
            str(tmp_path / "ablage"),
            # NIE der Standardpfad: sonst liest der Test die echte
            # Owner-Ablage der Maschine und zaehlt fremde Dateien mit.
            "--ablage-inbox",
            str(tmp_path / "inbox"),
            "--ziel",
            str(tmp_path / "board.md"),
            "--heute",
            "2026-04-15",
        ]
    )
    assert code == 2
    zeilen = (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(zeilen[0])["owner_zug"] == 1
    assert "Owner-Zug" in (tmp_path / "board.md").read_text(encoding="utf-8")


def test_should_detect_iil_mandant_from_mail_domain_alone():
    """Rechnungen ohne Kontozeile nennen den Mandanten nur ueber die
    Rechnungsadresse — die Domain reicht als Beleg."""
    assert bb.empfaenger_bestimmen(PDF_RECHNUNG_NUR_DOMAIN) == "iil"


def test_should_keep_foreign_billing_account_unklar_despite_own_mail_domain():
    """Ein Zahlungsbeleg auf fremdes Konto bleibt Owner-Sache, auch wenn die
    eigene Rechnungsmailadresse daneben steht (real so gesehen 2026-09-13)."""
    text = PDF_RECEIPT_USD + "\nBilling email rechnung@iil.gmbh\n"
    assert bb.empfaenger_bestimmen(text, ["iilkonto"]) == "unklar"


def test_should_search_supplier_without_abgang_when_flag_is_set(
    tmp_path, register_datei
):
    """Lieferant, der ueber ein anderes Konto bezahlt wird: kein Abgang, die
    Rechnung liegt trotzdem im Postfach und soll ein Entwurf werden."""
    postfach = _Postfach(
        {"m9": ("Modellordner", "receipt.pdf", PDF_RECHNUNG_NUR_DOMAIN)}
    )
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(tmp_path, register_datei, [], anlegen=True),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert postfach.suchen, "Eintrag mit ohne_abgang muss abgesucht werden"
    assert postfach.suchen[0][3] == "Modellordner"
    assert postfach.suchen[0][2] == 120  # Fenster des Laufs, kein Abgang als Anker
    assert len(ergebnis["pdf_ohne_abgang"]) == 1
    assert ergebnis["pdf_ohne_abgang"][0]["beleg_id"] == "v-1"
    assert ergebnis["entwuerfe"] == []


def test_should_not_search_supplier_without_abgang_when_flag_is_missing(
    tmp_path, register_datei
):
    """Ohne das Feld bleibt es beim alten Verhalten: kein Abgang, keine Suche
    — sonst durchsucht jeder Lauf das Postfach nach jedem Register-Eintrag."""
    register = json.loads(register_datei.read_text(encoding="utf-8"))
    for eintrag in register["eintraege"]:
        eintrag.pop("ohne_abgang", None)
    register_datei.write_text(json.dumps(register), encoding="utf-8")
    postfach = _Postfach(
        {"m9": ("Modellordner", "receipt.pdf", PDF_RECHNUNG_NUR_DOMAIN)}
    )
    ergebnis = bb.lauf(
        _args(tmp_path, register_datei, []),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    assert postfach.suchen == []
    assert ergebnis["pdf_ohne_abgang"] == []


# ── Owner-Ablage (~/shared/inbox/invoices) ─────────────────────────────────


def _ablage_ordner(tmp_path: Path) -> Path:
    """Zwei abgelegte Rechnungen: eine mit Register-Treffer, eine ohne."""
    ordner = tmp_path / "inbox"
    ordner.mkdir()
    (ordner / "beispiel-cloud-2026-04.pdf").write_text(
        PDF_RECHNUNG_EUR_KOMMA, encoding="utf-8"
    )
    (ordner / "5000000000.pdf").write_text(
        "Voellig Unbekannter Anbieter\nRechnungsdatum 04.04.2026\nGesamtbetrag 5,00 EUR",
        encoding="utf-8",
    )
    return ordner


def test_should_read_invoices_from_the_owner_dropbox(tmp_path, register_datei):
    """Von Hand geladene Rechnungen gehen denselben Weg wie Postfach-PDFs —
    Treffer ueber den Dateinamen, Rest als Owner-Zug mit Pfad."""
    ordner = _ablage_ordner(tmp_path)
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-07", "Beispiel Cloud Europe", 119.00)],
            ablage_inbox=ordner,
            anlegen=True,
        ),
        HEUTE,
        suche_fn=lambda *a, **k: [],
        download_fn=lambda *a, **k: [],
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert ergebnis["kennzahlen"]["ablage_pdf"] == 2
    assert len(ergebnis["entwuerfe"]) == 1
    assert ergebnis["entwuerfe"][0]["beleg_id"] == "v-1"
    assert any(
        z["art"] == "Ablage: Lieferant unbekannt" and "5000000000" in str(z["hinweis"])
        for z in ergebnis["owner"]
    )


def test_should_not_create_the_same_dropbox_invoice_twice(tmp_path, register_datei):
    """Der Index merkt sich Pfad und Aenderungszeit — der zweite Lauf legt
    dieselbe Datei nicht erneut an (die Datei bleibt liegen, ~/shared raeumt
    der Owner selbst auf)."""
    ordner = _ablage_ordner(tmp_path)
    anleger = _Anleger()
    args = _args(
        tmp_path,
        register_datei,
        [_abgang("2026-04-07", "Beispiel Cloud Europe", 119.00)],
        ablage_inbox=ordner,
        anlegen=True,
    )
    fakes = {
        "suche_fn": lambda *a, **k: [],
        "download_fn": lambda *a, **k: [],
        "anlegen_fn": anleger,
        "lese_fn": _lese_fn,
    }
    bb.lauf(args, HEUTE, **fakes)
    zweiter = bb.lauf(args, HEUTE, **fakes)
    assert len(anleger.aufrufe) == 1
    assert zweiter["kennzahlen"]["ablage_pdf"] == 1  # nur die ohne Zuordnung
    assert (ordner / "beispiel-cloud-2026-04.pdf").exists()


def test_should_treat_missing_dropbox_as_empty(tmp_path, register_datei):
    ergebnis = bb.lauf(
        _args(tmp_path, register_datei, [], ablage_inbox=tmp_path / "gibtsnicht"),
        HEUTE,
        suche_fn=lambda *a, **k: [],
        download_fn=lambda *a, **k: [],
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    assert ergebnis["kennzahlen"]["ablage_pdf"] == 0
    assert ergebnis["owner"] == []


def test_should_not_match_internal_register_entry_for_a_dropbox_file():
    """Ein Kontoauszug in der Ablage darf keinen Lieferantenbeleg ausloesen —
    intern-Eintraege zaehlen nicht als Treffer."""
    register = [
        {"muster": "kontoauszug", "weg": "intern", "lieferant": "Bank"},
        {"muster": "beispiel cloud", "weg": "mail", "lieferant": "Beispiel Cloud"},
    ]
    assert bb.eintrag_aus_ablage("kontoauszug-04.pdf", "", register) is None
    assert bb.eintrag_aus_ablage("4711.pdf", "Beispiel Cloud", register) is not None


# ── Hoster-Layout: Summe nach den Positionen (#3118) ───────────────────────

PDF_HOSTER = """
Beispiel Hoster GmbH
Rechnungsnummer: 090000000000
Rechnungsdatum: 16.04.2026
Gesamtuebersicht
Service zeitraum Netto Steuer Brutto
Projekt "eins" 03/2026 140,55 EUR 26,70 EUR 167,25 EUR
Projekt "zwei" 03/2026 62,99 EUR 11,97 EUR 74,96 EUR
Summe 203,54 EUR 38,67 EUR 242,21 EUR
Der Rechnungsbetrag ist sofort faellig ohne Abzug, zahlbar nicht spaeter als 10 Tage nach Rechnungsdatum.
Position 1 CPX42 Cloud Server Monate 2 25,4900 EUR 50,9800 EUR
Zwischensumme 140,55 EUR
Position 2 CCX33 Cloud Server Monate 1 62,4900 EUR 62,4900 EUR
Zwischensumme 62,99 EUR
Beispiel Hoster GmbH Industriestr. 25 Bankverbindung:
USt-IdNr. DE000000000 info@hoster.invalid
"""


def test_should_read_the_total_line_that_stands_after_the_positions():
    """Zwischensummen NACH der Endsumme, ein Fliesstext mit 'Rechnungsbetrag …
    10 Tage' und eine Anschrift mit 'Industriestr.' — alle drei haben den
    Parser im Echtlauf in die Irre gefuehrt (#3118)."""
    feld = bb.pdf_lesen(PDF_HOSTER, "hoster.pdf")
    assert feld["brutto"] == 242.21
    assert feld["steuer"] == 38.67
    assert feld["datum"] == "2026-04-16"


def test_should_not_take_a_number_from_running_text_as_the_total():
    text = (
        "Rechnung\nGesamtbetrag 50,00 EUR\nDer Rechnungsbetrag ist zahlbar in 10 Tagen."
    )
    assert bb.pdf_lesen(text, "x.pdf")["brutto"] == 50.00


def test_should_not_read_a_street_number_as_tax():
    """'ust' steckt in 'Industriestr.' — ohne Wortgrenze wurde die Hausnummer
    zum Steuerbetrag."""
    text = (
        "Rechnung\nGesamtbetrag 50,00 EUR\nBeispiel GmbH Industriestr. 25 Musterstadt"
    )
    assert bb.pdf_lesen(text, "x.pdf")["steuer"] == 0.00


# ── Steuerregel aus dem PDF (#3118) ────────────────────────────────────────


def test_should_prefer_taxrule_9_when_the_pdf_shows_german_vat():
    beleg = {"steuer": 19.00}
    taxrule, hinweis = bb.taxrule_bestimmen(beleg, {"taxrule": "12"})
    assert taxrule == "9"
    assert "12" in hinweis and "9" in hinweis


def test_should_keep_the_register_taxrule_when_the_pdf_shows_no_vat():
    taxrule, hinweis = bb.taxrule_bestimmen({"steuer": 0.00}, {"taxrule": "12"})
    assert taxrule == "12"
    assert hinweis == ""


def test_should_pass_the_corrected_taxrule_to_the_draft(tmp_path, register_datei):
    """Register sagt 12 (Reverse Charge), das PDF weist USt aus — angelegt
    wird mit 9, und das Board sagt, warum."""
    postfach = _Postfach({"m1": ("Beispielordner", "r.pdf", PDF_RECHNUNG_EUR_KOMMA)})
    anleger = _Anleger()
    args = _args(
        tmp_path,
        register_datei,
        [_abgang("2026-04-07", "—", 119.00, "BEISPIEL PLATTFORM INC")],
    )
    ergebnis = bb.lauf(
        args,
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert anleger.aufrufe[0].taxrule == "9"
    assert ergebnis["entwuerfe"][0]["taxrule"] == "9"
    assert "Register 12" in bb.render_markdown(ergebnis, args)


# ── Dedup innerhalb eines Laufs (#3118) ────────────────────────────────────


def test_should_count_the_same_invoice_number_only_once_per_run(
    tmp_path, register_datei
):
    """Rechnungsmail und Zahlungsbeleg tragen dieselbe Nummer — nur die erste
    Fundstelle wird zur Vorschau-Zeile."""
    postfach = _Postfach(
        {
            "m1": ("Beispielordner", "invoice.pdf", PDF_RECEIPT_USD),
            "m2": ("Beispielordner", "receipt.pdf", PDF_RECEIPT_USD),
        }
    )
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    assert ergebnis["kennzahlen"]["bereits_im_lauf"] == 1
    assert len(ergebnis["entwuerfe"]) + len(ergebnis["pdf_ohne_abgang"]) == 1


# ── Mandanten iil | edv | beide (#3112) ────────────────────────────────────


def _edv_lauf(tmp_path, register_datei, mandant: str, monkeypatch, vorhanden=True):
    monkeypatch.setattr(bb, "secret_datei", lambda m: tmp_path / f"token-{m}")
    if vorhanden:
        (tmp_path / "token-edv").write_text("KEY=synthetisch", encoding="utf-8")
    postfach = _Postfach({"m1": ("inbox", "r.pdf", PDF_RECHNUNG_EUR_EDV)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-07", "Beispiel Cloud Europe", 742.56)],
            mandant=mandant,
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    return ergebnis, anleger


def test_should_create_edv_invoice_in_the_edv_mandant(
    tmp_path, register_datei, monkeypatch
):
    ergebnis, anleger = _edv_lauf(tmp_path, register_datei, "edv", monkeypatch)
    assert [ns.mandant for ns in anleger.aufrufe] == ["edv"]
    assert ergebnis["pdf_ohne_abgang"][0]["mandant"] == "edv"
    assert ergebnis["kennzahlen"]["entwuerfe_je_mandant"] == {"edv": 1}
    assert not any(z["art"] == "anderer Mandant (edv)" for z in ergebnis["owner"])


def test_should_keep_edv_invoice_as_owner_move_in_iil_mode(
    tmp_path, register_datei, monkeypatch
):
    ergebnis, anleger = _edv_lauf(tmp_path, register_datei, "iil", monkeypatch)
    assert anleger.aufrufe == []
    assert any(z["art"] == "anderer Mandant (edv)" for z in ergebnis["owner"])


def test_should_report_missing_edv_access_instead_of_aborting(
    tmp_path, register_datei, monkeypatch
):
    ergebnis, anleger = _edv_lauf(
        tmp_path, register_datei, "beide", monkeypatch, vorhanden=False
    )
    assert anleger.aufrufe == []
    arten = [z["art"] for z in ergebnis["owner"]]
    assert "edv-Zugang fehlt" in arten
    assert "anderer Mandant (edv)" in arten


def test_should_never_create_a_draft_for_an_unclear_recipient(
    tmp_path, register_datei, monkeypatch
):
    """Auch mit --mandant beide bleibt ein Beleg ohne erkennbaren Empfaenger
    Owner-Sache — geraten wird nie."""
    monkeypatch.setattr(bb, "secret_datei", lambda m: tmp_path / "token")
    (tmp_path / "token").write_text("KEY=synthetisch", encoding="utf-8")
    fremdes_konto = PDF_RECEIPT_USD.replace(
        "Account billed testkonto", "Account billed fremdkonto"
    )
    postfach = _Postfach({"m1": ("Beispielordner", "r.pdf", fremdes_konto)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
            mandant="beide",
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert anleger.aufrufe == []
    assert any(z["art"] == "Empfaenger unklar" for z in ergebnis["owner"])


# ── Login → Mandant (Owner-Wort 2026-09-13) ────────────────────────────────


def test_should_map_each_billing_login_to_its_own_mandant():
    """Zwei Konten, zwei Firmen: das Register sagt, welches Konto zu welcher
    gehoert — vorher war das persoenliche Konto pauschal 'unklar'."""
    zuordnung = {"orgkonto": "iil", "privatkonto": "edv"}
    org = PDF_RECEIPT_USD.replace("Account billed testkonto", "Account billed orgkonto")
    privat = PDF_RECEIPT_USD.replace(
        "Account billed testkonto", "Account billed privatkonto"
    )
    fremd = PDF_RECEIPT_USD.replace(
        "Account billed testkonto", "Account billed fremdkonto"
    )
    assert bb.empfaenger_bestimmen(org, zuordnung) == "iil"
    assert bb.empfaenger_bestimmen(privat, zuordnung) == "edv"
    assert bb.empfaenger_bestimmen(fremd, zuordnung) == "unklar"


def test_should_still_accept_the_old_login_list_as_all_iil():
    """Die Vorlage im Repo und aeltere lokale Register tragen eine Liste —
    die bleibt gueltig und meint den eigenen Mandanten."""
    assert bb.logins_zuordnung({"eigene_logins": ["Orgkonto"]}) == {"orgkonto": "iil"}
    assert bb.logins_zuordnung({"logins": {"A": "EDV"}}) == {"a": "edv"}
    assert bb.logins_zuordnung({}) == {}


def test_should_ignore_a_login_mapped_to_an_unknown_mandant():
    """Ein Tippfehler im Register darf keinen Beleg in einen erfundenen
    Mandanten legen."""
    text = PDF_RECEIPT_USD.replace("Account billed testkonto", "Account billed konto")
    assert bb.empfaenger_bestimmen(text, {"konto": "gibtsnicht"}) == "unklar"


def test_should_create_drafts_in_both_mandanten_by_login(
    tmp_path, register_datei, monkeypatch
):
    """Zwei Zahlungsbelege desselben Lieferanten, zwei Konten — mit
    --mandant beide entsteht je Beleg ein Entwurf im richtigen Mandanten."""
    monkeypatch.setattr(bb, "secret_datei", lambda m: tmp_path / "token")
    (tmp_path / "token").write_text("KEY=synthetisch", encoding="utf-8")
    privat = PDF_RECEIPT_USD.replace(
        "Account billed testkonto", "Account billed privatkonto"
    ).replace("ch_synthetisch123", "ch_synthetisch999")
    postfach = _Postfach(
        {
            "m1": ("Beispielordner", "org.pdf", PDF_RECEIPT_USD),
            "m2": ("Beispielordner", "privat.pdf", privat),
        }
    )
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
            mandant="beide",
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert sorted(ns.mandant for ns in anleger.aufrufe) == ["edv", "iil"]
    assert ergebnis["kennzahlen"]["entwuerfe_je_mandant"] == {"edv": 1, "iil": 1}
    assert ergebnis["owner"] == []


# ── Steuer aus Klammertext / Fussnote (#3121) ──────────────────────────────

#: Mehrspaltiges Layout: der Steuerbetrag steht allein in einer Zeile, die
#: Beschriftung darunter, und in der Klammer steht die Rechenformel.
PDF_STEUER_UEBER_BESCHRIFTUNG = """
Beispiel Modelle Inc.
Invoice number BSP-0001
Date of issue April 7, 2026
$10.00
Subtotal $10.00
$1.90
VAT - Germany (19% on $10.00)
(€1.64)
Total $11.90
"""

#: Reverse Charge mit Fussnotenmarke: "[1]" wurde als Steuerbetrag 1,00
#: gelesen, bevor Klammerinhalte ausgeschlossen wurden.
PDF_REVERSE_CHARGE_US = """
Beispiel Modelle Inc.
548 Market Street, San Francisco, United States
Invoice number BSP-0002
Rechnungsdatum 07.04.2026
Max plan - 20x 1 €180.00 0% €180.00
 [1]
Subtotal €180.00
Total €180.00
[1] Tax to be paid on reverse charge basis
"""

PDF_REVERSE_CHARGE_EU = PDF_REVERSE_CHARGE_US.replace(
    "548 Market Street, San Francisco, United States",
    "Beispielstrasse 1, Dublin, Irland",
)


def test_should_ignore_amounts_inside_parentheses_and_take_the_line_above():
    """Die Klammer traegt die Rechenformel, nicht den Betrag; der Steuerbetrag
    steht in der Zeile ueber seiner Beschriftung."""
    feld = bb.pdf_lesen(PDF_STEUER_UEBER_BESCHRIFTUNG, "b.pdf")
    assert feld["brutto"] == 11.90
    assert feld["steuer"] == 1.90
    assert feld["waehrung"] == "USD"
    assert feld["reverse_charge"] is False


def test_should_not_read_a_footnote_marker_as_tax():
    feld = bb.pdf_lesen(PDF_REVERSE_CHARGE_US, "b.pdf")
    assert feld["brutto"] == 180.00
    assert feld["steuer"] == 0.00
    assert feld["reverse_charge"] is True


def test_should_choose_third_country_reverse_charge_for_us_supplier():
    feld = bb.pdf_lesen(PDF_REVERSE_CHARGE_US, "b.pdf")
    taxrule, hinweis = bb.taxrule_bestimmen(feld, {"taxrule": "9"})
    assert taxrule == "12"
    assert "Reverse Charge" in hinweis


def test_should_choose_eu_reverse_charge_for_supplier_outside_the_us():
    feld = bb.pdf_lesen(PDF_REVERSE_CHARGE_EU, "b.pdf")
    assert feld["us_adresse"] is False
    taxrule, _hinweis = bb.taxrule_bestimmen(feld, {"taxrule": "9"})
    assert taxrule == "14"


def test_should_let_the_register_override_the_reverse_charge_rule():
    """``taxrule_rc`` ist die Owner-Angabe und gewinnt gegen die Anschrift."""
    feld = bb.pdf_lesen(PDF_REVERSE_CHARGE_US, "b.pdf")
    taxrule, _hinweis = bb.taxrule_bestimmen(feld, {"taxrule": "9", "taxrule_rc": "14"})
    assert taxrule == "14"


def test_should_keep_rule_9_when_vat_is_shown_even_with_rc_wording():
    """Die USt-Regel steht vor der Reverse-Charge-Regel: eine Rechnung mit
    ausgewiesener Steuer ist kein §13b-Fall."""
    taxrule, _hinweis = bb.taxrule_bestimmen(
        {"steuer": 1.90, "reverse_charge": True, "us_adresse": True}, {"taxrule": "12"}
    )
    assert taxrule == "9"


# ── Register-Feld "mandant" (Owner-Wort 2026-09-13) ────────────────────────


def _register_mit_mandant(tmp_path: Path, mandant: str) -> Path:
    pfad = tmp_path / "bezugswege-mandant.json"
    pfad.write_text(
        json.dumps(
            {
                "eintraege": [
                    {
                        "muster": "beispiel[ -]?cloud",
                        "weg": "mail",
                        "lieferant": "Beispiel Cloud",
                        "absender": "noreply@cloud.invalid",
                        "betreff": "Rechnung",
                        "ordner": ["inbox"],
                        "mandant": mandant,
                        "taxrule": "9",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return pfad


def test_should_follow_the_register_mandant_against_the_pdf_recipient(
    tmp_path, monkeypatch
):
    """Der Owner bucht diesen Lieferanten in der zweiten Firma, obwohl die
    Rechnung auf die erste lautet — das Register entscheidet."""
    monkeypatch.setattr(bb, "secret_datei", lambda m: tmp_path / "token")
    (tmp_path / "token").write_text("KEY=synthetisch", encoding="utf-8")
    register = _register_mit_mandant(tmp_path, "edv")
    postfach = _Postfach({"m1": ("inbox", "r.pdf", PDF_RECHNUNG_EUR_KOMMA)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register,
            [_abgang("2026-04-07", "Beispiel Cloud Europe", 119.00)],
            mandant="beide",
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert [ns.mandant for ns in anleger.aufrufe] == ["edv"]
    assert ergebnis["kennzahlen"]["entwuerfe_je_mandant"] == {"edv": 1}


def test_should_keep_register_mandant_edv_as_owner_move_in_iil_mode(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(bb, "secret_datei", lambda m: tmp_path / "token")
    register = _register_mit_mandant(tmp_path, "edv")
    postfach = _Postfach({"m1": ("inbox", "r.pdf", PDF_RECHNUNG_EUR_KOMMA)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register,
            [_abgang("2026-04-07", "Beispiel Cloud Europe", 119.00)],
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
    )
    assert anleger.aufrufe == []
    assert any(z["art"] == "anderer Mandant (edv)" for z in ergebnis["owner"])


# ── Dubletten ueber beide Mandanten (#3121) ────────────────────────────────


def test_should_not_create_a_draft_that_already_exists_in_the_other_mandant(
    tmp_path, register_datei, monkeypatch
):
    """Der Owner hat die Rechnung im anderen Mandanten erfasst — ohne
    Abgleich ueber beide Bestaende entstuende hier ein zweiter Beleg."""
    monkeypatch.setattr(bb, "secret_datei", lambda m: tmp_path / f"token-{m}")
    for name in ("iil", "edv"):
        (tmp_path / f"token-{name}").write_text("KEY=synthetisch", encoding="utf-8")
    bestand = {
        "iil": [],
        "edv": [
            {"id": "v-alt", "description": "Beispiel Invoice ch_synthetisch123 — April"}
        ],
    }
    postfach = _Postfach({"m1": ("Beispielordner", "r.pdf", PDF_RECEIPT_USD)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
        bestand_fn=lambda m: bestand[m],
    )
    assert anleger.aufrufe == []
    assert ergebnis["entwuerfe"][0]["ergebnis"] == "DUPLIKAT (anderer Mandant: edv)"
    assert ergebnis["kennzahlen"]["duplikate_fremder_mandant"] == 1
    assert ergebnis["kennzahlen"]["entwuerfe_je_mandant"] == {}


def test_should_still_create_the_draft_when_only_the_own_mandant_has_it(
    tmp_path, register_datei, monkeypatch
):
    """Der eigene Bestand ist Sache von beleg_entwurf.duplikat — dieser
    Abgleich darf ihm nicht vorgreifen."""
    monkeypatch.setattr(bb, "secret_datei", lambda m: tmp_path / f"token-{m}")
    for name in ("iil", "edv"):
        (tmp_path / f"token-{name}").write_text("KEY=synthetisch", encoding="utf-8")
    bestand = {
        "iil": [{"id": "v-alt", "description": "ch_synthetisch123"}],
        "edv": [],
    }
    postfach = _Postfach({"m1": ("Beispielordner", "r.pdf", PDF_RECEIPT_USD)})
    anleger = _Anleger()
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
            anlegen=True,
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=anleger,
        lese_fn=_lese_fn,
        bestand_fn=lambda m: bestand[m],
    )
    assert len(anleger.aufrufe) == 1
    assert ergebnis["kennzahlen"]["duplikate_fremder_mandant"] == 0


def test_should_say_in_the_board_which_mandanten_were_checked(
    tmp_path, register_datei, monkeypatch
):
    """Fehlt ein Zugang, wird nicht stillschweigend weniger geprueft."""
    monkeypatch.setattr(bb, "secret_datei", lambda m: tmp_path / f"token-{m}")
    (tmp_path / "token-iil").write_text("KEY=synthetisch", encoding="utf-8")
    args = _args(tmp_path, register_datei, [])
    ergebnis = bb.lauf(
        args,
        HEUTE,
        suche_fn=lambda *a, **k: [],
        download_fn=lambda *a, **k: [],
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
        bestand_fn=lambda m: [],
    )
    assert ergebnis["kennzahlen"]["dubletten_geprueft_gegen"] == ["iil"]
    assert "Dubletten geprueft gegen: iil" in bb.render_markdown(ergebnis, args)


def test_should_report_no_cross_check_when_no_bestand_is_available(
    tmp_path, register_datei
):
    ergebnis = bb.lauf(
        _args(tmp_path, register_datei, []),
        HEUTE,
        suche_fn=lambda *a, **k: [],
        download_fn=lambda *a, **k: [],
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    assert ergebnis["kennzahlen"]["dubletten_geprueft_gegen"] == []


def test_should_map_known_login_without_account_billed_line():
    """GitHub-Rechnungslayout: Login steht nur unter BILL TO (Echtprobe 2026-09-13)."""
    logins = {"orgbeispiel": "iil", "privatbeispiel": "edv"}
    text = "GitHub, Inc. Invoice # INV1 Support Contact BILL TO 88 Street privatbeispiel privatbeispiel Germany"
    assert bb.empfaenger_bestimmen(text, logins) == "edv"
    assert bb.empfaenger_bestimmen("BILL TO orgbeispiel", logins) == "iil"
    assert bb.empfaenger_bestimmen("BILL TO fremderlogin", logins) == "unklar"
    # Teilwort darf nicht treffen
    assert bb.empfaenger_bestimmen("BILL TO privatbeispiel2", logins) == "unklar"


# ── Rechnungsnummer: Gruppen und Sonderzeichen (#3133) ─────────────────────


def test_should_join_digit_groups_of_an_invoice_number():
    """Die Nummer steht zur Lesbarkeit in Dreiergruppen — der Parser nahm
    vorher nur die erste Gruppe."""
    assert bb.nummer_finden(["Rechnungsnummer 733 934 0350"], "x.pdf") == "7339340350"


def test_should_keep_slashes_and_brackets_inside_an_invoice_number():
    zeile = "Invoice Number D56/(260)257231 [ORIGINAL]"
    assert bb.nummer_finden([zeile], "x.pdf") == "D56/(260)257231"


def test_should_stop_the_invoice_number_at_a_column_gap():
    zeile = "Abrechnungsnummer S999000111   Kundennummer 4711"
    assert bb.nummer_finden([zeile], "x.pdf") == "S999000111"


def test_should_read_additional_invoice_number_labels():
    for zeile, erwartet in (
        ("Rechnungs-Nr. BSP-0001", "BSP-0001"),
        ("Rechnungsnr. BSP-0002", "BSP-0002"),
        ("Invoice # BSP-0003", "BSP-0003"),
        ("Invoice No BSP-0004", "BSP-0004"),
        ("Receipt # BSP-0005", "BSP-0005"),
        ("Beleg-Nr. BSP-0006", "BSP-0006"),
    ):
        assert bb.nummer_finden([zeile], "x.pdf") == erwartet


def test_should_fall_back_to_the_filename_without_a_label():
    assert bb.nummer_finden(["Nur Fliesstext ohne Kennung"], "beleg-4711.pdf") == (
        "beleg-4711"
    )


# ── Endsumme schlaegt jede andere Total-Zeile (#3133) ───────────────────────

PDF_MEHRERE_TOTALS = """
Beispiel Anbieter Ltd.
Invoice Number D56/(260)257231 [ORIGINAL]
Rechnungsdatum 01.09.2026
Total: 4.00 USD
VAT (0.00%): 0.00 USD
Total include VAT: 4.00 USD
Total Monthly Recurring Services (Current Month): 4.00 USD
"""

PDF_DEUTSCHE_ENDSUMME = """
Beispiel Anbieter GmbH
Rechnungsnummer 733 934 0350
Rechnungsdatum 01.09.2026
Summe Betrag 36,09 €
+19 % USt. auf 36,09 € 6,86 €
Rechnungsbetrag 42,95 €
"""


def test_should_prefer_the_total_including_vat_line():
    """Ohne Vorrang gewann die letzte Total-Zeile und der Beleg trug 0,00."""
    feld = bb.pdf_lesen(PDF_MEHRERE_TOTALS, "x.pdf")
    assert feld["brutto"] == 4.00
    assert feld["steuer"] == 0.00
    assert feld["nummer"] == "D56/(260)257231"


def test_should_prefer_the_german_rechnungsbetrag_over_the_subtotal():
    feld = bb.pdf_lesen(PDF_DEUTSCHE_ENDSUMME, "x.pdf")
    assert feld["brutto"] == 42.95
    assert feld["steuer"] == 6.86
    assert feld["nummer"] == "7339340350"


def test_should_not_read_a_vat_total_line_as_the_tax_amount():
    """Eine Zeile mit Steuer- UND Summenwort ist eine Endsumme."""
    text = "Rechnung\nTotal include VAT: 4.00 USD\n"
    assert bb.pdf_lesen(text, "x.pdf")["brutto"] == 4.00
    assert bb.pdf_lesen(text, "x.pdf")["steuer"] == 0.00


# ── Anhang-Muster und Beilagen (#3133) ─────────────────────────────────────


def test_should_only_read_attachments_that_match_the_register_pattern(
    tmp_path, register_datei
):
    """Die Mail traegt Rechnung UND Zahlungsbeleg; nur die Rechnung zaehlt."""
    register = json.loads(register_datei.read_text(encoding="utf-8"))
    for eintrag in register["eintraege"]:
        if eintrag["muster"] == "beispiel plattform":
            eintrag["anhang_muster"] = "^Invoice-"
    register_datei.write_text(json.dumps(register), encoding="utf-8")

    class _ZweiAnhaenge(_Postfach):
        def download_fn(self, msg_id, ziel):
            self.downloads.append(msg_id)
            Path(ziel).mkdir(parents=True, exist_ok=True)
            (Path(ziel) / "Invoice-BSP0001.pdf").write_text(
                PDF_RECEIPT_USD, encoding="utf-8"
            )
            (Path(ziel) / "bill-ord-bsp.pdf").write_text(
                "Zahlungsbeleg ohne Datum und Betrag", encoding="utf-8"
            )
            return ["Invoice-BSP0001.pdf", "bill-ord-bsp.pdf"]

    postfach = _ZweiAnhaenge({"m1": ("Beispielordner", "x.pdf", PDF_RECEIPT_USD)})
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    assert ergebnis["kennzahlen"]["pdf_gefunden"] == 1


def test_should_read_all_attachments_without_a_pattern(tmp_path, register_datei):
    class _ZweiAnhaenge(_Postfach):
        def download_fn(self, msg_id, ziel):
            self.downloads.append(msg_id)
            Path(ziel).mkdir(parents=True, exist_ok=True)
            (Path(ziel) / "Invoice-BSP0001.pdf").write_text(
                PDF_RECEIPT_USD, encoding="utf-8"
            )
            (Path(ziel) / "bill-ord-bsp.pdf").write_text(
                PDF_RECHNUNG_EUR_KOMMA, encoding="utf-8"
            )
            return ["Invoice-BSP0001.pdf", "bill-ord-bsp.pdf"]

    postfach = _ZweiAnhaenge({"m1": ("Beispielordner", "x.pdf", PDF_RECEIPT_USD)})
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    assert ergebnis["kennzahlen"]["pdf_gefunden"] == 2


def test_should_mark_a_mail_attachment_without_invoice_data_as_anlage(
    tmp_path, register_datei
):
    """Eine Beilage ohne Datum und Betrag ist keine kaputte Rechnung."""
    postfach = _Postfach(
        {
            "m1": (
                "Beispielordner",
                "anlage.pdf",
                # Die Beilage nennt den Kunden (wie eine echte
                # Kontenuebersicht), traegt aber weder Datum noch Betrag.
                "Anlage Rechnungskonten\nKunde: IIL GmbH\nUebersicht der Konten",
            )
        }
    )
    ergebnis = bb.lauf(
        _args(
            tmp_path,
            register_datei,
            [_abgang("2026-04-10", "—", 43.05, "BEISPIEL PLATTFORM INC")],
        ),
        HEUTE,
        suche_fn=postfach.suche_fn,
        download_fn=postfach.download_fn,
        anlegen_fn=_Anleger(),
        lese_fn=_lese_fn,
    )
    zeilen = ergebnis["entwuerfe"] + ergebnis["pdf_ohne_abgang"]
    assert [z["art"] for z in zeilen] == ["Anlage ohne Rechnungsdaten"]
    assert ergebnis["kennzahlen"]["anlagen_uebersprungen"] == 1
    # Die Art muss im Board stehen, nicht nur in der Kennzahl — sonst sieht
    # die Zeile dort weiter wie ein Parserfehler aus.
    assert "Anlage ohne Rechnungsdaten" in bb.render_markdown(
        ergebnis, _args(tmp_path, register_datei, [])
    )
