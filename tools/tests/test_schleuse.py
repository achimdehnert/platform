"""Schleuse: Unentschieden-Eintraege verfallen nach 90 Tagen — Secrets nie.

Owner-Entscheid 2026-09-07 (platform#2895 Item 57): "unentschieden" ist kein
Dauerzustand mehr. Ab UNENTSCHIEDEN_FRIST_TAGE gilt ein Eintrag ohne passende
Regel als faellig und wandert mit --aufraeumen --apply ins Archiv, genau wie
jede benannte Klasse. Die Ausnahme fuer Secrets (nie archivieren) darf davon
nicht aufgeweicht werden — das ist hier die Positivkontrolle, kein Nebenfall.

Das Dateisystem wird ausschliesslich ueber tmp_path + monkeypatch simuliert,
nie das echte ~/shared.
"""

import datetime
import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "schleuse.py"
_spec = importlib.util.spec_from_file_location("schleuse", _SRC)
schleuse = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(schleuse)

HEUTE = datetime.date(2026, 9, 7)


def _anlegen(schleuse_pfad: pathlib.Path, name: str, alter_tage: int, ist_datei=True):
    ziel = schleuse_pfad / name
    if ist_datei:
        ziel.write_text("inhalt")
    else:
        ziel.mkdir()
        (ziel / "datei.txt").write_text("inhalt")
    stand = HEUTE - datetime.timedelta(days=alter_tage)
    zeitstempel = datetime.datetime.combine(stand, datetime.time(12, 0)).timestamp()
    import os

    os.utime(ziel, (zeitstempel, zeitstempel))
    return ziel


def _sammeln(monkeypatch, tmp_path):
    monkeypatch.setattr(schleuse, "SCHLEUSE", tmp_path)
    return schleuse.sammeln(HEUTE)


def _finde(posten, name):
    for x in posten:
        if x["pfad"].name == name:
            return x
    raise AssertionError(f"{name} nicht in posten: {[p['pfad'].name for p in posten]}")


def test_should_mark_unentschieden_faellig_after_91_days(monkeypatch, tmp_path):
    _anlegen(tmp_path, "irgendein-ordner", 91, ist_datei=False)

    posten = _sammeln(monkeypatch, tmp_path)

    eintrag = _finde(posten, "irgendein-ordner")
    assert eintrag["unentschieden"] is True
    assert eintrag["faellig"] is True


def test_should_keep_unentschieden_in_frist_at_89_days(monkeypatch, tmp_path):
    _anlegen(tmp_path, "irgendein-ordner", 89, ist_datei=False)

    posten = _sammeln(monkeypatch, tmp_path)

    eintrag = _finde(posten, "irgendein-ordner")
    assert eintrag["unentschieden"] is True
    assert eintrag["faellig"] is False


def test_should_never_mark_secrets_container_faellig_even_at_200_days(
    monkeypatch, tmp_path
):
    # SECRETS_TOP ist der Top-Level-Ordner, der die Secrets traegt (inbox/secrets
    # -> "inbox"). sammeln() klassifiziert nur Top-Level-Eintraege, daher hier.
    _anlegen(tmp_path, schleuse.SECRETS_TOP, 200, ist_datei=False)

    posten = _sammeln(monkeypatch, tmp_path)

    eintrag = _finde(posten, schleuse.SECRETS_TOP)
    assert eintrag["unentschieden"] is True
    assert eintrag["faellig"] is False


def test_should_report_unentschieden_faellig_separately_from_in_frist(
    monkeypatch, tmp_path, capsys
):
    _anlegen(tmp_path, "faelliger-ordner", 91, ist_datei=False)
    _anlegen(tmp_path, "frischer-ordner", 40, ist_datei=False)

    posten = _sammeln(monkeypatch, tmp_path)
    schleuse.bericht(posten, zeige_alle=False)
    ausgabe = capsys.readouterr().out

    assert "UNENTSCHIEDEN, IN FRIST (1)" in ausgabe
    assert "UNENTSCHIEDEN, FAELLIG (1)" in ausgabe
    assert "faelliger-ordner" in ausgabe
    assert "frischer-ordner" in ausgabe


def test_should_move_unentschieden_faellig_entry_via_aufraeumen_apply(
    monkeypatch, tmp_path
):
    eintrag_pfad = _anlegen(tmp_path, "alter-rest", 120, ist_datei=False)
    monkeypatch.setattr(schleuse, "SCHLEUSE", tmp_path)

    posten = schleuse.sammeln(HEUTE)
    schleuse.aufraeumen(posten, apply=True, heute=HEUTE)

    assert not eintrag_pfad.exists()
    archiviert = tmp_path / schleuse.ARCHIV / HEUTE.isoformat() / "alter-rest"
    assert archiviert.is_dir()


# ── #2622: die Schutzlogik von aufraeumen/endgueltig selbst ──────────────────


def test_should_leave_everything_untouched_in_dry_run(monkeypatch, tmp_path, capsys):
    eintrag = _anlegen(tmp_path, "alter-rest", 120, ist_datei=False)
    posten = _sammeln(monkeypatch, tmp_path)
    assert _finde(posten, "alter-rest")["faellig"]
    schleuse.aufraeumen(posten, apply=False, heute=HEUTE)
    assert eintrag.exists()
    assert not (tmp_path / schleuse.ARCHIV).exists()
    assert "WUERDE VERSCHIEBEN" in capsys.readouterr().out


def test_should_keep_entries_within_deadline_even_with_apply(monkeypatch, tmp_path):
    jung = _anlegen(tmp_path, "junger-rest", 5, ist_datei=False)
    posten = _sammeln(monkeypatch, tmp_path)
    schleuse.aufraeumen(posten, apply=True, heute=HEUTE)
    assert jung.exists()


def test_should_delete_only_archive_folders_older_than_threshold(monkeypatch, tmp_path):
    monkeypatch.setattr(schleuse, "SCHLEUSE", tmp_path)
    archiv = tmp_path / schleuse.ARCHIV
    alt = archiv / (HEUTE - datetime.timedelta(days=91)).isoformat()
    jung = archiv / (HEUTE - datetime.timedelta(days=10)).isoformat()
    for d in (alt, jung):
        d.mkdir(parents=True)
        (d / "datei").write_text("x")
    schleuse.endgueltig(apply=True, heute=HEUTE, tage=90)
    assert not alt.exists()
    assert jung.exists()


def test_should_not_delete_in_endgueltig_dry_run(monkeypatch, tmp_path):
    monkeypatch.setattr(schleuse, "SCHLEUSE", tmp_path)
    alt = (
        tmp_path / schleuse.ARCHIV / (HEUTE - datetime.timedelta(days=200)).isoformat()
    )
    alt.mkdir(parents=True)
    schleuse.endgueltig(apply=False, heute=HEUTE, tage=90)
    assert alt.exists()


def test_should_ignore_undated_folders_in_archive(monkeypatch, tmp_path):
    """Nur datierte Ordner sind loeschbar — alles andere im Archiv bleibt liegen."""
    monkeypatch.setattr(schleuse, "SCHLEUSE", tmp_path)
    fremd = tmp_path / schleuse.ARCHIV / "manuell-abgelegt"
    fremd.mkdir(parents=True)
    schleuse.endgueltig(apply=True, heute=HEUTE, tage=0)
    assert fremd.exists()


def test_should_never_touch_paths_outside_the_schleuse(monkeypatch, tmp_path):
    """Der Loeschpfad ist immer SCHLEUSE/_archiv/<datum> — nie ein fremder Ort."""
    monkeypatch.setattr(schleuse, "SCHLEUSE", tmp_path / "shared")
    (tmp_path / "shared").mkdir()
    fremd = tmp_path / "_archiv" / (HEUTE - datetime.timedelta(days=200)).isoformat()
    fremd.mkdir(parents=True)
    schleuse.endgueltig(apply=True, heute=HEUTE, tage=90)
    assert fremd.exists()


# ── #3405: die Klassen aus der Bestandsaufnahme 2026-09-23 ───────────────────
#
# Jeder Name hier ist ein echter Eintrag aus ~/shared vom 2026-09-23 — die
# Regeln sind an diesem Bestand entstanden, also wird auch an ihm geprueft.
# Die beiden Kontrollen am Ende sind der eigentliche Punkt: die Regeln duerfen
# weder den Secrets-Ordner einfangen noch alles andere pauschal abraeumen.


@pytest.mark.parametrize(
    ("name", "erwartete_klasse", "erwartete_frist"),
    [
        ("pr-o-series.md", "PR-/Issue-Text", 14),
        ("issue-189.md", "PR-/Issue-Text", 14),
        ("commit-o-series.txt", "PR-/Issue-Text", 14),
        ("review 2.md", "PR-/Issue-Text", 14),
        ("cf-access-recon.sh", "Wegwerf-Skript", 21),
        ("w11-inventar.ps1", "Wegwerf-Skript", 21),
        ("paperless-access-konten.py", "Wegwerf-Skript", 21),
        ("hetzner.png", "Bildschirmfoto", 30),
        ("DESKTOP-G1MN89S_C.csv", "Lauf-Ausgabe", 30),
        # "probe" traegt weiter als der comfyui-Prefix: eine Probe-Ausgabe ist
        # eine Lauf-Ausgabe, egal welches Werkzeug sie erzeugt hat.
        ("comfyui-probe.txt", "Lauf-Ausgabe", 30),
        ("konz041-pilot-verifikation-2026-08-06.txt", "Lauf-Ausgabe", 30),
        ("meiki-hnu-TOM-2026-07-27-entwurf.pdf", "Dokument-Entwurf", 30),
        ("MEiKI-P1-Steckbrief-ENTWURF.docx", "Dokument-Entwurf", 30),
        ("lora-hina-paket.zip", "Modell-Ausgabe", 30),
        ("bakeoff-int8", "Modell-Ausgabe", 30),
        ("kd-sync-2026-08-03", "Datierte Uebergabe", 45),
        ("gov-redaction-originals-2026-07-08", "Datierte Uebergabe", 45),
    ],
)
def test_should_classify_real_schleuse_entries(
    monkeypatch, tmp_path, name, erwartete_klasse, erwartete_frist
):
    _anlegen(tmp_path, name, 5)

    eintrag = _finde(_sammeln(monkeypatch, tmp_path), name)

    assert eintrag["klasse"] == erwartete_klasse
    assert eintrag["frist"] == erwartete_frist


@pytest.mark.parametrize(
    "name",
    [
        "CAD",
        "Second Brain",
        "FRITZ!Box 7590.pdf",
        "konzept-hybrid.md",
        "cloudflared-risk-hub-staging-config.yml",
    ],
)
def test_should_leave_genuine_single_cases_unentschieden(monkeypatch, tmp_path, name):
    """Positivkontrolle: die neuen Regeln duerfen nicht alles einfangen.

    Diese fuenf lagen am 2026-09-23 ebenfalls in der Schleuse und sind echte
    Einzelfaelle — ein Projektordner, eine Notiz, eine Konfiguration. Sie
    muessen unentschieden bleiben, sonst ist die Klassifikation nur noch ein
    Etikett fuer "alles verfaellt".
    """
    _anlegen(tmp_path, name, 40, ist_datei=name.endswith((".pdf", ".md", ".yml")))

    eintrag = _finde(_sammeln(monkeypatch, tmp_path), name)

    assert eintrag["klasse"] == "unklassifiziert"
    assert eintrag["unentschieden"] is True


def test_should_not_let_new_rules_reach_the_secrets_container(monkeypatch, tmp_path):
    """Die Datums-Regel ist die breiteste — sie darf den Secrets-Ordner nicht fassen."""
    _anlegen(tmp_path, schleuse.SECRETS_TOP, 200, ist_datei=False)

    eintrag = _finde(_sammeln(monkeypatch, tmp_path), schleuse.SECRETS_TOP)

    assert eintrag["klasse"] == "unklassifiziert"
    assert eintrag["faellig"] is False


# ── Reihenfolge der REGELN ist tragend (#3405, Retro 4ed2e5 Befunde 2–4) ────
#
# `klasse_von()` nimmt den ERSTEN Treffer. Zwei Muster ueberlappen sich
# absichtlich, und die Reihenfolge entscheidet, welches gewinnt. Das war bis zu
# dieser Retro nirgends festgehalten: der einzige Test zur Klasse
# "PR-/Issue-Text" benutzte `"review 2.md"` — die einzige Variante, die den
# Konflikt gar nicht beruehrt. Er war gruen, ohne die Grenze zu pruefen.


@pytest.mark.parametrize(
    ("name", "klasse", "warum"),
    [
        # Bindestrich-Variante: echte Berichte aus dem Bestand vom 2026-09-23.
        (
            "review-KONZ-writing-hub-014-zweitmeinung-2026-08-20.md",
            "Bericht",
            "Zweitmeinung zu einem Konzept — gehoert nach docs/ des Repos",
        ),
        (
            "review-skill-einmotten-adaption-2026-07-17.md",
            "Bericht",
            "Review eines Skills — ebenfalls ein Bericht",
        ),
        # Leerzeichen-Variante: Notizen zu einem PR.
        ("review 1.md", "PR-/Issue-Text", "Notiz zu einem PR"),
        ("review 2.md", "PR-/Issue-Text", "Notiz zu einem PR"),
    ],
)
def test_should_keep_the_boundary_between_bericht_and_pr_text(
    monkeypatch, tmp_path, name, klasse, warum
):
    """Wer die Reihenfolge der REGELN aendert, bricht diesen Test sichtbar."""
    _anlegen(tmp_path, name, 5)

    eintrag = _finde(_sammeln(monkeypatch, tmp_path), name)

    assert eintrag["klasse"] == klasse, warum


def test_should_treat_k4_as_a_prefix_not_an_exact_match():
    """Der `$`-Anker mitten in der Alternation machte aus dem Praefix einen
    exakten Vergleich — `k4` traf, `k4-run-2026` nicht."""
    _, muster, _, _ = next(r for r in schleuse.REGELN if r[0] == "Modell-Ausgabe")

    assert muster.match("k4") is not None
    assert muster.match("k4w") is not None
    assert muster.match("k4-run-2026") is not None
    assert muster.match("k4width-test") is not None
    # Positivkontrolle: das Muster sagt nicht zu allem ja.
    assert muster.match("kuenersberg") is None


def test_should_not_let_a_later_rule_be_shadowed_unnoticed():
    """Waechter fuer kuenftige Regeln: je Klasse ein Name, der genau dort landen
    soll. Faellt eine Zeile, hat eine frueher stehende Regel sie eingefangen —
    dann ist entweder die Reihenfolge oder das Muster zu aendern, nicht dieser
    Test.
    """
    erwartet = {
        "pr-o-series.md": "PR-/Issue-Text",
        "cf-access-recon.sh": "Wegwerf-Skript",
        "hetzner.png": "Bildschirmfoto",
        "DESKTOP-G1MN89S_C.csv": "Lauf-Ausgabe",
        "meiki-hnu-TOM-2026-07-27-entwurf.pdf": "Dokument-Entwurf",
        "lora-hina-paket.zip": "Modell-Ausgabe",
        "kd-sync-2026-08-03": "Datierte Uebergabe",
        "adr-handoff-ADR-063-2026-08-26.md": "ADR-Uebergabe",
        "von-box": "Box-Lane",
    }
    tatsaechlich = {name: schleuse.klasse_von(name)[0] for name in erwartet}

    assert tatsaechlich == erwartet
