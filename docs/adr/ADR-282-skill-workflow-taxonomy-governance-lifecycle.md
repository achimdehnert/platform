---
status: proposed
decision_date: 2026-07-23
deciders: Achim Dehnert
domains: [tooling, dx, governance, drift-prevention]
supersedes: []
amends: [claude-skills.md]
related: [ADR-229, ADR-230, ADR-233, ADR-280, ADR-281]
tags: [skills, workflows, governance, taxonomy, lifecycle, registry, retirement, sprawl]
ai_sparring_by:
    date: 2026-07-23
    summary: "Zwei unabhängige externe LLM-Reviews via /adr-handoff-extern (manueller Handoff, PII-frei); beide Verdikt 'überarbeiten', stark konvergent auf: Achse vermischt Statefulness/Trigger, 4 Artefakttypen nicht gemappt, Selbst-Widersprüche (Phase-4-Kadenz, Phase-5-Policy, zirkuläre Acceptance, §2.4↔Phase-1), Registry-Souveränität (föderiert), schwache Kennzahlen, Registry-SSoT, Substrat-Schwelle unscharf. 14x valid eingearbeitet; Rückfluss-Tag-Tabelle in §7.2."
---

# ADR-282: Skill-/Workflow-Taxonomie, Governance und Lebenszyklus — Wildwuchs über den vollen Lebenszyklus verhindern

> **Kontext.** Bestimmte Lotsen-Fähigkeiten sind zustandsbehaftete Prozesse (z.B.
> Betroffenenrechte), keine zustandslosen Skills; manche Skills sind repo-spezifisch. Heute
> liegen alle ~52 Skills zentral und maschinenweit verteilt — ohne Achsen-Trennung, ohne
> abfragbare Registry, ohne Retirement. Diese ADR macht Taxonomie **und** Governance **und**
> Lebenszyklus verbindlich. Sie ist durch **drei Review-Runden** gehärtet (§7): Owner-Review,
> interner `adr-challenger`, **zwei unabhängige externe Provider** (beide „überarbeiten") — alle
> Verdikte getaggt und adressiert.

## Metadaten

| Attribut | Wert |
|---|---|
| **Status** | Proposed |
| **Scope** | platform (+ Konvention für alle Repos) |
| **Erstellt** | 2026-07-23 |
| **Autor** | Achim Dehnert |
| **Externes Sparring** | 1 strukturiertes Owner-Review, 2026-07-23 — 5 Punkte, alle übernommen; Rückfluss in §Externes Sparring |
| **Amends** | Policy `claude-skills.md` (Achsen + Registry) — **erst bei Acceptance**. `platform-agents.md` wird nur **referenziert**, nicht geändert. |
| **Depends on (Sequencing)** | **ADR-280 muss Option A erreichen** (accepted, §8.1 6/6) **vor** Accept dieser ADR — sonst kippt die Heimat-Matrix §2.1 (Rückfall Option D = zwei Lanes). Symlink-Heimat setzt ADR-281 voraus. |
| **Relates to** | ADR-229/230 (Skill-Distribution), ADR-233 (Worktree). **Adressiert ADR-280 §10 Option F / #1298** (Reichweite repo-lokaler Skills). |

## Repo-Zugehörigkeit

| Repo | Rolle | Betroffene Pfade / Komponenten |
|---|---|---|
| `platform` | Primär | `docs/adr/`, `tools/cc-skill-dist/`, neue Registry-Generierung + CI-Gate, `~/.claude/policies/claude-skills.md` (`platform-agents.md` nur referenziert) |
| `dev-hub` | Sekundär | Heimat headless/plattformweiter Agenten (`apps/<agent>/`) — unverändert, nur eingeordnet |
| *(Domänen-Hubs)* | Sekundär | Heimat repo-spezifischer Skills (`.claude/`) + stateful Prozess-State-Machines |

> **Kein Fleet-Rewrite.** Die ADR ordnet ein und ergänzt Governance; sie zwingt keine
> Bestandsmigration außer der Registry-Erzeugung + einem einmaligen Retirement-Scan.

---

## Decision Drivers

- **Zustandsbehaftete Prozesse als Skills modelliert = Prozesslogik in Prompt-Text dupliziert.** Betroffenenrechte haben Status, Frist, Auslöser, Akteure — das gehört in eine State-Machine, nicht in Markdown.
- **Repo-spezifische Skills liegen global** → maschinenweites Rauschen, unauffindbare Duplikate, unerreichbar für Cloud-Sessions (ADR-280 §10 / #1298).
- **„Registry" war bisher ein Wunsch, kein Mechanismus** — ohne generierte, verifizierte, zentrale Quelle ist ein Dedup-Check zahnlos.
- **Kein Retirement** — Wildwuchs entsteht genauso durch nie gelöschte, verwaiste Skills wie durch Neuanlage.
- **Belegte Sprawl-Historie:** `project_skill_system_not_contradiction_free` (Regel-Kopie / Kanon-Konflikt / lügender Index / Latenz).

---

## 1. Context and Problem Statement

Es fehlt eine verbindliche Antwort auf zwei Fragen: **(1)** Wo lebt eine neue Lotsen-Fähigkeit — als Skill, als Prozess, als headless Agent, zentral oder repo-lokal? **(2)** Wie verhindert man, dass die Menge dieser Artefakte über die Zeit zum unpflegbaren Wildwuchs wächst?

Die Erstskizze beantwortete (1) mit einer Vier-Zeilen-Lookup-Tabelle und (2) mit vier Entstehungs-Regeln. Das Owner-Review deckte auf: die Tabelle vermischte zwei unabhängige Achsen, „Registry" blieb unspezifiziert, ein Retirement-Mechanismus fehlte ganz, die Substrat-Schwelle war eine Bauchzahl, und ein Erfolgsmaß fehlte. Diese ADR behebt alle fünf.

## 2. Decision Outcome

### 2.1 Drei unabhängige Merkmale — Heimat ist ihre *Funktion*, keine Matrix-Zeile

**Rev nach externem Sparring (§7.2, AD-1/AD-2/M28-1):** die frühere „Ausführungsmodus"-Achse war **nicht trennscharf** — ein `scheduled` Agent kann zugleich zustandsbehaftet sein und fiel damit in zwei Zeilen. Ersetzt durch **drei unabhängige Merkmale** je Fähigkeit (im Frontmatter gesetzt):

- **`scope`:** `plattformweit` · `geteilt` (n>1, aber nicht alle Repos) · `repo-spezifisch`
- **`statefulness`:** `zustandslos` · `zustandsbehaftet` (Status/Frist/Audit über die Zeit)
- **`trigger`:** `interaktiv` (Mensch ruft) · `scheduled` (cron) · `event` (Auslöser)

**Heimat-Ableitungsregel (Priorität, erste zutreffende gewinnt):**
1. `statefulness = zustandsbehaftet` → **State-Machine in der Domänen-App** (Prozess-Muster §2.2), *unabhängig* vom `trigger`. Der zusätzliche Treiber-Artefakttyp folgt dann aus `trigger`+`scope`.
2. sonst `trigger ∈ {scheduled, event}` → **headless Agent**: `scope=plattformweit` → dev-hub Platform-Agent (`platform-agents.md`); `scope=repo-spezifisch` → Domänen-Hub Celery-Task/Command.
3. sonst (`zustandslos` + `interaktiv`) → **Skill**: `plattformweit` → zentral `platform/skills/` (`cc-skill-dist`); `geteilt` → zentral, aber im Frontmatter auf die Ziel-Repos begrenzt; `repo-spezifisch` → `<repo>/.claude/skills/` (committed, erreicht Cloud-Sessions).

**Zuordnung der vier `claude-skills.md`-Artefakttypen** (Bestand — hier nur eingeordnet, AD-2):

| Artefakttyp (Bestand) | statefulness | trigger | Heimat-Regel |
|---|---|---|---|
| Slash-Command / CC-Skill | zustandslos | interaktiv | Regel 3 (Skill) |
| Anthropic Agent Skill | zustandslos | interaktiv | Regel 3 (`~/.claude/skills/` bzw. repo-lokal) |
| Django Platform-Agent | oft zustandsbehaftet | scheduled/event | Regel 1/2 (App/Agent) |
| CC-Sub-Agent | zustandslos | interaktiv (delegiert) | Regel 3, aber Claude-only |

**Merkmalswechsel (R2-Promotion, AD-5 rev1):** ändert eine Fähigkeit ihr `scope` (repo-lokal → plattformweit) oder ihre `statefulness`, ist das ein **bewusster Umzug** — Frontmatter aktualisieren, Artefakt an die neue Heimat verschieben, Registry-Eintrag neu ableiten; im PR dokumentiert, nicht still.

### 2.2 Prozess-Muster: State · Treiber · Registry (drei Rollen, kein Prompt-Text)

Eine zustandsbehaftete Fähigkeit wird **nie** als Skill nachgebildet, sondern in drei Rollen zerlegt:

1. **State** — State-Machine + Frist + Audit-Trail + Transitionen in der **Domänen-App** (Django). Referenzimplementierung: risk-hub `DeletionRequest` (Betroffenenrechte, Art. 17).
2. **Treiber** — ein **dünner** Skill, der den Zustand über eine programmatische Schnittstelle (Management-Command/API) anlegt/fortschreibt. Referenz: `create_deletion_request` + `/mailcheck`.
3. **Registry-Eintrag** — der Prozess ist im Katalog geführt (§2.4), damit er auffindbar ist und nicht ad hoc neu erfunden wird.

Kein generisches Workflow-Substrat wird jetzt gebaut (YAGNI). **Schwelle für ein gemeinsames Substrat — duplikatsbasiert, prüfbar (M28-4):** sobald **zwei produktive** State-Machines in **allen vier** Merkmalen übereinstimmen — gleiche **Transitionstopologie**, gleiches **Fristenmodell**, gleiches **Rollenmodell**, gleiches **Audit-Trail-Verhalten** — ist die Extraktion einer geteilten Basis zu erwägen. Nicht „ab Prozess Nr. 3", nicht „gefühlt ähnlich".

### 2.3 Governance-Regeln (Entstehung)

- **R1 — Scope-Entscheidung bei Anlage:** beide Achsen (§2.1) explizit benennen → Heimat folgt daraus.
- **R2 — Promotions-Schwelle:** die **bestehende** `claude-skills.md`-Regel (wiederkehrender Workflow >3×/Woche manuell → Skill-Kandidat) gilt unverändert — hier nur eingeordnet, nicht neu erfunden. Präzedenz: `read-mail` nach 4× Ad-hoc.
- **R3 — Dedup-Check gegen die Registry** vor jeder Anlage (setzt §2.4 voraus).

### 2.4 (d) Registry — Mechanismus, nicht Wunsch (föderiert, souveränitäts-sicher)

**Rev nach externem Sparring (§7.2):** SSoT geklärt, V1-Scope präzisiert, Cross-Repo **föderiert** statt zentraler Scanner.

| Frage | Festlegung |
|---|---|
| **SSoT?** | Das **Frontmatter** der Artefakt-Datei ist die **alleinige Quelle der Wahrheit** (M28-3). Die Registry (`docs/registry/skills.{json,md}`) ist eine **reproduzierbare Projektion** — bei Bedarf als menschenlesbarer `.md`-Nachweis eingecheckt, aber **nie** von Hand editiert; das CI-Gate regeneriert und diffed sie (analog `INDEX.md`). |
| **V1-Scope** | **Nur `platform/skills/`-Frontmatter** (AD-3 rev2: §2.4 und Phase 1 synchron — V1 ist eine *platform-Skill-Registry*, **nicht** schon eine vollständige Skill-/Workflow-/Agent-/Prozess-Registry). |
| **Cross-repo (später, föderiert)** | **Kein** zentraler Scanner, der fremde Repos ausliest. Jedes Repo generiert + validiert sein eigenes Capability-Manifest **lokal** (eigene CI); `platform` **aggregiert nur veröffentlichte Manifeste** (AD-3 rev1 / M28-2 / Out-of-the-Box #1). **Souveräne Orgs (`ttz-lif`/`meiki-lra`) werden nie zentral gescannt** — sie publizieren höchstens ein PII-freies Manifest oder opten aus. |
| **Wer verifiziert?** | Ein **CI-Gate** in `platform`, das die platform-Registry deterministisch erzeugt und **bei Drift den Build bricht** (analog `doctor.py`); für föderierte Manifeste Schema-Validierung im jeweiligen Repo, Aggregation nur über gültige. |
| **Schema-Versionierung** | Neue Frontmatter-Felder (`scope`,`statefulness`,`trigger`,`owner_repo`,`state_backend`) tragen eine **`schema_version`** (M28-3), damit spätere Erweiterungen einen Migrationspfad haben statt das Gate zu brechen. |

Damit hat R3 (Dedup) etwas Abfragbares; der „lügende Index" wird durch Generierung + Gate strukturell verhindert — **ohne** einen zentralen Cross-Repo-Scanner, der die Souveränitäts-Grenze verletzt.

### 2.5 (e) Retirement — R4, nutzungsbasiert

- **R4 — Retirement nutzt den bestehenden `tools/usage_sweep.py`** (Issue #1076, Owner-Entscheid 2026-07-11, **quartalsweise**, misst Skill-Aufrufe aus CC-Transkripten; 0 Aufrufe → `[usage-sweep]`-Rückbau-Kandidat, human-gated, Kill nach 2 Sweeps ohne Rückbau). **Kein neuer, konkurrierender Mechanismus, keine abweichende Kadenz** (Rev nach adr-challenger — die frühere „monatlich/N=6"-Formulierung war ein Doppler zur gemergten Policy). ADR-282 erweitert `usage_sweep.py` ausschließlich um die neuen Artefakttypen (repo-lokale Skills, Prozess-Treiber) im Registry-Inventar; Kadenz und Gating bleiben wie in `claude-skills.md` §Lifecycle.

### 2.6 (Erfolgsmaß) Woran man in 6 Monaten misst

**Rev nach externem Sparring (§7.2, AD-8/AD-9):** keine Kennzahl, die Zentralisierung belohnt oder deren Nullwert mehrdeutig ist.

| Kennzahl | Richtung | Quelle |
|---|---|---|
| Aktive Artefakte gesamt · Neuanlagen · Retirements | erklärbar, nicht monoton wachsend | Registry |
| **Anteil korrekt klassifizierter** Artefakte (Merkmale gesetzt, Heimat = Regel) | steigend → 100 % | Registry-Gate |
| **Dedup-Quote** = Anlagen mit dokumentiertem Registry-Check / alle Anlagen; **plus** verhinderte/zusammengeführte Duplikate | Quote → 100 %; **0 verhinderte ≠ automatisch Misserfolg** (AD-8) | CI-Gate-Log |
| Ad-hoc → Skill-Promotions (R2) | dokumentiert, nicht 0 | PR-Historie |
| Unused-Count (R4-Kandidaten) | sinkend nach erstem Sweep | `usage_sweep.py` |

> **Nicht** „Skills pro Repo sinkend" (AD-9) — das belohnte künstliche Zentralisierung und widerspräche der bewussten Entscheidung für sinnvolle repo-lokale Skills. Repo-lokale Verlagerungen werden **nicht** negativ bewertet.

---

## 3. Implementation Details (phasiert)

| Phase | Inhalt | Gate |
|---|---|---|
| 0 | Diese ADR (Taxonomie + Governance + Lifecycle) | dieser PR |
| 1 | Registry-Generator + zentraler Katalog (`docs/registry/`) **nur aus `platform/skills/`-Frontmatter** (SUGGEST) | Katalog = platform-Realität |
| 2 | CI-Gate „Registry-Drift bricht Build" (analog `doctor.py`) | Negativtest: künstlicher Drift rötet |
| 3 | Frontmatter-Erweiterung (`scope`,`statefulness`,`trigger`,`owner_repo`,`state_backend`,`schema_version`) an Bestands-Skills nachziehen | Schema-Validate grün |
| 4 | Retirement via bestehendem `usage_sweep.py` (**quartalsweise**, non-blocking) auf neue Artefakttypen erweitern + erster Bericht | Bericht liegt vor, 0 Auto-Deletes |
| 5 | **Bei Acceptance (atomar):** `claude-skills.md` um Merkmale + Registry-Verweis ergänzen **und** Statuswechsel (§6) | Policy-Edit + Accept im selben PR |

Aufgeschobenes bekommt je ein Tracking-Issue **im selben Zug** (House-Rule); Phasen 1–4 werden als Issues angelegt, nicht im ADR-Text „versprochen". Der **cross-repo `.claude/`-Scan** ist bewusst **nicht** in Phase 1 — eigenes Issue, Start erst hinter dem ersten realen repo-lokalen Konsumenten (🌀 `feedback_fleet_adr_scan_before_accept`: nicht für ~0 Inputs bauen).

## 4. Consequences

**Positiv:** Prozesslogik bleibt in Apps (testbar), Skills bleiben dünn; repo-spezifisches liegt lokal (kein globales Rauschen, Cloud-erreichbar); Duplikate werden abfragbar; verwaiste Skills werden sichtbar; „Kanon" wird an Kennzahlen messbar.

**Negativ / Kosten:** ein Generator + ein CI-Gate + ein Scan sind zu bauen und zu warten; Frontmatter-Nachzug an ~52 Bestands-Skills; ein zusätzliches Governance-Ritual bei Anlage (R1/R3).

## 5. Risks

- **Registry-Gate zu streng → Reibung.** Mitigation: Phase 1/2 erst **SUGGEST/non-blocking**, Baseline sichten, dann gating (Präzedenz `feedback_advisory_scanner_reactivation_needs_baseline`).
- **Retirement-Fehlalarm löscht Genutztes.** Mitigation: **human-gated**, nie Auto-Delete; N kalibrierbar.
- **Frontmatter-Nachzug unvollständig → Katalog lückenhaft.** Mitigation: Schema-Validate + Gate erzwingen Vollständigkeit.

## 6. Confirmation / Rollout-Gate

**Technische Vorbedingungen (vor Acceptance):**
- [ ] platform-Registry deterministisch generiert; Katalog = platform-Realität (Phase 1).
- [ ] CI-Gate rötet bei künstlichem Drift (Negativtest, Phase 2).
- [ ] Retirement (`usage_sweep.py`) liefert ersten Bericht, **0 Auto-Deletes** (Phase 4).
- [ ] Erfolgsmaße (§2.6) sind erhebbar (Kennzahl-Quellen existieren).
- [ ] **Sequencing:** ADR-280 hat Option A erreicht (accepted).

**Acceptance-Aktion (atomar, AD-7):** Der `claude-skills.md`-Edit **und** der Statuswechsel `proposed → accepted` erfolgen **gemeinsam im Acceptance-PR** — die Policy-Änderung ist *kein* vorgelagertes Gate (sonst zirkulär).

**Re-Review-Trigger (AD-2/REC-5 rev1):** Fällt ADR-280 auf Option D (zwei Lanes) zurück, wird §2.1 (Skill-Heimat) re-opened — nicht still veraltet.

## 7. Externes Sparring — Rückfluss-Tagging

Diese ADR ist das direkte Ergebnis eines strukturierten Owner-Reviews (2026-07-23). Fünf Punkte, alle übernommen:

| # | Review-Punkt | Wirkung in dieser ADR |
|---|---|---|
| 1 | Scope-Tabelle vermischt zwei Achsen | §2.1 — zwei orthogonale Achsen, Heimat = Funktion (Matrix statt Lookup) |
| 2 | „Registry" unterspezifiziert | §2.4 — Quelle/Verifikation/Ort konkret (Frontmatter+Scan / CI-Gate / zentral) |
| 3 | Kein Retirement | §2.5 — R4 nutzungsbasiert, human-gated |
| 4 | Substrat-Schwelle unbegründet („3–4") | §2.2 — duplikatsbasiert (2 State-Machines mit identischer Struktur) |
| 5 | Kein Erfolgsmaß | §2.6 — 4 Kennzahlen mit Quelle |

### 7.1 Zweite Sparring-Runde — adr-challenger (2026-07-23)

Ein **unabhängiger** adr-challenger-Subagent (Richter ≠ Angeklagter, KONZ-010) prüfte den Entwurf. Verdikt „tragfähig mit 4 Änderungen". Übernommen:

| Befund (verifiziert) | Wirkung |
|---|---|
| R4 dupliziert die **gemergte** `usage_sweep.py` (quartalsweise) | §2.5 auf `usage_sweep.py` reconciliert — kein neuer Mechanismus |
| R2 restated `claude-skills.md` „>3×/Woche" | §2.3 als Referenz gekennzeichnet |
| ADR-280/281 nur `related` trotz Sequencing-Abhängigkeit | Metadaten: **Depends-on** + Option-F/#1298-Link |
| Fleet-`.claude/`-Scan für ~0 Repos in Phase 1 | §2.4/§3: platform-only zuerst, cross-repo hinter 1. Konsument |
| Split/Narrow (Taxonomie≈Policy vs Registry=ADR-Kern) | Owner wählte **(A) eine ADR** (2026-07-23), §9 |

### 7.2 Dritte + vierte Runde — zwei externe Provider (cross-provider, 2026-07-23)

Zwei **unabhängige** externe LLM-Reviews via `/adr-handoff-extern` (manueller Handoff, PII-frei, `ai_sparring_by` im Frontmatter). **Beide Verdikt „überarbeiten"**, stark konvergent. Rückfluss-Tagging — nur `[valid]` fließt als begründete Änderung ein:

| Befund (extern) | Verdikt | Aktion |
|---|---|---|
| Achse „Ausführungsmodus" vermischt Statefulness & Trigger (scheduled Agent kann stateful sein) | **[valid]** | §2.1 in **drei Merkmale** (`scope`/`statefulness`/`trigger`) + Ableitungsregel zerlegt |
| 4 `claude-skills.md`-Artefakttypen nicht gemappt | **[valid]** | §2.1 Zuordnungstabelle ergänzt |
| Phase 4 „monatlich" ↔ §2.5 „quartalsweise" (Selbst-Widerspruch) | **[valid]** | Phase 4 auf quartalsweise `usage_sweep.py` korrigiert |
| Phase 5 `platform-agents.md` ↔ Metadaten „nur referenziert" | **[valid]** | Phase 5 + §6 + Repo-Tabelle: nur `claude-skills.md` |
| Zirkuläre Acceptance (Policy erst bei Acceptance, Status hängt am Gate) | **[valid]** | §6: Policy-Edit + Statuswechsel **atomar** im Acceptance-PR |
| §2.4 verspricht „alle Dateien", Phase 1 nur `platform/skills/` | **[valid]** | §2.4 als V1 = platform-Skill-Registry präzisiert |
| Zentrale Registry scannt souveräne Org-Repos (ttz-lif/meiki-lra) | **[valid]** | §2.4 **föderiert** — Repos publizieren eigenes Manifest, souverän nie zentral gescannt |
| Kennzahl „Dedup > 0" mehrdeutig; „Skills/Repo sinkend" belohnt Zentralisierung | **[valid]** | §2.6 Quote + verhinderte Dups; „Skills/Repo" entfernt |
| Registry-SSoT unklar (JSON vs Frontmatter vs Build-Artefakt) | **[valid]** | §2.4: Frontmatter = SSoT, Registry = reproduzierbare Projektion |
| Substrat-Schwelle „nahezu identisch" subjektiv | **[valid]** | §2.2 vier prüfbare Kriterien (Topologie/Fristen/Rollen/Audit) |
| Binäre Scope-Achse ohne „geteilt (n>1)"; R2-Zellwechsel unspezifiziert | **[valid]** | §2.1 `scope=geteilt` + Merkmalswechsel-Regel |
| Re-Review-Trigger falls ADR-280→D | **[valid]** | §6 Re-Review-Trigger ergänzt |
| Schema-Versionierung neuer Frontmatter-Felder fehlt | **[valid]** | §2.4 `schema_version` ergänzt |
| „Volle Maschinerie für 0 repo-lokale Skills / 1 Prozess = Über-Engineering" | **[teilweise]** | 52 Skills rechtfertigen die platform-Registry (der andere Provider bestätigt das, PRO-2); cross-repo bleibt an 1. Konsument gekoppelt — Kern verteidigt, Trigger-Kopplung präzisiert |
| „Bestehendes Katalog-Tool statt Eigenbau" | **[kontext]** | Frontmatter ist Claude-Code-spezifisch; Eigenbau = ein dünner Generator, Fremdtool-Integration teurer |

**Bilanz:** 13× `[valid]` eingearbeitet, 1× `[teilweise]` (Kern verteidigt, Trigger-Kopplung präzisiert), 1× `[kontext]`. Beide „überarbeiten"-Verdikte adressiert; tiefste Änderung = Zerlegung der Achse (§2.1). Provider/Datum durabel in `ai_sparring_by` (Frontmatter).

## 9. Offene Entscheidung — Scope (Owner)

Der Challenger nennt als stärkstes Gegenargument (Conf. 78): der genuine ADR-Kern ist der **generierte, CI-drift-gegatete Registry-Mechanismus** (§2.4); Taxonomie (§2.1) + R2 + R4 sind überwiegend **Klärung/Referenz** bestehender Policy (`claude-skills.md`) und damit per `adr-threshold.md` eher Policy-Edit als ADR-Stoff. Zwei Wege:

- **(A) Eine ADR behalten**, aber Taxonomie/R2/R4 klar als „referenziert/eingeordnet, nicht neu" markieren (bereits umgesetzt) — Vorteil: ein Lese-Ort für den vollen Lebenszyklus.
- **(B) Splitten:** ADR-282 auf den Registry-Mechanismus verengen; die 2-Achsen-Taxonomie + Promotions-Regel als `claude-skills.md`-Edit. Näher an `adr-threshold.md`, kleinerer Blast-Radius.

**Owner-Entscheid (2026-07-23): Option A** — eine ADR; Taxonomie/R2/R4 bleiben als „referenziert/eingeordnet, nicht neu" markiert (§2.1/§2.3/§2.5). Split (B) bleibt dokumentierte Rückfalloption, falls das Code-Owner-Review ihn verlangt. `status: proposed` bis das Sequencing (ADR-280 → Option A accepted) **und** das Rollout-Gate (§6) erfüllt sind.

## 8. Changelog

- 2026-07-23: Initial (proposed). Taxonomie (2 Achsen) + Prozess-Muster (State/Treiber/Registry) + Governance R1–R4 + Registry-Mechanismus + Retirement + Erfolgsmaße. Basiert auf Owner-Review (§7). Referenz-Implementierung Betroffenenrechte: risk-hub `DeletionRequest` (#449) + `/mailcheck` (#1383).
- 2026-07-23 (Rev, nach adr-challenger §7.1): R4 auf `usage_sweep.py` reconciliert (war Doppler zur gemergten Policy), R2 als Policy-Referenz markiert, ADR-280/281-**Depends-on** + Option-F/#1298-Link ergänzt, cross-repo-Scan aus Phase 1 in eigenes Issue vertagt, `amends: platform-agents.md` gestrichen (nur referenziert). Offen: Scope-Split (§9, Owner).
- 2026-07-23 (Owner-Entscheid §9): **Option A** — eine ADR, kein Split; Taxonomie/R2/R4 als Referenz belassen. Bleibt `proposed` bis Sequencing (ADR-280 Option A) + Rollout-Gate §6.
- 2026-07-23 (Rev, nach 2 externen Cross-Provider-Reviews §7.2): beide Verdikt „überarbeiten". **§2.1 Achse in drei Merkmale zerlegt** (`scope`/`statefulness`/`trigger` + Ableitungsregel + 4-Artefakttyp-Mapping); §2.4 **föderiert + SSoT-geklärt + souveränitäts-sicher**; §2.6 Kennzahlen entschärft (keine Zentralisierungs-Belohnung, Dedup als Quote); §2.2 Substrat-Schwelle mit 4 prüfbaren Kriterien; Selbst-Widersprüche behoben (Phase-4-Kadenz, Phase-5-Policy, zirkuläre Acceptance → §6 atomar); Re-Review-Trigger + `schema_version` ergänzt. `ai_sparring_by` im Frontmatter.
