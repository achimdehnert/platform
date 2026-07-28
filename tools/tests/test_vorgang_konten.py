"""Konten-Nenner des Deckungsausweises (ADR-286 §8.13).

Regression zum Befund vom 2026-07-28: Die Konten-Aufzählung entstand aus einem Glob
über die IMAP-Konfigurationen. Dadurch zählte eine Ordner-Routing-Tabelle als Konto,
eine reine Versand-Konfiguration ebenfalls — und das Microsoft-365-Hauptpostfach mit
44.878 Nachrichten fehlte vollständig, weil sein Zugang in einer anderen Datei liegt.

Ein realer Lauf meldete daraufhin "Konten 1/4" und wies als Lücken genau die kleinen
Nebenschauplätze aus, während die mit Abstand größte Lücke unerwähnt blieb. Das ist
die Fehlerklasse, gegen die der Ausweis gebaut wurde.

Die Prüffälle bilden deshalb den echten Konfigurationsstand nach, nicht erfundene
Randfälle — inklusive einer Negativprobe, die belegt, dass die alte Logik den Fehler
erzeugt und die neue ihn nicht mehr erzeugt.
"""

import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "vorgang.py"
_spec = importlib.util.spec_from_file_location("vorgang", _SRC)
vg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vg)

IMAP = "IMAP_HOST=imap.example.org\n"


def _basis(tmp_path, dateien):
    for name, inhalt in dateien.items():
        (tmp_path / name).write_text(inhalt, encoding="utf-8")
    return tmp_path


def test_should_include_graph_accounts_from_calendar_config(tmp_path):
    basis = _basis(
        tmp_path,
        {
            "mail-hnu.env": IMAP,
            "calendar.env": "GRAPH_ACCOUNTS=achim.dehnert@iil.gmbh\nGRAPH_TENANT=x\n",
        },
    )
    assert vg.bekannte_konten(basis) == ["achim.dehnert@iil.gmbh", "hnu"]


def test_should_exclude_folder_routing_table(tmp_path):
    """Die Ordner-Zuordnungstabelle ist kein Postfach."""
    basis = _basis(
        tmp_path,
        {"mail-hnu.env": IMAP, "mail-folders.env": "IIL.Kunden/Foo | kunde | foo.de\n"},
    )
    assert vg.bekannte_konten(basis) == ["hnu"]


def test_should_exclude_send_only_config(tmp_path):
    """Nur SMTP konfiguriert: versendbar, aber nicht lesbar — kein Nenner-Beitrag."""
    basis = _basis(tmp_path, {"mail.env": "SMTP_HOST=smtp.example.org\nSMTP_PORT=587\n"})
    assert vg.bekannte_konten(basis) == []


def test_should_count_default_when_base_config_is_readable(tmp_path):
    basis = _basis(tmp_path, {"mail.env": "SMTP_HOST=s\n" + IMAP})
    assert vg.bekannte_konten(basis) == ["default"]


def test_should_tolerate_missing_calendar_config(tmp_path):
    basis = _basis(tmp_path, {"mail-hnu.env": IMAP})
    assert vg.bekannte_konten(basis) == ["hnu"]


def test_should_split_and_trim_multiple_graph_accounts(tmp_path):
    basis = _basis(tmp_path, {"calendar.env": "GRAPH_ACCOUNTS= a@x.de , b@y.de \n"})
    assert vg.bekannte_konten(basis) == ["a@x.de", "b@y.de"]


def test_should_not_duplicate_when_same_name_appears_twice(tmp_path):
    basis = _basis(
        tmp_path, {"mail-a@x.de.env": IMAP, "calendar.env": "GRAPH_ACCOUNTS=a@x.de\n"}
    )
    assert vg.bekannte_konten(basis) == ["a@x.de"]


def test_should_reproduce_the_finding_with_the_old_logic(tmp_path):
    """Negativprobe: die alte Logik erzeugt den realen Fehlstand, die neue nicht.

    Ohne sie belegt nichts, dass die Korrektur den dokumentierten Fehler trifft.
    """
    basis = _basis(
        tmp_path,
        {
            "mail.env": "SMTP_HOST=s\n",
            "mail-folders.env": "IIL.Kunden/Foo | kunde | foo.de\n",
            "mail-hnu.env": IMAP,
            "mail-search.env": IMAP,
            "calendar.env": "GRAPH_ACCOUNTS=achim.dehnert@iil.gmbh\n",
        },
    )

    alt = ["default"] + sorted(
        p.stem.removeprefix("mail-") for p in basis.glob("mail-*.env")
    )
    assert alt == ["default", "folders", "hnu", "search"], "realer Fehlstand 2026-07-28"
    assert "achim.dehnert@iil.gmbh" not in alt, "Hauptpostfach fehlte im Nenner"
    assert "folders" in alt, "Routing-Tabelle wurde als Konto gezaehlt"

    neu = vg.bekannte_konten(basis)
    assert neu == ["achim.dehnert@iil.gmbh", "hnu", "search"]
