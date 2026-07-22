# Agent Handover — Session-Log (append-only)

**Zweck:** chronologischer Mitschrieb der Session-Stände. Jede Session hängt ihren
Block **unten** an. Bestehende Einträge werden **nie** geändert, umsortiert oder
gelöscht — auch nicht, wenn sie sich im Nachhinein als falsch erweisen; dann kommt
die Korrektur als **neuer** Eintrag darunter.

**Warum so streng:** Diese Datei trägt `merge=union` (siehe `.gitattributes`).
Bei konkurrierenden Änderungen nimmt git beide Seiten auf, statt einen Konflikt zu
melden — deshalb können zwei parallele Sessions gleichzeitig anhängen, ohne sich zu
blockieren. Diese Gutartigkeit hängt vollständig daran, dass nur angehängt wird:
wird eine bestehende Zeile geändert, mischt Union alte und neue Fassung stillschweigend
ineinander. Der CI-Check `handover-append-only` setzt das durch.

**Was hier NICHT hingehört:** die `## Prioritäten`-Tabelle und alles, was laufend
umgeschrieben wird. Das bleibt in [`AGENT_HANDOVER.md`](AGENT_HANDOVER.md), wo
Konflikte laut bleiben — `session-ende` Phase 0c schreibt dort ausdrücklich vor,
erledigte Zeilen zu entfernen und neu zu nummerieren.

**Gemessene Grundlage (2026-07-22):** GitHub wendet `merge=union` serverseitig
**nicht** an — ein zweiter PR bleibt `CONFLICTING`, auch „Update branch" hilft nicht.
Der Nutzen liegt allein in der *lokalen* Auflösung: `git pull` im Worktree führt beide
Stände still zusammen, danach genügt ein Push. Aus „von Hand auflösen" wird „pullen
und pushen" — mehr verspricht dieser Arm nicht (Beleg: Kommentar an PR #1319).

**Kosmetische Nebenwirkung, kein Fehler:** Beim Zusammenführen zweier paralleler
Anhänge kann die Leerzeile zwischen den Blöcken wegfallen (gemessen 2026-07-22) —
die Einträge selbst bleiben vollständig und in Reihenfolge. Nicht nachträglich
„aufräumen": das wäre eine Änderung an bestehenden Zeilen und damit genau der Bruch,
den der Check verhindert.

**Ältere Stände:** [`AGENT_HANDOVER.md`](AGENT_HANDOVER.md) (aktueller + vorheriger
Stand) und [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md) (alles davor).
Dieser Log beginnt bewusst leer statt mit einer Migration: bestehende Blöcke zu
verschieben wäre selbst genau die Art Umschreibung, die hier verboten ist.

---

<!-- Neue Einträge ab hier anhängen. Format:

## <YYYY-MM-DD HH:MM> — <Session-Kürzel> — <Ein-Zeilen-Thema>

- was erledigt wurde (PR/Issue verlinkt)
- was offen bleibt
- was NICHT verifiziert ist

Nichts oberhalb dieser Zeile anfassen. -->
