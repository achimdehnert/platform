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


# ── Subjektbindung (Ausweitung 2026-08-20, #2143) ───────────────────────────
# Die Korroboration fragte bisher nur, OB belegartiges Werkzeug lief. Diese Tests
# halten fest, dass sie nach dem GENANNTEN Gegenstand fragt.


def _transcript_mit_evidenz(
    tmp_path, assistant_text: str, tool_input: dict, ergebnis: str
):
    import json as _json

    p = tmp_path / "transcript_ev.jsonl"
    zeilen = [
        {"type": "user", "message": {"content": "mach mal"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": tool_input},
                    {"type": "text", "text": assistant_text},
                ]
            },
        },
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": ergebnis}]},
        },
    ]
    p.write_text("\n".join(_json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def test_should_subjekt_aus_dem_satz_ziehen():
    gefunden = scanner._subjekte(
        "Der Fix in tools/mail_agent/mail_view.py ist live, PR #2147 gemergt."
    )
    assert "tools/mail_agent/mail_view.py" in gefunden
    assert "#2147" in gefunden


def test_should_ohne_benennbaren_gegenstand_leer_bleiben():
    """Kein Subjekt heisst: altes Verhalten, kein Block aus dem Nichts."""
    assert scanner._subjekte("Alles gruen und fertig.") == []


def test_should_claim_ueber_fremden_gegenstand_scharf_geschaltet_melden(
    monkeypatch, capsys, tmp_path
):
    """Zwanzig Kommandos zu Thema A belegen keine Behauptung ueber Thema B.

    Scharf geschaltet entwaffnet die fremde Evidenz den Claim nicht mehr.
    """
    monkeypatch.setenv("EVIDENCE_SCANNER_SUBJEKTBINDUNG", "scharf")
    p = _transcript_mit_evidenz(
        tmp_path,
        "Die Tests in tools/tests/test_ganz_anderes.py sind 8/8 gruen.",
        {"command": "pytest tools/tests/test_mail_view.py"},
        "20 passed in 0.4s",
    )
    rc, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc != 0 or out, "unbelegtes Subjekt muss scharf geschaltet gemeldet werden"


def test_should_im_kalibrierfenster_nicht_blocken(monkeypatch, capsys, tmp_path):
    """Ohne Scharfschaltung bleibt derselbe Fall still — er wird nur protokolliert."""
    monkeypatch.delenv("EVIDENCE_SCANNER_SUBJEKTBINDUNG", raising=False)
    p = _transcript_mit_evidenz(
        tmp_path,
        "Die Tests in tools/tests/test_ganz_anderes.py sind 8/8 gruen.",
        {"command": "pytest tools/tests/test_mail_view.py"},
        "20 passed in 0.4s",
    )
    rc, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0 and not out


def test_should_claim_mit_passendem_beleg_durchlassen(monkeypatch, capsys, tmp_path):
    """Gegenprobe: nennt die Evidenz denselben Gegenstand, bleibt es still."""
    p = _transcript_mit_evidenz(
        tmp_path,
        "Die Tests in tools/tests/test_mail_view.py sind 8/8 gruen.",
        {"command": "pytest tools/tests/test_mail_view.py"},
        "8 passed in 0.4s",
    )
    rc, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert rc == 0 and not out


# --- ci-status: ordnungsgebundene Korroboration (Retro aa58f9, 2026-08-25) ---------
# Zwei Rueckfaelle in einer Sitzung: "CI gruen" nach dem Push, der die CI rot
# machte, und "laeuft im Hintergrund" nach einem Dispatch mit 404. Beide Turns
# hatten FRUEHER ein `gh pr checks` — die generische Korroboration war erfuellt
# und belegte den falschen Zeitpunkt.


def _transcript_mit_werkzeugen(tmp_path, kommandos: list[str], assistant_text: str):
    import json as _json

    p = tmp_path / "transcript_ci.jsonl"
    inhalt = [
        {"type": "tool_use", "name": "Bash", "input": {"command": k}} for k in kommandos
    ]
    inhalt.append({"type": "text", "text": assistant_text})
    zeilen = [
        {"type": "user", "message": {"content": "mach mal"}},
        {"type": "assistant", "message": {"content": inhalt}},
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": "ok"}]},
        },
    ]
    p.write_text("\n".join(_json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def test_should_ci_status_nach_push_ohne_check_blocken(monkeypatch, capsys, tmp_path):
    """Der Realfall: gh pr checks VOR dem Push, dann Push, dann 'CI gruen'."""
    p = _transcript_mit_werkzeugen(
        tmp_path,
        ["gh pr checks 2285", "git push origin HEAD"],
        "Gepusht — CI grün, wartet auf Code-Owner.",
    )
    _, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert out.get("decision") == "block", out
    assert "ci-status" in out.get("reason", "")


def test_should_ci_status_mit_check_nach_push_durchlassen(
    monkeypatch, capsys, tmp_path
):
    p = _transcript_mit_werkzeugen(
        tmp_path,
        ["git push origin HEAD", "gh pr checks 2285"],
        "Gepusht — CI grün, wartet auf Code-Owner.",
    )
    _, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert out.get("decision") != "block", out


def test_should_check_im_selben_kommando_hinter_dem_push_zaehlen(
    monkeypatch, capsys, tmp_path
):
    p = _transcript_mit_werkzeugen(
        tmp_path,
        ["git push origin HEAD && gh pr checks 2285"],
        "Gepusht — CI grün.",
    )
    _, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert out.get("decision") != "block", out


def test_should_hintergrundlauf_nach_dispatch_ohne_run_view_blocken(
    monkeypatch, capsys, tmp_path
):
    """Der zweite Realfall: Dispatch lieferte 404, die Schleife lief auf leerer Run-ID."""
    p = _transcript_mit_werkzeugen(
        tmp_path,
        ["gh workflow run backup-deckung.yml --ref session/x"],
        "Der Beweislauf läuft im Hintergrund.",
    )
    _, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert out.get("decision") == "block", out
    assert "ci-status" in out.get("reason", "")


def test_should_ci_status_ohne_push_im_turn_nicht_ordnungsgebunden_feuern(
    monkeypatch, capsys, tmp_path
):
    """Ohne push/dispatch entscheidet die generische Korroboration — hier: gh pr checks lief."""
    p = _transcript_mit_werkzeugen(
        tmp_path, ["gh pr checks 2285"], "Stand: CI grün auf #2285."
    )
    _, out = _run_main(monkeypatch, capsys, tmp_path, {"transcript_path": str(p)})
    assert out.get("decision") != "block", out


# --- Ausweitung 2026-08-25: Schreibweise und abgeschnittener Beleg ----------------
# Anlass: Retro fdd368 §5a. Zwei getrennte Luecken im selben Realfall — der Satz
# „alle sieben Checks gruen" stand in einer Antwort, waehrend zwei Checks rot waren.


@pytest.mark.parametrize(
    "satz",
    [
        # Der woertliche Satz vom 2026-08-25. Traf das alte Muster NICHT, weil es
        # eine Ziffer verlangte.
        "PR #761 ist MERGEABLE, alle sieben Checks grün, reviewDecision leer.",
        "alle drei Repos sind sauber",
        "alle zwölf Sessions laufen noch",
        # Die Ziffern-Variante muss weiterhin treffen (keine Regression).
        "alle 7 Checks grün",
        "alle 3 Repos sind sauber",
    ],
)
def test_should_allaussage_auch_bei_ausgeschriebener_zahl_erkennen(satz: str) -> None:
    assert "universal-claim" in _klassen(satz), (
        f"{satz!r} rutscht durch — dieselbe Aussage in Ziffern wuerde treffen "
        "(gate-matches-spelling-not-substance)"
    )


@pytest.mark.parametrize(
    "satz",
    [
        # Zahlwort ohne Allquantor ist keine Allaussage.
        "Ich habe sieben Checks angesehen.",
        "Drei Repos waren betroffen.",
        # „alle" ohne Zahlwort/Objekt bleibt ausserhalb dieses Musters.
        "alle weiteren Schritte folgen morgen",
    ],
)
def test_should_zahlwoerter_ohne_allquantor_in_ruhe_lassen(satz: str) -> None:
    assert "universal-claim" not in _klassen(satz), f"{satz!r} ist ein Fehlalarm"


def _bash(cmd: str) -> tuple[str, dict]:
    return ("Bash", {"command": cmd})


def test_should_abgeschnittenes_listen_kommando_als_beleg_verwerfen() -> None:
    """Der Originalfall: `gh pr checks | tail -12` zeigte nur die gruenen Zeilen."""
    assert scanner._beleg_abgeschnitten([_bash("gh pr checks 761 | tail -12")])


def test_should_gegenprobe_im_selben_zug_gelten_lassen() -> None:
    """Wer nach dem GEGENTEIL filtert, hat die Liste vollstaendig befragt."""
    zug = [
        _bash("gh pr checks 761 | tail -12"),
        _bash('gh pr checks 761 | awk \'$2!="pass" && $2!="skipping"\''),
    ]
    assert not scanner._beleg_abgeschnitten(zug)


@pytest.mark.parametrize(
    "cmd",
    [
        # pytest schreibt seine Summenzeile ans Ende — dort ist `tail` die richtige
        # Stelle, kein Verlust. Kein Listen-Kommando, also kein Treffer.
        "make test-pg ARGS='-q' | tail -3",
        "python3 -m pytest tests/ -q | tail -5",
        # Listen-Kommando OHNE Anschnitt ist unverdaechtig.
        "gh pr checks 761",
        # Anschnitt OHNE Listen-Kommando ebenfalls.
        "cat CHANGELOG.md | head -20",
    ],
)
def test_should_legitimen_anschnitt_nicht_verwerfen(cmd: str) -> None:
    assert not scanner._beleg_abgeschnitten([_bash(cmd)]), (
        f"{cmd!r} ist ein Fehlalarm — hier traegt der Anschnitt die Aussage"
    )
