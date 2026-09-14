"""Rev 8 des Evidenz-Scanners — Kriteriums-Claim (Retro oqu6Z6 §5a, Befund #4, M5).

platform#3015 wurde mit „Alle fünf Kriterien sind erreicht und belegt" geschlossen.
K3 verlangte Verfallsignale „mit Schwelle und Vorlauf", einen Melder, der feuert,
„bevor der Ausfall eintritt", und eine Positivkontrolle mit „Beleg im Journal". Die
Belegzeile gab das Kriterium verkuerzt wieder; Vorlauf, Ausfall und Journal fehlten.

Der erste Test haelt die Messung fest, aus der Rev 8 folgt: der alte Body-Zweig traf
den Satz zwar (`universal-claim`), wurde aber von einem `gh issue view` im Turn
entwaffnet — gelesen hatte die Sitzung das Kriterium, nur nicht Satzteil fuer Satzteil
dagegengehalten. Gegenprobe zu jedem Treffer: eine Zeile derselben Bauart, die NICHT
feuern darf.
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("evidence_claim_scanner_r8", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

#: Wortlaut K3 aus dem Body von platform#3015 (oeffentlich, unveraendert).
K3_WORTLAUT = (
    "- **K3 Vorbeugende Wartung:** Je Anwendung mindestens drei Verfallsignale mit "
    "Schwelle und Vorlauf (Beispiele: Index älter als 36 Stunden, offener Vorgang ohne "
    "Frist). Der Melder feuert als Issue oder Board-Zeile, bevor der Ausfall eintritt. "
    "Positivkontrolle: Schwelle künstlich reißen, Melder feuert, Beleg im Journal."
)

#: Abschluss-Kommentar von platform#3015 (2026-09-14T07:06:04Z), auf K3 gekuerzt.
REALFALL_BODY = (
    "Abschluss 2026-09-14: Alle fünf Kriterien sind erreicht und belegt; die "
    "Folgearbeiten laufen unter eigenen Ankern.\n\n"
    "| K | Kriterium | Beleg |\n|---|---|---|\n"
    "| K3 | Vorbeugende Wartung: Verfallsignale mit Schwelle, Positivkontrolle | "
    "`tools/mail_agent/verfallsmelder.py` (#3064); Zeitung: Canary + leer = Fehler "
    "(news-hub#48), Canary im Tageslauf auf dem Host, Positivkontrolle 2026-09-13 "
    "17:36 UTC (Abbruch, Alarm-Dienst feuerte) |\n"
)

VOLLSTAENDIGER_BODY = (
    "Abschluss: K3 ist erreicht.\n\n"
    "| K3 | Verfallsignale mit Schwelle und Vorlauf je Anwendung; der Melder feuert "
    "vor dem Ausfall als Issue; Positivkontrolle mit künstlich gerissener Schwelle, "
    "Beleg im Journal | news-hub#51 |\n"
)


# --- Die Messung, aus der Rev 8 folgt --------------------------------------


def test_should_zeigen_dass_der_alte_body_zweig_von_einem_issue_view_entwaffnet_wurde() -> (
    None
):
    getroffen = [
        lab for pat, lab in scanner.CLAIM_PATTERNS if pat.search(REALFALL_BODY)
    ]
    assert getroffen == ["universal-claim"], getroffen
    assert scanner.BODY_EVIDENCE_TOKENS.search("gh issue view 3015")


# --- Reine Funktion: Treffer und Nicht-Treffer nebeneinander ---------------


def test_should_die_ausgelassenen_satzteile_des_realfalls_benennen() -> None:
    """POSITIVKONTROLLE am Realfall."""
    luecken = scanner._kriteriums_luecken([REALFALL_BODY], K3_WORTLAUT)
    assert len(luecken) == 1, luecken
    assert luecken[0].startswith("K3: ")
    for teil in ("Vorlauf", "Ausfall", "Journal"):
        assert teil in luecken[0], luecken


def test_should_eine_belegzeile_mit_jedem_satzteil_durchlassen() -> None:
    """NEGATIVKONTROLLE: jeder Satzteil ist angesprochen."""
    assert scanner._kriteriums_luecken([VOLLSTAENDIGER_BODY], K3_WORTLAUT) == []


def test_should_ungelesenen_wortlaut_als_luecke_melden() -> None:
    luecken = scanner._kriteriums_luecken([REALFALL_BODY], "gh pr checks 3141\tpass")
    assert luecken == ["K3: Wortlaut nicht im Turn gelesen"], luecken


def test_should_body_ohne_erreicht_behauptung_in_ruhe_lassen() -> None:
    body = "Erneut geschlossen: K3-Akte korrigiert (news-hub#51, gemergt)."
    assert scanner._kriteriums_luecken([body], "") == []


def test_should_body_ohne_kennungen_in_ruhe_lassen() -> None:
    """Bewusste Grenze: „Akzeptanzkriterien erfuellt" ohne K-Kennung bleibt still."""
    assert scanner._kriteriums_luecken(["Alle Akzeptanzkriterien erfüllt."], "") == []


def test_should_pfade_im_wortlaut_nicht_als_satzteil_zerschneiden() -> None:
    wortlaut = "- **K1 Akte:** Dokumentiert in `docs/betrieb/<anwendung>.md` mit Zweck."
    body = "K1 erreicht: Zweck dokumentiert in der Akte (#3054)."
    assert scanner._kriteriums_luecken([body], wortlaut) == []


# --- Ende zu Ende durch main() ---------------------------------------------


def _transcript(tmp_path, body: str) -> Path:
    p = tmp_path / "transcript_kriterium.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "schliesse den Auftrag"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "b1",
                        "input": {"command": "gh issue view 3015"},
                    },
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "b2",
                        "input": {"command": f"gh issue close 3015 --comment '{body}'"},
                    },
                    {"type": "text", "text": "Auftrag geschlossen."},
                ]
            },
        },
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": K3_WORTLAUT}]},
        },
    ]
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def _run(monkeypatch, capsys, tmp_path, pfad: Path) -> str:
    monkeypatch.setenv("EVIDENCE_SCANNER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"transcript_path": str(pfad)}))
    )
    scanner.main()
    out = capsys.readouterr()
    return out.out + out.err


def test_should_kriteriums_claim_im_realfall_ueber_main_melden(
    monkeypatch, capsys, tmp_path
) -> None:
    """POSITIVKONTROLLE Ende zu Ende: Kriterium gelesen, Belegzeile verkuerzt."""
    ausgabe = _run(monkeypatch, capsys, tmp_path, _transcript(tmp_path, REALFALL_BODY))
    assert "kriteriums-claim" in ausgabe, ausgabe
    assert "Vorlauf" in ausgabe, ausgabe


def test_should_vollstaendige_belegzeile_ueber_main_durchlassen(
    monkeypatch, capsys, tmp_path
) -> None:
    ausgabe = _run(
        monkeypatch, capsys, tmp_path, _transcript(tmp_path, VOLLSTAENDIGER_BODY)
    )
    assert "kriteriums-claim" not in ausgabe, ausgabe
