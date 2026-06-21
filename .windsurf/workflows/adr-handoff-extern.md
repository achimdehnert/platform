---
tool_targets: [windsurf-review]
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
- **Review-Runden:** Standard = **eine** externe Runde. Eine zweite nur bei wirklich kontroversen
  oder weitreichenden Entscheidungen — sonst sinkt der Grenznutzen schnell (Folgerunden liefern
  meist nur Wort-Schärfungen statt neuer Risiken; belegt am ADR-031-Dogfood).

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
/adr-handoff-extern ADR-NNN --auto           # Round-Trip automatisch absetzen (Step 4b) statt Copy-Paste
```

Das fertige Briefing wird als **Markdown-Datei nach `~/shared/`** geschrieben (Pfad + Dateiname
siehe Step 4) — nicht nur inline ausgegeben. So liegt es direkt kopierbereit für den externen Chat.

**`--auto` (optional):** Statt das Briefing manuell in einen externen Chat zu kopieren, setzt der
Skill den Call selbst ab (Step 4b) und legt die Antwort als zweite `.md` ab. **Default ohne Flag =
manueller Copy-Paste-Pfad** (unverändert). `--auto` automatisiert nur den **Transport**, nicht das
Urteil: Step 5 (Befund-Tagging) bleibt zwingend Mensch. Für souveräne ADRs (ttz-lif/meiki-lra/
Mandantendaten) ist `--auto` wirkungslos — das Hard-Gate (Step 4b.1) bricht VOR jedem Egress ab.

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
Gib die GESAMTE Antwort als **einen einzigen fenced Markdown-Codeblock** zurück
(öffnend mit drei Backticks + `markdown`, schließend mit drei Backticks), damit sie 1:1
als `.md` gespeichert werden kann. Struktur darin:

1. `## Steelman` — 3–5 Sätze.
2. `## Befunde` — eine Tabelle; jede Beobachtung eine Zeile mit **stabiler ID**:
   `| ID | Rolle | Befund (1 Satz) | Schweregrad (hoch/mittel/niedrig) | betroffener ADR-Teil |`
   ID-Präfix nach Rolle: `PRO-1…` (Proponent), `AD-1…` (Advocatus Diabolus), `M28-1…` (Maintainer 2028).
3. `## Out-of-the-Box` — je Ansatz: Idee · Vorteil · Nachteil · verworfen? (ja/nein + 1 Satz).
4. `## Empfehlung` — annehmen / überarbeiten / ablehnen + die EINE wichtigste Begründung.
5. `## Vorgeschlagene Änderungen` — nummerierte Liste `REC-1, REC-2, …`; jede mit Bezug auf
   eine Befund-ID (z. B. „REC-1 → AD-3").
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

## Step 4b — Auto-Round-Trip (NUR bei `--auto`)

Setzt den externen Call selbst ab, statt den Nutzer copy-pasten zu lassen. **Ohne `--auto`
übersprungen.** Automatisiert wird der **Transport**, nicht das Urteil — Step 5 bleibt Mensch.

**4b.1 — Hard-Gate VOR jedem Egress (nicht verhandelbar).**
Vor *irgendeinem* Netzwerk-Call programmatisch prüfen — schlägt einer an, **Abbruch ohne Call,
ohne Antwort-Datei**, Verweis auf `/adr-challenger`:
- **Org-Quelle = `git -C <repo> remote get-url origin`** (autoritativ), Org ∈ {`ttz-lif`, `meiki-lra`}
  → ABORT. **NICHT** allein auf `project-facts.md` bauen — die ist in souveränen Repos teils leer
  oder fehlt ganz (dogfood 2026-06-20: `ttz-hub` hat keine `project-facts.md`), ein nur darauf
  gestütztes Gate **fail-opent** genau für die zu schützenden Repos.
- ADR-Text trägt Mandantendaten-/Realdaten-Marker (Kundennamen, personenbezogene Daten,
  `data-sovereignty`-Klassifikation) → ABORT.
- **Fail-closed:** Lässt sich die Org nicht eindeutig bestimmen (kein Remote, mehrdeutig) →
  ABORT, nicht durchlassen.
Dieses Gate ersetzt den menschlichen Egress-Aktuator des manuellen Pfads; ohne grünen Gate-Check
darf `--auto` nicht senden. (Genau diese Bedingung trägt die „kein ADR"-Einstufung — KONZ-platform-007.)

**4b.2 — Modell wählen (NICHT hardcoden).**
- Ziel-Modell + `provider: openai` im Frontmatter des Review-Workflows setzen; aifw validiert die
  Modell-ID gegen seine Model-Registry (`LLMModel`/`LLMProvider`). Unbekannte ID → aifw-Fehler statt
  stillem Fallback; ID nicht raten, sondern aus der Registry nehmen (Präzedenz Routing-Reality-Check
  2026-05-13 — angenommenes Modell war nicht auf dem Account).
- **Provider-Diversität ist der Zweck:** ein *anderer* Anbieter als der interne `adr-challenger`
  (Default OpenAI). Das ist die begründete Frontier-Ausnahme zur LLM-Routing-Policy (Tier-1-Default
  gilt nicht — adversarialer Architektur-Review ist reasoning-schwer + Cross-Provider ist das Ziel).

**4b.3 — Call über aifw/Orchestrator absetzen (NICHT lokal curlen).**
- **Lokales curl ist tot (verifiziert 2026-06-20):** `~/.secrets/*_api_key` ist `root:root` mode 600;
  eine CC-Session als `devuser` kann den Key **nicht** lesen, kein passwordless sudo, nicht als Env
  injiziert. Der Key lebt korrekt im **Orchestrator-Container** — der Egress läuft durch ihn.
- Egress über **aifw** (Django-AI-Framework, im Orchestrator mit OpenAI-Provider konfiguriert).
  Routing: `workflow_executor` wählt `(model, provider, action_code)` aus dem Workflow-Frontmatter,
  sonst Default-Provider `groq`. **Für Cross-Provider zwingend `provider: openai` setzen** — der
  Default routet sonst nicht-extern (belegt: `review_adr` lief auf `anthropic/claude-sonnet-4-6`,
  also KEINE Provider-Diversität — exakt das, was dieser Skill vermeiden soll).
- Konkret: das Briefing aus Step 4 als Prompt durch aifw→OpenAI schicken (`workflow_execute` mit
  einem Review-Workflow, dessen Frontmatter `provider: openai` trägt; **eine** Runde, s. „When").
  Kein lokaler Key-Zugriff. Bei Fehler einmal melden, **nicht** still zurückfallen.

**4b.4 — Antwort ablegen.**
Antwort als zweite, deterministisch benannte `.md` neben das Briefing schreiben:
```
~/shared/adr-handoff-<ADR-NNN>-<JJJJ-MM-TT>-response.md           # Standard
~/shared/adr-handoff-<ADR-NNN>-<mode>-<JJJJ-MM-TT>-response.md    # bei --mode
```
Idempotent (überschreibt pro ADR+Modus+Tag). Pfad nennen, dann **direkt zu Step 5** — die Antwort
ist eine externe Beobachtung, kein Fakt, und fließt erst nach dem Tagging ein.

## Step 5 — Rückfluss-Gate (beim Einarbeiten der Antwort)

Die GPT-Antwort ist eine **externe Beobachtung**, kein Fakt. Dank der stabilen IDs (`AD-…`/`REC-…`)
ist jeder Punkt einzeln adressierbar: tagge jede **Befund- und REC-ID** `[valid]` /
`[missversteht-Kontext]` / `[out-of-scope]` — nur `[valid]` fließt ein, und zwar als Änderung mit
eigener Begründung, nicht als wörtliche GPT-Prosa. Halte die Tag-Tabelle (ID → Verdikt → Aktion)
als Nachweis fest.

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
- ❌ Reflexhaft eine zweite externe Runde fahren — Default ist eine Runde (s. „When").
- ❌ **`--auto` senden lassen, bevor das Hard-Gate (Step 4b.1) grün ist** — der programmatische
  Souveränitäts-Check ist Vorbedingung des Calls, kein Best-Effort danach.
- ❌ Bei `--auto` das Befund-Tagging (Step 5) **mit-automatisieren** — das Urteil bleibt Mensch;
  Auto-Rückfluss macht die Zweitmeinung zum Gummistempel.
- ❌ Modell-ID (z. B. „gpt-5.5") hardcoden statt aus Frontmatter `model` / `${ADR_HANDOFF_MODEL}`.
- ❌ **Lokal curlen / `~/.secrets/*_api_key` lesen wollen** — root-only, in CC-Session nicht lesbar;
  Egress läuft über aifw/Orchestrator (Step 4b.3).
- ❌ **`provider: openai` vergessen** — der Orchestrator-Default routet zu groq/anthropic, also
  KEINE Cross-Provider-Diversität (der einzige Zweck dieses Skills).
- ❌ Bei Call-Fehler still auf den manuellen Pfad zurückfallen, ohne es zu sagen.

## Changelog

- 2026-05-29: Initial. Cross-Provider-Pfad zur Session-Übergabe-Vorgabe; Steelman→Drei-Rollen→
  Out-of-the-Box als Default, Pre-Mortem-/Blind-Modus, Rückfluss-Tagging-Gate, Souveränitäts-Gate.
- 2026-05-29: `mode: write` — Briefing wird als `.md` nach `~/shared/` geschrieben (Step 4,
  deterministischer Dateiname = idempotent pro ADR+Modus+Tag); Anti-Patterns für Schreibziel ergänzt.
- 2026-05-29: Antwort-Format strukturiert (nach Dogfood ADR-031) — GPT liefert alles in EINEM
  Markdown-Codeblock (1:1 als `.md` speicherbar); Befunde + Empfehlungen tragen stabile IDs
  (`AD-`/`REC-`), Step-5-Rückfluss-Gate taggt deterministisch pro ID statt über freie Prosa.
- 2026-05-29: Review-Runden-Konvention — Default eine externe Runde; zweite nur bei kontroversen/
  weitreichenden Entscheidungen (sinkender Grenznutzen, belegt am ADR-031-Dogfood).
- 2026-06-20: `--auto`-Pfad (Step 4b) — optionaler automatisierter Round-Trip an externes Frontier-LLM
  (OpenAI). Hard-Gate VOR jedem Egress (souveräne Org/Mandantendaten → Abort), Modell aus
  `${ADR_HANDOFF_MODEL}` + `/v1/models`-Preflight (kein Hardcoding), Key aus `~/.secrets/openai_api_key`
  (nie echoen), Antwort als `*-response.md`. **Step 5 bleibt zwingend manuell** — Transport
  automatisiert, Urteil nicht. Konzept + RISK-1-Auflösung (kein ADR, getragen vom Hard-Gate-Test):
  `platform/docs/konzepte/KONZ-platform-007-adr-handoff-extern-automation.md`.
- 2026-06-20: **4b.3 korrigiert nach echtem Lauf (ADR-254).** Lokales curl war falsch — `~/.secrets/
  *_api_key` ist root-only, CC-Session (`devuser`) kann nicht lesen. Egress läuft über **aifw/
  Orchestrator** (Key im Container), Routing via Workflow-Frontmatter; **`provider: openai` zwingend**,
  sonst Default groq/anthropic = keine Diversität (belegt: `review_adr` lief auf `anthropic/
  claude-sonnet-4-6`). 4b.2 auf aifw-Model-Registry statt `/v1/models` umgestellt.
