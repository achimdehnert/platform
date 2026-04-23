"""Shared constants for doc_templates package."""

from collections import OrderedDict

# ── AI Source Document Types ────────────────────────────────────
# Single source of truth — used by:
#   - Template editor JS (via json_script)
#   - Instance editor (source labels)
#   - LLM prefill (prompt context)

AI_SOURCE_TYPES: OrderedDict[str, str] = OrderedDict([
    ("sds", "Sicherheitsdatenblätter (SDS)"),
    ("bedienungsanleitung", "Bedienungsanleitungen"),
    ("standortdaten", "Standort- und Gebäudedaten"),
    ("cad", "CAD-Zeichnungen / Anlagenpläne"),
    ("zonenplan", "Zonenpläne / Ex-Zonen"),
    ("gefaehrdungsbeurteilung", "Gefährdungsbeurteilungen"),
    ("betriebsanweisung", "Betriebsanweisungen"),
    ("pruefbericht", "Prüfberichte / Protokolle"),
    ("rechtliche_grundlagen", "Rechtliche Grundlagen / Normen"),
    ("wartungsplan", "Wartungs- und Instandhaltungspläne"),
    ("risikobewertung", "Risikobewertungen"),
    ("brandschutz", "Brandschutzkonzepte"),
])

# Short labels for compact display in document editor
AI_SOURCE_SHORT_LABELS: dict[str, str] = {
    "sds": "SDS",
    "bedienungsanleitung": "Bedienungsanl.",
    "standortdaten": "Standortdaten",
    "cad": "CAD",
    "zonenplan": "Zonenpläne",
    "gefaehrdungsbeurteilung": "GBU",
    "betriebsanweisung": "Betriebsanw.",
    "pruefbericht": "Prüfberichte",
    "rechtliche_grundlagen": "Normen",
    "wartungsplan": "Wartungsplan",
    "risikobewertung": "Risikobew.",
    "brandschutz": "Brandschutz",
}

# JS-compatible format for template editor
AI_SOURCE_TYPES_JS = [
    {"value": k, "label": v} for k, v in AI_SOURCE_TYPES.items()
]


# ── Field Types ─────────────────────────────────────────────────

FIELD_TYPES = [
    {"value": "textarea", "label": "Freitext", "icon": "📝"},
    {"value": "table", "label": "Tabelle", "icon": "📊"},
    {"value": "text", "label": "Kurztext", "icon": "✏️"},
    {"value": "number", "label": "Zahl", "icon": "#"},
    {"value": "date", "label": "Datum", "icon": "📅"},
    {"value": "boolean", "label": "Ja/Nein", "icon": "☑"},
]


# ── LLM Token Limits per Field Type (#5) ───────────────────────

MAX_TOKENS_BY_FIELD_TYPE: dict[str, int] = {
    "textarea": 1500,
    "table": 2000,
    "text": 200,
    "number": 50,
    "date": 50,
    "boolean": 10,
}

DEFAULT_MAX_TOKENS = 500
