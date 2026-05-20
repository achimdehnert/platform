---
id: ADR-211
title: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)
status: accepted
date: 2026-05-19
deciders: [achim]
informed: [all-repos]
domains: [ux, requirements, process, security, drift-prevention]
supersedes: []
amends: []
depends_on: []
tags: [klickdummy, mockup, requirements-spec, parity-test, prod-guard, convention]
scope:
  include_paths:
    - "policies/klickdummy.md"
    - "scripts/checks/klickdummy_*.sh"
    - "**/klickdummy/**"
---

# ADR-211: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)

- **Status:** accepted *(2026-05-19, Decider-Ratifizierung des Entscheids I1–I4 + Enforcement-Pfad; Adoption-Scoreboard SF1–SF6 läuft separat und gatet den Status NICHT — siehe Acceptance-Trigger)*
- **Datum:** 2026-05-19
- **Entscheider:** Achim Dehnert
- **Verwandt:** risk-hub:ADR-046, writing-hub:ADR-180, meiki-hub:ADR-020
- **Adversarial reviews:** fünf Cascade-Pässe (Rev 2/3/4/9 + Rev 10), siehe Revisionshistorie

## Zusammenfassung

Mehrere Repos bauen „Klickdummies". Der naheliegende Rahmen — „jeder macht
sein Ding, wir teilen Vokabular" — wäre **keine Entscheidung** (per
`adr-threshold.md` reichte eine Konvention). Dieses ADR trifft drei harte,
erzwingbare Entscheidungen, weil jede einen realen Schaden verhindert:

1. **Spec-zentriert statt Renderer-zentriert.** Dauerhaftes Artefakt ist die
   **maschinenlesbare Anforderungs-Spec**, nicht ihre Darstellung. Ein
   Klickdummy *rendert* sie; ein Parity-Test ist das Konformitäts-Gate.
2. **Mock-Prototyp ≠ Demo-Render — harter, plattform-extern geprüfter
   Prod-Guard.** Ein Demo-Render der *echten* App (`?demo=<state>`) ist eine
   **Prod-Sicherheitsfläche**.
3. **Parity-grün ist die Off-Ramp, mit TTL.** Parity-grün pro Screen ⇒
   statische Quelle mechanisch entfernt — beendet das „Static-Leichen"-Muster
   auch im Dauer-Staging.

Die drei *Schaden-Entscheidungen* entsprechen den Invarianten I1–I3; **I4
(Namensraum)** ergänzt sie als Drift-Schutz für Cross-Repo-Refs.
Implementierungs-Stack bleibt repo-lokal; alle vier Invarianten sind
ansatz-offen.

## Kontext

Ist-Lage (2026-05-19): meiki-hub (Manifest-Single-File-Mock, CI-Invariante),
writing-hub (`?demo=`-Render echter Templates + Parity, ADR-180), risk-hub
(Spec-Driven UI Convention, repo-lokal, ADR-046 Rev 2). Drei Formen, kein
gemeinsamer „fertig"-Begriff. Die Mehrdeutigkeit „klickdummy"/„ADR-180" über
Repo-Grenzen verursachte in dieser Session eine konkrete Fehlzuordnung —
Drift-Episode `2026-05-19-klickdummy-adr180-collision`, **belegt** als
Drift-Memory (meiki-hub-Auto-Memory, `drift: true`) **und** Followup-Issue
`adr-211-followup/SF5`, nicht nur hier erzählt (R5).

> **Selbsttest gegen `adr-threshold.md`:** kehrt den Status quo repo-autonomer
> Klickdummy-Proliferation um, adressiert eine **Sicherheitsfläche**
> (Demo-Render in Prod), cross-cutting über ≥ 3 Repos → Pflicht-Kriterien
> erfüllt, echte Entscheidung.

## Entscheidung — vier Invarianten (ansatz-offen)

| # | Invariante | Erzwingung |
|---|---|---|
| **I1 Spec-first** | Maschinenlesbares, versioniertes Spec-Artefakt (YAML/JSON/strukturiertes Frontmatter); Markdown-Bullets zählen nicht. Klickdummy rendert es, ist nicht die Quelle. **Bidirektionale Coverage:** jede Impl-Route hat einen Spec-Eintrag *und* jeder Spec-Eintrag eine Route/Screen — kein einseitiges „Datei existiert & rendert". | `make -C <repo> klickdummy-i1` (Exit-Code), CI-verifiziert — prüft Spec↔Route-Coverage, nicht nur Spec==Render |
| **I2 Prod-Sicherheit** | Genau eine Klasse je Klickdummy, **explizit deklariert**: **Mock-Prototyp** (kein Backend; Systemgrenzen als Target-Mock) ODER **Demo-Render** (env-gegated; in Prod nicht erreichbar). „Keine Klasse deklariert" ist I2-Verstoß (kein vacuous pass). | **Zwei Schichten:** (a) repo-definierter `make -C <repo> klickdummy-i2` (Selbstaussage); (b) **plattform-externer, repo-unabhängiger Prod-Probe** `klickdummy_prod_guard.sh` gegen die Registry-Prod-URL: `?demo=<state>` live ⇒ 404/disabled. (b) ist das **bindende Cross-Repo-Signal** — die Behauptung wird adversarial extern getestet, nicht dem Repo-Selbstcheck geglaubt (F3) |
| **I3 Lebenszyklus + TTL** | **A ohne Zielsystem:** endet bei dok. Fachabteilungs-Review → ADR `accepted-frozen`/`superseded`, Spec eingefroren, Pfad `klickdummy/archive/`. **B Transition:** ab erstem Screen mit Impl-Route greift I3 je Screen. **C mit Zielsystem:** Doppelquelle endet bei **`min(prod-Release, Parity-grün + N Tagen)`** (N Default **30 d**, repo-tunbar) — schließt das „ewig auf Staging"-Leck (F4). Staging ist erlaubter Doppelquell-Raum *innerhalb* der TTL. | `make -C <repo> klickdummy-i3`: assert je Screen mit Impl-Route + grünem Parity ⇒ statische Quelle abwesend, sobald prod-Release **oder** Parity-grün-Alter > N |
| **I4 Namensraum** | Klickdummy-ADRs tragen reserviertes Titel-Präfix; Cross-Repo-Refs **nur** `repo:ADR-NNN` (inkl. `conforms_to: platform:ADR-211`). Drift-Schutz (vgl. Drift-Memory `klickdummy-adr180-collision`). | `platform/scripts/checks/adr_cross_repo_refs.sh` (plattformseitig, kein repo-Make-Target — generischer ADR-Lint) |

**Auswahlhilfe (illustrativ):** Konzeptphase ohne Backend → Mock-Prototyp
(meiki-hub:ADR-020). App-Repo mit Zielsystem → Demo-Render + Parity
(writing-hub:ADR-180). UI-Spec primär → Spec-Driven (risk-hub:ADR-046).
KI-generiert/Figma-as-Spec zulässig, sofern I1–I4 erfüllt.

### Was repo-lokal bleibt
Tech-Stack, Schema, UI-Bausteine, Teststack. risk-hub:ADR-046 behält seine
Repo-Lokalität; dieses ADR ersetzt keine Implementierungs-ADR.

### Hinweis zu I4-Scope (Rev 10)
I4 ist hier *klickdummy-skopiert* (Refs in den Klickdummy-ADRs und
`conforms_to`-Felder). Eine plattformweite Verallgemeinerung des
Cross-Repo-Ref-Formats wäre ein **eigener** ADR — sie gehört **nicht** in
ADR-207 (Doku-Strategie/Ingest), wie Rev 9/F5 fälschlich annahm.

## Enforcement-Pfad

Mechanik exakt wie `policies/README.md` (Rev 5 — keine Erfindung eines
Parallelpfads):

1. **Rationale:** dieses ADR.
2. **SSoT (versioniert):** `platform/policies/klickdummy.md` — im Plattform-Repo,
   reviewbar; Änderung **nur per platform-PR + Changelog-Bump**.
3. **Injektion (operativ):** `~/.claude/policies/klickdummy.md` ist ein
   **Symlink** in einen gepinnten platform-Worktree (`~/github/platform-pinned/policies/`),
   denselben Mechanismus wie `adr-threshold.md`/`llm-routing.md`;
   `inject_policies.py`/`claude-policy` lesen den Symlink unverändert. **Kein
   Kopier-Sync.** Der gepinnte Worktree zieht beim nächsten Refresh nach; das
   Scoreboard-Item S6 erkennt einen *stale gepinnten Worktree*.
4. **Adoption:** `onboard-repo`-Skill prüft I1–I4 + ADR-Header + `make klickdummy-{i1,i2,i3}` (I4 plattformseitig via Lint, siehe S5).
5. **Verifikation:** `platform/scripts/checks/klickdummy_registry.sh` über `registry/repos.yaml`.

## Acceptance-Trigger (F1/F2 — Entscheidung ≠ Rollout)

**Kategorienkorrektur (Rev 9):** Frühere Revisionen verwechselten
„Entscheidung getroffen" mit „flottenweit ausgerollt & grün". Das erzeugte
einen **Deadlock** (das Acceptance-Gate verlangte die gemergte Policy, deren
Merge an der Acceptance hing) und einen **mit der Flotte oszillierenden
Status**. Korrektur:

- **`status: accepted`** ⇔ der *Entscheid* (I1–I4 + Enforcement-Pfad) ist von
  den Decidern ratifiziert (Review dieses ADR). Das Mergen von
  `policies/klickdummy.md` ist **Teil des Acceptance-Akts**, keine
  Vorbedingung. Kein zirkulärer Fixpunkt.
- **C1–S6** (vormals „Confirmation C1–C6") sind ein **separates, lebendes
  Adoption-Scoreboard** in `adr-211-followup` (SF1–SF6). Es trackt den
  Rollout-Fortschritt und **gatet `status` nicht** — eine akzeptierte
  Architekturentscheidung ist stabil, nicht eine Funktion fortlaufender
  Flotten-Drift.

## Adoption-Scoreboard (lebend, nicht status-gatend)

> Baseline 2026-05-19: 0/6. Fortschritt in `adr-211-followup` SF1–SF6.
> Reihenfolge frei; keiner blockt die Acceptance des Entscheids.

```bash
# S1 Registry-Konformität (SF1)
platform/scripts/checks/klickdummy_registry.sh
#   GELTUNGSBEREICH: nur in registry/repos.yaml gelistete (achimdehnert-)Repos.
#   Andere Orgs (z. B. meiki-lra:meiki-hub) NICHT abgedeckt — Repo-CI verantwortet.
#   Konformität = Repo-ADR-Frontmatter `conforms_to: platform:ADR-211`.

# S2 I1 Spec↔Route-Coverage je Repo (SF2)
make -C <repo> klickdummy-i1

# S3 I2 Prod-Guard — ZWEISCHICHTIG (SF3)
make -C <repo> klickdummy-i2                              # (a) Repo-Selbstaussage
platform/scripts/checks/klickdummy_prod_guard.sh <repo>  # (b) externer Prod-Probe,
#   registry-URL + '?demo=' ⇒ erwartet 404/disabled. (b) ist bindend, repo-unabhängig.

# S4 I3 Off-Ramp mit TTL, Grenze = min(prod-Release, Parity-grün + N d) (SF4)
make -C <repo> klickdummy-i3

# S5 I4 Cross-Repo-Ref-Format (Rev 10: zurück in ADR-211; F5 zurückgenommen)
platform/scripts/checks/adr_cross_repo_refs.sh
#   Validiert qualifizierte Cross-Repo-Refs (^[a-z][a-z0-9-]+:ADR-[0-9]{3}$).
#   Klickdummy-skopiert; plattformweite Verallgemeinerung wäre eigener ADR.

# S6 Policy-SSoT existiert UND gepinnter Worktree nicht stale (SF6)
platform/scripts/checks/klickdummy_policy_sync.sh
#   FAIL wenn SSoT fehlt ODER Injektions-Ziel fehlt/weicht ab (staler Pinned).
#   SKIP (exit 0) ohne ~/.claude/policies (off-machine CI); --strict ⇒ FAIL.
```

## Konsequenzen

**Positiv:** Spec-first beendet Renderer-Wildwuchs; Off-Ramp+TTL verhindert
Static-Leichen auch im Dauer-Staging; der **extern geprüfte** Demo-Render-
Prod-Guard schließt die Sicherheitslücke *cross-repo verifizierbar* (nicht
nur per Repo-Selbstaussage); Entscheid/Scoreboard-Trennung macht den Status
stabil und löst den Acceptance-Deadlock; Enforcement nutzt den bestehenden
Pinned-Worktree-Symlink (policies/README.md), kein Parallelpfad.
**Negativ:** je Repo einmaliger Aufwand `make klickdummy-{i1..i3}`; der
plattform-externe Prod-Probe (S3b) braucht eine erreichbare Registry-Prod-URL
je Demo-Render-Repo; 6 SF-Followups sind Rollout-Aufwand (aber **nicht**
Acceptance-blockierend).
**Governance-Risiko (F8, offen):** security-perimeter + org-bindend, aber
`deciders:[achim]`, `consulted:[]`. Eine per-Vertrauen nicht erzwingbare
Sicherheitsregel (Grund für den externen S3b-Probe) mit Bus-Faktor 1 ist
fragil — **mind. ein `consulted` empfohlen** vor `accepted`.
**Abhängigkeit (F7, Rev 10 angepasst):** `depends_on: []` — die in Rev 9
behauptete Abhängigkeit zu ADR-207 war Konsequenz der Fehl-Auslagerung F5
(siehe Rev 10). ADR-207 ist Doku-Strategie/Ingest, kein Namensraum-Heim.

## Glossar (lokal)

| Begriff | Definition |
|---|---|
| **Anforderungs-Spec** | Versioniertes, maschinenlesbares Quell-Artefakt (YAML/JSON/Frontmatter); Markdown-Bullets zählen nicht |
| **Klickdummy** | Oberbegriff: *Renderer* der Spec zur frühen Validierung |
| **Mock-Prototyp** | Wegwerf-Renderer ohne Backend (Target-Mock-Systemgrenzen) |
| **Demo-Render** | Env-gegateter Zustand der echten App (`?demo=`) — Prod-Sicherheitsfläche |
| **Parity-Test** | Renderer↔Implementierung-Äquivalenztest — Gate **und** Off-Ramp |
| **Off-Ramp** | Parity-grün ⇒ mechanische Entfernung der statischen Quelle (Grenze: `min(prod-Release, Parity-grün + N d)`) |
| **Adoption-Scoreboard** | Lebende SF1–SF6-Rollout-Metrik; **gatet `status` nicht** (Rev 9) |

## Acceptance-Trigger

`status` → `accepted`, sobald die Decider den **Entscheid** (I1–I4 +
Enforcement-Pfad) im Review ratifizieren; das Mergen von
`policies/klickdummy.md` ist Teil dieses Akts. Das Adoption-Scoreboard
(SF1–SF6) ist **kein** Acceptance-Vorbehalt (Rev-9-Korrektur von F1/F2).
(Im Frontmatter bewusst kein Custom-Feld — Schema lässt nur Standard-
Properties zu; Acceptance-Logik im Body.)

## Revisionshistorie

Fünf Cascade-Adversarial-Pässe + Schema-/YAML-Härtung:

- **Rev 1** — initial proposal
- **Rev 2** (bf7c4d6) — Spec-first, Prod-Guard, Parity-Off-Ramp
- **Rev 3** (47ff4f9) — Enforcement in-repo, I1/Confirmation executable
- **Rev 4** — R4 prod-Grenze, R3 repo-definierte Checks, R2 Baseline 0/N, R5 Drift belegt, R6 Acceptance-Trigger
- **Rev 5** — Mechanik: `~/.claude/policies` Symlink in gepinnten platform-Worktree (kein Kopier-Sync)
- **Rev 6** — C1-Geltungsbereich (nur registry-Repos); `conforms_to` I4-qualifiziert; SF1-Regex + SF5
- **Rev 7** — C6 auf Script `klickdummy_policy_sync.sh`; SF6
- **Rev 8** — Frontmatter schema-konform (`review_history`/`acceptance_trigger` in Body; YAML-`date:`-Fix)
- **Rev 9 (tiefer Adversarial-Pass)** — **F1/F2:** Entscheid ↔ Rollout entkoppelt (löst Acceptance-Deadlock + oszillierenden Status; C1–C6 → status-neutrales Adoption-Scoreboard). **F3:** I2 um plattform-externen, repo-unabhängigen Prod-Probe erweitert (Sicherheitsinvariante cross-repo verifizierbar statt per-Vertrauen). **F4:** I3 Off-Ramp-TTL `min(prod-Release, Parity-grün+N d)` (Dauer-Staging-Leck). **F5:** I4 → ADR-207 ausgelagert, `scope` entschlackt, „vier"→„drei Invarianten". **F6:** I1 bidirektionale Spec↔Route-Coverage statt Format-Existenz. **F7/F8** als offene Punkte dokumentiert.
- **Rev 10** — **F5 zurückgenommen:** ADR-207 ist Doku-Strategie/Ingest-Trichter (eine Doku-Wahrheit pro Repo, MD>PDF>docx, inbox-Trichter) — **nicht** Cross-Repo-ADR-Namensraum. Die I4-Auslagerung war thematische Fehl-Zuordnung. **I4 zurück in ADR-211** (klickdummy-skopiert; eine plattformweite Verallgemeinerung wäre ein eigener ADR, nicht ADR-207). `depends_on: []`, „drei"→„vier Invarianten" zurück, ADR-207 aus Verwandt/Bezug entfernt (war nur wegen F5 drin).

## Bezug

- risk-hub:ADR-046 · writing-hub:ADR-180 · meiki-hub:ADR-020 (Implementierungen)
- Followups `adr-211-followup` SF1–SF6 (Adoption-Scoreboard-Baseline 0/6, **nicht status-gatend**)
- Drift-Memory `2026-05-19-klickdummy-adr180-collision` (meiki-hub-Auto-Memory, `drift: true`)
- Policy `adr-threshold.md` (Selbsttest)
