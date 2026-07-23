---
status: proposed
decision_date: 2026-07-23
deciders: Achim Dehnert
domains: [tooling, dx, governance, drift-prevention]
supersedes: []
amends: [claude-skills.md, platform-agents.md]
related: [ADR-229, ADR-230, ADR-233, ADR-280, ADR-281]
tags: [skills, workflows, governance, taxonomy, lifecycle, registry, retirement, sprawl]
---

# ADR-282: Skill-/Workflow-Taxonomie, Governance und Lebenszyklus — Wildwuchs über den vollen Lebenszyklus verhindern

> **Kontext.** Bestimmte Lotsen-Fähigkeiten sind zustandsbehaftete Prozesse (z.B.
> Betroffenenrechte), keine zustandslosen Skills; manche Skills sind repo-spezifisch. Heute
> liegen alle ~52 Skills zentral und maschinenweit verteilt — ohne Achsen-Trennung, ohne
> abfragbare Registry, ohne Retirement. Diese ADR macht Taxonomie **und** Governance **und**
> Lebenszyklus verbindlich. Sie ruht auf einem detaillierten externen Review (§Externes
> Sparring), das die Erstskizze in fünf Punkten korrigiert hat.

## Metadaten

| Attribut | Wert |
|---|---|
| **Status** | Proposed |
| **Scope** | platform (+ Konvention für alle Repos) |
| **Erstellt** | 2026-07-23 |
| **Autor** | Achim Dehnert |
| **Externes Sparring** | 1 strukturiertes Owner-Review, 2026-07-23 — 5 Punkte, alle übernommen; Rückfluss in §Externes Sparring |
| **Amends** | Policies `claude-skills.md`, `platform-agents.md` — **erst bei Acceptance** |
| **Relates to** | ADR-229/230 (Skill-Distribution), ADR-233 (Worktree), ADR-280 (Lane-Konsolidierung), ADR-281 (Symlink) |

## Repo-Zugehörigkeit

| Repo | Rolle | Betroffene Pfade / Komponenten |
|---|---|---|
| `platform` | Primär | `docs/adr/`, `tools/cc-skill-dist/`, neue Registry-Generierung + CI-Gate, `~/.claude/policies/claude-skills.md`, `platform-agents.md` |
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

### 2.1 Zwei orthogonale Achsen — Heimat ist ihre *Funktion*, keine Zeile

Die frühere „vier sich ausschließende Fälle"-Tabelle wird ersetzt durch zwei unabhängige Dimensionen:

- **Geltungsbereich:** *plattformweit* ↔ *repo-spezifisch*
- **Ausführungsmodus:** *interaktiv-zustandslos* ↔ *stateful/langlebig* ↔ *headless/scheduled*

Die Heimat ergibt sich aus **beiden**:

| Modus \ Geltungsbereich | **plattformweit** | **repo-spezifisch** |
|---|---|---|
| **interaktiv-zustandslos** (Skill) | zentral `platform/skills/` → `cc-skill-dist` | `<repo>/.claude/skills/` (committed, nur dort aktiv; erreicht Cloud-Sessions) |
| **stateful/langlebig** (Prozess) | State-Machine in gemeinsamer App (dev-hub) **+** Treiber-Skill (zentral) **+** Registry | State-Machine in der Domänen-App (das Repo) **+** Treiber-Skill (repo-lokal) **+** Registry |
| **headless/scheduled** (Agent) | dev-hub Platform-Agent (`platform-agents.md`) | Domänen-Hub Celery-Task/Command |

Damit sind die vom Review benannten Mischfälle sauber abbildbar: ein **stateful Prozess kann repo-spezifisch** sein (Zeile 2, rechts), ein **headless Agent plattformweit** (Zeile 3, links).

### 2.2 Prozess-Muster: State · Treiber · Registry (drei Rollen, kein Prompt-Text)

Eine zustandsbehaftete Fähigkeit wird **nie** als Skill nachgebildet, sondern in drei Rollen zerlegt:

1. **State** — State-Machine + Frist + Audit-Trail + Transitionen in der **Domänen-App** (Django). Referenzimplementierung: risk-hub `DeletionRequest` (Betroffenenrechte, Art. 17).
2. **Treiber** — ein **dünner** Skill, der den Zustand über eine programmatische Schnittstelle (Management-Command/API) anlegt/fortschreibt. Referenz: `create_deletion_request` + `/mailcheck`.
3. **Registry-Eintrag** — der Prozess ist im Katalog geführt (§2.4), damit er auffindbar ist und nicht ad hoc neu erfunden wird.

Kein generisches Workflow-Substrat wird jetzt gebaut (YAGNI). **Schwelle für ein gemeinsames Substrat — duplikatsbasiert, nicht prozess-gezählt:** sobald **zwei** State-Machines nahezu identische Struktur (Frist-Feld, Auslöser, Akteure, Audit-Trail) duplizieren, ist die Extraktion einer geteilten Basis zu erwägen. Nicht „ab Prozess Nr. 3".

### 2.3 Governance-Regeln (Entstehung)

- **R1 — Scope-Entscheidung bei Anlage:** beide Achsen (§2.1) explizit benennen → Heimat folgt daraus.
- **R2 — Promotions-Schwelle:** erst Ad-hoc, Skill **nur bei Wiederholung** (Präzedenz: `read-mail` nach 4× Ad-hoc). Einmaliges wird nicht skill-ifiziert.
- **R3 — Dedup-Check gegen die Registry** vor jeder Anlage (setzt §2.4 voraus).

### 2.4 (d) Registry — Mechanismus, nicht Wunsch

| Frage | Festlegung |
|---|---|
| **Woraus generiert?** | Aus dem **Frontmatter** jeder Skill-/Workflow-/Agent-Datei (Name, Achsen, `owner_repo`, `state_backend` bei Prozessen) **plus** Repo-Scan aller `.claude/`-Verzeichnisse der Flotte. Keine Handpflege. |
| **Wer verifiziert?** | Ein **CI-Gate** in `platform` (`tools/cc-skill-dist/` erweitert): erzeugt die Registry deterministisch und **bricht den Build bei Drift** (Katalog ≠ Realität) — analog `doctor.py`. Kein manueller Review als Wahrheit. |
| **Wo lebt sie?** | **Zentral im `platform`-Repo** (eine generierte Datei, z.B. `docs/registry/skills.json` + `.md`), damit **cross-repo** dedupt werden kann. Repo-lokale Skills melden sich über ihr Frontmatter, werden aber zentral katalogisiert. |

Damit hat R3 (Dedup) etwas Abfragbares; „lügender Index" (bekannter Drift) wird durch die Generierung + das Gate strukturell verhindert.

### 2.5 (e) Retirement — R4, nutzungsbasiert

- **R4 — Retirement-Scan:** periodisch (z.B. monatlich, non-blocking) wertet Nutzung aus; **kein Aufruf seit N Monaten → Archiv-Kandidat** (N Startwert = 6, kalibrierbar). Archivierung/Löschung bleibt **human-gated** (kein Auto-Delete). Datenquelle: vorhandene Aufruf-Telemetrie (`llm_calls`/Session-Logs) bzw. ein leichter Nutzungszähler; die konkrete Quelle wird in der Umsetzung festgelegt, nicht hier erfunden.

### 2.6 (Erfolgsmaß) Woran man in 6 Monaten misst

| Kennzahl | Richtung | Quelle |
|---|---|---|
| Skills pro Repo (Verteilung) | stabil/sinkend, nicht monoton wachsend | Registry |
| Dedup-Trefferrate bei Anlage (R3) | > 0 heißt: Governance greift real | CI-Gate-Log |
| Ad-hoc → Skill-Promotions (R2) | dokumentiert, nicht 0 (sonst wird R2 umgangen) | PR-Historie |
| Unused-Count (R4-Kandidaten) | sinkend nach erstem Scan | Retirement-Scan |

---

## 3. Implementation Details (phasiert)

| Phase | Inhalt | Gate |
|---|---|---|
| 0 | Diese ADR (Taxonomie + Governance + Lifecycle) | dieser PR |
| 1 | Registry-Generator + zentraler Katalog (`docs/registry/`) aus Frontmatter + Repo-Scan | CI grün, Katalog = Realität |
| 2 | CI-Gate „Registry-Drift bricht Build" (analog `doctor.py`) | Negativtest: künstlicher Drift rötet |
| 3 | Frontmatter-Erweiterung (`axes`, `owner_repo`, `state_backend`) an Bestands-Skills nachziehen | Schema-Validate grün |
| 4 | Retirement-Scan (non-blocking, monatlich) + erster Bericht | Bericht liegt vor, 0 Auto-Deletes |
| 5 | **Bei Acceptance:** `claude-skills.md` + `platform-agents.md` um die zwei Achsen + Lifecycle ergänzen | Policies aktualisiert |

Aufgeschobenes bekommt je ein Tracking-Issue **im selben Zug** (House-Rule); Phasen 1–4 werden als Issues angelegt, nicht im ADR-Text „versprochen".

## 4. Consequences

**Positiv:** Prozesslogik bleibt in Apps (testbar), Skills bleiben dünn; repo-spezifisches liegt lokal (kein globales Rauschen, Cloud-erreichbar); Duplikate werden abfragbar; verwaiste Skills werden sichtbar; „Kanon" wird an Kennzahlen messbar.

**Negativ / Kosten:** ein Generator + ein CI-Gate + ein Scan sind zu bauen und zu warten; Frontmatter-Nachzug an ~52 Bestands-Skills; ein zusätzliches Governance-Ritual bei Anlage (R1/R3).

## 5. Risks

- **Registry-Gate zu streng → Reibung.** Mitigation: Phase 1/2 erst **SUGGEST/non-blocking**, Baseline sichten, dann gating (Präzedenz `feedback_advisory_scanner_reactivation_needs_baseline`).
- **Retirement-Fehlalarm löscht Genutztes.** Mitigation: **human-gated**, nie Auto-Delete; N kalibrierbar.
- **Frontmatter-Nachzug unvollständig → Katalog lückenhaft.** Mitigation: Schema-Validate + Gate erzwingen Vollständigkeit.

## 6. Confirmation / Rollout-Gate

- [ ] Registry deterministisch generiert; Katalog = Realität (Phase 1).
- [ ] CI-Gate rötet bei künstlichem Drift (Negativtest, Phase 2).
- [ ] Retirement-Scan liefert ersten Bericht, **0 Auto-Deletes** (Phase 4).
- [ ] Erfolgsmaße (§2.6) sind erhebbar (Kennzahl-Quellen existieren).
- [ ] Policies aktualisiert (Phase 5, erst bei Acceptance).

## 7. Externes Sparring — Rückfluss-Tagging

Diese ADR ist das direkte Ergebnis eines strukturierten Owner-Reviews (2026-07-23). Fünf Punkte, alle übernommen:

| # | Review-Punkt | Wirkung in dieser ADR |
|---|---|---|
| 1 | Scope-Tabelle vermischt zwei Achsen | §2.1 — zwei orthogonale Achsen, Heimat = Funktion (Matrix statt Lookup) |
| 2 | „Registry" unterspezifiziert | §2.4 — Quelle/Verifikation/Ort konkret (Frontmatter+Scan / CI-Gate / zentral) |
| 3 | Kein Retirement | §2.5 — R4 nutzungsbasiert, human-gated |
| 4 | Substrat-Schwelle unbegründet („3–4") | §2.2 — duplikatsbasiert (2 State-Machines mit identischer Struktur) |
| 5 | Kein Erfolgsmaß | §2.6 — 4 Kennzahlen mit Quelle |

## 8. Changelog

- 2026-07-23: Initial (proposed). Taxonomie (2 Achsen) + Prozess-Muster (State/Treiber/Registry) + Governance R1–R4 + Registry-Mechanismus + Retirement + Erfolgsmaße. Basiert auf Owner-Review (§7). Referenz-Implementierung Betroffenenrechte: risk-hub `DeletionRequest` (#449) + `/mailcheck` (#1383).
