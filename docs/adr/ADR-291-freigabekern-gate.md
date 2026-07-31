---
status: proposed
decision_date: 2026-07-31
deciders: [Achim Dehnert]
consulted: [Claude Code, Ilja Lerch (SB-Neu, indirekt)]
informed: []
supersedes: []
amends: []
related: [ADR-233, ADR-290]
implementation_status: none
last_reviewed: 2026-07-31
staleness_months: 3
tags: [ci, governance, drift, guardrails, konvention]
---

# ADR-291: Freigabekern-Gate — anweisungstragende Dateien gegen den festgeschriebenen Stand

> **Nummern-Hinweis:** 291 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).

## Status-Hinweis

`proposed`. Setzt ADR-290 voraus — ohne deklarierte Steuerzone gibt es nichts zu prüfen.

**Nachtrag 2026-07-31 (ADR-290 Fassung 2, zwei externe Reviews):** Zwei Annahmen dieses
ADR sind durch die Überarbeitung von ADR-290 überholt und werden hier **noch nicht**
eingearbeitet — der externe Review zu ADR-291 selbst steht aus, und ich will die beiden
Runden nicht vermischen:

1. **Prüfung 2 ist nicht mehr nur SUGGEST-würdig, sondern normativ unterlegt.** ADR-290
   Regel 2 entscheidet den Status der verteilten Kopien: Sie tragen Zonenstatus nur,
   solange ihr `manifest.json` zur freigegebenen Repo-Quelle passt. Die hier als „echte
   Lücke" benannte CI-Schwäche (der Pfad `~/.claude/` existiert in CI nicht) wird dadurch
   nicht kleiner — aber der Vergleich gegen das Manifest ist jetzt die *definierte*
   Autoritätsbedingung statt eines Behelfs.
2. **Vor dem Marker-Scanner steht ein heuristikfreier Ladelisten-Check** (ADR-290
   Option C'): prüfen, was automatisch in einen Agentenkontext geladen wird, gegen
   Loader/Manifest — per Konstruktion ohne Fehlalarme und damit ohne Baseline-Runde
   sofort gating-fähig. Beide externen Reviewer schlugen das unabhängig vor. Die
   Umsetzungs-Reihenfolge unten (Schritt 3: „Prüfung 2 SUGGEST, Baseline über ≥5 Repos")
   ist dadurch voraussichtlich zu ändern.

Beides gehört in eine Fassung 2 dieses ADR, **nach** seinem eigenen externen Review.

## Context

Wir haben ein wiederkehrendes, belegtes Problem: **Kanon-Entscheidungen driften weg, weil
nichts sie erzwingt.** Die Memory-Historie nennt es dreimal unabhängig:

| Lehre | Kern |
|---|---|
| `canon-decision-needs-enforcement-gate` | Banner ohne CI-Gate driftet |
| `policy-edits-belong-in-platform-pr-not-pinned` | Policy-Edits am verteilten Ort statt an der Quelle |
| `ruleset-bypass-durable-artifact` | Bypass ohne Audit-Spur |

Dazu kommt ein vierter, jüngerer Fall: `generate.py --target` hat am 2026-07-30 das
komplette Lane-Verzeichnis `~/.claude` ausgetauscht, und `--allow-live` prüfte nur
Gleichheit, nicht Identität des Ziels (#1558).

Das gemeinsame Muster: Die **Quelle** der handlungsleitenden Texte (`policies/`,
`skills/`, `.windsurf/workflows/`, `CLAUDE.md`) und ihre **verteilten Kopien** unter
`~/.claude/` können auseinanderlaufen, ohne dass jemand es merkt. Die Kopien sind das,
was der Agent tatsächlich liest.

**Vergleichsfall (Fremdsystem).** SB-Neu prüft seine Steuerzone bei **jedem** Werkzeuglauf:

- Liegt alles unterhalb `steuer\` byte-gleich im festgeschriebenen Stand?
- Trägt jede Änderung einen korrespondierenden Eintrag im Freigabejournal?
- Ist das Journal **anfügungsfest** — stehen alle je angefügten Einträge auch im Commit?

Mit **eigenem Rückgabewert**, der vor allen anderen Befunden steht: *„dieses Urteil stammt
nicht von dem Werkzeug, das die Versionskontrolle trägt."* Ich habe das am 2026-07-31
scharf laufen lassen — es funktioniert, auch unter Linux.

## Decision

**Ein CI-Gate prüft bei jedem PR, dass die Steuerzone (ADR-290) im festgeschriebenen Stand
liegt und ihre verteilten Kopien damit übereinstimmen.**

Drei Prüfungen, in dieser Rangfolge:

| # | Prüfung | Bei Verletzung |
|---|---|---|
| 1 | **Versionsbindung** — jede Datei der Steuerzone liegt im Commit, byte-gleich zum Arbeitsbaum | hart rot |
| 2 | **Distributionsgleichheit** — `~/.claude/{skills,commands}` stimmt mit dem Quellstand überein (Manifest-Hash gegen `manifest.json`) | SUGGEST zunächst |
| 3 | **Anfügungsfestigkeit** — Änderungen an `policies/` erscheinen im PR-Diff, nicht nur am verteilten Ort | hart rot |

Prüfung 2 startet **SUGGEST / non-gating** nach `repo-health-rule-discipline`: neue Regeln
gehen erst scharf, wenn sie über mindestens fünf Repos null Fehlalarme produziert haben.
Prüfung 1 und 3 sind deterministisch-strukturell und können sofort gaten.

**Vorrangregel, übernommen von SB-Neu:** Meldet Prüfung 1 eine Abweichung, steht dieser
Befund **vor** allen anderen — ein Lauf, dessen eigene Regelbasis nicht im
festgeschriebenen Stand liegt, trifft über nichts anderes ein belastbares Urteil.

## Options considered

| Option | Beschreibung | Konsequenz | Verdikt |
|---|---|---|---|
| **A — Status quo** | Regel in Memory + Policy, keine Prüfung | Nichts zu bauen. Das Muster ist viermal aufgetreten und wird wieder auftreten. | verworfen |
| **B — Nur Versionsbindung** | Prüfung 1 allein | Billig, sofort scharf. Fängt den häufigsten Fall (Edit an der Quelle ohne Commit) — aber **nicht** den teuersten (#1558: Drift zwischen Quelle und Kopie). | verworfen als alleinige Maßnahme |
| **C — Alle drei, gestaffelt** (gewählt) | 1 und 3 gatend, 2 SUGGEST | Deckt beide Fälle. Kostet einen Job und eine Baseline-Runde für Prüfung 2. | **gewählt** |
| **D — Freigabejournal wie SB-Neu** | Zusätzlich Pflicht-Eintrag je Zonenänderung | Vollständigster Nachweis. Für uns aber Doppelung: Der PR **ist** unser Freigabejournal — mit Review, Zeitstempel und Signatur. | verworfen (Doppelung) |

Option D ist der Punkt, an dem sich unsere Systeme legitim unterscheiden: SB-Neu hat kein
GitHub und musste sich das Journal selbst bauen. Wir haben es.

## Consequences

**Positiv.** Vier belegte Drift-Vorfälle bekommen erstmals einen mechanischen Fänger. Die
Aussage „das Gate war grün" gewinnt Bedeutung, weil die Regelbasis des Gates selbst
mitgeprüft wird.

**Negativ / Kosten.** Ein CI-Job mehr auf jedem PR. Prüfung 2 braucht eine Baseline-Runde,
bevor sie scharf geht — bis dahin ist sie Lärm mit Nutzen nahe null. Und ein hartes Gate
auf `policies/` erhöht die Reibung genau dort, wo bisher am schnellsten editiert wurde;
das ist beabsichtigt, aber spürbar.

**Risiko, ausdrücklich.** Prüfung 2 vergleicht gegen `~/.claude/` — einen Pfad **außerhalb
des Repos**, der je Maschine anders aussieht. In CI existiert er gar nicht. Die Prüfung
kann dort also nur gegen das mitgelieferte `manifest.json` laufen, nicht gegen den echten
Live-Stand. **Damit prüft sie in CI etwas schwächeres als lokal** — das ist eine echte
Lücke und kein Detail. Sie ist der Hauptgrund, warum Prüfung 2 SUGGEST startet.

**Komplexitäts-Bilanz.** Fügt hinzu (ein Workflow-Job, ein Prüfskript), entfernt nichts.
Begründung des Zuwachses: Er ersetzt vier Memory-Zeilen, die dasselbe Problem beschreiben,
ohne es zu verhindern — Zeilen, die bei jedem Sessionstart Kontext kosten und trotzdem
viermal nicht gegriffen haben.

## Umsetzungs-Reihenfolge

| Schritt | Inhalt | Gate |
|---|---|---|
| 1 | ADR-290 accepted (Zone deklariert) | Owner |
| 2 | Prüfskript + Prüfung 1 und 3 gatend | grüner Lauf auf einem echten PR |
| 3 | Prüfung 2 SUGGEST, Baseline über ≥5 Repos | 0 Fehlalarme nachgewiesen |
| 4 | Prüfung 2 gatend | Owner |

Schritt 2 verlangt ausdrücklich einen **echten Lauf in CI**, kein lokales Skriptergebnis —
Gate `autonomous-no-human-review` und `claim-before-cheapest-check`.

## Herkunft

Analyse des Fremdsystems SB-Neu am 2026-07-31. Der dort gebaute Nachweis
(`steuer\werkzeug\pruefen.py`, Prüfung 5 „Freigabekern") lief im Rahmen dieser Analyse
einmal scharf unter Linux und bestätigte seine Zusagen; Details in
`~/.claude/boards/sb-neu-bewertung.md`.
