# Vorschlagsregister (ADR-308 §4.2, B3)

Jedes Sandbox-Ergebnis bekommt hier eine stabile ID und einen Zustand. Zustände:
`geprüft` (Erkenntnisauftrag, Bericht auf dem Host bestanden), `eingereicht` (Werkstück,
PR offen), `angenommen`, `abgelehnt`, `zurückgezogen`. Frist für Werkstücke: eine
Review-Sitzung nach Einreichung; danach zählt ein offenes Werkstück im Nenner von B3.

Lauf-Verzeichnisse liegen auf dem Host unter `~/sandbox-laeufe/`.

| ID | Datum | Klasse | Spiegel | Auftrag | Zustand | Frist | Lauf | Ergebnis |
|---|---|---|---|---|---|---|---|---|
| P1 | 2026-10-06 | Erkenntnisauftrag | platform | Hook-Inventar: Sperr-Test je Hook | geprüft | – | 2026-10-06T052428-3225156 | [platform#3785](https://github.com/achimdehnert/platform/issues/3785#issuecomment-6011205466) |
| P2 | 2026-10-06 | Erkenntnisauftrag | dev-hub | Platform Agents ohne Hauptpfad-Test | geprüft | – | 2026-10-06T052649-3242222 | [dev-hub#469](https://github.com/achimdehnert/dev-hub/issues/469) |
| P3 | 2026-10-06 | Erkenntnisauftrag | mcp-hub | Dependabot-Abdeckung | geprüft | – | 2026-10-06T052842-3262661 | [mcp-hub#304](https://github.com/achimdehnert/mcp-hub/issues/304) |
| E4 | 2026-10-06 | Erkenntnisauftrag | platform | Block-Modus-Schalter bei zehn Hooks | geprüft | – | 2026-10-06T072552-3890270 | kein Schalter bei allen zehn; [platform#3785](https://github.com/achimdehnert/platform/issues/3785) |
| W1 | 2026-10-06 | Werkstück | mcp-hub | Dependabot um docker, docker-compose, rag_mcp erweitern | angenommen | – | 2026-10-06T072704-3897241 | [mcp-hub#305](https://github.com/achimdehnert/mcp-hub/pull/305) gemergt 2026-10-06 `adcdda9`, Owner-Wort |
| W2 | 2026-10-06 | Werkstück | dev-hub | Hauptpfad-Test `mail_ingest` (dev-hub#469) | zurückgezogen | – | 2026-10-06T083331-283576 | Doppel: Test seit dev-hub@`e62cd48` upstream, Kopie war 8 Commits alt; Fix in `sandbox.sh` |
