# Sunset-Ledger (KONZ-038 §5.4 / K3)

**Append-only Ereignis-Log.** Jede Sunset-Entscheidung und jede Rücknahme wird hier
angehängt — nie editiert, nie gelöscht. Das Ledger ist bewusst **keine Regel-Quelle**
(A/B/C-Labels leben ausschließlich in Memory-/Policy-Frontmatter, §6 AD-3) und damit
keine SSoT-Kollision.

## Regeln (aus KONZ-038, hier nur wiederholt)

- Eintragspflicht: jeder kontrollierte Auslass-Test (Pfad 1), jeder Default-Expiry-Verfall
  (Pfad 2) und **jede Rücknahme** (= realer Schadensfall) — mit Regel-Referenz + Begründung
  (EXT2-M28-6).
- **Lernphase (EXT2-AD-6, symmetrisch kalibriert):** die ersten 2 Rücknahmen gelten als
  deklarierte Lernphase. Danach: **>30 % Rücknahmen bei N≥10** ⇒ Sunset-Pfad eingefroren,
  Owner-Entscheid nötig.
- Typ B/C sind von beiden Sunset-Pfaden ausgenommen und tauchen hier nie auf.

## Zählerstand

| Zähler | Stand | Stand vom |
|---|---|---|
| Sunset-Ereignisse (N) | 0 | 2026-08-02 |
| Rücknahmen | 0 | 2026-08-02 |
| Lernphasen-Zähler | 0/2 | 2026-08-02 |

*(Zählerstand wird je Ritual-Lauf aktualisiert — das ist die einzige erlaubte
Nicht-Append-Änderung in dieser Datei.)*

## Einträge (append-only, neueste unten)

| Datum | Regel (Quelle/Slug) | Ereignis | Begründung / Beleg |
|---|---|---|---|

*Noch keine Einträge — Ledger angelegt 2026-08-02 (Ritual-Lauf-1-Vorbereitung, #1640).*
