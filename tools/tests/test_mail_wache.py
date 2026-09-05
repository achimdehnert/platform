"""Reine Logik von mail_wache.py — ohne Netz (chat-hub#48 F4)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mail_agent"))

import mail_wache as mw  # noqa: E402


def test_should_select_only_accounts_with_existing_credentials_file() -> None:
    vorhandene_pfade = {mw.zugangsdatei("hnu"), mw.zugangsdatei("iil")}
    ok, meldungen = mw.waehle_konten(
        ["hnu", "iil", "ad"], existiert=lambda p: p in vorhandene_pfade
    )
    assert ok == ["hnu", "iil"]
    assert len(meldungen) == 1
    assert "ad" in meldungen[0]
    assert "übersprungen" in meldungen[0]


def test_should_not_abort_when_no_account_would_be_available() -> None:
    ok, meldungen = mw.waehle_konten(["ad"], existiert=lambda p: False)
    assert ok == []
    assert len(meldungen) == 1


def test_should_map_iil_to_graph_config_and_ad_to_default_mail_env() -> None:
    assert mw.zugangsdatei("iil") == mw.graph_mail.CONFIG_FILE
    assert mw.zugangsdatei("ad") == mw.CONFIG_FILE
    assert mw.zugangsdatei("hnu").name == "mail-hnu.env"


def test_should_detect_idle_in_capability_line() -> None:
    assert mw.idle_in_capability(b"IMAP4rev1 IDLE UIDPLUS") is True
    assert mw.idle_in_capability("IMAP4REV1 idle") is True
    assert mw.idle_in_capability(b"IMAP4rev1 UIDPLUS") is False
    assert mw.idle_in_capability(b"") is False


def test_should_parse_exists_line_from_idle_response() -> None:
    assert mw.parse_exists_zeile(b"* 12 EXISTS\r\n") == 12
    assert mw.parse_exists_zeile(b"* 3 RECENT\r\n") is None
    assert mw.parse_exists_zeile(None) is None
    assert mw.parse_exists_zeile(b"") is None


def test_should_return_only_uids_above_the_watermark() -> None:
    assert mw.neue_uids(100, b"98 99 100 101 102") == [101, 102]
    assert mw.neue_uids(100, b"101") == [101]
    assert mw.neue_uids(100, None) == []
    assert mw.neue_uids(100, b"") == []


def test_should_sort_new_uids_ascending() -> None:
    assert mw.neue_uids(0, b"5 3 1 4 2") == [1, 2, 3, 4, 5]


def test_should_shorten_sender_display_name_from_full_header() -> None:
    assert mw.kurz_absender('"Max Muster" <max@beispiel.de>') == "Max Muster"
    assert mw.kurz_absender("max@beispiel.de") == "max@beispiel.de"
    assert mw.kurz_absender("<ohne-namen@beispiel.de>") == "ohne-namen@beispiel.de"
    assert mw.kurz_absender("") == ""


def test_should_build_output_line_and_decode_rfc2047_subject() -> None:
    header = {
        "From": "=?UTF-8?B?TWF4IE3DvHN0ZXI=?= <max@beispiel.de>",
        "Subject": "=?UTF-8?B?QmV0cmVmZiBtaXQgw5w=?=",
    }
    zeile = mw.zeile_aus_header("hnu", "INBOX", "42", header)
    assert zeile["konto"] == "hnu"
    assert zeile["ordner"] == "INBOX"
    assert zeile["uid"] == "42"
    assert zeile["von"] == "Max Müster"
    assert zeile["betreff"] == "Betreff mit Ü"
    assert zeile["ts"].endswith("Z")
    assert "link" not in zeile


def test_should_fall_back_to_placeholder_for_missing_subject() -> None:
    zeile = mw.zeile_aus_header("hnu", "INBOX", "1", {"From": "a@b.de", "Subject": ""})
    assert zeile["betreff"] == "(kein Betreff)"


def test_should_build_link_only_for_known_folder_slug() -> None:
    slugs = {"INBOX": "posteingang"}
    assert (
        mw.link_fuer("hnu", "INBOX", "123", slugs)
        == "https://mail.iil.pet/m/hnu/posteingang/123"
    )


def test_should_omit_link_when_folder_slug_is_not_derivable() -> None:
    assert mw.link_fuer("iil", "inbox", "abc123", {}) is None
    assert mw.link_fuer("hnu", "Entw&APw-rfe", "9", {"INBOX": "posteingang"}) is None


def test_should_derive_slug_from_encoded_imap_folder_name() -> None:
    slugs = mw.slugs_fuer_ordner("Entw&APw-rfe")
    assert slugs == {"Entw&APw-rfe": "entwuerfe"}


def test_should_grow_backoff_exponentially_capped_at_five_minutes() -> None:
    assert mw.backoff_sekunden(1) == 5
    assert mw.backoff_sekunden(2) == 10
    assert mw.backoff_sekunden(3) == 20
    assert mw.backoff_sekunden(10) == 300


def test_should_pick_iil_account_by_address_hint() -> None:
    accounts = ["achim.dehnert@hnu.de", "achim.dehnert@iil.gmbh"]
    assert mw.iil_konto(accounts) == "achim.dehnert@iil.gmbh"


def test_should_fall_back_to_first_account_without_iil_hint() -> None:
    assert mw.iil_konto(["irgendwer@example.com"]) == "irgendwer@example.com"
