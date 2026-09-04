#!/usr/bin/env python3
"""Rollen-Profil-Registry für Mail-Identität (KONZ-platform-033).

Eine deklarative Registry (JSON, stdlib-only — mail_agent bleibt ohne PyYAML)
mappt eine Rolle auf Absender, Transport, Signatur, Design-Akzent und
Governance. Konsumenten (send_mail/draft_mail/graph_mail) lösen per role-id
das Profil auf und rendern eine Outlook-feste HTML-Mail im Stil "Klare Linie".

Registry-Ort (personenbezogen → NICHT im Repo, wie mail.env):
  ~/.claude/mail-roles.json        (real; ein Beispiel liegt als mail-roles.example.json im Repo)
Signatur-/Footer-Inhalte:
  ~/.claude/mail-sig/<name>.txt

SSoT-Disziplin: die Registry referenziert den Transport nur per Key
(smtp | graph_draft | imap_append) — Credentials/Hosts bleiben in mail*.env
bzw. ~/.secrets und werden hier NIE kopiert.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

DEFAULT_REGISTRY = Path.home() / ".claude" / "mail-roles.json"

# Transport-Keys → nur Referenz; die tatsächliche Verbindung lebt in mail*.env.
VALID_TRANSPORTS = {"smtp", "graph_draft", "imap_append"}

# Semantische Statusfarben für den optionalen Status-Block (getrennt vom Akzent).
_STATE_COLORS = {
    "good": "#1F7A4D",
    "warn": "#B7791F",
    "bad": "#B23B3B",
    "info": None,  # None → Akzentfarbe des Profils
}

_REQUIRED_FIELDS = ("display_name", "from", "transport")

# --- Kanal-Grenze (#1481) ---------------------------------------------------
# `transport` beschreibt den technischen Weg der Nachricht, NICHT die
# Handlungsfähigkeit des Absenders. Eine Rolle kann per Mail hinausgehen und
# trotzdem außerstande sein, ein Telefonat einzulösen. `darf_nicht_zusagen`
# benennt genau diese Kanäle je Rolle.
#
# Bewusst eine Wortliste und kein Sprachmodell (#1481 "Abgrenzung"): überprüfbar,
# deterministisch, falsifizierbar. Die Listen sind absichtlich ENG geschnitten —
# eine zu breite Liste erzeugt dieselbe Fehlerklasse wie eine zu breite
# Ablage-Regel (ADR-284 §7a: die Gegenprobe entscheidet, nicht die Formulierung).
# Deshalb steht "Termin" NICHT in `vor-ort-termin`: eine Assistenz darf für ihren
# Auftraggeber sehr wohl einen Termin vorschlagen — sie kann ihn nur nicht selbst
# wahrnehmen. Wer schärfer prüfen will, überschreibt die Liste in der Registry
# (Top-Level "kanal_signale") statt den Code zu ändern.
KANAL_SIGNALE: dict[str, tuple[str, ...]] = {
    "telefonat": (
        "telefon",
        "telefonisch",
        "telefonat",
        "anruf",
        "anrufen",
        "angerufen",
        "rückruf",
        "rueckruf",
        "durchwahl",
        "hörer",
        "hoerer",
    ),
    "vor-ort-termin": (
        "vor ort",
        "vor-ort",
        "vorbeikommen",
        "vorbeischauen",
        "persönlich vorbei",
        "persoenlich vorbei",
        "besuche sie",
        "besuchen sie",
    ),
    "unterschrift": (
        "unterschrift",
        "unterschreib",
        "unterzeichn",
        "handschriftlich",
        "rechtsverbindlich zeichn",
    ),
    "videokonferenz": (
        "videokonferenz",
        "videocall",
        "video-call",
        "bildschirmfreigabe",
    ),
}


class KanalgrenzeVerletzt(ValueError):
    """Der Text sagt einen Kanal zu, den die Rolle nicht einlösen kann."""


@dataclass
class Profile:
    role_id: str
    display_name: str
    sender: str
    transport: str
    role_line: str = ""
    accent: str = "#12626B"
    accent_deep: str = ""
    monogram: str = "•"
    tone: str = ""
    signature: str = ""
    legal_footer: str | None = None
    requires_legal_footer: bool = False
    darf_nicht_zusagen: tuple[str, ...] = ()
    kanal_signale: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: dict(KANAL_SIGNALE)
    )
    raw: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.accent_deep:
            self.accent_deep = self.accent


def _read_text_ref(ref: str | None) -> str | None:
    if not ref:
        return None
    p = Path(ref).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Signatur/Footer-Datei nicht gefunden: {p}")
    return p.read_text().rstrip("\n")


def load_registry(path: str | Path | None = None) -> dict:
    p = Path(path).expanduser() if path else DEFAULT_REGISTRY
    if not p.exists():
        raise FileNotFoundError(
            f"Rollen-Registry fehlt: {p} — anlegen (Vorlage: mail-roles.example.json)"
        )
    data = json.loads(p.read_text())
    if "roles" not in data or not isinstance(data["roles"], dict):
        raise ValueError(f"Registry {p} hat kein 'roles'-Objekt")
    return data


def resolve(
    role_id: str, path: str | Path | None = None, registry: dict | None = None
) -> Profile:
    """Rolle → validiertes Profil. Wirft bei unbekannter Rolle oder verletzter Governance."""
    reg = registry if registry is not None else load_registry(path)
    roles = reg["roles"]
    if role_id not in roles:
        raise ValueError(
            f"unbekannte Rolle '{role_id}' — bekannt: {', '.join(sorted(roles))}"
        )
    r = roles[role_id]
    missing = [k for k in _REQUIRED_FIELDS if not r.get(k)]
    if missing:
        raise ValueError(
            f"Rolle '{role_id}': Pflichtfelder fehlen: {', '.join(missing)}"
        )
    if r["transport"] not in VALID_TRANSPORTS:
        raise ValueError(
            f"Rolle '{role_id}': transport '{r['transport']}' ungültig "
            f"(erlaubt: {', '.join(sorted(VALID_TRANSPORTS))})"
        )

    # Kanal-Grenze: Registry darf die Signalwörter global überschreiben/ergänzen.
    signale = {k: tuple(v) for k, v in KANAL_SIGNALE.items()}
    for kanal, woerter in (reg.get("kanal_signale") or {}).items():
        signale[kanal] = tuple(w.lower() for w in woerter)
    gesperrt = tuple(r.get("darf_nicht_zusagen", ()) or ())
    unbekannt = [k for k in gesperrt if k not in signale]
    if unbekannt:
        # Ein Tippfehler im Kanalnamen darf nicht als "nichts gesperrt" durchgehen.
        raise ValueError(
            f"Rolle '{role_id}': unbekannte(r) Kanal/Kanäle in darf_nicht_zusagen: "
            f"{', '.join(unbekannt)} — bekannt: {', '.join(sorted(signale))}"
        )

    requires_footer = bool(r.get("requires_legal_footer", False))
    legal_footer = _read_text_ref(r.get("legal_footer_file"))
    # Governance-Enforcement (R1): Pflicht-Footer ohne Inhalt = Versand-Blocker.
    if requires_footer and not (legal_footer and legal_footer.strip()):
        raise ValueError(
            f"Rolle '{role_id}': requires_legal_footer=true, aber legal_footer_file "
            "fehlt oder ist leer — Versand blockiert (Compliance)."
        )

    return Profile(
        role_id=role_id,
        display_name=r["display_name"],
        sender=r["from"],
        transport=r["transport"],
        role_line=r.get("role_line", ""),
        accent=r.get("accent", "#12626B"),
        accent_deep=r.get("accent_deep", ""),
        monogram=r.get("monogram", "•"),
        tone=r.get("tone", ""),
        signature=_read_text_ref(r.get("signature_file")) or "",
        legal_footer=legal_footer,
        requires_legal_footer=requires_footer,
        darf_nicht_zusagen=gesperrt,
        kanal_signale=signale,
        raw=r,
    )


def finde_kanalzusagen(profile: Profile, *texte: str | None) -> list[tuple[str, str]]:
    """Fundstellen gesperrter Kanäle in den übergebenen Texten.

    Rückgabe: Liste von (kanal, gefundenes_signalwort), dedupliziert und stabil
    sortiert. Leere Liste = nichts zu beanstanden.
    """
    if not profile.darf_nicht_zusagen:
        return []
    hay = " \n ".join(t for t in texte if t).lower()
    if not hay.strip():
        return []
    treffer: list[tuple[str, str]] = []
    for kanal in profile.darf_nicht_zusagen:
        for wort in profile.kanal_signale.get(kanal, ()):
            if wort in hay and (kanal, wort) not in treffer:
                treffer.append((kanal, wort))
    return treffer


def pruefe_kanalgrenze(profile: Profile, *texte: str | None) -> None:
    """Pre-Send-Gate (#1481): bricht ab, wenn der Text einen gesperrten Kanal zusagt.

    Analog zu `requires_legal_footer` eine harte Bedingung, kein Hinweis — der
    reale Schaden am 2026-07-27 entstand genau dadurch, dass die Mail trotzdem
    hinausging. Es gibt bewusst KEIN Bypass-Flag: wer den Satz braucht, nimmt
    eine Rolle, die ihn einlösen kann.
    """
    treffer = finde_kanalzusagen(profile, *texte)
    if not treffer:
        return
    zeilen = "\n".join(f"  - {kanal}: Signalwort '{wort}'" for kanal, wort in treffer)
    raise KanalgrenzeVerletzt(
        f"Rolle '{profile.role_id}' ({profile.display_name}) kann folgende Kanäle "
        f"nicht einlösen, der Text sagt sie aber zu:\n{zeilen}\n"
        "→ Satz streichen oder eine Rolle wählen, die den Kanal bedienen kann "
        "(Kanal-Grenze aus der Rollen-Registry, Feld 'darf_nicht_zusagen')."
    )


GRUSSFORMELN = (
    "herzliche grüße",
    "viele grüße",
    "beste grüße",
    "mit freundlichen grüßen",
    "freundliche grüße",
    "liebe grüße",
    "grüße",
)

#: Eine Grußformel-ZEILE ist die Formel und nichts sonst — höchstens gefolgt von
#: Satzzeichen. Der frühere `str.startswith(GRUSSFORMELN)` prüfte nur den Anfang
#: und hielt darum auch "Grüße deine Frau von mir." für eine Grußformel; die
#: Folgezeile wurde daraufhin aus der Mail gelöscht (Retro-Befund 2026-07-31,
#: reproduziert). Ein Wortgrenzen-`\b` genügt NICHT: nach "Grüße" steht dort ein
#: Leerzeichen, die Grenze ist erfüllt. Nur der Vollzeilen-Match trennt die
#: Grußformel vom gleichlautenden Satzanfang.
_GRUSSFORMEL_ZEILE = re.compile(
    r"^(?:" + "|".join(re.escape(g) for g in GRUSSFORMELN) + r")[\s,.!;:]*$",
    re.IGNORECASE,
)


def _ist_grussformel(zeile: str) -> bool:
    """Ist diese Zeile eine Grußformel — und nichts anderes?"""
    return bool(_GRUSSFORMEL_ZEILE.match(zeile.strip()))


#: Akademische Titel und gängige Abkürzungen vor einem Namen — für den Vergleich
#: "steht dieser Name schon in der Signatur?" irrelevant.
_TITEL_PRAEFIX = re.compile(
    r"^(?:prof\.?|dr\.?|dipl\.-?\w*\.?|mag\.?|ing\.?)\s+", re.IGNORECASE
)


def _namenskern(zeile: str) -> str:
    """Zeile → vergleichbarer Namenskern: ohne Titel, ohne Funktionszusatz, klein.

    "Prof. Dr. Achim Dehnert · Leiter" und "Achim Dehnert" ergeben beide
    "achim dehnert" — genau das braucht der Dopplungs-Check unten.
    """
    kern = zeile.split("·")[0].strip()
    while True:
        gekuerzt = _TITEL_PRAEFIX.sub("", kern)
        if gekuerzt == kern:
            break
        kern = gekuerzt
    return " ".join(kern.lower().split())


def _ohne_doppelten_namen(text: str, signatur: str) -> str:
    """Namenszeile nach der Grußformel entfernen, wenn die Signatur sie ohnehin trägt.

    Realfall 2026-07-30: der Entwurf zeigte "Herzliche Grüße / Achim Dehnert" und
    darunter erneut "Prof. Dr. Achim Dehnert · Leiter" aus der Rollen-Signatur.

    Zwei Bedingungen müssen BEIDE gelten, damit kein Fließtext getroffen wird:
    die Zeile davor ist eine Grußformel, UND der Namenskern stimmt mit dem der
    ersten Signaturzeile überein. Ein "…habe mit Achim Dehnert gesprochen." am
    Textende bleibt damit unangetastet.
    """
    zeilen = text.rstrip().split("\n")
    if len(zeilen) < 2 or not signatur.strip():
        return text.rstrip()
    if not _ist_grussformel(zeilen[-2]):
        return text.rstrip()
    if _namenskern(zeilen[-1]) != _namenskern(signatur.strip().split("\n")[0]):
        return text.rstrip()
    return "\n".join(zeilen[:-1]).rstrip()


def text_mit_signatur(profile: Profile, text: str) -> str:
    """Hängt Signatur und ggf. Pflicht-Footer an einen reinen Textkörper.

    Eine Namenszeile direkt nach der Grußformel wird entfernt, wenn die Signatur
    denselben Namen trägt — sonst steht er zweimal untereinander.
    """
    teile = [_ohne_doppelten_namen(text, profile.signature)]
    if profile.signature:
        teile.append(profile.signature)
    if profile.legal_footer:
        teile.append(profile.legal_footer)
    return "\n\n".join(t for t in teile if t) + "\n"


def html_mit_signatur(profile: Profile, html: str) -> str:
    """Hängt Signatur und ggf. Pflicht-Footer an einen HTML-Körper (ohne --design).

    Realfall 2026-09-04: `draft_mail --role hnu --html-file …` legte vier
    HNU-Entwürfe ohne Signatur ab, drei davon wurden so gesendet — die Rolle
    signierte nur Klartext (`text_mit_signatur`) oder das Design, nicht den
    rohen HTML-Weg. Die Signatur kommt als eigener Block mit `pre-line`, damit
    ihre Zeilenumbrüche ohne harte <br> erhalten bleiben; Namen und Adressen
    werden HTML-escaped.
    """
    import html as _html

    teile = [html.rstrip()]
    if profile.signature:
        teile.append(
            '<div style="white-space:pre-line;">'
            + _html.escape(profile.signature.strip())
            + "</div>"
        )
    if profile.legal_footer:
        teile.append(
            '<div style="white-space:pre-line;font-size:smaller;">'
            + _html.escape(profile.legal_footer.strip())
            + "</div>"
        )
    return "\n".join(t for t in teile if t) + "\n"


def zerlege_klartext(text: str) -> dict:
    """Klartext-Mail → Bausteine für `render_email_html`.

    Der Klartext ist die Arbeitsform (so werden Entwürfe geschrieben und
    gegengelesen); das Rollen-Design braucht ihn zerlegt. Erste Zeile = Anrede;
    Grußformel und der Namensblock darunter fallen weg, weil `render_email_html`
    beides aus der Rolle setzt (Signatur/Footer) — sonst stünde der Name doppelt.
    Absatz-interne Zeilenumbrüche (Datums-/Punktlisten) bleiben erhalten.
    """
    zeilen = [z.rstrip() for z in text.strip().split("\n")]
    greeting = zeilen.pop(0).strip() if zeilen else ""
    closing = ""
    for i in range(len(zeilen) - 1, -1, -1):  # Grußformel von hinten suchen
        if _ist_grussformel(zeilen[i]):
            closing = zeilen[i].strip().rstrip(",")
            del zeilen[i:]
            break
    absaetze: list[str] = []
    puffer: list[str] = []
    for z in zeilen:
        if z.strip():
            puffer.append(z.strip())
        elif puffer:
            absaetze.append("\n".join(puffer))
            puffer = []
    if puffer:
        absaetze.append("\n".join(puffer))
    return {
        "greeting": greeting,
        "paragraphs": absaetze,
        "closing": closing or "Viele Grüße",
    }


_ROW = Template(
    '<tr><td style="padding:12px 16px;font-size:13.5px;color:#2A3138;$border">$label</td>'
    '<td align="right" style="padding:12px 16px;font-size:12.5px;color:$color;font-weight:600;$border">'
    "&#9679;&nbsp;$text</td></tr>"
)

_HTML = Template(
    """<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>$subject</title></head>
<body style="margin:0;padding:0;background:#F1EEE8;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F1EEE8;"><tr>
<td align="center" style="padding:32px 16px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;background:#FFFFFF;border-radius:14px;overflow:hidden;font-family:'Segoe UI',-apple-system,Roboto,Helvetica,Arial,sans-serif;">
<tr><td style="height:3px;line-height:3px;font-size:0;background:$accent;">&nbsp;</td></tr>
<tr><td style="padding:24px 40px 18px 40px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td width="46" valign="middle" style="width:46px;"><table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td align="center" valign="middle" style="width:34px;height:34px;background:$accent_soft;border-radius:8px;color:$accent_deep;font-weight:700;font-size:15px;">$monogram</td>
</tr></table></td>
<td valign="middle"><div style="font-size:13px;font-weight:600;color:#1E2428;">$display_name</div>
<div style="font-size:12px;color:#8A9099;">$sender</div></td>
<td valign="middle" align="right" style="font-size:11px;color:#8A9099;line-height:1.5;">$role_line</td>
</tr></table></td></tr>
<tr><td style="padding:0 40px;"><div style="height:1px;line-height:1px;font-size:0;background:#F0ECE4;">&nbsp;</div></td></tr>
<tr><td style="padding:22px 40px 6px 40px;">
<div style="font-size:11px;letter-spacing:1.6px;text-transform:uppercase;color:$accent;font-weight:600;margin-bottom:14px;">$eyebrow</div>
<p style="margin:0 0 15px 0;font-size:14.5px;line-height:1.62;color:#2A3138;">$greeting</p>
$paragraphs$status
<p style="margin:0 0 15px 0;font-size:14.5px;line-height:1.62;color:#2A3138;">$closing</p></td></tr>
<tr><td style="padding:6px 40px 30px 40px;">
<div style="height:1px;line-height:1px;font-size:0;background:#F0ECE4;margin-bottom:16px;">&nbsp;</div>
<div style="font-size:12.5px;line-height:1.55;color:#55606A;white-space:pre-line;">$signature</div>
$legal_footer</td></tr>
</table></td></tr></table></body></html>"""
)


def _hex_soft(accent: str) -> str:
    """Sehr helle Tönung des Akzents für die Monogramm-Fläche (deterministisch, ohne Deps)."""
    try:
        r = int(accent[1:3], 16)
        g = int(accent[3:5], 16)
        b = int(accent[5:7], 16)
    except (ValueError, IndexError):
        return "#E3EEEE"

    def mix(c: int) -> int:
        return round(c + (255 - c) * 0.88)

    return f"#{mix(r):02X}{mix(g):02X}{mix(b):02X}"


def render_email_html(
    profile: Profile,
    *,
    eyebrow: str,
    greeting: str,
    paragraphs: list[str],
    subject: str = "",
    status_rows: list[dict] | None = None,
    closing: str = "Viele Grüße",
) -> str:
    """Baut eine Outlook-feste HTML-Mail im Stil 'Klare Linie' mit den Rollen-Tokens."""
    # Zeilenumbruch INNERHALB eines Absatzes bleibt erhalten (Datums-/Punktlisten
    # kämen sonst als eine lange Zeile an) — erst escapen, dann <br> einsetzen.
    paras = "".join(
        f'<p style="margin:0 0 15px 0;font-size:14.5px;line-height:1.62;color:#2A3138;">{p}</p>'
        for p in (html.escape(x).replace("\n", "<br>") for x in paragraphs)
    )
    status_html = ""
    if status_rows:
        rows = []
        for i, row in enumerate(status_rows):
            color = _STATE_COLORS.get(row.get("state", "info")) or profile.accent
            border = "" if i == 0 else "border-top:1px solid #F0ECE4;"
            rows.append(
                _ROW.substitute(
                    label=html.escape(row["label"]),
                    text=html.escape(row.get("text", "")),
                    color=color,
                    border=border,
                )
            )
        status_html = (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:18px 0 20px 0;border:1px solid #E7E3DB;border-radius:10px;">'
            + "".join(rows)
            + "</table>"
        )
    footer_html = ""
    if profile.legal_footer:
        footer_html = (
            '<div style="margin-top:14px;padding-top:12px;border-top:1px solid #F0ECE4;'
            'font-size:10.5px;line-height:1.5;color:#A0A6AD;white-space:pre-line;">'
            + html.escape(profile.legal_footer)
            + "</div>"
        )
    return _HTML.substitute(
        subject=html.escape(subject or eyebrow),
        accent=profile.accent,
        accent_deep=profile.accent_deep,
        accent_soft=_hex_soft(profile.accent),
        monogram=html.escape(profile.monogram),
        display_name=html.escape(profile.display_name),
        sender=html.escape(profile.sender),
        role_line=html.escape(profile.role_line),
        eyebrow=html.escape(eyebrow),
        greeting=html.escape(greeting),
        paragraphs=paras,
        status=status_html,
        closing=html.escape(closing),
        signature=html.escape(profile.signature),
        legal_footer=footer_html,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Rollen-Registry: auflösen / HTML rendern")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list", help="Rollen auflisten")
    p_list.add_argument("--registry", default=None)
    p_show = sub.add_parser("show", help="ein Profil zeigen (validiert)")
    p_show.add_argument("role")
    p_show.add_argument("--registry", default=None)

    args = ap.parse_args()
    try:
        if args.cmd == "list":
            reg = load_registry(args.registry)
            for rid, r in reg["roles"].items():
                print(f"{rid:16} {r.get('from', ''):28} {r.get('transport', '')}")
        elif args.cmd == "show":
            prof = resolve(args.role, args.registry)
            print(f"Rolle       : {prof.role_id}")
            print(f"Absender    : {prof.sender}")
            print(f"Transport   : {prof.transport}")
            print(f"Akzent      : {prof.accent}")
            print(
                f"Footer-Pflicht: {prof.requires_legal_footer} "
                f"({'vorhanden' if prof.legal_footer else 'keiner'})"
            )
            print(
                "Kann NICHT zusagen: "
                + (", ".join(prof.darf_nicht_zusagen) or "— (keine Kanal-Grenze)")
            )
    except (FileNotFoundError, ValueError) as e:
        sys.exit(f"FEHLER: {e}")


if __name__ == "__main__":
    main()
