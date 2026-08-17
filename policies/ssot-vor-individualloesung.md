# Policy: SSoT vor Individuallösung
<!-- rule_class: A | assessed_with: claude-opus-5 | reassess_by: 2026-12-01 -->

**Trigger words:** ssot, single source of truth, hardcod, hartcod, hartkod, hart kodiert, magic number, konstante, individuall, einzellös, einzelloes, sonderfall, sonderweg, extralocke, duplizier, kopieren, symmetrie, elegante lös, elegante loes, punktlös, punktloes, workaround

<!-- Trigger absichtlich als STÄMME, nicht als ganze Wörter: der Hook prüft per
     Substring (`wort in prompt`). „hardcoded" verfehlt „hardcoden", und
     „individuallösung" verfehlt das umlautlose „Individualloesung" — beides
     gemessen beim Anlegen dieser Datei. Ein Trigger, der Schreibweisen matcht
     statt Begriffe, ist genau der Fehler, gegen den diese Policy geschrieben
     ist. Beim Ergänzen weiterer Trigger: Stamm wählen, dann beide Schreibweisen
     gegen `wort in prompt.lower()` gegenprüfen. -->


## Rule (User-Weisung 2026-08-17, org-weit)

**SSoT so oft wie sinnvoll. Individuallösung nur im begründeten Notfall.
Datenbank/SSoT vor Hardcoding.**

Der Reflex, die vorliegende Instanz zu reparieren, ist stärker als die Frage
nach der Struktur, die Instanzen erzeugt. Diese Policy setzt die Frage **vor**
die Umsetzung — nicht in den Retro danach.

## Die drei Fragen vor dem Umsetzen

Sie kosten zusammen weniger als eine Minute und werden **vor** dem ersten Edit
gestellt, nicht beim Review:

1. **Instanz oder Klasse?** Behebe ich diesen Fall — oder das, was ihn
   erzeugt? Wenn nur den Fall: warum ist das hier richtig?
2. **Gibt es eine zweite Stelle?** Beantwortet irgendwo sonst derselbe Code
   dieselbe Frage? Wenn ja: warum zwei Antworten? Die Doppelstelle ist der
   Befund, nicht der Fix an einer von beiden.
3. **Ist der Wert ein Vertrag?** Ein Literal, auf das sich jemand anderes
   verlassen muss, ist keine Konstante — es ist eine Schnittstelle. Verträge
   werden **deklariert** (Env, Config, Registry, DB), nicht wiederholt.

**Fällt eine der drei Antworten zugunsten der Individuallösung aus, gehört die
Begründung in denselben Commit/PR** — ein Satz genügt, aber er muss dastehen.
Eine unbegründete Individuallösung ist ein Befund, kein Ergebnis.

## Rangfolge

| Rang | Form | Wann |
|---|---|---|
| 1 | **DB / Registry / SSoT-Datei** | Der Wert ändert sich, wird von mehr als einer Stelle gelesen, oder ist ein Vertrag |
| 2 | **Deklarierte Konfiguration** (Env, `env:`-Block, Input mit Default) | Der Wert ist umgebungsabhängig oder muss nach außen sichtbar sein |
| 3 | **Eine benannte Konstante an einer Stelle** | Der Wert ist stabil und rein intern |
| 4 | **Literal, mehrfach** | Nur mit Begründung im Commit — das ist der begründete Notfall |

## Warum das eine Policy ist und keine Stilfrage

Drei kommandobelegte Fälle aus **einem** Arbeitstag
([platform#2037](https://github.com/achimdehnert/platform/issues/2037)):

- **Ein Zwei-Zeilen-Fix kostete 37 PRs.** `iilgmbh/shared-ci` hat keinen
  beweglichen Major-Tag; ~30 Consumer pinnen Punktversionen. Die Flotte wurde
  von Hand synchronisiert, der Mechanismus, der sie synchron *hält*, fehlt
  weiter. Am Morgen liefen elf `_ci-python`-Versionen nebeneinander.
- **15 hartkodierte Zugangsdaten, davon 2 als Vertrag deklariert.** In
  `_ci-python.yml` stehen `POSTGRES_USER`/`PASSWORD`/`DB` je **fünfmal**
  wörtlich, ohne `env:`-Block; an die Test-Schritte exportiert werden nur
  `HOST` und `PORT`. Die drei anderen Werte muss jedes Consumer-Repo
  **erraten** — dreimal am selben Tag von Hand nachgebaut
  (billing-hub, trading-hub, kopiert aus frist-hub).
- **Geschwister-Schritte mit verschiedener Fehlerbehandlung.** Der
  Integrationsschritt trug einen Guard, der Unit-Schritt daneben keinen; im
  Nachbarmodul prüft ein Schritt korrekt auf `pyproject.toml`, der andere nur
  auf Verzeichnis-Existenz — und nimmt den defekten Pfad per Namen aus.

Gemeinsame Form: **der Fix adressiert die Instanz, nicht die Struktur.**

## Abgrenzung — wann die Individuallösung richtig ist

Diese Policy ist kein Auftrag zur Vorab-Abstraktion. Der begründete Notfall
existiert und ist ausdrücklich erlaubt:

- **Ein einziger Aufrufer, keine Aussicht auf einen zweiten** — eine SSoT für
  einen Leser ist Overhead, kein Gewinn.
- **Die Verallgemeinerung kostet mehr Kopplung, als sie Duplikation spart** —
  zwei ähnliche Stellen sind nicht automatisch dieselbe Stelle.
- **Zeitdruck bei einem Prod-Vorfall** — dann Individuallösung **plus**
  Tracking-Artefakt im selben Zug (Hausregel: bewusst Ausgelassenes bekommt
  ein Artefakt, „steht im PR-Text" zählt nicht).

Der Unterschied zur schlechten Individuallösung ist **nicht** die Form,
sondern ob die Begründung dasteht.

## Anti-Patterns

- ❌ Denselben Literalwert an N Stellen pflegen, den ein anderer kennen muss.
- ❌ Eine Doppelstelle „reparieren", indem man die falsche der beiden angleicht,
  ohne zu fragen, warum es zwei gibt.
- ❌ Eine Flotte von Hand synchronisieren, ohne den Mechanismus zu benennen,
  der sie auseinanderlaufen ließ.
- ❌ Individuallösung ohne Begründungssatz im Commit/PR.
- ❌ Umgekehrt: alles verallgemeinern, was zweimal vorkommt — die Policy
  verlangt die **Frage**, nicht immer die Abstraktion.

## Wo die Regel greift

- **Vor dem ersten Edit** einer Umsetzung (die drei Fragen).
- **Im Review** — eine Individuallösung ohne Begründungssatz ist ein
  Review-Befund.
- **In `/session-retro`** wird sie nachträglich als Slug
  `gate-matches-spelling-not-substance` bzw. als Punktlösungs-Befund erfasst;
  das ist der Fang **nach** dem Merge und ausdrücklich die schlechtere Stelle.

## Precedence

Repo-`CLAUDE.md` > Orchestrator-MCP > diese Datei. Widerspricht ein Repo dieser
Policy bewusst, gehört der Grund in dessen `CLAUDE.md` — nicht in eine
stillschweigende Ausnahme.
