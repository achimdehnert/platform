# Policy: SSoT vor Individuallösung
<!-- rule_class: A | assessed_with: claude-opus-5 | reassess_by: 2026-12-01 -->

**Trigger words:** ssot, single source of truth, hardcod, hard cod, hartcod, hartkod, hart cod, hart kod, magic number, konstante, individuall, individuell, einzellös, einzelloes, einzelfall, sonderfall, sonderweg, sonderreg, extralocke, punktlös, punktloes, punktuell, duplizier, redundan, kopieren, symmetrie, elegante lös, elegante loes, workaround

<!-- Trigger als STÄMME über die WORTKLASSE, nicht als Liste beobachteter
     Schreibweisen. Der Hook prüft per Substring (`wort in prompt.lower()`),
     also deckt ein Stamm alle Beugungen ab — aber nur die, an deren Wortstamm
     man gedacht hat.
     Zweimal gemessen und beide Male zu eng: (1) „hardcoded" verfehlte
     „hardcoden", „individuallösung" das umlautlose „Individualloesung";
     (2) der Fix darauf verfehlte weiterhin „individuell lösen" (e statt a),
     „punktuelle Lösung", „Sonderregel" und „hart codiert" (c statt k) —
     gefunden von einem Prüfer mit fremdem Kontext, nicht von mir.
     Lehre: nach dem Ergänzen NICHT die zwei gemeldeten Varianten testen,
     sondern die Wortklasse durchdeklinieren (Verb/Adjektiv/Substantiv, c/k,
     Umlaut/ae-oe-ue) — sonst patcht man das Symptom, das gerade vorlag.
     Das ist exakt der Fehler, gegen den diese Policy geschrieben ist; er ist
     ihr hier zweimal selbst unterlaufen. -->


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

Drei kommandobelegte Fälle aus **einem** Arbeitstag, Belege in
[platform#2037](https://github.com/achimdehnert/platform/issues/2037):

- **37 PRs für einen Zwei-Zeilen-Fix** — `shared-ci` hat keinen beweglichen
  Major-Tag, ~30 Consumer pinnen Punktversionen (11 Versionen gleichzeitig live).
- **15 hartkodierte Zugangsdaten, davon 2 als Vertrag exportiert** — die drei
  anderen muss jedes Consumer-Repo erraten; dreimal am selben Tag von Hand nachgebaut.
- **Geschwister-Schritte mit verschiedener Fehlerbehandlung** — der Fix repariert
  die falsche der beiden Stellen, statt zu fragen, warum es zwei gibt.

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

- ❌ Individuallösung ohne Begründungssatz im Commit/PR.
- ❌ Eine Flotte von Hand synchronisieren, ohne den Mechanismus zu benennen,
  der sie auseinanderlaufen ließ.
- ❌ Umgekehrt: alles verallgemeinern, was zweimal vorkommt — die Policy
  verlangt die **Frage**, nicht immer die Abstraktion.

## Wo die Regel greift

Vor dem ersten Edit (die drei Fragen) und im Review. `/session-retro` fängt
Verstöße nachträglich als Slug `gate-matches-spelling-not-substance` — das ist
**nach** dem Merge und ausdrücklich die schlechtere Stelle.

## Precedence

Repo-`CLAUDE.md` > Orchestrator-MCP > diese Datei. Widerspricht ein Repo dieser
Policy bewusst, gehört der Grund in dessen `CLAUDE.md` — nicht in eine
stillschweigende Ausnahme.
