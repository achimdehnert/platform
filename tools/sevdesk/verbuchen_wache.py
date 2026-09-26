#!/usr/bin/env python3
"""Paperless-Tag ``verbuchen`` → sevdesk-Beleg (Owner-Wort 2026-09-21: „als Aktion
'verbuchen' wie 'senden'").

Der Owner laedt eine Rechnung in Paperless hoch, setzt die Tags ``edv``/``iil``
(Mandant), ggf. ``macan``/``x4``/``8er`` (Kostenstelle) und ``verbuchen`` (das
Kommando). Diese Wache laeuft per systemd-Timer (``systemd/sevdesk-verbuchen.*``)
und macht daraus je Dokument einen Beleg:

1. Felder aus dem OCR-Text (``belegbeschaffung.pdf_lesen``): Datum, Brutto,
   Steuer, Rechnungsnummer; Lieferant = Paperless-Korrespondent, sonst erste
   Textzeile. Probe netto+steuer==brutto ist Pflicht.
2. Konto NUR aus der Owner-Regeldatei (``~/.claude/sevdesk-konten.json``,
   genau eine treffende Regel) — sonst bleibt es leer und steht in der Notiz.
3. Beleg anlegen (``beleg_entwurf.anlegen`` mit Kontakt + Bankdaten,
   Kostenstelle) und auf **offen** (Status 100) stellen — offen, nicht
   bezahlt: Zahlung/Buchung bleibt beim Owner (aus sevdesk heraus anweisen).
4. Paperless: Tag ``verbuchen`` → ``in-sevdesk`` + Notiz mit Beleg-ID, Konto,
   Kostenstelle. Geht etwas nicht: ``verbuchen`` → ``verbuchen-unklar`` +
   Notiz mit dem Grund; der Owner korrigiert und setzt ``verbuchen`` neu.

Dedup: ist die Rechnungsnummer schon ein Beleg im Mandanten, wird nichts
angelegt und das Dokument bekommt ``in-sevdesk`` mit der vorhandenen ID.
``--dry-run`` zeigt den Plan je Dokument und veraendert weder sevdesk noch
Paperless.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import beleg_entwurf as be  # noqa: E402
import belegbeschaffung as bb  # noqa: E402
import paperless  # noqa: E402
from mandant import SECRET_DATEIEN  # noqa: E402

TAG_KOMMANDO = "verbuchen"
TAG_FERTIG = "in-sevdesk"
TAG_UNKLAR = "verbuchen-unklar"
JOURNAL = Path.home() / ".claude" / "sevdesk-verbuchen-journal.jsonl"
PDF_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "sevdesk-verbuchen"


class Unklar(Exception):
    """Grund, warum ein Dokument nicht automatisch zum Beleg wird."""


KOPF_ZEILEN = 15  # Absender/Briefkopf einer Rechnung — dort steht der Lieferantenname


def konto_aus_regeln(
    lieferant: str, beschreibung: str, regeln: list[dict], kopf: str = ""
) -> str | None:
    """Genau eine treffende Owner-Regel → Kontonummer; sonst None (nie raten).

    ``kopf`` (die ersten Textzeilen) gehoert mit in den Suchtext: ohne
    Paperless-Korrespondent ist ``lieferant`` nur die erste Zeile ("KFZ -
    Meisterbetrieb"), der Name aus der Regel steht eine Zeile tiefer
    (Echtprobe 2026-09-21, Dok 2553).
    """
    treffer = [
        v
        for v in be.vorschlaege(f"{lieferant} {kopf}", beschreibung, regeln, [])
        if v["quelle"] == "Regel"
    ]
    konten = {v["konto"] for v in treffer}
    return konten.pop() if len(konten) == 1 else None


def plan_fuer(dok: dict, regeln: list[dict], kostenstellen: list[dict]) -> dict:
    """Reiner Plan aus Dokument + Regeln — ohne sevdesk-/Paperless-Zugriff.

    Wirft :class:`Unklar` mit einem Satz, der dem Owner sagt, was fehlt.
    """
    tags = dok.get("tags") or []
    mandant = paperless.mandant_aus_tags(tags)
    if mandant is None:
        raise Unklar(f"Mandanten-Tag fehlt oder doppelt (edv/iil) — Tags: {tags}")
    felder = bb.pdf_lesen(dok.get("content") or "", dok.get("title") or "")
    brutto, steuer = felder.get("brutto"), felder.get("steuer")
    if not brutto or brutto <= 0:
        raise Unklar("Bruttobetrag nicht im Text erkennbar")
    if felder.get("waehrung") != "EUR":
        raise Unklar(f"Waehrung {felder.get('waehrung')} — Fremdwaehrung nur von Hand")
    if not felder.get("datum"):
        raise Unklar("Rechnungsdatum nicht erkennbar")
    nummer = felder.get("nummer") or ""
    if not nummer or nummer == Path(dok.get("title") or "").stem:
        raise Unklar("Rechnungsnummer nicht erkennbar (Dedup-Schluessel)")
    lieferant = (
        dok.get("correspondent") or felder.get("lieferant_hinweis") or ""
    ).strip()
    if not lieferant:
        raise Unklar("Lieferant unbekannt — Korrespondent in Paperless setzen")
    ks = paperless.kostenstelle_aus_tags(tags, kostenstellen)
    beschreibung = f"Rechnung {nummer}"
    kopf = " ".join((dok.get("content") or "").splitlines()[:KOPF_ZEILEN])
    konto = konto_aus_regeln(lieferant, beschreibung, regeln, kopf)
    taxrule = "9" if steuer and steuer > 0 else "10"
    return {
        "mandant": mandant,
        "lieferant": lieferant,
        "datum": felder["datum"],
        "brutto": f"{brutto:.2f}",
        "steuer": f"{(steuer or 0):.2f}",
        "beschreibung": beschreibung,
        "nummer": nummer,
        "taxrule": taxrule,
        "konto": konto,
        "kostenstelle": ks["name"] if ks else None,
        "korrespondent_fehlt": not dok.get("correspondent"),
        "bankdaten": paperless.bankdaten_aus_text(dok.get("content") or ""),
    }


def _namespace(plan: dict, pdf: str) -> argparse.Namespace:
    return argparse.Namespace(
        mandant=plan["mandant"],
        pdf=pdf,
        ohne_dokument=False,
        lieferant=plan["lieferant"],
        datum=plan["datum"],
        brutto=plan["brutto"],
        steuer=plan["steuer"],
        beschreibung=plan["beschreibung"],
        taxrule=plan["taxrule"],
        konto=plan["konto"] or "",
        waehrung="EUR",
        kurs=None,
        konto_vorschlag=False,
        trotzdem=False,
        strikt=False,
        dry_run=False,
        kostenstelle=plan["kostenstelle"],
        kontakt=True,
        bankdaten=plan["bankdaten"],
    )


def offen_stellen(client, beleg_id: str) -> dict:
    """Entwurf → offen (Status 100) mit expliziten Positionssummen — der
    Roundtrip ohne Summen halbiert Fremdwaehrungsbelege (Memory 2026-09-13);
    hier nur EUR, die Summen gehen trotzdem mit, damit der Weg ueberall gleich ist."""
    pos = client.get(
        "/VoucherPos",
        params={"voucher[id]": beleg_id, "voucher[objectName]": "Voucher"},
    )
    pos.raise_for_status()
    daten = {
        "voucher[id]": str(beleg_id),
        "voucher[objectName]": "Voucher",
        "voucher[mapAll]": "true",
        "voucher[status]": "100",
    }
    for i, p in enumerate(pos.json().get("objects") or []):
        daten[f"voucherPosSave[{i}][id]"] = str(p["id"])
        daten[f"voucherPosSave[{i}][objectName]"] = "VoucherPos"
        daten[f"voucherPosSave[{i}][mapAll]"] = "true"
        daten[f"voucherPosSave[{i}][net]"] = "false"
        for feld in ("sumNet", "sumTax", "sumGross", "taxRate"):
            daten[f"voucherPosSave[{i}][{feld}]"] = str(p[feld])
    r = client.post("/Voucher/Factory/saveVoucher", data=daten)
    r.raise_for_status()
    v = client.get(f"/Voucher/{beleg_id}")
    v.raise_for_status()
    obj = v.json()["objects"]
    obj = obj[0] if isinstance(obj, list) else obj
    if str(obj.get("status")) != "100":
        raise RuntimeError(f"Beleg {beleg_id}: Status {obj.get('status')} statt 100")
    return obj


def anlegen(plan: dict, dok: dict) -> dict:
    """Legt den Beleg an (oder findet die Dublette) und stellt ihn offen."""
    pdf = paperless.pdf_holen(dok, PDF_DIR)
    puffer = io.StringIO()
    with contextlib.redirect_stdout(puffer):
        rc = be.anlegen(_namespace(plan, str(pdf)))
    ausgabe = puffer.getvalue()
    with contextlib.suppress(OSError):
        pdf.unlink()
    if "DUPLIKAT:" in ausgabe:
        vorhanden = ausgabe.split("existiert als Beleg", 1)[1].split()[0]
        return {"beleg_id": vorhanden, "dublette": True}
    if rc != 0:
        raise Unklar(f"beleg_entwurf brach ab (rc {rc}): {ausgabe.strip()[-300:]}")
    zeile = next((z for z in ausgabe.splitlines() if z.startswith('{"beleg_id"')), None)
    if not zeile:
        raise RuntimeError(f"keine beleg_id in der Ausgabe: {ausgabe[-300:]}")
    beleg = json.loads(zeile)
    offen_stellen(be._client(plan["mandant"]), beleg["beleg_id"])
    return {
        "beleg_id": beleg["beleg_id"],
        "dublette": False,
        "kontakt": beleg.get("kontakt"),
    }


def notiz_fertig(plan: dict, ergebnis: dict) -> str:
    teile = [
        f"sevdesk ({plan['mandant']}): Beleg {ergebnis['beleg_id']}"
        + (
            " (bestand schon)"
            if ergebnis.get("dublette")
            else " angelegt, Status offen"
        ),
        f"{plan['brutto']} EUR brutto, {plan['datum']}, {plan['lieferant']}",
        f"Konto {plan['konto']}" if plan["konto"] else "Konto LEER — in sevdesk setzen",
        f"Kostenstelle {plan['kostenstelle']}"
        if plan["kostenstelle"]
        else "ohne Kostenstelle",
    ]
    if plan.get("korrespondent_fehlt"):
        teile.append(
            "Lieferant aus der ersten Textzeile — Korrespondent in Paperless setzen"
        )
    return " · ".join(teile)


def journal(zeile: dict) -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    zeile = {"zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"), **zeile}
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def melden(text: str) -> None:
    """Auftragsraum-Meldung wie beim Rechnungslauf — Ausfall ist kein Abbruch."""
    env = Path.home() / ".claude" / "auftragsraum.env"
    lotse = Path.home() / ".venvs" / "chat-lotse" / "bin" / "python"
    cl = Path.home() / "github" / "chat-hub" / "deploy" / "chat_lotse.py"
    if not (env.exists() and lotse.exists() and cl.exists()):
        return
    raum = next(
        (
            z.split("=", 1)[1].strip().strip('"')
            for z in env.read_text().splitlines()
            if z.startswith("RAUM_ID=")
        ),
        None,
    )
    if not raum:
        return
    subprocess.run(
        [str(lotse), str(cl), "send", "--room", raum, "--text", text], check=False
    )


def lauf(dry_run: bool) -> int:
    start = time.monotonic()
    doks = paperless.dokumente_mit_tag(TAG_KOMMANDO)
    if not doks:
        return 0
    regeln = be.regeln_laden(be.KONTEN_DATEI)
    kostenstellen_je_mandant: dict[str, list[dict]] = {}
    fertig, unklar = [], []
    for dok in doks:
        try:
            tags = dok.get("tags") or []
            mandant = paperless.mandant_aus_tags(tags)
            if mandant and mandant not in kostenstellen_je_mandant:
                kostenstellen_je_mandant[mandant] = be.kostenstellen_laden(
                    be._client(mandant)
                )
            plan = plan_fuer(
                dok, regeln, kostenstellen_je_mandant.get(mandant or "", [])
            )
            if dry_run:
                print(
                    json.dumps(
                        {
                            "dok": dok["id"],
                            "plan": {k: v for k, v in plan.items() if k != "bankdaten"},
                        },
                        ensure_ascii=False,
                    )
                )
                continue
            ergebnis = anlegen(plan, dok)
            text = notiz_fertig(plan, ergebnis)
            paperless.tag_tauschen(dok["id"], TAG_KOMMANDO, TAG_FERTIG, text)
            fertig.append((dok["id"], ergebnis["beleg_id"]))
            journal(
                {
                    "dok": dok["id"],
                    "beleg": ergebnis["beleg_id"],
                    "mandant": plan["mandant"],
                    "konto": plan["konto"],
                    "kostenstelle": plan["kostenstelle"],
                    "dublette": ergebnis.get("dublette", False),
                }
            )
        except Unklar as e:
            grund = str(e)
            if dry_run:
                print(
                    json.dumps({"dok": dok["id"], "unklar": grund}, ensure_ascii=False)
                )
                continue
            paperless.tag_tauschen(
                dok["id"],
                TAG_KOMMANDO,
                TAG_UNKLAR,
                f"verbuchen nicht moeglich: {grund}",
            )
            unklar.append((dok["id"], grund))
            journal({"dok": dok["id"], "unklar": grund})
    if not dry_run and (fertig or unklar):
        teile = [
            f"verbuchen: {len(fertig)} Beleg(e) angelegt"
            + (
                " — " + ", ".join(f"Dok {d}→Beleg {b}" for d, b in fertig)
                if fertig
                else ""
            )
        ]
        if unklar:
            teile.append(
                f"{len(unklar)} unklar — "
                + ", ".join(f"Dok {d}: {g}" for d, g in unklar)
            )
        melden(" · ".join(teile))
        journal(
            {
                "lauf": len(doks),
                "fertig": len(fertig),
                "unklar": len(unklar),
                "dauer_s": round(time.monotonic() - start, 1),
            }
        )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan je Dokument zeigen, nichts schreiben",
    )
    args = p.parse_args()
    for m, pfad in SECRET_DATEIEN.items():
        if not pfad.exists():
            print(
                f"WARNUNG: Secret-Datei fuer Mandant {m} fehlt ({pfad}) — Dokumente dieses Mandanten werden unklar.",
                file=sys.stderr,
            )
    return lauf(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
