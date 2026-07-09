---
id: ADR-267
title: Review-Requirement für Deploy-Approvals — deterministisches Fail-Closed-Gate + HITL-Lern-Vorschlagsschicht (Cross-Repo)
status: accepted
date: 2026-07-08
deciders: [achim]
informed: [all-repos]
domains: [security, process, governance, deployment, drift-prevention]
supersedes: []
amends: []
depends_on: [KONZ-platform-014, ADR-268]
tags: [approvals, deploy, review-policy, segregation-of-duties, fail-closed, hitl, codeowners, environments]
scope:
  include_paths:
    - "**/.github/CODEOWNERS"
    - "**/.github/workflows/deploy.yml"
    - "dev-hub/apps/operations/**"
---

# ADR-267: Review-Requirement für Deploy-Approvals — deterministisches Fail-Closed-Gate + HITL-Lern-Vorschlagsschicht (Cross-Repo)

- **Status:** accepted *(2026-07-08. Richtung Owner-bestätigt; nach zwei externen Zweitmeinungen substanziell überarbeitet (§Externe Zweitmeinung). Der externe Kern-Einwand **PRE-A** (Token-/Reviewer-Identität) ist durch **stehende Betriebspraxis** aufgelöst — s. §0 —, nicht offen. Enforcement-Grenze: dieses ADR beschreibt das Modell — scharf wird es erst mit den unter §Umsetzung genannten Änderungen.)*
- **Datum:** 2026-07-08
- **Entscheider:** Achim Dehnert
- **Verwandt:** KONZ-platform-014 (Deploys & Approvals Board), dev-hub#117 (Stufe A/B-lite), dev-hub#118 (Stufe B One-Click-Approve)
- **Externe Sparring:** zwei unabhängige externe LLM-Reviews (2026-07-08); Befund-Tagging + PRE s. §Externe Zweitmeinung.

## Zusammenfassung

Das Deploys-&-Approvals-Board (KONZ-platform-014) erlaubt ab Stufe B, wartende
Deployments **cross-repo** (achimdehnert + iilgmbh) freizugeben. Governance-Frage:
**Welche Deploys brauchen eine menschliche Zweitmeinung (Reviewer `wirdigital`),
welche nicht?** Owner-Setzung: **wichtige Entscheidungen sind reviewpflichtig; reine
Docs-Updates o.ä. nicht.**

Zwei harte Entscheidungen:

1. **Das „reviewpflichtig?"-Gate ist deterministisch und fail-closed** — eine deklarative,
   **restriktiv-per-Default** Pfad-Policy, ausgewertet von **genau einem Klassifikator**,
   verankert **GitHub-nativ**, **nicht** ein lernendes/probabilistisches Modell.
2. **Der „Lern"-Wunsch wird als reine Vorschlags-Schicht (HITL) realisiert** — und erst in
   **Phase 2** (nach belegtem Pflegeschmerz). Sie **schlägt** Policy-Verfeinerungen zur
   **menschlichen Ratifizierung** vor, verschiebt das Gate nie autonom, entscheidet nie eine
   einzelne Freigabe.

## Kontext & Problem

- **Auslöser:** Stufe B (dev-hub#118) gibt One-Click über den bestehenden **geteilten
  achimdehnert-`GITHUB_TOKEN`** frei (führend: achimdehnert + iilgmbh). `wirdigital` ist
  **menschlicher** Zweitmeinungs-Reviewer, keine Token-Identität.
- **Governance-Fork-Risiko:** Ein Board-Approve darf den effektiven Approver-Kreis nicht auf
  „jeder Staff in devhub" ausweiten und GitHubs Reviewer-ACL nicht durch eine schwächere
  Parallel-ACL ersetzen. SoD (Vier-Augen) darf nicht zum Theater werden.
- **Offene Frage:** *Wo* verlangt ein Deploy die Zweitmeinung? Ohne klare Regel entweder
  Reibung (alles reviewpflichtig) oder Löcher (Wichtiges rutscht als „docs-only" durch).

## Entscheidungstreiber

- **Fail-closed:** Unbekannt/unklassifiziert ⇒ reviewpflichtig (nie das Gegenteil).
- **Determinismus & Auditierbarkeit:** jede Gate-Entscheidung reproduzierbar & nachvollziehbar.
- **Single Source of Truth (echt, nicht aspirativ):** **eine** Policy-Datei, **ein** Evaluator —
  Badge und Enforcement dürfen die Liste nicht unabhängig zweimal interpretieren.
- **Cross-Repo:** gilt für alle Repos beider Orgs — inkl. **neu angelegter** Repos (die dürfen
  nicht still fail-**open** sein, bis jemand sie konfiguriert).
- **Verfügbarkeit:** ein einziger Zweit-Reviewer darf nicht zum org-weiten Deploy-Freeze führen.
- **Adaptivität ohne Autonomie:** Regel-Pflege darf lernen — aber nur *vorschlagend*.

## Betrachtete Optionen

| Option | Gate-Mechanismus | Bewertung |
|--------|------------------|-----------|
| **A — Reiner Lern-Mechanismus** | ML/Heuristik klassifiziert & wendet an | ❌ verworfen: probabilistisches Gate für eine Sicherheitskontrolle, fällt im Zweifel offen. |
| **B — Nur GitHub-nativ, ohne Lerner** | Environment-Rules + CODEOWNERS + Klassifikator | ✅ **wird Phase 0** — bei 1+1-Skala vollwertig; der Lerner ist ein späteres Delta, kein Startzwang. |
| **C — Deterministisch (fail-closed) + HITL-Lern-Vorschlag** | wie B **plus** spätere Vorschlagsschicht | ✅ **Zielbild, zweiphasig** (B zuerst, C sich verdienen). |

## Entscheidung

**Option C, zweiphasig ausgerollt (B als Phase 0).**

**§0 — Token-/Reviewer-Identität (PRE-A) — durch stehende Praxis aufgelöst.**
Der externe Review sah hier den kritischsten Punkt. Er ist **kein offener Unbekannter**, sondern
**gelebte Betriebspraxis**: achimdehnert (+ iilgmbh) ist die handelnde/führende Identität; der
`wirdigital`-Zweitmeinungs-Review wichtiger Deploys läuft seit Langem **direkt in GitHub** und ist
über die Environment-Reviewer-Konfiguration verankert. Daraus die explizite Auflösung:
- Der achimdehnert-Token gibt **nur** Environments frei, für die er selbst Reviewer ist
  (`current_user_can_approve=true`). Wo eine **Zweitmeinung** verlangt ist, hält GitHub den Deploy
  bis `wirdigital` **manuell** zustimmt — das Board-One-Click kann das **nicht** umgehen.
- Damit ist der gewollte **Split** (Token handelt, wo berechtigt; `wirdigital` second-opinion-t das
  Wichtige) **kein** Vier-Augen-Theater, sondern die bestehende Kontrolle — hier nur **explizit
  festgehalten** (vorher implizit).

*(Verifizierbarkeit: die stehende Praxis ist die Evidenz; ein zusätzlicher Wegwerf-Test an einem
`wirdigital`-required Environment kann das jederzeit bestätigen, ändert die Auflösung aber nicht.)*

**§1 — Deterministische Pfad-Policy als Gate (restriktiv per Default, fail-closed, TIER-abhängig).**
Ein Deploy ist *nicht* reviewpflichtig **nur** wenn *alle* geänderten Pfade auf der für dieses Repo
geltenden **Review-frei-Allowlist** liegen. Diese Allowlist, die `wirdigital`-Pflicht und die
Kill-Reaktion sind **nicht flach**, sondern kommen aus **`f(Projektart, Reife-Phase)` gemäß
ADR-268** (Assurance-Tiers): ein privater/Prototyp-Deploy ist großzügig, ein Government-Prod-Deploy
maximal streng, und *vor* Prod/echten Daten ist die Strenge für alle Klassen gedeckelt. Das Repo-Tier
kommt aus der verbindlichen Registry (ADR-268 SSoT; fehlt es → T5, fail-closed). Präzisierungen:
- **Restriktiver Default:** die Allowlist enthält **nur nachweislich inerten Inhalt**
  (`*.md`-Prosa, `CHANGELOG.md`). **Build-/config-ausführende Dateien sind ausgenommen** —
  `mkdocs.yml`, Docs-Hooks, CI-/Workflow-Config sind Code-Execution-Fläche, **nie** review-frei,
  unabhängig von der Endung.
- **`docs/**` ist NICHT automatisch review-frei** — in Repos, die daraus produktive Artefakte
  publizieren, ist `docs/**` deploy-relevant. Default restriktiv + **repo-spezifische
  Risiko-Ausnahmen**, nicht ein globaler Glob für alle.
- **Autoritative Diff-Quelle festgelegt:** maßgeblich ist der **PR-Head-vs-Base-Diff** (bzw. bei
  direktem Push die Compare-Range des auslösenden `deploy.yml`-Run-SHA). Diese **Diff-Referenz +
  die Policy-Version** werden im Audit gespeichert (M28-2: „warum war das review-frei?" muss 2028
  beantwortbar sein).
- **Fail-closed an den Rändern:** leere/unbekannte Diffs, >300-Dateien-Fälle (GitHub-Path-Filter-
  Cap) ⇒ reviewpflichtig. Der **gegatete** Deploy ist der **Default, der immer läuft**; der
  Docs-Fast-Path wird **nur bei positivem, verifiziertem Docs-only-Signal** gewählt — **nie** durch
  bloßes Ausbleiben eines Filter-Treffers.

**§2 — Verankerung GitHub-nativ, EINE normative Variante, EIN Klassifikator (SSoT).**
- **Normativ (nicht Auswahlmenü):** getrennte Deploy-Klassen — `deploy-docs` (ohne
  Production-Environment) vs. `deploy-production` (mit Required Reviewer `wirdigital`). Die
  **Architektur** entscheidet den Deploy-Typ, nicht nur Dateipfade. Keine mehreren
  halb-äquivalenten Mechanismen (`paths-ignore` *und* CODEOWNERS *und* Badge) nebeneinander.
- **Ein geteilter, unit-getesteter Klassifikator** (Composite-Action) konsumiert `review-free-paths`
  als **einzigen** Input und erzeugt **sowohl** die Board-Badge-Berechnung **als auch** das
  Workflow-Routing — Drift zwischen Advisory und Enforcement ist damit strukturell unmöglich.
- Das Board umgeht die ACL nie — `current_user_can_approve` bleibt letzte Instanz.

**§3 — Board klassifiziert nur advisorisch (neutral formuliert).**
Badge-Text neutral: **„Policy-Auswertung: review-frei laut Policy vX"** (nicht „docs-only", das
sonst als Freigabe-*Empfehlung* gelesen wird). Bei jeder Freigabe werden die **maßgeblichen Pfade +
die Policy-Version** angezeigt. Der Badge liest **denselben** Klassifikator wie das Gate (§2) —
keine abweichende gecachte Wahrheit. One-Click nur bei `current_user_can_approve=true` **und**
Portal-seitiger Berechtigung der angemeldeten Person.

**§4 — HITL-Lern-Vorschlagsschicht (Phase 2, erst bei belegtem Bedarf).**
Erst **nachdem** manuelle Allowlist-Pflege nachweislich weh tut. Dann: Auswertung der
`ApprovalAction`-Audit-Spur; jeder Vorschlag braucht eine **Harmlosigkeits-Begründung des Pfads**
(nicht bloß „wurde oft schnell freigegeben"). Vorschläge landen als **PR gegen die Allowlist**
(menschlicher Merge). **Kein Auto-Apply, keine autonome Gate-Verschiebung.**

**Kernsatz:** Das Gate ist deterministisch + fail-closed + von *einem* Klassifikator ausgewertet;
der Lerner (Phase 2) schlägt nur begründete Regeländerungen zur menschlichen Ratifizierung vor.

## Konsequenzen

**Positiv:** deterministisch/auditierbar/fail-closed; **echte** SSoT (ein Klassifikator); reibungsarm
für inerte Docs ohne Löcher; Verfügbarkeit via Break-Glass; Adaptivität ohne autonome Gate-
Verschiebung; cross-repo inkl. neuer Repos.

**Negativ / bewusst getragen:** Pfad ist ein **Proxy** für „Wichtigkeit" — docs-förmige-aber-
folgenreiche Änderungen deckt nur die Build-Config-Ausnahme + restriktiver Default + (optional)
ein Risiko-Manifest ab; Allowlist-Pflege bleibt (Phase-2-Lerner mildert); die Akteurs-Identität
lebt **bauartbedingt** in der Board-lokalen Audit-Spur (geteilter Token), Policy/Gate in GitHub —
das ist **zwei Wahrheiten mit klarer Aufteilung**, im ADR explizit besessen (M28-5), keine Drift.

## Umsetzung (zweiphasig, cross-repo, je gegated)

- **Vorbedingung:** PRE-A (§0) empirisch klären.
- **Phase 0 (= Option B):** `review-free-paths.yml` (restriktiv) + geteilter Klassifikator +
  `deploy-production`-Environment mit Required Reviewer + `deploy-docs`-Pfad. **Org-Bootstrap:**
  Org-Ruleset / Template-Repo, das **jedes neue Repo bei Anlage garantiert fail-closed** stellt
  (Production-Environment + Required Reviewer vorkonfiguriert); bis dahin dokumentieren, dass
  unkonfigurierte Repos außerhalb des Gates liegen.
- **Break-Glass:** zeitbegrenzter, voll auditierter Notfall-Deploy → **Auto-Incident** +
  **verpflichtender retroaktiver `wirdigital`-Review**. Das ist ein *kontrolliert-geloggter*,
  nachgelagert geprüfter Pfad — **nicht** stilles Fail-Open — gegen den Reviewer-SPOF (M28-1).
- **Reviewer-Responsiveness sichtbar:** das Board alertet ab N Stunden auf alternde *gegatete*
  Approvals, damit fail-closed nicht still den 3-Tage-Block-Vorfall neu erzeugt (M28-2).
- **Kill-Switch getestet:** „alles reviewpflichtig" ist ein **dokumentierter, getesteter, schnell
  aktivierbarer** Modus **bevor** review-freie Deploys produktiv erlaubt werden — kein
  Workflow-Reparieren im Incident.
- **Phase 1:** Advisory-Badge (neutral). **Phase 2:** HITL-Lerner (nur bei belegtem Pflegeschmerz).

**Ehrliche Enforcement-Grenze:** Bis Phase 0 gemergt ist, ist dies ein *Modell*, kein erzwungenes
Gate. Kein Schritt mit org-weitem Deploy-/Approve-Effekt wird solo gemergt (autonomy-gate).

## Kill-Gate / Review

- **review_by:** 2026-10-08.
- **Fail-open-Erkennung (definiert):** ein wiederkehrender Audit vergleicht die als „review-frei"
  klassifizierten Deploys stichprobenartig gegen ihren **tatsächlichen** Diff. Ein belegter Fall
  „reviewpflichtig, aber als docs-only durchgelaufen" ist **immer** ein protokolliertes Ereignis;
  die Reaktion ist **tier-gestaffelt und repo-lokal gemäß ADR-268** (nicht der frühere flache
  Plattform-Freeze): der Fast-Path *dieses* Repos wird abgeschaltet, bei T4/T5 zusätzlich
  Incident + `wirdigital`-Sign-off. Aufhebung stets per geprüftem PR (Ursache behoben +
  Fast-Path reaktiviert). Kein globaler Schalter — die niedrigen Tiers bremsen das System nie.
- **Reibungs-Kill:** >30% „False-Reviewpflichtig" im ersten Quartal ⇒ Allowlist/Policy überarbeiten.
- **Lern-Schicht-Kill (skalenbewusst, korrigiert):** **nicht** „<20% ratifiziert ⇒ Versagen" — eine
  *stabile* Allowlist ohne neue Vorschläge ist **Erfolg**. Kill nur, wenn die Schicht **schädlich**
  wird (Rauschen/Over-Proposing, das Ratifizierung zur Last macht) → abschalten, Policy bleibt.

## Externe Zweitmeinung (2026-07-08)

`external_sparring_by: two-external-llms @ 2026-07-08` (im Body statt Frontmatter — der
`iil-adrfw`-Schema-Validator kennt den Key noch nicht).

Zwei unabhängige externe LLM-Reviews (Provider-Diversität, via `/adr-handoff-extern`). Beide:
**„Überarbeiten"** (Richtung tragfähig; Umsetzbarkeit auf GitHub-Primitiven schärfen). Befund-Tagging
(nur `[valid]` eingearbeitet; Review-A- und Review-B-IDs zusammengeführt):

| Thema | Review-IDs (A/B) | Verdikt | Eingearbeitet als |
|-------|------------------|---------|-------------------|
| **Token vs. Required-Reviewer-Identität** | B-AD-1, B-REC-1 | ✅ valid (kritisch) — **durch stehende Praxis aufgelöst** | **§0** (Split explizit; kein SoD-Theater) |
| **Echte SSoT: eine Policy, ein getesteter Klassifikator (Badge+Routing)** | A-AD-2, A-AD-4, A-REC-1, B-AD-2, B-REC-2, B-OOTB1, A-M28-1, M28-7 | ✅ valid | **§2** (Composite-Action-Klassifikator) |
| **Autoritative Diff-Quelle + im Audit speichern (Referenz+Policy-Version)** | A-AD-5, A-M28-2, A-REC-2, B-AD-3, B-REC-3 | ✅ valid | **§1** (PR-Head-vs-Base + Audit) |
| **paths-ignore nicht fail-closed → gegateter Deploy ist Default** | B-AD-3, A-OOTB2 | ✅ valid | **§1/§2** (positives Docs-Signal statt Filter-Ausbleiben) |
| **Build-/Config-Dateien aus Allowlist ausnehmen** | B-AD-4, B-REC-4, A-AD-1 | ✅ valid | **§1** (inert vs. build-executing) |
| **`docs/**` nicht auto-safe; restriktiver Default + repo-Ausnahmen** | A-AD-3, A-REC-3 | ✅ valid | **§1** |
| **Zwei Deploy-Klassen als normative Variante** | A-AD-2, A-REC-4, A-OOTB2, B-REC-3 | ✅ valid | **§2** (`deploy-docs`/`deploy-production`) |
| **Break-Glass gegen Reviewer-SPOF (auditiert, retroaktiv)** | A-M28-6, A-REC-10, B-M28-1, B-REC-5 | ✅ valid | **Umsetzung** (Break-Glass) |
| **Reviewer-Responsiveness sichtbar (Alert auf alternde Approvals)** | B-M28-2, B-REC-8 | ✅ valid | **Umsetzung** |
| **Neue Repos fail-closed by default (Org-Bootstrap)** | B-M28-3, B-REC-6 | ✅ valid | **Umsetzung** (Org-Ruleset/Template) |
| **Zweiphasig: B zuerst, Lerner sich verdienen** | A-AD-9, A-REC-9, B-AD-6, B-REC-7, A-OOTB3, B-OOTB2/3 | ✅ valid | **Optionen/§4/Umsetzung** (Phase 0→2) |
| **Lern-Kill skalenbewusst (nicht <20%)** | B-M28-4, B-REC-7 | ✅ valid | **Kill-Gate** (korrigiert) |
| **HITL-Vorschlag braucht Harmlosigkeits-Begründung, nicht Häufigkeit** | A-AD-7, A-M28-3, A-REC-7 | ✅ valid | **§4** |
| **Badge neutral formulieren + Regeln/Pfade zeigen** | A-M28-4, A-REC-6 | ✅ valid | **§3** |
| **Fail-open-Erkennung definieren** | A-AD-8, A-REC-8 | ✅ valid | **Kill-Gate** (Stichproben-Audit) |
| **Kill-Switch als getesteter Schalter, nicht Incident-Reparatur** | A-M28-5, A-REC-8, B-M28-5-nah | ✅ valid | **Umsetzung** |
| **SSoT-Nuance besitzen: Actor lokal, Policy in GitHub** | B-M28-5, B-REC-9 | ✅ valid | **Konsequenzen** |
| **Pfad ≠ Wichtigkeit (inhärente Proxy-Grenze)** | B-AD-5 | ✅ valid (Grenze benannt) | **Konsequenzen** (bewusst getragen) |
| **Risiko-Manifest `deploy-risk.yml` als Ergänzung** | A-OOTB1 | 🟡 valid als **spätere** Option | Konsequenzen (Evolutionspfad) |
| **Board-One-Click an current_user_can_approve + Portal-Policy** | A-AD-6, A-REC-5 | ✅ valid | **§3** (war implizit) |
| **Docs-only nie für Production, nur Staging-Fastlane** | A-OOTB4 | ⛔ out-of-scope | widerspricht Owner-Prämisse (docs-only *ist* für Prod erlaubt) |

**Nicht eingearbeitet:** A-OOTB4 (`[out-of-scope]`, Owner-Prämisse). Proponent-Befunde
(A/B-PRO-*) bestätigen die Richtung — keine Änderung nötig.
