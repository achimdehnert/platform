"""In-Reply-To/References werden nie als MIME-Encoded-Word kodiert.

Anlass 2026-09-16: ein Antwortentwurf an einen Exchange-Absender trug
``In-Reply-To: =?utf-8?q?=3CBEXP...?=`` — die Message-ID hatte 83 Zeichen, die
Standardbibliothek kodierte sie beim Falten. RFC 2047 §5 verbietet das in einer
msg-id; der Strang reisst beim Empfaenger.
"""

from __future__ import annotations

import argparse
import re
import sys
from email import message_from_bytes, policy
from email.message import EmailMessage
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))
dm = pytest.importorskip("draft_mail")
sm = pytest.importorskip("send_mail")

#: Echte Laenge einer Exchange-Kennung (83 Zeichen), Werte erfunden.
OUTLOOK_ID = (
    "<BEXP281MB0215000000000000000000000000000@BEXP281MB0215.DEUP281.PROD.OUTLOOK.COM>"
)
KURZE_ID = "<6554facb82e748de82c515966ba47079@hnu.de>"
BETREFF = "AW: Günzburg — Schnittstelle Posteingang zwischen Partner und PostAssist — Rückfragen zur Übergabe"


def _kopf(msg: EmailMessage) -> str:
    return msg.as_bytes().split(b"\n\n", 1)[0].decode()


def _feld(kopf: str, name: str) -> str:
    treffer = re.search(rf"^{name}:.*?(?=^\S|\Z)", kopf, re.S | re.M)
    assert treffer, f"{name} fehlt"
    return treffer.group(0)


def test_should_detect_encoded_word_with_plain_emailmessage():
    # Positivkontrolle: ohne die Richtlinie tritt der Fehler auf — der Test
    # unten kann ihn also sehen.
    m = EmailMessage()
    m["In-Reply-To"] = OUTLOOK_ID
    m.set_content("x")
    assert "=?" in _feld(_kopf(m), "In-Reply-To")


def test_should_not_encode_long_msgid_in_draft():
    msg = dm.build_draft(
        "a@hnu.de",
        ["b@example.org"],
        [],
        BETREFF,
        text="x",
        in_reply_to=OUTLOOK_ID,
        references=f"{KURZE_ID} {OUTLOOK_ID}",
    )
    kopf = _kopf(msg)
    assert "=?" not in _feld(kopf, "In-Reply-To")
    assert "=?" not in _feld(kopf, "References")


def test_should_not_encode_long_msgid_in_sent_mail():
    args = argparse.Namespace(
        to=["b@example.org"],
        cc=None,
        subject=BETREFF,
        in_reply_to=OUTLOOK_ID,
        references=f"{KURZE_ID} {OUTLOOK_ID}",
        body="x",
        body_file=None,
        html_file=None,
        attach=[],
    )
    kopf = _kopf(sm.build_message("a@hnu.de", args))
    assert "=?" not in _feld(kopf, "In-Reply-To")
    assert "=?" not in _feld(kopf, "References")


def test_should_keep_ids_readable_after_round_trip():
    msg = dm.build_draft(
        "a@hnu.de",
        ["b@example.org"],
        [],
        BETREFF,
        text="x",
        in_reply_to=OUTLOOK_ID,
        references=f"{KURZE_ID} {OUTLOOK_ID}",
    )
    zurueck = message_from_bytes(msg.as_bytes(), policy=policy.default)
    assert str(zurueck["In-Reply-To"]).strip() == OUTLOOK_ID
    assert str(zurueck["References"]).split() == [KURZE_ID, OUTLOOK_ID]
    assert str(zurueck["Subject"]) == BETREFF


def test_should_keep_subject_rfc2047_compliant():
    # Nebenwirkung ausschliessen: der Betreff faltet und kodiert wie bisher.
    kopf = _kopf(dm.build_draft("a@hnu.de", ["b@example.org"], [], BETREFF, text="x"))
    worte = re.findall(r"=\?utf-8\?[qb]\?.*?\?=", _feld(kopf, "Subject"))
    assert worte, "Betreff mit Umlauten muss kodiert sein"
    assert max(map(len, worte)) <= 75
    assert max(len(z) for z in kopf.splitlines()) <= 78 + len(OUTLOOK_ID)


def test_should_wrap_reference_chain_only_between_ids():
    kette = " ".join(f"<{i:02d}-{'x' * 40}@hnu.de>" for i in range(4))
    kopf = _kopf(
        dm.build_draft(
            "a@hnu.de",
            ["b@example.org"],
            [],
            "AW: x",
            text="x",
            in_reply_to=OUTLOOK_ID,
            references=kette,
        )
    )
    feld = _feld(kopf, "References")
    assert len(feld.splitlines()) > 1, "lange Kette wird umbrochen"
    for zeile in feld.splitlines():
        teile = zeile.replace("References:", "").split()
        assert all(t.startswith("<") and t.endswith(">") for t in teile), zeile
