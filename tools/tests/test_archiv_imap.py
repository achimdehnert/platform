"""IMAP-Transport des Jahrgangs-Einsortierers.

Der sicherheitskritische Teil ist nicht das Verschieben, sondern das **Löschen
danach**. Ohne die MOVE-Erweiterung (RFC 6851) besteht ein Umzug aus COPY, dann
`\\Deleted` setzen, dann expungen — und ein blankes `EXPUNGE` löscht **alle** als
gelöscht markierten Nachrichten des Ordners, auch die, die jemand anders markiert
hat. Nur `UID EXPUNGE` (UIDPLUS, RFC 4315) trifft genau die eigenen.

Fehlt beides, wird nicht verschoben. Diese Verweigerung ist das Verhalten, das
hier geprüft wird — sie ist leicht wegzuoptimieren und teuer, wenn sie fehlt.
"""

import importlib.util
import pathlib

_SRC = (
    pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "archiv_einsortieren.py"
)
_spec = importlib.util.spec_from_file_location("archiv_einsortieren_imap", _SRC)
ae = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ae)


class FakeImap:
    """Nur so viel IMAP, wie die geprüften Pfade anfassen."""

    def __init__(self, capabilities, select_ok=True):
        self.capabilities = capabilities
        self._select_ok = select_ok
        self.aufrufe = []

    def select(self, name, readonly=False):
        self.aufrufe.append(("select", name, readonly))
        return ("OK" if self._select_ok else "NO", [b"5"])

    def uid(self, befehl, *rest):
        self.aufrufe.append(("uid", befehl, *rest))
        return ("OK", [b"done"])


# --- Fähigkeiten ----------------------------------------------------------


def test_should_read_capabilities_given_as_strings():
    """imaplib liefert ein str-Tupel; ein bytes-join darauf wirft TypeError."""
    imap = FakeImap(("IMAP4REV1", "MOVE", "UIDPLUS"))
    assert ae.imap_kann_move(imap) is True
    assert ae.imap_kann_uid_expunge(imap) is True


def test_should_read_capabilities_given_as_bytes():
    imap = FakeImap((b"IMAP4REV1", b"MOVE"))
    assert ae.imap_kann_move(imap) is True


def test_should_be_case_insensitive():
    assert ae.imap_kann_move(FakeImap(("move",))) is True


def test_should_report_missing_capabilities():
    imap = FakeImap(("IMAP4REV1",))
    assert ae.imap_kann_move(imap) is False
    assert ae.imap_kann_uid_expunge(imap) is False


# --- Verschiebewege -------------------------------------------------------


def test_should_use_atomic_move_when_available():
    imap = FakeImap(("MOVE", "UIDPLUS"))
    anzahl, fehler = ae.imap_verschiebe(imap, "INBOX", [b"1", b"2"], "Archiv/2025")
    assert (anzahl, fehler) == (2, "")
    befehle = [a[1] for a in imap.aufrufe if a[0] == "uid"]
    assert befehle == ["MOVE"]  # kein COPY/STORE/EXPUNGE noetig


def test_should_fall_back_to_copy_delete_uid_expunge():
    imap = FakeImap(("UIDPLUS",))
    anzahl, fehler = ae.imap_verschiebe(imap, "INBOX", [b"1"], "Archiv/2025")
    assert (anzahl, fehler) == (1, "")
    assert [a[1] for a in imap.aufrufe if a[0] == "uid"] == [
        "COPY",
        "STORE",
        "EXPUNGE",
    ]


def test_should_refuse_when_neither_move_nor_uid_expunge_exists():
    """Ohne UID EXPUNGE bleibt nur ein blankes EXPUNGE — das loescht fremd
    markierte Nachrichten mit. Dann lieber gar nicht verschieben."""
    imap = FakeImap(("IMAP4REV1",))
    anzahl, fehler = ae.imap_verschiebe(imap, "INBOX", [b"1"], "Archiv/2025")
    assert anzahl == 0
    assert "EXPUNGE" in fehler
    assert not [a for a in imap.aufrufe if a[0] == "uid"]  # nichts angefasst


def test_should_open_source_folder_writable():
    """readonly=True liesse jeden Schreibbefehl scheitern — leise."""
    imap = FakeImap(("MOVE",))
    ae.imap_verschiebe(imap, "INBOX", [b"1"], "Archiv/2025")
    select = next(a for a in imap.aufrufe if a[0] == "select")
    assert select[2] is False


def test_should_do_nothing_for_an_empty_uid_list():
    imap = FakeImap(("MOVE",))
    assert ae.imap_verschiebe(imap, "INBOX", [], "Archiv/2025") == (0, "")
    assert imap.aufrufe == []


def test_should_report_when_source_folder_cannot_be_opened():
    imap = FakeImap(("MOVE",), select_ok=False)
    anzahl, fehler = ae.imap_verschiebe(imap, "INBOX", [b"1"], "Archiv/2025")
    assert anzahl == 0
    assert "INBOX" in fehler
