"""Profil-abgeleitete Voreinstellungen des Print-Agents (#1297, zweiter Befund).

Reine Funktionen über dem geladenen Profil-Dict — **bewusst importfrei** (keine
``yaml``/``weasyprint``/``litellm``), damit sie aus ``tools/tests/`` prüfbar
sind. ``tools/print_agent/tests/`` läuft in keinem Workflow; eine Regel, die
nur dort getestet wird, ist praktisch ungegatet (siehe ``llm_gate.py``).

Hintergrund: ``--profile iil-extern`` erzeugt Angebote und Verträge. Zwei
Voreinstellungen waren dafür falsch:

1. Die LLM-Anreicherung lief auch dort — ein KI-generierter Zusammenfassungs-
   Kasten über die eigenen Vertragsbedingungen, in einem Dokument mit
   Unterschriftsfeld. Der beobachtete Text war zudem sachlich schief.
2. Ohne ``**Typ:**`` im Body trug ein Angebot den Untertitel
   „Internes Dokument", weil jedes Profil hart auf ``meta_template="db"``
   lief und dessen Default für interne Dokumente gedacht ist.
"""

_EXTERN = "extern"
_INTERN = "intern"


def audience(profile: dict) -> str:
    """``"extern"`` oder ``"intern"`` — wer das Dokument lesen soll.

    Vorrang hat ein ausdrückliches ``audience:`` im Profil. Sonst wird
    ``authorship.recipient`` gelesen (``iil-extern.yaml`` trägt dort
    „extern (Kunden, Stakeholder, Konzerne)"). Im Zweifel ``intern`` —
    die vorsichtigere Annahme, weil sie nichts nach außen lockert.
    """
    explicit = str(profile.get("audience", "")).strip().lower()
    if explicit in {_EXTERN, _INTERN}:
        return explicit
    recipient = str(profile.get("authorship", {}).get("recipient", "")).strip().lower()
    return _EXTERN if recipient.startswith(_EXTERN) else _INTERN


def enrichment_enabled(profile: dict) -> bool:
    """Soll die LLM-Anreicherung für dieses Profil standardmäßig laufen?

    Ausdrückliches ``llm_enrichment:`` im Profil gewinnt. Sonst: extern aus,
    intern an. Die CLI (``--enrich``/``--no-enrich``) sticht beides.
    """
    explicit = profile.get("llm_enrichment")
    if isinstance(explicit, bool):
        return explicit
    return audience(profile) != _EXTERN


def default_doc_type(aud: str, meta_template: str) -> str:
    """Untertitel-Typ, wenn das Dokument keinen ``**Typ:**`` angibt.

    Für extern gerichtete Dokumente wird **kein** Typ geraten: ein falsches
    Etikett („Internes Dokument" auf einem Angebot, oder „Angebot" auf einem
    Bericht) ist schlechter als gar keines — die Zeile trägt dann nur das
    Datum. Intern bleibt das bisherige Verhalten unverändert.
    """
    if aud == _EXTERN:
        return ""
    return "Internes Dokument" if meta_template == "db" else "Angebot"
