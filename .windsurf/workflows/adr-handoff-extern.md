---
description: Schreibt ADR-Review-Briefing als .md nach ~/shared/ für externe LLM-Zweitmeinung (Advocatus Diabolus + Out-of-the-Box).
mode: write
---

# /adr-handoff-extern

Erzeugt einen **portablen ADR-Review-Auftrag** für ein externes LLM (GPT-5.5, Gemini, …),
das weder unser Repo noch Orchestrator-Memory noch frühere ADRs sehen kann. Alles Nötige
wird **inline** mitgegeben; das Ergebnis ist eine externe *Zweitmeinung* — keine Entscheidung.

## When

- Du willst eine architektonische Zweitmeinung zu einem ADR aus einem **anderen** Modell-Anbieter
  (Perspektiv-Diversität, die ein interner Single-Provider-`adr-challenger` nicht liefert).
- Der ADR ist nicht-trivial / hat einen Trade-off, der eine Gegenstimme verdient.

## When NOT

- **Daten-Souveränität (HARTES GATE):** ADRs aus `ttz-hub`/`meiki-hub` oder mit realen
  Mandantendaten (z.B. Gröger) verlassen die Plattform NICHT. Dafür intern `/adr-challenger`
  (Ollama-local). Siehe Drift-Memory *seed-vs-live*.
- Reine Ergänzung nach bestehendem Muster → gar kein ADR (Policy `adr-threshold.md`).
- Du willst den ADR umschreiben lassen — dieser Skill liefert **Befund**, kein Rewrite.

## Verwendung

```
/adr-handoff-extern ADR-NNN
/adr-handoff-extern ADR-NNN --mode blind     # Blind-Redesign statt Review
/adr-handoff-extern ADR-NNN --mode premortem # Pre-Mortem statt Standard-Review
```

Das fertige Briefing wird als **Markdown-Datei nach `~/shared/`** geschrieben (Pfad + Dateiname
siehe Step 4) — nicht nur inline ausgegeben. So liegt es direkt kopierbereit für den externen Chat.

## Step 0 — Repo-Kontext laden (NICHT hardcoden)

1. Lies `project-facts.md` des aktiven Repos für Org, Stack, Domains, Related Repos.
2. Lokalisiere den ADR (`docs/adr/` im Repo, oder `~/github/platform/docs/adr/` für Plattform-ADRs).
3. **Souveränitäts-Check:** Ist der ADR aus `ttz-lif`/`meiki-lra` oder referenziert er reale
   Mandantendaten? → ABBRECHEN, auf `/adr-challenger` verweisen.

## Step 1 — Belege sammeln (Quellen-Disziplin)

Nur aus belegbaren Quellen, nichts aus dem Gedächtnis nachziehen (`evidence-discipline.md`):
- ADR-Volltext.
- **Verwandte / abgelöste ADRs** — pro Stück 1 Satz Kern (nicht nur die Nummer; GPT kennt sie nicht).
- **Konventionen**, gegen die der ADR passen muss — zur Laufzeit aus `~/.claude/policies/`
  + `project-facts.md` + Platform-ADRs ziehen. Baseline-Digest (verifizieren, nicht blind glauben):
  - **Orgs:** `achimdehnert` (Plattform-default), `ttz-lif` (Public-Sector/Souveränität),
    `meiki-lra` (LRA/Citizen-facing).
  - **Wo lebt was:** Plattform-ADRs/Shared-Packages → `platform`; Cross-Cutting-Agents →
    `dev-hub/apps/` (headless/scheduled); CC-Skills → `platform-workflows/.windsurf/workflows/`.
  - **ADR-Schwelle:** ADR nur bei echter Architektur-Entscheidung (neue Service-Grenze/Dep,
    Reversal, Cross-Repo-Impact, Souveränität/Security/Lizenz) — sonst CHANGELOG+PR.
  - **LLM-Routing:** Groq-Free-first, paid nur mit Begründung; Tier-Disziplin.
  - **SSoT:** keine zwei Wahrheitsstände — referenzieren statt duplizieren.

## Step 2 — „Settled / nicht neu aufrollen" benennen

Liste die im ADR bereits **bewusst getroffenen** Entscheidungen, die NICHT zur Debatte stehen,
mit je 1 Satz Begründung. Schützt vor der größten externen-Review-Gefahr: einer plausiblen,
aber kontext-blinden Kritik, die Geklärtes neu aufrollt.

## Step 3 — Briefing nach Vorlage erzeugen (Output-Format)

Standard-Modus erzwingt **Steelman → Drei-Rollen → Befund**:

## Output-Format

```markdown
# ADR-Review-Auftrag: ADR-NNN <Titel>
_Externe Zweitmeinung · du siehst weder unser Repo noch frühere ADRs — alles Nötige steht unten._

## So nutzt du dieses Dokument
Lies alles. Arbeite die Schritte unten in DIESER Reihenfolge ab. Erfinde keinen Kontext,
den du nicht hier findest (keine angenommenen Repos, Tools, Versionen).

## Dein Auftrag — in dieser Reihenfolge
1. **Steelman zuerst.** Formuliere die stärkstmögliche Version dieser Entscheidung,
   bevor du sie angreifst. (Kein Angriff vor dem Steelman.)
2. **Drei Rollen, nacheinander:**
   - 🟢 **Proponent:** Warum ist das die richtige Entscheidung?
   - 😈 **Advocatus Diabolus:** Greife sie maximal hart an — wo bricht sie, welche
     Annahme ist fragil, welche verworfene Alternative war in Wahrheit besser?
   - 🔮 **Maintainer 2028:** Du erbst dieses System in 2 Jahren — was bereust du?
3. **Out-of-the-Box:** Nenne mindestens EINEN Ansatz, den das Briefing gar nicht erwägt
   (anderes Paradigma, Kauf-statt-Bau, ganz weglassen, …). Auch wenn du ihn am Ende verwirfst.
4. **Befund & Empfehlung:** annehmen / überarbeiten (konkrete Punkte) / ablehnen.

## Der ADR im Volltext
<kompletter ADR-Text inline>

## Kontext, den du brauchst (inline, da du ihn nicht laden kannst)
- **Verwandte / abgelöste ADRs:** ADR-NNN — <1-Satz-Kern> …
- **Konventionen, gegen die der ADR passen muss:** <aus Step 1>
- **Constraints:** <Stack, Domains, Souveränität, Lizenz>

## Bereits entschieden — NICHT neu aufrollen
- <Punkt> — <warum settled> …

## Do-not-assume
- Dein trainiertes „Best Practice" gilt NICHT automatisch. Wo es den Konventionen oben
  widerspricht, **gewinnen unsere Konventionen** — benenne den Konflikt, statt unsere Wahl
  als Fehler zu werten.
- Trenne Beobachtung von Vermutung; markiere Unsicheres als unsicher statt zu raten.

## Gewünschtes Output-Format (deine Antwort)
1. Steelman (3–5 Sätze)
2. Drei Rollen (je Stichpunkte)
3. Out-of-the-Box-Ansatz/Ansätze
4. Empfehlung: annehmen / überarbeiten / ablehnen + die EINE wichtigste Begründung
```

### Modus `--mode premortem`
Ersetze „Dein Auftrag" durch: *„Es ist 2028. Diese Entscheidung ist krachend gescheitert.
Schreibe die Post-Mortem: Was genau ist passiert, welche Annahme war der Sargnagel, welches
Frühwarnsignal haben wir 2026 ignoriert?"* Erzwingt konkrete Failure-Modes statt generischem „consider X".

### Modus `--mode blind`
Gib **das Problem/den Kontext OHNE unsere Entscheidung** (Abschnitt „Der ADR im Volltext" wird
zu „Das zu lösende Problem"). Bitte um eine eigenständige Empfehlung. Danach intern vergleichen:
Wo weicht der Blind-Vorschlag ab? Das deckt Anchoring-Bias auf, den ein Review am fertigen ADR nicht sieht.

## Step 4 — Briefing nach `~/shared/` speichern

Schreibe das erzeugte Briefing als Markdown-Datei in das Shared-Verzeichnis des Nutzers (`~/shared/`),
mit **deterministischem** Dateinamen:

```
~/shared/adr-handoff-<ADR-NNN>-<JJJJ-MM-TT>.md            # Standard-Modus
~/shared/adr-handoff-<ADR-NNN>-<mode>-<JJJJ-MM-TT>.md     # bei --mode premortem|blind
```

- **Idempotenz:** Der Dateiname ist pro ADR + Modus + Tag deterministisch → ein erneuter Lauf am
  selben Tag **überschreibt** dieselbe Datei (kein Zuwuchern mit Duplikaten). Existiert die Datei
  bereits aus einem früheren Lauf, vor dem Überschreiben kurz bestätigen lassen.
- Nach dem Schreiben den **vollständigen Pfad** nennen und den Nutzer auf die ⚠️-markierten
  „erneut bereitstellen"-Quellen hinweisen (falls vorhanden).
- Kann in der Sitzung keine Datei geschrieben werden, gib das Briefing stattdessen in **einem**
  Markdown-Codeblock aus, damit es kopierbar bleibt.

## Step 5 — Rückfluss-Gate (beim Einarbeiten der Antwort)

Die GPT-Antwort ist eine **externe Beobachtung**, kein Fakt. Bevor irgendein Einwand den ADR berührt:
tagge jeden Punkt `[valid]` / `[missversteht-Kontext]` / `[out-of-scope]` — nur `[valid]` fließt ein,
und zwar als Änderung mit eigener Begründung, nicht als wörtliche GPT-Prosa.

## Anti-Patterns (darf NICHT)

- ❌ ttz-lif/meiki-lra-ADRs oder reale Mandantendaten an ein externes LLM geben.
- ❌ ADR-Nummern statt Inhalt referenzieren — GPT kennt unsere ADRs nicht.
- ❌ Auf SSoT (Orchestrator-Memory, project-facts) *verweisen* statt inline — extern nicht ladbar.
- ❌ GPT-Befund 1:1 in den ADR kippen, ohne Step-5-Tagging.
- ❌ Angriff ohne vorausgehenden Steelman (Cheap-Shot-Review).
- ❌ Repo-Pfade / Org-Namen / MCP-Prefixe hardcoden — aus `project-facts.md` zur Laufzeit.
- ❌ Das Briefing **ins Repo** schreiben (Working-Tree/`docs/`) — Ausgabe gehört nach `~/shared/`,
  nicht in versionierte Repo-Pfade.
- ❌ Für einen souveränen ADR (ttz-lif/meiki-lra/Realdaten) überhaupt eine Briefing-Datei
  materialisieren — das Souveränitäts-Gate (Step 0) bricht VOR dem Schreiben ab.
- ❌ Nicht-deterministische/zeitstempel-genaue Dateinamen, die bei jedem Lauf neue Dateien
  anhäufen — der Name ist pro ADR+Modus+Tag fix (Idempotenz).

## Changelog

- 2026-05-29: Initial. Cross-Provider-Pfad zur Session-Übergabe-Vorgabe; Steelman→Drei-Rollen→
  Out-of-the-Box als Default, Pre-Mortem-/Blind-Modus, Rückfluss-Tagging-Gate, Souveränitäts-Gate.
- 2026-05-29: `mode: write` — Briefing wird als `.md` nach `~/shared/` geschrieben (Step 4,
  deterministischer Dateiname = idempotent pro ADR+Modus+Tag); Anti-Patterns für Schreibziel ergänzt.
