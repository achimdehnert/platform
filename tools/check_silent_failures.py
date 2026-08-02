#!/usr/bin/env python3
"""Findet Workflow-Stellen, an denen ein Fehlschlag still bleibt.

Anlass (2026-07-31): Der Hardcoding-Megatest lief **zwei Wochen lang nicht** —
`python` statt `python3` auf dem Runner, `command not found`. Der Workflow meldete
trotzdem `success`, weil der Schritt `continue-on-error: true` trägt. Der
Melde-Schritt dahinter hängt an `steps.megatest_run.outcome == 'failure'` und
feuerte zwar, fand aber keine Ausgabe — und erzeugte 21 inhaltsleere Issues.

Dasselbe Bauprinzip steckt in drei „Meter"-Workflows:

    - name: "Meter ausführen"
      id: meter
      continue-on-error: true          # Absturz ⇒ Workflow bleibt grün
      run: python3 tools/xyz_meter.py

    - name: "Issue bei Verletzung"
      if: steps.meter.outputs.violations != '' …   # leerer Output ⇒ kein Issue

Stürzt das Skript ab, ist der Output leer, das `if` greift nicht, **kein Alarm
entsteht** — und der Workflow ist grün. Ein Melder, der beim Ausfall schweigt,
ist schlimmer als keiner: Sein Grün wird als „geprüft" gelesen.

Geprüft werden zwei Dinge:

1. **Begründung.** Jedes `continue-on-error: true` braucht einen Kommentar in
   der Nähe. Nicht als Bürokratie — wer die Absicht aufschreiben muss, merkt
   beim Schreiben, ob es eine gibt.
2. **Fehlerpfad.** Trägt der weichgestellte Schritt eine `id`, auf deren
   `outputs` ein späterer Schritt reagiert, muss irgendwo im selben Job auch
   auf `.outcome` reagiert werden — sonst ist Absturz gleich Stille.

stdlib + PyYAML, keine weiteren Abhängigkeiten. Exit 1 bei Fund.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - Umgebungsfrage, kein Logikpfad
    print("FEHLER: PyYAML fehlt (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(2) from None

#: So weit über der Zeile darf die Begründung stehen. Großzügig: Kommentare
#: sitzen mal über `- name:`, mal direkt über `continue-on-error`.
KOMMENTAR_FENSTER = 8

_OUTCOME = re.compile(r"steps\.([A-Za-z0-9_-]+)\.outcome")
_OUTPUTS = re.compile(r"steps\.([A-Za-z0-9_-]+)\.outputs")


class Fund:
    def __init__(self, datei: Path, job: str, schritt: str, art: str, text: str):
        self.datei, self.job, self.schritt = datei, job, schritt
        self.art, self.text = art, text

    def __str__(self) -> str:
        return f"  {self.datei.name} · {self.job} · {self.schritt}\n      [{self.art}] {self.text}"


#: Wörter, an denen ein Header-Kommentar als Begründung für weichgestellte
#: Schritte erkennbar ist. Bewusst knapp gehalten: der Check soll fehlende
#: Absicht finden, nicht Formulierungen vorschreiben.
HEADER_SIGNALE = (
    "continue-on-error",
    "weichgestellt",  # die Formulierung, die dieser Check selbst verwendet
    "weich gestellt",
    "blockier",  # "würden PRs blocken", "nicht blockierend"
    "advisory",
    "alarm-müdigkeit",
    "alarm-muedigkeit",
    "nicht blockend",
)


def _header_begruendet(zeilen: list[str]) -> bool:
    """Erklärt der Datei-Header, warum hier weichgestellt wird?

    `staging-registry-checks.yml` begründet acht weichgestellte Jobs in einem
    zwölfzeiligen Header — nicht über jeder einzelnen Zeile. Ohne diese Prüfung
    meldet der Check dort acht Fehlalarme (gemessen 2026-07-31, erster Lauf).
    Eine Begründung, die für die ganze Datei gilt, gehört auch dorthin.
    """
    kopf = []
    for zeile in zeilen:
        blank = zeile.strip()
        if blank.startswith("#"):
            kopf.append(blank.lower())
        elif blank:  # erste Nicht-Kommentarzeile beendet den Header
            break
    text = " ".join(kopf)
    return any(signal in text for signal in HEADER_SIGNALE)


def _begruendet(zeilen: list[str], treffer: int) -> bool:
    """Steht über der Zeile ein Kommentar, der als Begründung durchgeht?"""
    start = max(0, treffer - KOMMENTAR_FENSTER)
    for zeile in zeilen[start:treffer]:
        blank = zeile.strip()
        # Reine Trenn-/Deko-Kommentare zählen nicht als Begründung.
        if blank.startswith("#") and len(blank.lstrip("# ")) > 12:
            return True
    return False


def _weichgestellte_zeilen(text: str) -> list[int]:
    return [
        i
        for i, z in enumerate(text.split("\n"))
        if re.match(r"\s*continue-on-error:\s*true\s*$", z)
    ]


def pruefe_datei(pfad: Path) -> list[Fund]:
    roh = pfad.read_text(encoding="utf-8")
    zeilen = roh.split("\n")
    funde: list[Fund] = []

    # --- 1. Begründungs-Pflicht (rein textuell, damit Kommentare erhalten bleiben)
    header_deckt_ab = _header_begruendet(zeilen)
    for nr in _weichgestellte_zeilen(roh):
        if not header_deckt_ab and not _begruendet(zeilen, nr):
            funde.append(
                Fund(
                    pfad,
                    f"Zeile {nr + 1}",
                    "—",
                    "ohne Begründung",
                    "`continue-on-error: true` ohne erklärenden Kommentar darüber. "
                    "Ein stiller Fehlschlag ohne Begründung ist eine Wette darauf, "
                    "dass niemand hinsieht.",
                )
            )

    # --- 2. Fehlerpfad-Pflicht (braucht die Struktur)
    try:
        doc = yaml.safe_load(roh) or {}
    except yaml.YAMLError as fehler:
        funde.append(Fund(pfad, "—", "—", "nicht parsebar", str(fehler)[:120]))
        return funde

    for job_name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        schritte = job.get("steps") or []
        if not isinstance(schritte, list):
            continue
        job_text = yaml.safe_dump(job, allow_unicode=True)
        reagiert_auf_outcome = set(_OUTCOME.findall(job_text))

        for schritt in schritte:
            if (
                not isinstance(schritt, dict)
                or schritt.get("continue-on-error") is not True
            ):
                continue
            sid = schritt.get("id")
            if not sid:
                continue
            # Reagiert irgendwer auf die OUTPUTS dieses Schritts?
            liest_outputs = any(
                sid in _OUTPUTS.findall(str(anderer.get("if", "")))
                for anderer in schritte
                if isinstance(anderer, dict)
            )
            if liest_outputs and sid not in reagiert_auf_outcome:
                funde.append(
                    Fund(
                        pfad,
                        job_name,
                        schritt.get("name", sid),
                        "Absturz bleibt still",
                        f"Schritt `{sid}` ist weichgestellt, spätere Schritte hängen an "
                        f"`steps.{sid}.outputs.…` — aber niemand prüft "
                        f"`steps.{sid}.outcome`. Stürzt er ab, sind die Outputs leer, "
                        f"kein Folge-Schritt feuert, der Workflow bleibt grün.",
                    )
                )
    return funde


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "pfade",
        nargs="*",
        default=[".github/workflows"],
        help="Workflow-Dateien oder -Verzeichnisse (Default: .github/workflows)",
    )
    ap.add_argument(
        "--nur-fehlerpfad",
        action="store_true",
        help="nur 'Absturz bleibt still' melden, Begründungs-Pflicht überspringen",
    )
    args = ap.parse_args()

    dateien: list[Path] = []
    for eintrag in args.pfade:
        p = Path(eintrag)
        dateien.extend(sorted(p.glob("*.yml")) if p.is_dir() else [p])

    alle: list[Fund] = []
    for datei in dateien:
        alle.extend(pruefe_datei(datei))
    if args.nur_fehlerpfad:
        alle = [f for f in alle if f.art == "Absturz bleibt still"]

    if not alle:
        print(f"✅ {len(dateien)} Workflow(s) geprüft — kein stiller Fehlschlag.")
        return 0

    nach_art: dict[str, list[Fund]] = {}
    for f in alle:
        nach_art.setdefault(f.art, []).append(f)
    for art, funde in sorted(nach_art.items()):
        print(f"\n🔴 {art} ({len(funde)}):")
        for f in funde:
            print(f)
    print(
        f"\n{len(alle)} Fund(e) in {len(dateien)} Workflow(s).\n"
        "Begründung ergänzen, Fehlerpfad nachrüsten — oder `continue-on-error` entfernen."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
