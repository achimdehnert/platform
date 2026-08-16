#!/usr/bin/env python3
"""agent_handover_reconcile.py — Nightly-Reconciler AGENT_HANDOVER.md ↔ GitHub-Live-State.

Stufe 1 (dieser Stand): **strikt read-only**. Prüft für jede Referenz in den offenen
Handover-Abschnitten (Parser: handover_refs.py), ob das Objekt auf GitHub noch offen
ist, und schreibt einen Markdown-Report (stdout + optional --summary für
$GITHUB_STEP_SUMMARY). KEIN Kommentar, KEIN Issue, KEIN Schreibrecht — das
Scharfschalten von Schreib-Aktionen ist per Gate `autonomous-no-human-review`
separat gegated (Follow-up-Issue, siehe Workflow-Kommentar).

Motiv: `handover-stale-vor-merge` ist das häufigste gate-pflichtige Muster (12×,
Retro f218be); die Session-Start-Reconciliation (session-start Phase 2.6) findet
stale Prios erst beim nächsten interaktiven Start — nachts findet sie niemand.

Klassifikation je Referenz:
- OK          — Objekt ist offen (Handover-Eintrag konsistent)
- DISKREPANZ  — Objekt ist geschlossen/gemergt, steht aber als offen im Handover
- UNKNOWN     — API nicht abfragbar (Token-Scope cross-repo/privat, gelöscht, Netz)
                → wird gemeldet, NICHT unterschlagen (kein Silent Cap)

Exit-Code: immer 0 im Report-Modus (ein dauerroter Nightly-Check erzeugt
Alarm-Müdigkeit — Befunde gehören in die Summary, nicht in den Job-Status).
Mit --strict: Exit 1 bei ≥1 DISKREPANZ (für den PR-Wiring-Beweis nicht nutzen).

Aufruf:
  agent_handover_reconcile.py AGENT_HANDOVER.md --repo-slug achimdehnert/platform \
      [--summary /pfad/zur/summary.md] [--strict]

Braucht `gh` im PATH mit GH_TOKEN (in Actions: github.token, read-only Scopes).
Tests (Parser): tools/tests/test_handover_refs.py. Verdrahtet in
.github/workflows/handover-reconcile.yml.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handover_refs import Ref, extract_refs  # noqa: E402

# Registry-Schiedsrichter (platform#2006): `tools/registry_api.owner()` loest den
# Ist-Owner eines Repos auf — per-Repo `github:`-Feld, dann `repo_owner`-Override,
# dann `owner_prefix_rules` (meiki-/ttz-/bahn-), dann Default. Bewusst KEIN zweiter
# Aufloeser: den gibt es bereits, und eine Kopie waere die naechste Drift-Quelle.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
try:
    import registry_api as _reg
except Exception:  # noqa: BLE001 — yaml fehlt, Pfad anders, Registry unlesbar
    _reg = None


def registry_verfuegbar() -> bool:
    """Kann der Schiedsrichter ueberhaupt urteilen?

    Die Unterscheidung entscheidet ueber die Aussagekraft: ohne Registry liefert
    `owner()` fuer JEDES Repo `None`, und ein naiver Aufruf wuerde die komplette
    Flotte als „unbekanntes Repo" melden. Ein Werkzeug, das bei fehlender
    Datenbasis maximal laut wird, ist schlimmer als eines, das dann schweigt.
    """
    if _reg is None:
        return False
    try:
        return bool(_reg.load_canonical().get("repos"))
    except Exception:  # noqa: BLE001
        return False


def schiedsrichter(ref: Ref) -> tuple[Ref, tuple[str, str] | None]:
    """Owner gegen die Registry halten. Liefert (korrigierte Referenz, Urteil).

    Zwei verschiedene Faelle, und sie auseinanderzuhalten ist der ganze Punkt:

    - **Der Owner stand nicht im Text** (`repo#N`, blankes `#N`). Dann hat der
      Parser ihn angenommen, und eine Abweichung ist **kein Befund**, sondern eine
      Korrektur: die Referenz wird auf den richtigen Owner umgeschrieben und ganz
      normal abgefragt.
    - **Der Owner stand im Text** (volle URL oder `owner/repo#N`) und widerspricht
      der Registry. Das ist ein **echter** Befund — ein Link, der ins Leere zeigt
      oder nur ueber einen GitHub-Redirect funktioniert.

    Warum die Unterscheidung teuer erkauft ist: der erste Entwurf meldete alle vier
    Abweichungen des 2026-08-16 als „Adressfehler im Handover". Der Blick in die
    Quellzeile widerlegte das — bei `frist-hub#117` stand die **richtige** URL
    (`meiki-lra/frist-hub`) unmittelbar daneben, gelesen wurde nur der Label-Text.
    Vier der zwoelf `UNKNOWN` waren also nie ein Token-Problem, sondern eine
    Annahme dieses Parsers. Ein Werkzeug, das seine eigene Annahme dem Dokument
    als Fehler vorhaelt, ist schlimmer als eines, das schweigt.
    """
    if not registry_verfuegbar():
        return ref, None
    soll = _reg.owner(ref.repo)
    if soll is None:
        if not ref.owner_explizit:
            # Nur geraten und die Registry kennt das Repo nicht — daraus laesst
            # sich nichts folgern. Die API bekommt die Frage.
            return ref, None
        return ref, (
            "UNBEKANNTES_REPO",
            f"{ref.owner}/{ref.repo} steht nicht in registry/canonical.yaml",
        )
    if soll == ref.owner:
        return ref, None
    if not ref.owner_explizit:
        return replace(ref, owner=soll), None
    return ref, (
        "FALSCHE_ORG",
        f"real {soll}/{ref.repo} — im Text steht {ref.owner}/{ref.repo}",
    )


def token_env_name(owner: str) -> str:
    """Name der Env-Variable, die den Token fuer diesen Owner traegt.

    `iilgmbh` → ``RECONCILE_TOKEN_IILGMBH``; `meiki-lra` → ``RECONCILE_TOKEN_MEIKI_LRA``.
    """
    normal = "".join(c if c.isalnum() else "_" for c in owner).upper()
    return f"RECONCILE_TOKEN_{normal}"


def token_fuer(owner: str) -> str | None:
    """Owner-spezifischer Token, falls vorhanden — sonst None (Default gilt).

    Die Flotte liegt in fuenf Orgs (`achimdehnert`, `iilgmbh`, `meiki-lra`,
    `ttz-lif`, `bahn-sqf`). Ein Installation-Token einer GitHub App gilt je
    Installation, also je Org; deshalb ein Token PRO Owner statt eines fuer alles.
    Fehlt einer, bleibt es beim Default-Token — die betroffenen Referenzen landen
    dann wie bisher unter „nicht pruefbar". Ein fehlender Token darf den Lauf nie
    rot faerben: ein dauerrot laufender Nightly wird abgeschaltet (#1508).

    Gemessen am 2026-08-16, warum das ueberhaupt gebaut wird: derselbe Handover
    ergab mit dem Repo-Token `DISKREPANZ 8 · nicht pruefbar 12`, mit einem Token
    mit Flotten-Sicht `DISKREPANZ 18 · nicht pruefbar 0`. **Zehn echte veraltete
    Referenzen** waren also unsichtbar — nicht hypothetisch, sondern gezaehlt.
    """
    wert = os.environ.get(token_env_name(owner), "").strip()
    return wert or None


def query_state(ref: Ref) -> tuple[str, str]:
    """Liefert (klasse, detail) für eine Referenz via gh api (issues-Endpoint deckt auch PRs)."""
    umgebung = dict(os.environ)
    tok = token_fuer(ref.owner)
    if tok:
        # NUR fuer diesen Aufruf; der Wert wird nirgends ausgegeben (auch nicht im
        # Fehlerdetail — `gh` schreibt ihn nicht in stderr, und wir kuerzen ohnehin).
        umgebung["GH_TOKEN"] = tok
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{ref.owner}/{ref.repo}/issues/{ref.number}"],
            capture_output=True,
            text=True,
            timeout=30,
            env=umgebung,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "UNKNOWN", f"gh nicht ausführbar/Timeout: {exc}"
    if proc.returncode != 0:
        fehler = (proc.stderr.strip().split("\n")[0] or "gh api Fehler")[:120]
        # 404 bei plausiblem Owner heisst mit diesem Token: privat oder geloescht —
        # und die beiden lassen sich damit NICHT unterscheiden. Das ist eine
        # Abdeckungsluecke, kein Befund; als solche gehoert sie in eine eigene
        # Klasse, damit sie die echten Treffer nicht zudeckt (platform#2006).
        if "404" in fehler:
            # Mit einem org-eigenen Token ist 404 eine ANDERE Aussage als ohne:
            # dann faellt „privat" als Erklaerung weg und geloescht/umbenannt
            # bleibt uebrig. Das gehoert in den Text, sonst liest man spaeter
            # dieselbe Zeile mit der falschen Erwartung.
            grund = (
                "Org-Token vorhanden → nicht „privat“, sondern geloescht/umbenannt"
                if tok
                else "privat oder geloescht (ohne Org-Token nicht unterscheidbar)"
            )
            return "NICHT_PRUEFBAR", (
                f"{fehler} — Owner laut Registry korrekt, {grund}"
            )
        return "UNKNOWN", fehler
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "UNKNOWN", "unparsebare API-Antwort"
    state = data.get("state", "?")
    is_pr = "pull_request" in data
    merged = bool((data.get("pull_request") or {}).get("merged_at"))
    kind = "PR" if is_pr else "Issue"
    if state == "open":
        return "OK", f"{kind} offen"
    detail = f"{kind} {'gemergt' if merged else 'geschlossen'}"
    return "DISKREPANZ", detail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("handover", type=Path)
    ap.add_argument(
        "--repo-slug", required=True, help="owner/repo für nackte #N-Referenzen"
    )
    ap.add_argument("--summary", type=Path, default=None)
    ap.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Maschinenlesbaren Befund-Datensatz hierhin schreiben (Leseflaeche, #1908 L1).",
    )
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    owner, repo = args.repo_slug.split("/", 1)
    if not args.handover.is_file():
        print(
            f"::warning::{args.handover} nicht gefunden — nichts zu prüfen (PASS-degradiert)"
        )
        return 0

    refs, skipped_sections = extract_refs(args.handover.read_text(), owner, repo)
    rows: list[tuple[str, Ref, str]] = []
    for ref in refs:
        # Schiedsrichter zuerst: er korrigiert einen bloss angenommenen Owner
        # (dann fragt die API das RICHTIGE Repo) und meldet nur einen im Text
        # stehenden, widersprechenden Owner als Befund.
        ref, vorab = schiedsrichter(ref)
        klass, detail = vorab if vorab else query_state(ref)
        rows.append((klass, ref, detail))

    disc = [r for r in rows if r[0] == "DISKREPANZ"]
    adressfehler = [r for r in rows if r[0] in ("FALSCHE_ORG", "UNBEKANNTES_REPO")]
    unknown = [r for r in rows if r[0] in ("UNKNOWN", "NICHT_PRUEFBAR")]

    out: list[str] = []
    out.append("## Handover-Reconcile (Stufe 1, read-only)")
    out.append("")
    out.append(
        f"Geprüft: **{len(rows)}** Referenzen aus offenen Abschnitten · "
        f"OK {len(rows) - len(disc) - len(adressfehler) - len(unknown)} · "
        f"DISKREPANZ {len(disc)} · ADRESSFEHLER {len(adressfehler)} · "
        f"nicht prüfbar {len(unknown)}"
    )
    if not registry_verfuegbar():
        out.append("")
        out.append(
            "> ⚠️ **Registry-Schiedsrichter inaktiv** (`registry/canonical.yaml` nicht "
            "lesbar oder PyYAML fehlt). Falsch adressierte Referenzen sind in diesem "
            "Lauf **nicht** von privaten Repos unterscheidbar — sie stehen unten "
            "gemeinsam unter „nicht prüfbar“."
        )

    # Token-Abdeckung ausweisen: welche Orgs wurden mit eigenem Token geprueft und
    # welche nur mit dem Default? Ohne diese Zeile liest sich „nicht prüfbar 12"
    # wie ein Repo-Problem, obwohl es eine fehlende Installation sein kann —
    # Herkunft vor Urteil, dieselbe Regel wie bei der Marker-Herkunft in #1986.
    beruehrte_owner = sorted({ref.owner for _, ref, _ in rows})
    mit_token = [o for o in beruehrte_owner if token_fuer(o)]
    ohne_token = [o for o in beruehrte_owner if not token_fuer(o)]
    out.append("")
    out.append(
        "Token-Abdeckung: "
        + (
            f"eigener Token für **{', '.join(mit_token)}**"
            if mit_token
            else "kein Org-Token"
        )
        + (f" · Default-Token für {', '.join(ohne_token)}" if ohne_token else "")
    )
    if adressfehler:
        out.append("")
        out.append("### 🚩 Adressfehler (Referenz zeigt ins Leere)")
        out.append("")
        out.append("| Referenz | Befund | Handover-Zeile |")
        out.append("|---|---|---|")
        for _, ref, detail in adressfehler:
            out.append(
                f"| {ref.owner}/{ref.repo}#{ref.number} | {detail} "
                f"| Z.{ref.line_no}: {ref.line[:80].replace('|', '/')} |"
            )
        out.append("")
        out.append(
            "→ Das ist ein **echter** Befund, kein Zugriffsproblem: der Link im "
            "Handover trägt die falsche Org (oder ein Repo, das die Registry nicht "
            "kennt). Ein GitHub-Redirect kann das maskieren — die Referenz "
            "funktioniert dann für Menschen und scheitert für jedes Werkzeug ohne "
            "Zugriff. Org im Handover korrigieren, nicht den Token erweitern."
        )
    if disc:
        out.append("")
        out.append("### ⚠️ Diskrepanzen (im Handover offen, auf GitHub zu)")
        out.append("")
        out.append("| Referenz | Live-State | Handover-Zeile |")
        out.append("|---|---|---|")
        for _, ref, detail in disc:
            out.append(
                f"| {ref.owner}/{ref.repo}#{ref.number} | {detail} "
                f"| Z.{ref.line_no}: {ref.line[:80].replace('|', '/')} |"
            )
        out.append("")
        out.append(
            "→ Nächste interaktive Session: Handover-Nachzug-PR (Muster: platform#1251). "
            "Ein DISKREPANZ-Treffer kann auch ein False-Positive sein "
            "(Verlaufs-Referenz im offenen Abschnitt) — Triage vor Nachzug."
        )
    if unknown:
        out.append("")
        out.append("### ❔ Nicht prüfbar (kein Silent Skip)")
        out.append("")
        for _, ref, detail in unknown:
            out.append(f"- {ref.owner}/{ref.repo}#{ref.number} — {detail}")
    if skipped_sections:
        out.append("")
        out.append(
            "Nicht gescannte Abschnitte (bewusste Parser-Grenze, s. handover_refs.py): "
            + " · ".join(f"„{s}“" for s in skipped_sections[:8])
        )

    report = "\n".join(out)
    print(report)
    if args.summary:
        args.summary.write_text(report + "\n")
    if args.json:
        # Maschinenlesbare Zweitausgabe fuer die Leseflaeche (platform#1908 Etappe 1,
        # Kriterium L1). Der Markdown-Report bleibt unveraendert die menschliche
        # Ausgabe; ihn zu parsen waere die fragile Variante — genau daran scheiterte
        # bisher jeder Versuch, das Ergebnis weiterzuverwenden.
        args.json.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "geprueft": len(rows),
                    "befunde": [
                        {
                            "schluessel": f"{ref.owner}/{ref.repo}#{ref.number}",
                            "klasse": klass,
                            "detail": detail,
                            "zeile_nr": ref.line_no,
                            "zeile": ref.line[:200],
                        }
                        for klass, ref, detail in rows
                        if klass
                        in (
                            "DISKREPANZ",
                            "FALSCHE_ORG",
                            "UNBEKANNTES_REPO",
                            "NICHT_PRUEFBAR",
                            "UNKNOWN",
                        )
                    ],
                    "nicht_gescannte_abschnitte": skipped_sections,
                },
                ensure_ascii=False,
                indent=1,
            )
            + "\n",
            encoding="utf-8",
        )
    if args.strict and disc:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
