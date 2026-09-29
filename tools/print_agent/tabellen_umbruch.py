"""Seitenumbruch-Stil fuer Tabellen (Realfall 2026-09-29).

`base.css` hielt jede Tabelle mit `page-break-inside: avoid` zusammen. Eine
Tabelle mit zehn Zeilen und Fliesstext in vier Spalten passte nicht mehr auf
den Rest von Seite 2 und wanderte komplett auf Seite 3 — Seite 2 blieb zur
Haelfte leer (Marktpreis-Papier, 8 Seiten, davon eine halbe weiss).

Regel jetzt:
- Lange Tabellen fliessen ueber die Seitengrenze; die Kopfzeile wiederholt sich
  (CSS `thead { display: table-header-group }`), keine Zeile wird zerschnitten.
- Kurze Tabellen (bis KURZE_TABELLE_MAX_ZEILEN Datenzeilen) bleiben wie bisher
  zusammen, weil eine zwei- oder dreizeilige Tabelle ueber zwei Seiten
  schlechter liest als ein kleiner Weissraum davor.

Die Schwelle steht hier als Konstante und nicht im CSS, weil CSS die Zeilenzahl
nicht kennt. Das Modul ist bewusst importfrei (kein weasyprint), damit die Tests
ohne PDF-Engine laufen.
"""

from __future__ import annotations

import re

# Datenzeilen (tbody), bis zu denen eine Tabelle als Block zusammenbleibt.
KURZE_TABELLE_MAX_ZEILEN = 6

# Klasse, die base.css mit `page-break-inside: avoid` belegt.
KLASSE_ZUSAMMENHALTEN = "keep-together"

_TABLE_RE = re.compile(r"<table(?P<attrs>[^>]*)>(?P<body>.*?)</table>", re.DOTALL | re.IGNORECASE)
_TR_RE = re.compile(r"<tr\b", re.IGNORECASE)
_THEAD_RE = re.compile(r"<thead\b.*?</thead>", re.DOTALL | re.IGNORECASE)
_CLASS_RE = re.compile(r'\sclass="(?P<classes>[^"]*)"', re.IGNORECASE)


def datenzeilen(table_html: str) -> int:
    """Zahl der Zeilen ausserhalb von <thead>."""
    ohne_kopf = _THEAD_RE.sub("", table_html)
    return len(_TR_RE.findall(ohne_kopf))


def _mit_klasse(attrs: str, klasse: str) -> str:
    m = _CLASS_RE.search(attrs)
    if not m:
        return f'{attrs} class="{klasse}"'
    vorhandene = m.group("classes").split()
    if klasse in vorhandene:
        return attrs
    neu = " ".join(vorhandene + [klasse])
    return attrs[: m.start()] + f' class="{neu}"' + attrs[m.end() :]


def markiere_kurze_tabellen(body_html: str, max_zeilen: int = KURZE_TABELLE_MAX_ZEILEN) -> str:
    """Haengt KLASSE_ZUSAMMENHALTEN an jede Tabelle mit hoechstens `max_zeilen` Datenzeilen.

    Laengere Tabellen bleiben unveraendert und fliessen per CSS ueber Seiten.
    """

    def ersetze(m: re.Match) -> str:
        attrs, body = m.group("attrs"), m.group("body")
        if datenzeilen(body) > max_zeilen:
            return m.group(0)
        return f"<table{_mit_klasse(attrs, KLASSE_ZUSAMMENHALTEN)}>{body}</table>"

    return _TABLE_RE.sub(ersetze, body_html)
