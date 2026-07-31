"""Tests für die Rollen-Profil-Registry (KONZ-platform-033, tools/mail_agent/roles.py)."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "roles.py"
_spec = importlib.util.spec_from_file_location("roles", _SRC)
roles = importlib.util.module_from_spec(_spec)
sys.modules["roles"] = (
    roles  # @dataclass braucht das Modul in sys.modules (string-Annotationen)
)
_spec.loader.exec_module(roles)


def _registry(tmp_path, **overrides):
    base = {
        "roles": {
            "dehnert_team": {
                "display_name": "KI-Assistent von A. D.",
                "role_line": "LUCA-Werkbank",
                "from": "ad@dehnert.team",
                "transport": "smtp",
                "accent": "#12626B",
                "monogram": "d.",
                "requires_legal_footer": False,
            },
            "iil": {
                "display_name": "Prof. Dr. A. D.",
                "role_line": "Leiter · IIL GmbH",
                "from": "a@iil.gmbh",
                "transport": "graph_draft",
                "accent": "#1F3A5F",
                "requires_legal_footer": True,
            },
        }
    }
    base["roles"].update(overrides)
    p = tmp_path / "mail-roles.json"
    p.write_text(json.dumps(base))
    return str(p)


def test_should_resolve_known_role_with_sender_and_transport(tmp_path):
    reg = _registry(tmp_path)
    prof = roles.resolve("dehnert_team", reg)
    assert prof.sender == "ad@dehnert.team"
    assert prof.transport == "smtp"
    assert prof.accent == "#12626B"


def test_should_raise_on_unknown_role(tmp_path):
    reg = _registry(tmp_path)
    with pytest.raises(ValueError, match="unbekannte Rolle"):
        roles.resolve("does_not_exist", reg)


def test_should_block_when_requires_footer_but_none(tmp_path):
    # iil hat requires_legal_footer=True, aber kein legal_footer_file -> Versand-Blocker
    reg = _registry(tmp_path)
    with pytest.raises(ValueError, match="requires_legal_footer"):
        roles.resolve("iil", reg)


def test_should_resolve_when_required_footer_present(tmp_path):
    footer = tmp_path / "iil-footer.txt"
    footer.write_text("IIL GmbH · HRB 12191 · GF Sabine Dehnert\n")
    reg = _registry(
        tmp_path,
        iil={
            "display_name": "Prof. Dr. A. D.",
            "role_line": "Leiter",
            "from": "a@iil.gmbh",
            "transport": "graph_draft",
            "requires_legal_footer": True,
            "legal_footer_file": str(footer),
        },
    )
    prof = roles.resolve("iil", reg)
    assert prof.legal_footer and "HRB 12191" in prof.legal_footer


def test_should_reject_invalid_transport(tmp_path):
    reg = _registry(
        tmp_path,
        bad={
            "display_name": "X",
            "from": "x@y.z",
            "transport": "carrier_pigeon",
        },
    )
    with pytest.raises(ValueError, match="transport"):
        roles.resolve("bad", reg)


def test_should_render_html_with_role_tokens(tmp_path):
    reg = _registry(tmp_path)
    prof = roles.resolve("dehnert_team", reg)
    htmlout = roles.render_email_html(
        prof,
        eyebrow="LUCA",
        greeting="Hallo Ilja,",
        paragraphs=["Erster Absatz.", "Zweiter Absatz."],
        status_rows=[{"label": "Import", "state": "good", "text": "erledigt"}],
    )
    assert prof.accent in htmlout  # Akzent-Token gerendert
    assert "d." in htmlout  # Monogramm
    assert "Erster Absatz." in htmlout
    assert "#1F7A4D" in htmlout  # good-Status-Farbe
    assert htmlout.lstrip().startswith("<!DOCTYPE html>")


def test_should_html_escape_body_content(tmp_path):
    reg = _registry(tmp_path)
    prof = roles.resolve("dehnert_team", reg)
    htmlout = roles.render_email_html(
        prof,
        eyebrow="x",
        greeting="g",
        paragraphs=["<script>alert(1)</script>"],
    )
    assert "<script>alert(1)</script>" not in htmlout
    assert "&lt;script&gt;" in htmlout


def test_should_raise_on_missing_registry(tmp_path):
    with pytest.raises(FileNotFoundError):
        roles.load_registry(str(tmp_path / "nope.json"))


# --- Kanal-Grenze (#1481) ---------------------------------------------------
# Realfall 2026-07-27: eine Mail unter der Rolle 'dehnert_team' bot ein Telefonat
# an — eine Zusage, die diese Identität nicht einlösen kann (Signatur ohne
# Rufnummer). Aufgefallen ist es dem Owner erst NACH dem Versand.

_SATZ = "Wenn dir Telefonieren lieber ist als Schreiben: sag kurz Bescheid."


def _mit_grenze(tmp_path, kanaele=("telefonat",)):
    return _registry(
        tmp_path,
        dehnert_team={
            "display_name": "KI-Assistent von A. D.",
            "from": "ad@dehnert.team",
            "transport": "smtp",
            "darf_nicht_zusagen": list(kanaele),
        },
    )


def test_should_default_to_no_channel_limit(tmp_path):
    # Rollen ohne das Feld verhalten sich exakt wie vorher — keine stille Verschärfung.
    prof = roles.resolve("dehnert_team", _registry(tmp_path))
    assert prof.darf_nicht_zusagen == ()
    roles.pruefe_kanalgrenze(prof, "Betreff", _SATZ)  # darf NICHT werfen


def test_should_block_phone_promise_for_role_that_cannot_call(tmp_path):
    prof = roles.resolve("dehnert_team", _mit_grenze(tmp_path))
    with pytest.raises(roles.KanalgrenzeVerletzt, match="telefonat"):
        roles.pruefe_kanalgrenze(prof, "Fortschritt", _SATZ)


def test_should_pass_same_text_for_human_role(tmp_path):
    """Negativprobe (Akzeptanzkriterium #1481): derselbe Text unter einer
    Menschen-Rolle geht durch — der Fix sperrt den Kanal, nicht den Satz."""
    footer = tmp_path / "f.txt"
    footer.write_text("IIL GmbH · HRB 12191\n")
    reg = _registry(
        tmp_path,
        iil={
            "display_name": "Prof. Dr. A. D.",
            "from": "a@iil.gmbh",
            "transport": "graph_draft",
            "requires_legal_footer": True,
            "legal_footer_file": str(footer),
            "darf_nicht_zusagen": [],
        },
    )
    prof = roles.resolve("iil", reg)
    roles.pruefe_kanalgrenze(prof, "Fortschritt", _SATZ)  # darf NICHT werfen


def test_should_find_signal_word_regardless_of_case_and_umlaut_spelling(tmp_path):
    prof = roles.resolve("dehnert_team", _mit_grenze(tmp_path))
    assert roles.finde_kanalzusagen(prof, "Melde dich für einen RÜCKRUF")
    assert roles.finde_kanalzusagen(prof, "Melde dich fuer einen Rueckruf")


def test_should_not_flag_plain_appointment_wording(tmp_path):
    """Gegenprobe (ADR-284 §7a): 'Termin' allein ist KEIN gesperrter Kanal —
    eine Assistenz darf für ihren Auftraggeber einen Termin vorschlagen."""
    prof = roles.resolve("dehnert_team", _mit_grenze(tmp_path, ("vor-ort-termin",)))
    assert roles.finde_kanalzusagen(prof, "Passt dir ein Termin am Dienstag?") == []
    assert roles.finde_kanalzusagen(prof, "Soll ich am Dienstag vorbeikommen?")


def test_should_reject_unknown_channel_name(tmp_path):
    # Tippfehler im Kanalnamen darf nicht als "nichts gesperrt" durchrutschen.
    reg = _mit_grenze(tmp_path, ("telefonatt",))
    with pytest.raises(ValueError, match="darf_nicht_zusagen"):
        roles.resolve("dehnert_team", reg)


def test_should_allow_registry_to_override_signal_words(tmp_path):
    base = json.loads(pathlib.Path(_mit_grenze(tmp_path)).read_text())
    base["kanal_signale"] = {"telefonat": ["klingeln"]}
    p = tmp_path / "override.json"
    p.write_text(json.dumps(base))
    prof = roles.resolve("dehnert_team", str(p))
    assert roles.finde_kanalzusagen(prof, "Ich klingele dich an") == []
    assert roles.finde_kanalzusagen(prof, "Soll ich klingeln?")
    assert roles.finde_kanalzusagen(prof, "Ruf mich an") == []


def test_should_append_signature_and_footer_to_text(tmp_path):
    sig = tmp_path / "sig.txt"
    sig.write_text("Viele Grüße\nA. D.\n")
    foot = tmp_path / "foot.txt"
    foot.write_text("IIL GmbH · HRB 12191\n")
    reg = _registry(
        tmp_path,
        dehnert_team={
            "display_name": "KI-Assistent",
            "from": "ad@dehnert.team",
            "transport": "smtp",
            "signature_file": str(sig),
            "legal_footer_file": str(foot),
            "requires_legal_footer": True,
        },
    )
    prof = roles.resolve("dehnert_team", reg)
    out = roles.text_mit_signatur(prof, "Kurzer Text.")
    assert out.startswith("Kurzer Text.")
    assert "A. D." in out and "HRB 12191" in out
    assert out.index("A. D.") < out.index("HRB 12191")  # Footer zuletzt


# --- Grußformel-Erkennung (Retro-Befund 2026-07-31) ------------------------


class TestGrussformelVollzeile:
    """Eine Grußformel-ZEILE ist die Formel und nichts sonst.

    Vorher prüfte `str.startswith(GRUSSFORMELN)` nur den Anfang — "Grüße deine
    Frau von mir." galt damit als Grußformel, und die Folgezeile wurde aus der
    versandfertigen Mail gelöscht. Ein Wortgrenzen-`\\b` hätte NICHT gereicht:
    nach "Grüße" steht ein Leerzeichen, die Grenze ist erfüllt.
    """

    @staticmethod
    def _profil():
        return roles.Profile(
            role_id="t",
            display_name="T",
            sender="t@example.org",
            transport="graph_draft",
            signature="Prof. Dr. Achim Dehnert · Leiter\nMobil +49 171 537 6151",
        )

    def _rumpf(self, text):
        out = roles.text_mit_signatur(self._profil(), text)
        return out.split("Prof. Dr.")[0]

    def test_should_keep_name_after_imperative_starting_with_gruesse(self):
        """'Grüße deine Frau von mir.' ist ein Satz, keine Grußformel."""
        text = "Bis dahin.\n\nGrüße deine Frau von mir.\nAchim Dehnert"
        assert "Achim Dehnert" in self._rumpf(text)

    def test_should_keep_name_after_word_starting_with_gruesse(self):
        text = "Kurz.\n\nGrüßeaustausch war nett\nAchim Dehnert"
        assert "Achim Dehnert" in self._rumpf(text)

    def test_should_still_drop_name_after_real_greeting(self):
        text = "Kurz.\n\nHerzliche Grüße\nAchim Dehnert"
        assert "Achim Dehnert" not in self._rumpf(text)

    def test_should_tolerate_punctuation_after_greeting(self):
        text = "Kurz.\n\nViele Grüße,\nProf. Dr. Achim Dehnert"
        assert "Achim Dehnert" not in self._rumpf(text)

    def test_should_not_cut_body_at_imperative_in_zerlege_klartext(self):
        """`zerlege_klartext` sucht die Grußformel von hinten — ein Satzanfang
        'Grüße…' hätte dort alles danach abgeschnitten."""
        text = (
            "Hallo,\n\nGrüße deine Frau von mir.\n\n"
            "Der eigentliche Punkt kommt erst hier.\n\nHerzliche Grüße\nAchim"
        )
        b = roles.zerlege_klartext(text)
        assert any("Der eigentliche Punkt" in p for p in b["paragraphs"])
        assert b["closing"] == "Herzliche Grüße"
