"""Der Wächter, gemessen an den Sätzen, an denen er versagt hat.

Am 2026-07-31 gingen an einem Tag fünf prüfbare Behauptungen falsch oder ungeprüft
raus. Der Scanner lief die ganze Zeit — er fing **eine**. Die vier anderen sind hier
wörtlich als Fixture hinterlegt, damit „ich achte künftig darauf" durch etwas ersetzt
wird, das beim nächsten Mal von selbst anschlägt.

Wichtig für die Bewertung dieser Datei: ein Test, der nur die neu gebauten Muster
bestätigt, wäre zirkulär. Deshalb stehen die **Nicht-Treffer** gleichberechtigt
daneben — Redewendungen, die dieselben Wörter tragen, aber nichts Prüfbares behaupten.
Ein Wächter, der bei „ich habe keine Zeit" anschlägt, wird abgeschaltet und schützt
dann gar nichts mehr.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_QUELLE = Path(__file__).resolve().parents[1] / "evidence_claim_scanner.py"
_spec = importlib.util.spec_from_file_location("evidence_claim_scanner", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)


def _klassen(satz: str) -> set[str]:
    return {label for muster, label in scanner.CLAIM_PATTERNS if muster.search(satz)}


# --- Die realen Fehlsätze vom 2026-07-31, wörtlich -------------------------------


@pytest.mark.parametrize(
    "satz, erwartet",
    [
        # Gelesen waren 100 von 140 Zeilen; alle drei Meter-Jobs trugen den Zweig.
        ("Kein einziger dieser Jobs fragt steps.meter.outcome ab.", "universal-claim"),
        ("Keiner der drei Melder prüft das outcome.", "universal-claim"),
        # Belegt war der Vortag, behauptet die Gegenwart.
        ("Der Megatest läuft weiterhin nicht.", "function-negation"),
        ("Das Gate greift nicht.", "function-negation"),
        # Aus dem Gedächtnis geschrieben, falsch: 29.07. vs. 30.07.
        ("Das war das zweite Mal am selben Tag.", "temporal-claim"),
        ("Der Check schlägt seit 14 Tagen fehl.", "temporal-claim"),
        # Vermutung im Gewand eines Befunds; geprüft waren es null.
        (
            "Viele dieser Issues sind längst erledigt und wurden nur nie geschlossen.",
            "soft-quantifier-claim",
        ),
        ("Die meisten der Repos haben den Scan schon aktiv.", "soft-quantifier-claim"),
    ],
)
def test_should_erkennen_die_realen_fehlsaetze(satz: str, erwartet: str) -> None:
    assert erwartet in _klassen(satz), f"{satz!r} rutscht weiterhin durch"


# --- Redewendungen: gleiche Wörter, keine prüfbare Behauptung ---------------------


@pytest.mark.parametrize(
    "satz",
    [
        "Ich habe keine Zeit, das heute noch zu prüfen.",
        "Das läuft nicht auf einen Rewrite hinaus.",
        "Es gibt keinen Grund, das jetzt zu entscheiden.",
        "Der Fix funktioniert nicht nur hier, sondern überall.",
        "Wir sollten das nicht zwingend heute klären.",
        "Viele Wege führen nach Rom.",
        "Das kostet viele Stunden Arbeit.",
    ],
)
def test_should_redewendungen_in_ruhe_lassen(satz: str) -> None:
    treffer = _klassen(satz) & {
        "universal-claim",
        "function-negation",
        "temporal-claim",
        "soft-quantifier-claim",
    }
    assert not treffer, f"Falschalarm auf {satz!r}: {treffer}"


# --- Beleg-Strenge: der falsche Beleg darf nicht durchgehen ----------------------


def test_should_diff_nicht_als_beleg_fuer_gegenwart_akzeptieren() -> None:
    """`git show` zeigt Code, nicht Verhalten.

    Genau dieser Fehlschluss trug den Megatest-Satz: die Workflow-Datei war
    unverändert, also „läuft weiterhin nicht" — ohne den heutigen Lauf anzusehen.
    """
    assert not scanner.RUN_EVIDENCE_TOKENS.search(
        "git show origin/main:.github/workflows/megatest.yml"
    )
    assert scanner.RUN_EVIDENCE_TOKENS.search("gh run view 30610979756 --log")


def test_should_stichprobe_nicht_als_beleg_fuer_allaussage_akzeptieren() -> None:
    """Ein gezielter Datei-Read deckt keine Aussage über eine ganze Menge."""
    assert not scanner.ABSENCE_EVIDENCE_TOKENS.search(
        "Read .github/workflows/megatest.yml limit=100"
    )
    assert scanner.ABSENCE_EVIDENCE_TOKENS.search(
        "grep -rn 'steps.meter.outcome' .github/workflows/"
    )


# --- Drill (KONZ-038 K4/D8): provozierter Verstoss MUSS blocken ------------------
# Ein Gate ohne bestandenen Negativ-Drill gilt als NICHT gebaut. Diese Tests SIND
# der Drill: ein unbelegter Claim erzwingt decision:block; der stop_hook_active-
# Guard verhindert den Block-Loop; das Advisory-Opt-out bleibt funktionsfaehig.


def _transcript(tmp_path, assistant_text: str):
    p = tmp_path / "transcript.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "mach mal"}},
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": assistant_text}]},
        },
    ]
    p.write_text(
        "\n".join(__import__("json").dumps(z) for z in zeilen), encoding="utf-8"
    )
    return p


def _run_main(monkeypatch, capsys, tmp_path, event: dict):
    import io
    import json as _json

    monkeypatch.setenv("EVIDENCE_SCANNER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr("sys.stdin", io.StringIO(_json.dumps(event)))
    rc = scanner.main()
    out = capsys.readouterr().out.strip()
    return rc, (_json.loads(out) if out else {})


def test_should_block_unbelegten_claim_im_blocking_mode(
    monkeypatch, capsys, tmp_path
) -> None:
    p = _transcript(tmp_path, "Fertig — alle Tests 8/8 grün, Deployment verifiziert.")
    rc, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0
    assert out.get("decision") == "block", f"Drill fehlgeschlagen: {out}"
    assert "KEINE Nutzer-Ablehnung" in out.get("reason", "")


def test_should_im_continuation_turn_nicht_erneut_blocken(
    monkeypatch, capsys, tmp_path
) -> None:
    p = _transcript(tmp_path, "Fertig — alle Tests 8/8 grün.")
    rc, out = _run_main(
        monkeypatch,
        capsys,
        tmp_path,
        {"transcript_path": str(p), "stop_hook_active": True},
    )
    assert rc == 0
    assert out == {}, "Block-Loop-Schutz verletzt: Hook feuerte im Continuation-Turn"


def test_should_advisory_optout_respektieren(monkeypatch, capsys, tmp_path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "evidence_scanner_mode").write_text("advisory", encoding="utf-8")
    p = _transcript(tmp_path, "Fertig — alle Tests 8/8 grün.")
    rc, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0
    assert "decision" not in out
    assert "additionalContext" in out.get("hookSpecificOutput", {})


def test_should_ohne_claim_still_bleiben_auch_im_blocking_mode(
    monkeypatch, capsys, tmp_path
) -> None:
    p = _transcript(tmp_path, "Ich schaue mir zuerst die Logdatei an.")
    rc, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0
    assert out == {}, "Kein Claim, aber Hook feuerte — False-Positive-Drill verletzt"
