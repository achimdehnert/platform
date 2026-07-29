"""Tests für tools/mail_agent/port_freigeben.py.

Statt echter Prozesse ein nachgebautes /proc im tmp_path: net/tcp, net/tcp6 und
je Prozess ein fd-Verzeichnis mit Socket-Symlinks. Damit lässt sich der Fall
prüfen, auf den es ankommt — ein FREMDER Prozess auf dem Port darf NICHT
beendet werden.
"""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

pf = pytest.importorskip("port_freigeben")

_KOPF = (
    "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when "
    "retrnsmt   uid  timeout inode\n"
)


def _zeile(port: int, inode: str, zustand: str = "0A") -> str:
    return (
        f"   0: 0100007F:{port:04X} 00000000:0000 {zustand} 00000000:00000000 "
        f"00:00000000 00000000  1000        0 {inode} 2 0 100 0 0 10 0\n"
    )


@pytest.fixture
def proc(tmp_path):
    (tmp_path / "net").mkdir()
    (tmp_path / "net" / "tcp").write_text(_KOPF)
    (tmp_path / "net" / "tcp6").write_text(_KOPF)
    return tmp_path


def _lauscher(proc: Path, port: int, inode: str, datei: str = "tcp"):
    pfad = proc / "net" / datei
    pfad.write_text(pfad.read_text() + _zeile(port, inode))


def _prozess(proc: Path, pid: int, inode: str, cmdline: str):
    verzeichnis = proc / str(pid)
    (verzeichnis / "fd").mkdir(parents=True)
    (verzeichnis / "cmdline").write_bytes(cmdline.replace(" ", "\x00").encode())
    ziel = verzeichnis / "socket_ziel"
    ziel.write_text("x")
    os.symlink(f"socket:[{inode}]", verzeichnis / "fd" / "3")
    return verzeichnis


class TestPortErkennung:
    def test_should_parse_port_from_hex_address(self):
        assert pf.hex_zu_port("0100007F:2233") == 0x2233

    def test_should_find_listening_inode(self, proc):
        _lauscher(proc, 8787, "12345")
        assert pf.lauschende_inodes(8787, proc) == {"12345"}

    def test_should_ignore_other_ports(self, proc):
        _lauscher(proc, 9999, "12345")
        assert pf.lauschende_inodes(8787, proc) == set()

    def test_should_ignore_non_listening_sockets(self, proc):
        _lauscher(proc, 8787, "12345", "tcp")
        pfad = proc / "net" / "tcp"
        pfad.write_text(_KOPF + _zeile(8787, "77777", zustand="01"))  # ESTABLISHED
        assert pf.lauschende_inodes(8787, proc) == set()

    def test_should_also_read_ipv6_table(self, proc):
        _lauscher(proc, 8787, "6666", datei="tcp6")
        assert pf.lauschende_inodes(8787, proc) == {"6666"}

    def test_should_map_inode_to_pid(self, proc):
        _lauscher(proc, 8787, "12345")
        _prozess(proc, 4711, "12345", "python3 mail_link_server.py --port 8787")
        assert pf.pids_zu_inodes({"12345"}, proc) == {4711}


class TestEigentumspruefung:
    def test_should_accept_own_process_with_marker(self, proc, monkeypatch):
        _prozess(proc, 4711, "1", "python3 mail_link_server.py --port 8787")
        monkeypatch.setattr(os, "getuid", lambda: (proc / "4711").stat().st_uid)
        assert pf.ist_eigene_instanz(4711, proc_root=proc) is True

    def test_should_reject_process_without_marker(self, proc, monkeypatch):
        _prozess(proc, 4711, "1", "nginx -g daemon off;")
        monkeypatch.setattr(os, "getuid", lambda: (proc / "4711").stat().st_uid)
        assert pf.ist_eigene_instanz(4711, proc_root=proc) is False

    def test_should_reject_process_of_another_user(self, proc, monkeypatch):
        _prozess(proc, 4711, "1", "python3 mail_link_server.py")
        monkeypatch.setattr(os, "getuid", lambda: (proc / "4711").stat().st_uid + 1)
        assert pf.ist_eigene_instanz(4711, proc_root=proc) is False

    def test_should_reject_vanished_process(self, proc):
        assert pf.ist_eigene_instanz(999999, proc_root=proc) is False


class TestFreigeben:
    def test_should_do_nothing_when_port_is_free(self, proc):
        code, meldung = pf.freigeben(8787, proc_root=proc)
        assert code == 0
        assert "frei" in meldung

    def test_should_terminate_own_orphan(self, proc, monkeypatch):
        _lauscher(proc, 8787, "12345")
        _prozess(proc, 4711, "12345", "python3 mail_link_server.py --port 8787")
        monkeypatch.setattr(os, "getuid", lambda: (proc / "4711").stat().st_uid)
        gesendet = []

        def _toeten(pid, sig):
            gesendet.append((pid, sig))
            (proc / "net" / "tcp").write_text(_KOPF)  # Port wird frei

        code, meldung = pf.freigeben(8787, proc_root=proc, toeten=_toeten)
        assert code == 0
        assert gesendet == [(4711, signal.SIGTERM)]
        assert "4711" in meldung

    def test_should_never_touch_a_foreign_process(self, proc, monkeypatch):
        """Der Kern der Sache: ein fremder Dienst auf dem Port ist ein Befund,
        kein Hindernis, das ein Start-Skript wegräumt."""
        _lauscher(proc, 8787, "12345")
        _prozess(proc, 4711, "12345", "nginx -g daemon off;")
        monkeypatch.setattr(os, "getuid", lambda: (proc / "4711").stat().st_uid)
        gesendet = []

        code, meldung = pf.freigeben(
            8787, proc_root=proc, toeten=lambda p, s: gesendet.append((p, s))
        )
        assert code == 1
        assert gesendet == []
        assert "fremd" in meldung.lower()
        assert "nginx" in meldung

    def test_should_refuse_when_owner_is_unreadable(self, proc):
        """Belegt, aber kein zuordenbarer eigener Prozess → nichts beenden."""
        _lauscher(proc, 8787, "12345")
        code, meldung = pf.freigeben(8787, proc_root=proc, toeten=lambda p, s: None)
        assert code == 1
        assert "nicht" in meldung.lower()

    def test_should_escalate_to_sigkill_when_port_stays_busy(self, proc, monkeypatch):
        _lauscher(proc, 8787, "12345")
        _prozess(proc, 4711, "12345", "python3 mail_link_server.py")
        monkeypatch.setattr(os, "getuid", lambda: (proc / "4711").stat().st_uid)
        gesendet = []

        code, _ = pf.freigeben(
            8787,
            proc_root=proc,
            gnadenfrist=0.3,
            toeten=lambda p, s: gesendet.append((p, s)),
        )
        assert code == 0
        assert (4711, signal.SIGTERM) in gesendet
        assert (4711, signal.SIGKILL) in gesendet
