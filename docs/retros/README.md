# Session-Retro-Reports (durable)

Kanonische, git-versionierte Heimat der `/session-retro`-Reports (KONZ-platform-010).
`tools/retro_kpis.py` liest den Längsschnitt standardmäßig aus **diesem** Verzeichnis.

Zuvor lagen die Reports in `~/shared/` (ungetrackt, ungebackupt) — das machte `~/shared`
für eine benötigte Funktion nicht-wegwerfbar. Seit KONZ-010 ist die durable Heimat hier;
`~/shared` ist reines Wegwerf-Scratch (siehe `~/shared/README.md`).
