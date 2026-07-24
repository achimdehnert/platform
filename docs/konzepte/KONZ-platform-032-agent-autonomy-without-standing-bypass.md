---
concept_id: KONZ-platform-032
title: "Agenten-Autonomie ohne Standing-Bypass: Pfad-gescopte Review + Standing-Authorization-Klassen + Merge-Entkopplung"
pipeline_status: idea
tier: T3
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "Amendment an ADR-242 (Review-Scope) + Policy-Edit autonomy-gates.md; KEIN neuer ADR (Vollzug/Verfeinerung bestehender Entscheide ADR-242/264/267/238). Baustein 1 berührt Security-Perimeter → mind. T2, in Summe T3."
review_by: "2026-10-12"
kill_criteria: "T+90 (2026-10-12), messbar (Vorbild ADR-267 Reibungs-Kill): (a) Anteil platform-PRs, die wirdigital-Review brauchen OBWOHL sie keinen Governance-Pfad berühren, nicht von ~100% auf ~0 gefallen (Baustein 1 wirkungslos) ODER (b) >30% der Merges, die unter eine Standing-Authorization-Klasse fallen, brauchten doch eine Einzel-Freigabe (Klassen-Definition zu eng/falsch — Baustein 2 überarbeiten) ODER (c) EIN Standing-Bypass-Actor auf irgendeinem Ruleset live (die verworfene Profil-C-Variante ist durch die Hintertür zurück) → Rückbau: CODEOWNERS-Catch-all zurück, Klassen-Text raus, Befund als 🌀-Memory. Kill-Gate-Trigger via Reminder-Issue (nicht nur review_by-Feld — M28-1-Lehre)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "gh api repos/achimdehnert/platform/rulesets/17621471 (Live, diese Session): EIN Ruleset mit required_status_checks + pull_request-Regel; required_approving_review_count=1, require_code_owner_review=true, bypass_actors=[]", commit_or_pr: "live 2026-07-12", opened_in_session: true}
  - {claim_id: C2, source_path: ".github/CODEOWNERS: Catch-all '* @achimdehnert @wirdigital' + 3 Pfad-Regeln (/.github/, /registry/, /packages/)", commit_or_pr: "main, gelesen", opened_in_session: true}
  - {claim_id: C3, source_path: "~/.claude/policies/autonomy-gates.md: 5 Gates, Gate 2 'Merge selbst ist Prod-Schritt bei Auto-Deploy-on-main', Signal G (Roundtrips/Entscheidung, Ziel 1)", commit_or_pr: "auto-injiziert diese Session", opened_in_session: true}
  - {claim_id: C4, source_path: "docs/adr/ADR-238-*.md C1: 'Agent-Prozess hält KEINE standing Credentials … privilegierte Aktionen minten kurzlebige scope-minimale Tokens über separaten Broker'; Kill-Gate review_by 2026-09-06", commit_or_pr: "accepted, gelesen Z.66/89", opened_in_session: true}
  - {claim_id: C5, source_path: "docs/adr/ADR-267-*.md: Break-Glass = zeitbegrenzt + Auto-Incident + retroaktiver wirdigital-Review; Reibungs-Kill >30% False-Reviewpflichtig", commit_or_pr: "accepted, gelesen Z.164/187", opened_in_session: true}
  - {claim_id: C6, source_path: "docs/adr/ADR-264-*.md D2: 'merge→Staging (auto), gegatete Promotion Staging→Prod als GitHub-Environment-Approval'; implementation_status: not-started", commit_or_pr: "accepted 2026-07-03, gelesen Z.72", opened_in_session: true}
  - {claim_id: C7, source_path: "docs/adr/ADR-242-*.md: 'Break-Glass statt Bypass-Liste; kein stehender Admin-Bypass'; branch_protection_meter prüft required checks, NICHT bypass_actors", commit_or_pr: "accepted; Meter-Lücke subagent-verifiziert", opened_in_session: true}
  - {claim_id: C8, source_path: "5 Friktions-Ereignisse dieser Session: F1 cad-hub#39, F2 137-hub#65, F3 4 platform-PRs, F4 #1097-Bypass-Reuse, F5 Secrets-Reconcile", commit_or_pr: "eigene Session-Historie", opened_in_session: true}
  - {claim_id: C9, source_path: "gho_-Token (Scope repo) editierte Ruleset 17621471 HEUTE 4× (09:17/09:18/12:19/12:20, actor=User achimdehnert) — 'strukturell unfähig Rulesets zu ändern' falsifiziert", commit_or_pr: "Diabolus-Agent via gh api rulesets/history", opened_in_session: true}
  - {claim_id: C10, source_path: "docs/PROFILE_B.md + memory project_profile_b_app_state: iilgmbh-admin-App, PEM auf Agent-Host, kein Rotations-Runbook, review_by 2026-09-05", commit_or_pr: "gelesen diese Session", opened_in_session: true}
  - {claim_id: C11, source_path: "memory feedback_agent_push_publish_hardblocked_use_ci: 'User-Erlaubnis + Permission-Rule + Settings-Edit heben Classifier-Hard-Deny NICHT auf'", commit_or_pr: "Steelman-Agent-verifiziert", opened_in_session: true}
  - {claim_id: C12, source_path: "governance/rulesets/main-required-checks-template.json ('bypass_actors: []' fest); KEINE Review-Ruleset-Vorlage vorhanden", commit_or_pr: "Maintainer-2028-Agent M28-8", opened_in_session: true}
created: "2026-07-12"
---

# KONZ-platform-032 — Agenten-Autonomie ohne Standing-Bypass

> Auslöser (Achim, 2026-07-12): *"wir haben mit den Secrets und den unterschiedlichen Token immer
> wieder Probleme, insbesondere da du wegen Sicherheits-Gates nicht ungehindert agieren kannst.
> Gibt es eine … sichere und zukunftssichere Variante … und du hast gleichzeitig hohe Freiheit?"*
> + Zielpräzisierung: *"ich möchte, dass du stabil und sicher arbeitest, und nur nachfragen musst,
> wenn strategische Fragen durch mich freigegeben werden sollen."*
> Tier **T3** (Security-Perimeter · Governance-Config · org-weite Policy). Adversariat: 3 blinde
> Agenten (Diabolus / Steelman+OOTB / Maintainer-2028) + Fable-Synthese; Konfliktmatrix §6.4.
> **Dieses Konzept verwirft den zuerst erwogenen Vorschlag ("Profil C" — dauerhafter App-Bypass-Actor)
> und ersetzt ihn durch drei Bausteine, die KEINE neue privilegierte Identität einführen.**

## 1. Executive Summary

**Empfehlung: als MVP annehmen — mit einer im Prozess selbst gefällten Kehrtwende.** Der Auftrag
klingt nach einem Credential-/Token-Problem, ist aber zu 80 % keines. Die fünf realen Blockade-
Ereignisse dieser Session (C8) verteilen sich auf **zwei** Kontrollschichten: **eine** war echtes
GitHub-Enforcement (F3, das platform-Review-Ruleset), **vier** kamen vom Claude-Code-Classifier
(F1/F2/F4/F5) — einer Client-Schicht, die GitHub-Rechte gar nicht abfragt (C11: selbst
User-Erlaubnis + Permission-Rule + Settings-Edit heben einen Classifier-Hard-Deny nicht auf). Ein
neuer Token oder eine neue App kann an dieser Schicht per Konstruktion nichts ändern. Die zuerst
erwogene Lösung — ein drittes, eng geschnittenes GitHub-App-Profil ("Profil C") als dauerhafter
`bypass_actor` — wurde vom eigenen Adversariat dieser Analyse **falsifiziert**: (a) sie löst
0 von 5 Friktionen vollständig (§6.4 Matrix); (b) ihre Kernbehauptung "strukturell unfähig,
Rulesets zu ändern" ist empirisch falsch — der bestehende `gho_`-Token hat das Ruleset **heute
4×** editiert (C9), eine dritte Identität *addiert* Privileg, statt es wegzunehmen; (c) der
Kipp-Angriff: `contents:write` + Bypass genügt, um im *selben* gemergten PR `CODEOWNERS` oder das
Ruleset-Template zu ändern — die "kein Admin-Scope"-Sicherheit ist wertlos, weil man die
Kontrolldateien als normalen Datei-Inhalt schreibt (AD-3, §6.1); (d) ein Standing-Bypass
widerspricht ADR-242 ("kein stehender Admin-Bypass", C7), ADR-267 (Break-Glass statt Standing,
C5), ADR-238 C1 ("Agent hält KEINE standing Credentials", C4) und der 7 Tage alten Bus-Faktor-
Kontrolle (KONZ-012 R-0). Der einzige unstrittige Rest-Wert von Profil C — PAT-Konsolidierung —
ist ein Aufräum-, kein Autonomie-Thema und gehört zu KONZ-018/KONZ-003, nicht hierher.

**Das eigentliche Ziel ("nur strategische Nachfragen") erreichen drei Bausteine, die jeweils
Reibung wegnehmen, ohne Kontrolle abzuschaffen oder eine Identität hinzuzufügen:** (B1)
**Pfad-gescopte Review** — der CODEOWNERS-Catch-all `*` (C2) zwingt heute *jeden* platform-PR
zu wirdigell-Review, auch reine Handover-/Konzept-Nachträge; nach Verengung auf Governance-Pfade
bleibt die Zwei-Augen-Kontrolle exakt dort, wo sie KONZ-012 wollte (`/.github/`, `/registry/`,
`/docs/adr/`, `/packages/`), und alles andere fließt frei. (B2) **Standing-Authorization-Klassen**
in `autonomy-gates.md` — der Classifier blockt heute, weil "go autonom" ihm zu unspezifisch ist
(F4); definierte Klassen ("CI-grüner Merge in Hub-Repo ohne GitHub-Review-Pflicht = dauerfrei")
geben eine Klassen- statt Einzelwort-Freigabe, mit dem policy-eigenen Fail-Test (Signal G, C3).
(B3) **ADR-264 D2 weitertreiben** (accepted, not-started, C6) — es entkoppelt `merge` von `prod`
und räumt damit die Ursache weg, die Gate 2 bei jedem Hub-Merge überhaupt erst auslöst. B1 ist
sofort und billig, B2 ist ein Policy-PR, B3 ist ein bereits beschlossenes Programm. Keiner der
drei fügt eine neue standing Credential hinzu — womit KONZ-019 konsistent zum ADR-238-Zielbild
bleibt (Broker + kurzlebige Tokens), statt es zu präjudizieren.

## 2. Scope & Evidenzbasis

**Direkt verifiziert (Haupt-Session):** Ruleset-Parameter live (C1); CODEOWNERS (C2); Gate-Text
(C3); ADR-238-C1/264-D2/267/242-Kernstellen (C4-C7). **Adversariat-verifiziert:** C9 (4× Ruleset-
Edit heute), C11 (Classifier-Hard-Deny-Unaufhebbarkeit), C12 (fehlende Review-Ruleset-IaC + Meter-
Blindspot). **Als Hypothese markiert — der EINE offene technische Fakt (H1):** ob ein Ruleset mit
`required_approving_review_count: 0` **und** `require_code_owner_review: true` bei einem PR, der
einen CODEOWNERS-Pfad berührt, trotzdem ein Code-Owner-Approval erzwingt (= B1 funktioniert), oder
ob `count: 0` die Code-Owner-Pflicht mit aushebelt (= B1 in dieser Form kaputt). **Billigster Check
vor B1-Rollout: 10-Minuten-Test auf einem Wegwerf-Sandbox-Repo** (Gate 3, Owner-Freigabe) — NICHT
live auf platform ausprobieren. Solange H1 offen ist, ist B1 ein *Entwurf mit Vorbedingung*, keine
Zusage.

## 3. Infrastruktur-Fit

| Baustein | Status | Rolle |
|---|---|---|
| ADR-242-Ruleset + CODEOWNERS | live, Catch-all zu breit (C1/C2) | B1 verengt CODEOWNERS; Amendment an ADR-242 (Review-Scope) |
| autonomy-gates.md (5 Gates, Signal G) | live Policy | B2 erweitert Gate 2 um Standing-Authorization-Klassen; Fail-Test existiert bereits |
| ADR-264 D2 Promotion-Pipeline | accepted, **not-started** (C6) | B3 = Vollzug; entkoppelt Merge≠Prod → Gate-2-Fläche schrumpft strukturell |
| ADR-238 C1 Broker (kein standing Credential) | accepted, Kill-Gate 2026-09-06 (C4) | **Leitplanke**: KONZ-019 darf keine neue Identität schaffen; alle 3 Bausteine erfüllen das |
| ADR-267 Break-Glass + Reibungs-Kill (C5) | accepted | Vorbild für Kill-Gate §Frontmatter; Gegenmodell zu Standing-Bypass |
| branch_protection_meter | live, prüft `bypass_actors` NICHT (C7/C12) | **Muss erweitert werden BEVOR** irgendein Bypass-Gedanke je wiederkommt (Nicht-Ziel hier, aber benannt) |
| Profil B (iilgmbh-admin-App) | Break-Glass, voller Admin, PEM auf Host (C10) | **Nicht** als Merge-Alltagsidentität zweckentfremden (war die Profil-C-Falle) |

## 4. Steelman (des angenommenen Konzepts, nicht des verworfenen Profil C)

Die drei Bausteine sind allesamt *Verfeinerungen bestehender, akzeptierter Entscheide*, keine
Neuerfindung: B1 nutzt exakt den CODEOWNERS-/Ruleset-Mechanismus, den ADR-242 schon etabliert hat,
und macht ihn präziser — die Bus-Faktor-Absicherung (KONZ-012 R-0) war ausweislich ihrer Begründung
für Governance-*Substanz* gedacht, nie für Handover-Tippfehler; der Catch-all ist eine
Übergenauigkeit, kein Feature. B2 aktiviert eine Fähigkeit, die die Policy selbst schon vorsieht
(mehrstufige Freigabe unterhalb der Gates) und mit Signal G einen eingebauten Abbruch-Test
mitbringt. B3 ist kein Vorschlag, sondern ein *offener Auftrag* (ADR-264 accepted). Der stärkste
Zug: Das Konzept erhöht Autonomie **durch Reibungsabbau am richtigen Ort**, nicht durch
Schutzabbau — und bleibt damit als einziges der erwogenen Modelle konsistent zum bereits
beschlossenen Sicherheits-Zielbild (ADR-238 C1: weniger stehende Privilegien, nicht mehr).

## 5. Konzeptdefinition

### 5.1 Kernthese

Höhere Agenten-Freiheit bei gleichbleibender Sicherheit entsteht nicht durch eine neue
privilegierte Identität, sondern durch drei Reibungsabbauten an ihren jeweils richtigen Schichten:
GitHub-Enforcement wird **pfad-präzise** (Review nur für Governance-Substanz, B1), die
Classifier-Freigabe wird **klassenbasiert statt einzelwortbasiert** (B2), und die Merge=Prod-
Kopplung, die Gate 2 überhaupt erzeugt, wird durch das bereits beschlossene Promotion-Gate
**aufgelöst** (B3) — wobei keiner der Schritte eine stehende Credential hinzufügt (ADR-238-C1-treu).

### 5.2 Problem (verifiziert)

Fünf Friktionen, zwei Schichten (C8): **GitHub-Enforcement (1):** F3 — das platform-Ruleset
verlangt via Catch-all-CODEOWNERS + `count:1` für *jeden* PR ein wirdigell-Review; der einzige
autonome Ausweg war heute ein Backup→Bypass→Merge→Restore-Tanz (2× genutzt, F3+F4), der die
Kontrolle temporär *ganz* abschaltet. **Classifier (4):** F1/F2 — Gate 2 (Merge=Prod bei
Auto-Deploy-Repos) blockt Hub-Merges bis zum wörtlichen Einzel-OK, obwohl GitHub dort keine
Review-Pflicht hat; F4 — Bypass-Reuse ohne benannten Mechanismus geblockt; F5 — Secrets-Reconcile
als Credential-Scanning geblockt. Kein Token/keine App berührt die Classifier-Schicht (C11).

### 5.3 Zielbild (T+90)

Ein platform-PR, der nur `docs/konzepte/**`, `AGENT_HANDOVER.md`, `tools/**` o.ä. berührt, mergt
CI-grün ohne Zweit-Review; ein PR, der `/.github/`, `/registry/`, `/docs/adr/`, `/packages/`,
`CODEOWNERS` berührt, verlangt weiterhin wirdigell. Der Classifier lässt CI-grüne Merges definierter
Klassen ohne Einzelwort durch; strategische Aktionen (Prod-Deploy-Auslösung, irreversibel,
Security-Config, Publish, Spend) bleiben gate-pflichtig — genau die "nur strategische Nachfragen"-
Linie. Kein Standing-Bypass-Actor auf irgendeinem Ruleset. B3 in Rollout, sodass Hub-Merge und
Prod-Deploy getrennte, einzeln gatebare Schritte sind.

### 5.4 Nicht-Ziele

- **Kein Standing-Bypass-Actor, keine dritte App-Identität** (Profil C verworfen — §6.1 AD-1/AD-3,
  Widerspruch zu ADR-242/238-C1/267). Profil B bleibt Break-Glass, wird nicht Merge-Alltag.
- **Kein Anfassen der Classifier-Heuristik selbst** — die ist Harness-seitig (C11), nicht in
  diesem Repo editierbar; B2 wirkt über die *Policy*, die der Classifier liest, nicht über seinen Code.
- **Keine Token-Entfernung / kein Broker-Bau hier** — das ist ADR-238 C1 (eigenes Programm,
  Kill-Gate 2026-09-06); KONZ-019 bleibt dazu konsistent, greift aber nicht vor.
- **Kein Bypass-Meter-Bau als Teil dieses Konzepts** — aber als Vorbedingung für *jede* künftige
  Bypass-Diskussion benannt (C7/C12: der Meter ist heute blind für `bypass_actors`).
- **B1 nicht live ausrollen, solange H1 (count:0 + code_owner:true) nicht am Sandbox belegt ist.**

### 5.5 Maßnahmen

**B1 — Pfad-gescopte Review (Security-Perimeter, Gate 3, nach H1-Sandbox-Test):**

| Schritt | Mechanik |
|---|---|
| B1-0 | **H1-Sandbox-Test** (Wegwerf-Repo): Ruleset `count:0 + require_code_owner_review:true`, CODEOWNERS mit nur einem Pfad → PR auf dem Pfad muss Review verlangen, PR daneben nicht. Beweist/widerlegt B1-Mechanik. |
| B1-1 | `.github/CODEOWNERS`: Catch-all `* @achimdehnert @wirdigital` **entfernen**; Governance-Pfade behalten + ergänzen: `/.github/`, `/registry/`, `/packages/`, `/docs/adr/`, `/governance/`, `/CODEOWNERS`, `~/.claude`-verteilte Policy-Pfade sofern getrackt. |
| B1-2 | Ruleset 17621471 `required_approving_review_count: 1 → 0` (Governance-Review kommt dann aus `require_code_owner_review:true` + CODEOWNERS-Pfaden). **Diff als IaC** in `governance/rulesets/` festhalten (Review-Ruleset-Vorlage, die laut C12 heute fehlt). |
| B1-3 | ADR-242-Amendment: Review-Scope-Präzisierung dokumentiert (warum Catch-all → Pfad; Bus-Faktor bleibt auf Governance). |

**B2 — Standing-Authorization-Klassen (Policy-PR):**

| Schritt | Mechanik |
|---|---|
| B2-1 | `autonomy-gates.md` um Abschnitt "Standing-Authorization-Klassen" erweitern: benannte, dauerhaft freigegebene Aktionsklassen, die KEIN Einzelwort mehr brauchen — Kandidaten: (a) Merge CI-grüner PR in Hub-Repo **ohne** GitHub-Review-Pflicht **und ohne** Auto-Deploy-on-main; (b) Merge CI-grüner Nicht-Governance-PR in platform; (c) Secrets-*Datei-Hausputz* in `~/.secrets`/`~/shared` (F5-Klasse) unter Nenn-Auflagen (keine Inhalte ins Transkript). Auto-Deploy-Repos bleiben ausdrücklich AUSSEN (Gate 2 wirkt weiter). |
| B2-2 | Je Klasse: Signal-G-Zählung + Kill-Kriterium (>30% doch Einzel-Freigabe nötig ⇒ Klasse zu weit/falsch, ADR-267-Muster). |

**B3 — ADR-264 D2 weitertreiben (Vollzug, eigenes Tempo):**

| Schritt | Mechanik |
|---|---|
| B3-1 | Pilot-Repo für Promotion-Pipeline benennen (Vorbedingung Rollback-Fähigkeit, ADR-264 D2); merge→Staging auto, Staging→Prod als GitHub-Environment mit Approval. |
| B3-2 | Sobald ein Repo auf D2 läuft: Gate 2 feuert dort beim **Merge** nicht mehr (Merge≠Prod) — Autonomie-Gewinn ohne Sicherheitsverlust (Prod-Gate wandert an die richtige Stelle). |

### 5.6 Enforcement-Modell (ehrlich)

| Regel | Level | Grenze |
|---|---|---|
| Governance-Pfad-PR braucht Code-Owner-Review | hart (Ruleset, nach H1-Beweis) | schützt nur die enumerierten Pfade; neue Governance-Pfade müssen in CODEOWNERS nachgezogen werden (Pflege-Last, §M28) |
| Nicht-Governance-PR mergt CI-grün ohne Review | hart-freigegeben (Ruleset count:0) | greift nur, wenn H1 hält; sonst Rückfall auf Status quo |
| Standing-Authorization-Klassen | Policy (Classifier liest sie) — **weich**, kein Exit-Code | Classifier-Hard-Denys für echte Gates bleiben (C11); Klassen wirken nur im Graubereich, den heute das Einzelwort füllt |
| Merge≠Prod (B3) | hart (GitHub-Environment) | erst wirksam pro auf D2 migriertem Repo |
| Kein Bypass-Actor | hart (Meter — MUSS erst `bypass_actors` lesen lernen, sonst blind) | heute nicht erzwungen (C12); bis dahin Konvention + dieses Nicht-Ziel |

## 6. Adversariale Analyse

### 6.1 Advocatus Diabolus (11 Befunde gegen Profil C, konserviert — Kern)

**AD-1:** Profil C ist additiv — der `gho_`-Token editiert weiter (C9), Zahl standing privilegierter
Identitäten steigt 2→3. **AD-2:** Single-Ruleset (checks+review) → `bypass_mode:pull_request`
umgeht auch gitleaks/guardian; naive Form bricht ADR-242-Kernversprechen. **AD-3 (Kipp):**
`contents:write` + Bypass = Ein-Schritt-Selbstermächtigung (CODEOWNERS/Ruleset-Template im selben
bypassed PR ändern) — "kein Admin-Scope" wertlos. **AD-4:** bricht ADR-242 "kein stehender
Admin-Bypass" wörtlich. **AD-5:** branch_protection_meter blind für `bypass_actors` (C12). **AD-6:**
0 statt 1 unabhängiges Auge für jeden so gemergten PR (KONZ-012 R-0 stillgelegt). **AD-7:**
konterkariert ADR-238 C1 (Broker/de-privileg) durch dritte standing Identität. **AD-8:**
Ko-Lokation — PEM auf Agent-Host, Blast-Radius↑ (ADR-238 §1.1). **AD-9/AD-10:** präjudiziert
ADR-264 D2 / nähert sich der von ADR-270 abgelehnten Option B. **AD-11:** kein Re-Narrow-Gate
(anders als Profil B). → **Alle 11 fließen in die Verwerfung (§1, §5.4).**

### 6.2 Maintainer-2028 (Kern)

**M28-1:** `review_by`-Felder driften (KONZ-004 überfällig, 14/19 in idea) → Kill-Gate braucht
Reminder-Issue, nicht nur Feld (übernommen, Frontmatter). **M28-3:** ADR-264 D2 seit Accept
not-started — "saubere Lösung später" ist ein belegtes Verrottungsmuster → B3 mit Pilot-Termin,
nicht offen. **M28-5:** kein Key-Rotations-Runbook (Profil B seit 06-05 unrotiert) → für KONZ-019
irrelevant, weil **keine neue Credential** (Design-Vorteil). **M28-7/M28-8 (kritisch):** Meter
liest `bypass_actors` nicht + keine Review-Ruleset-IaC → **Vorbedingung** für jede Bypass-Zukunft
(Nicht-Ziel §5.4, aber benannt); B1 schreibt die fehlende Review-Ruleset-IaC (B1-2) gleich mit.
**M28-6:** ADR-267 hat Break-Glass-Gegenmodell 4 Tage vor diesem Konzept beschlossen → KONZ-019
erbt es statt zu widersprechen.

### 6.3 Steelman + OOTB (Kern)

Kernbefund bestätigt: Profil C ist GitHub-Enforcement-Mechanik, löst strukturell nur F3 (1/5).
**OOTB-Ranking übernommen:** #1 Standing-Authorization (→ B2, höchster Hebel/Aufwand, 4/5
Ereignisse), #2 Pfad-gescopte Review (→ B1, chirurgisch für F3 ohne Bus-Faktor-Verwässerung),
#3 ADR-264 D2 (→ B3, räumt Gate-2-Ursache). Token-Broker (ADR-238) = richtiges Zielbild, zu
langsam für Sofort-Entlastung → als Leitplanke, nicht Baustein. Merge-Queue/Label = Testballon,
unverifiziert ob Classifier "Label setzen" von "Merge auslösen" trennt → nicht aufgenommen.

### 6.4 Konfliktmatrix (Pflicht T3)

| # | Konflikt | Positionen | Auflösung |
|---|---|---|---|
| K1 | Grundrichtung Profil C | Achim: "grundsätzlich interessant" + eigener Erst-Vorschlag vs. Diabolus: 0/5 gelöst, Kipp-Angriff AD-3 vs. Steelman: nur F3, PAT-Bonus | Diabolus/Steelman gewinnen: Profil C als Autonomie-Fix verworfen; PAT-Bonus nach KONZ-018 ausgelagert. Der User-Wunsch bleibt erfüllt — durch B1/B2/B3 statt C |
| K2 | "strukturell unfähig Rulesets zu ändern" | Erst-Vorschlag: ja (kein Admin-Scope) vs. AD-1/C9: nein (gho_ editiert weiter) + AD-3 (indirekt via bypassed Diff) | AD gewinnt empirisch (4× Edit heute belegt) — Kernverkaufsargument gestrichen |
| K3 | Löst der App-Ansatz die Friktion? | Erst-Vorschlag: hohe Freiheit vs. Steelman/Matrix: 4/5 sind Classifier, App wirkt dort nicht (C11) | Steelman gewinnt: Friktion ist 80% Classifier → B2 (Policy) ist der eigentliche Hebel, nicht Enforcement |
| K4 | Pfad-Review technisch machbar? | Steelman: Hypothese, ungeprüft vs. Haupt-Session-Fund: count:1+code_owner:true ist der Ist-Zustand (C1) | offen als **H1**: `count:0 + code_owner:true`-Verhalten — Sandbox-Test-Vorbedingung (B1-0), nicht behauptet |
| K5 | Standing vs. Break-Glass | Erst-Vorschlag: dauerhaft vs. Maintainer/ADR-267: zeitbegrenzt+Auto-Incident+retro-Review | ADR-267 gewinnt: KONZ-019 hat gar keinen Bypass mehr; falls je einer nötig, erbt er das ADR-267-Muster, nicht Standing |
| — | Konvergenz | alle drei: Meter muss `bypass_actors` lesen lernen; ADR-264 D2 ist der strukturelle Fix | als §5.4-Nicht-Ziel (Meter) + B3 übernommen |

## 7. Deep-Dive: die zwei Kontrollschichten

**Warum eine App die Mehrheit der Friktion nicht anfassen kann:** Der Claude-Code-Classifier ist
eine Harness-Schicht *vor* jedem Tool-Call; er entscheidet anhand von Prompt-Kontext + `autonomy-
gates.md` + eingebauten Heuristiken, ob eine Aktion ausgeführt werden darf — *bevor* GitHub je
gefragt wird. C11 belegt, dass selbst eine User-Erlaubnis + eine Permission-Rule + ein
Settings-Edit einen Hard-Deny nicht aufheben. Wer die Classifier-Reibung senken will, hat genau
zwei legitime Hebel: (a) die *Policy* präziser machen, die der Classifier liest (B2 —
Standing-Authorization-Klassen geben ihm ein positives, benanntes Freigabe-Muster statt des vagen
"go autonom", das F4 auslöste); (b) die *Aktion selbst* aus einer Gate-Klasse herausnehmen (B3 —
wenn Merge ≠ Prod ist, feuert Gate 2 beim Merge nicht mehr). Ein Token ändert an beidem nichts —
das ist der Kern, warum der Erst-Vorschlag am Ziel vorbeizielte.

**Warum B1 Freiheit *und* Sicherheit gleichzeitig erhöht:** Der Catch-all `*` behandelt einen
Handover-Tippfehler wie eine ADR-Änderung — maximale Reibung bei null Schutzgewinn für die
Substanz. Die Verengung ist kein Schutzabbau, sondern eine *Präzisierung*: die Zwei-Augen-
Kontrolle bleibt vollständig auf `/docs/adr/`, `/registry/`, `/.github/`, `/packages/`, `CODEOWNERS`
— den Pfaden, für die KONZ-012 R-0 sie einführte. Freiheit steigt (Nicht-Governance mergt frei),
Schutz bleibt punktgenau. Der einzige Rest-Risiko-Vektor: ein PR, der Code *und* Governance-Pfad
mischt — der fällt korrekt unter Review (CODEOWNERS matcht den Governance-Teil). Das ist die
gewünschte Eigenschaft, kein Leck.

## 8. Alternativen

**A1 — Nichts tun, Einzelwort-Freigaben weiter:** ehrlich, aber Signal G bleibt bei ~3 Roundtrips/
Entscheidung (Baseline), und der Ruleset-Bypass-Tanz (heute 2×) wird laut Maintainer-Prognose zur
Floskel — die Kontrolle erodiert durch Gewöhnung, nicht durch Design. Verworfen.

**A2 — Profil C (Standing-Bypass):** der Erst-Vorschlag; §6.1 falsifiziert. Verworfen.

**A3 — Nur B2 (Policy), B1/B3 weglassen:** billigste Teilmenge, deckt F1/F2/F4. Lässt aber F3 (den
einzigen *harten* Blocker) ungelöst — bei jedem platform-Governance-PR bliebe der Review-Zwang für
auch-triviale Änderungen. B1 ist gerade der chirurgische Fix dafür; Weglassen verschenkt ihn.
B2-only ist ein legitimer **Phase-1-Zuschnitt**, falls H1 (B1-Vorbedingung) sich verzögert.

## 9. Out-of-the-Box (übernommen/verworfen)

- **Übernommen:** B2 Standing-Authorization (OOTB #1); B1 Pfad-Scoping (OOTB #3); B3 D2-Vollzug
  (OOTB #2). Meter-Erweiterung als Vorbedingung benannt (M28-7).
- **Verworfen mit Grund:** Token-Broker als KONZ-019-Baustein (zu langsam, ist ADR-238 —
  Leitplanke statt Baustein); Merge-Queue+Label (unverifiziert ob Classifier Label≠Merge trennt);
  Profil C downscoped-mit-Split (auch die Split-Form trägt AD-3 nicht weg — Maintainer M28-7/8).

## 10. Befunde (Kern)

| ID | Kategorie | Befund | Evidenz | Schwere |
|---|---|---|---|---|
| F-1 | Diagnose | 4 von 5 Friktionen sind Classifier, nicht GitHub — Token/App wirkt dort nicht | C8, C11 | kritisch (kippt Erst-Vorschlag) |
| F-2 | Sicherheit | Profil-C-Kernclaim empirisch falsch: gho_ editiert Ruleset weiter (4× heute) | C9 | kritisch |
| F-3 | Sicherheit | contents:write+Bypass = Ein-Schritt-Governance-Übernahme (AD-3) | §6.1 | kritisch |
| F-4 | Enforcement | CODEOWNERS-Catch-all zwingt jeden platform-PR zu Review (Übergenauigkeit) | C1, C2 | hoch (B1-Ansatz) |
| F-5 | Alterung | Meter blind für bypass_actors + keine Review-Ruleset-IaC | C7, C12 | hoch (Bypass-Vorbedingung) |
| F-6 | Konsistenz | ADR-238 C1 verlangt WENIGER standing Credentials — Profil C addiert eine | C4 | hoch |
| F-7 | offen | H1: count:0+code_owner:true-Verhalten unverifiziert | §2 | mittel (B1-Gate) |

## 11. Top-5-Risiken

**R1 — H1 hält nicht (`count:0` hebelt Code-Owner-Pflicht mit aus).** *Fix:* Sandbox-Test B1-0
VOR Live; falls negativ, B1 auf alternative Mechanik (separates Governance-Review-Ruleset mit
eigenem `count:1` nur auf Governance-Pfad-`conditions`, falls GitHub Path-Conditions auf
pull_request-Rules stützt — zweiter Sandbox-Test). *Rest:* GitHub-Ruleset-Semantik ist die harte
Unbekannte; deshalb ist B1 explizit gated.

**R2 — Standing-Authorization-Klasse zu weit → echter Prod-Merge rutscht durch.** *Fix:* Klassen
schließen Auto-Deploy-Repos hart aus (B2-1); Signal-G-Kill bei >30% (B2-2); Klassen sind
Positiv-Liste, kein Catch-all. *Rest:* Graubereich-Definition ist Urteilssache — deshalb messbar
+ rückrollbar.

**R3 — B3 bleibt liegen wie ADR-264 D2 seit Accept (M28-3).** *Fix:* Pilot-Repo + Datum in
B3-1, Reminder-Issue; B3 ist der langsamste Baustein, B1/B2 tragen die Sofort-Entlastung, sodass
B3-Verzug das Konzept nicht blockiert. *Rest:* Owner-Kapazität.

**R4 — Bypass kcommt durch die Hintertür zurück (jemand trägt doch einen Actor ein).** *Fix:*
Kill-Kriterium (c) im Frontmatter macht genau das zum Abbruch; Meter-Erweiterung (Nicht-Ziel, aber
benannt) würde es maschinell fangen. *Rest:* solange Meter blind ist (C12), nur Konvention.

**R5 — Konzept konkurriert mit KONZ-017/018-Wellen + laufender Bump-Welle um dieselben 2 Personen.**
*Fix:* B1 = 1 PR + 1 Sandbox-Test; B2 = 1 Policy-PR; B3 = bereits beschlossen. Netto-Neulast klein;
B3 im eigenen Tempo. *Rest:* real verfügbare Kapazität (identisch KONZ-017/018 R5).

## 12. Empfehlungen

- **REC-1 (du + ich, Gate 3):** B1-0 H1-Sandbox-Test freigeben (Wegwerf-Repo, Ruleset-Config) —
  einzige Vorbedingung für B1. Ich bereite Repo + Testmatrix vor, du gibst den Ruleset-Write frei.
- **REC-2 (ich, nach REC-1 positiv):** B1-1/B1-2/B1-3 als **ein** platform-PR (CODEOWNERS-Verengung
  + Ruleset-IaC + ADR-242-Amendment). Merge ist Gate 3 (Security-Config) → deine Freigabe.
- **REC-3 (ich, Policy-PR):** B2 Standing-Authorization-Klassen-Entwurf in `autonomy-gates.md`
  (via platform-PR, da Policy dort gepflegt wird) — Klassen als Vorschlag, du ratifizierst den
  Wortlaut (wie 2026-07-03 "3 go").
- **REC-4 (du + ich):** B3 Pilot-Repo für ADR-264 D2 benennen; danach Vollzug im eigenen Tempo.
- **REC-5 (ich, bei Annahme):** T+90-Reminder-Issue mit Kill-Gate-Checkliste (M28-1-Fix) + die
  aufgeschobenen Punkte (Meter-`bypass_actors`-Check, PAT-Konsolidierung→KONZ-018).

## 13. Entscheidung + Kill-Gate + 30/60/90

**Empfehlung: als MVP annehmen (B2 + B1 nach H1-Test; B3 im eigenen Tempo).** Nicht "Profil C
annehmen" — vom eigenen Adversariat falsifiziert (§6.1, transparent dokumentiert statt geglättet).
Nicht "nichts tun" (A1 — Reibung + erodierende Bypass-Gewöhnung). Der User-Wunsch ("nur
strategische Nachfragen") wird erfüllt, indem strategische Aktionen (Prod, irreversibel,
Security-Config, Publish, Spend) gate-pflichtig **bleiben** und alles darunter — CI-grüne Merges,
Nicht-Governance-PRs, Datei-Hausputz — frei fließt.

**Kill-Gate:** Frontmatter `kill_criteria` (messbar, ADR-267-Muster), Trigger via Reminder-Issue.

**30 Tage (bis 2026-08-11):** B1-0 Sandbox-Test durchgeführt (H1 beantwortet); bei positivem H1
B1-PR gestellt; B2-Klassen-Entwurf als PR; Signal-G-Baseline gemessen.

**60 Tage (bis 2026-09-10):** B1 live (falls H1 hielt), Nicht-Governance-platform-PRs mergen
review-frei; B2-Klassen ratifiziert + G gemessen (<3→Richtung 1); B3-Pilot benannt.

**90 Tage (bis 2026-10-12):** Kill-Gate-Review am Reminder; Anteil Governance-freier Reviews auf
~0; Standing-Authorization-FP <30%; kein Bypass-Actor live; B3-Pilot-Status berichtet.
