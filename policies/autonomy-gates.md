# Policy: Autonomy Gates

**Trigger words:** freigabe, genehmigung, approval, autonom, autonomie, darf ich,
user-eingriff, gate, permission, bypass

## Rule

Der Agent arbeitet **autonom durch** und holt Freigaben nur an den fünf Gates
unten ein. Alles unterhalb der Gates läuft ohne Rückfrage — auch mehrstufig
(Branch → Edits → PR → CI-Fix → plain-Merge bei grünem CI, sofern kein Gate
berührt wird).

## Die fünf Gates (Freigabe IMMER nötig)

1. **Irreversibles** — Daten/Branches löschen, force-push, Secret-Rotation,
   destruktive Migrationen.
2. **Prod-Zustandsänderung** — Deploy auslösen, Prod-Dateien/-Container/-DBs
   anfassen. Ausnahme: explizit allowlistete, backup-first Wartungs-Wrapper.
   Merke: In Repos mit Auto-Deploy-on-main ist der **Merge selbst** ein
   Prod-Schritt und damit gate-pflichtig.
3. **Security-/Governance-Config** — Branch-Protection/Rulesets, Tokens,
   Org-Permissions, Workflow-Permissions (`issues:write` etc., deckt sich mit
   Gate `autonomous-no-human-review`).
4. **Scope-Eskalation** — drittes Repo, Publish (PyPI/Release), neue
   Automatismen mit Schreibrecht (Scope-Checkpoint, house rule).
5. **Nennenswerter Spend** — Modell-Tier-Upgrade, Cloud-/Ultra-Runs, bezahlte APIs.

## Standing-Authorization-Klassen (dauerhaft freigegeben, KEIN Einzelwort nötig)

> **Motiv (KONZ-platform-019 B2):** Der Permission-Classifier blockte wiederholt
> Aktionen, die *keinen* der fünf Gates berühren, nur weil die Freigabe nicht
> *benannt* war (Realfall 2026-07-12: „go autonom" reichte nicht, „merge PR #N"
> schon). Diese **Positiv-Liste** benennt vorab freigegebene Aktionsklassen —
> innerhalb ihrer gilt die Freigabe als **stehend erteilt**, kein Einzel-OK pro
> Fall. Es ist eine **Positiv-Liste, kein Catch-all**: was nicht gelistet ist,
> bleibt gate-geregelt wie oben. Die Klassen liegen ausschließlich **unterhalb**
> der fünf Gates; berührt eine Aktion einen Gate, gewinnt der Gate.

- **SA-1 — Merge eines CI-grünen PR in ein Repo OHNE GitHub-Review-Pflicht UND
  OHNE Auto-Deploy-on-main.** ✅ **RATIFIZIERT (Achim, 2026-07-12).** Voraussetzung:
  alle Required Checks grün, kein Ruleset verlangt Review, und `main` triggert
  **keinen** Prod-Deploy. Deckt die Hub-Repo-Merges ab, die heute an Gate 2
  hängen, obwohl der Merge dort *kein* Prod-Schritt ist. **Ausdrücklich
  AUSGESCHLOSSEN:** jedes Auto-Deploy-on-main-Repo (dort ist der Merge ein
  Prod-Schritt → Gate 2 wirkt unverändert), und jeder PR mit Migrationen/
  destruktiven Änderungen (Gate 1).
- **SA-2 — Merge eines CI-grünen NICHT-Governance-PR in `platform`.**
  ⏸ **ZURÜCKGESTELLT bis KONZ-019 B1 (Entscheid Achim 2026-07-12).** Grund: SA-2
  ist erst dann auch GitHub-seitig mergebar, wenn das platform-Review-Ruleset
  pfad-gescopt ist (Catch-all-CODEOWNERS entfernt, nur Governance-Pfade
  reviewpflichtig). Vorher wäre SA-2 nur eine Classifier-Freigabe, während der
  Merge weiter am Review-Ruleset hängt — ein „deklariert-aber-nicht-durchsetzbar"-
  Zustand, den wir vermeiden. **ID SA-2 bleibt reserviert**; die Klasse wird
  gemeinsam mit B1 ratifiziert, nicht vorab.
- **SA-3 — Datei-Hausputz in `~/.secrets` / `~/shared` (Reconcile, KEIN Inhalts-Dump).**
  ✅ **RATIFIZIERT (Achim, 2026-07-12).** Verschieben/Deduplizieren/Löschen
  byte-identischer Secret-**Dateien** nach ihrer SSoT-Konvention (KONZ-010).
  **Auflage:** Secret-**Inhalte** werden NIE ins Transkript gelesen (kein
  `cat`/`grep` über Dateiinhalte) — nur Dateinamen, Größen, Hashes. Divergente/
  nicht-identische Dateien bleiben stehen + werden gemeldet (kein blindes
  Überschreiben). Secret-**Rotation** bleibt Gate 1.

**Grenzen (ehrlich):** Diese Klassen wirken über die *Policy*, die der Classifier
liest — sie heben **keinen** Classifier-Hard-Deny auf (der ist Harness-seitig;
Realfall-Memory: User-Erlaubnis + Permission-Rule + Settings-Edit heben ihn nicht
auf). Sie füllen den *Graubereich*, den heute das Einzelwort füllt, nicht die
harten Denys. Neue Klasse nötig? → wird wie diese hier **ratifiziert** (Achim,
wörtlich), nicht still ergänzt.

**Kill-Test je Klasse (bindend, ADR-267-Reibungs-Kill-Muster):** Muss in >30 %
der Fälle, die unter eine SA-Klasse fallen, doch ein Einzel-OK eingeholt werden
(weil die Klasse zu weit/falsch schnitt oder ein Gate übersehen wurde), ist die
Klasse **zu überarbeiten oder zu streichen**, nicht zu flicken. Gemessen über
Signal G (unten) je Klasse.

## How to apply (Agent-Seite)

- **Pre-Flight vor jedem PR**: Merge-Pfad prüfen (Rulesets/required checks vs.
  reale Check-Namen), damit Gates VOR der Freigabe-Frage bekannt sind — nicht
  danach. (Realfall 2026-07-02: Check-Präfix `CI / gate` vs. Required-Kontext
  `ci / gate` erst nach 3 Denials entdeckt; Fix war ein gate-freier
  Workflow-Commit statt Ruleset-Edit/--admin.)
- **Root-Cause vor Eskalation**: Bevor ein Gate angefragt wird, prüfen ob ein
  gate-freier Fix existiert (Workflow/Code ändern statt Protection bypassen).
- **Ein Freigabe-Block pro Runde**: alle gated Aktionen gesammelt, mit exakten
  Kommandos und Eskalationsstufe im Wortlaut — der Permission-Classifier lässt
  wörtlich Freigegebenes durch, nicht mehr.
- **Verbale Freigabe gilt wörtlich**: „mergen" ≠ „--admin", „ausführen" ≠
  „Ruleset ändern". Präzise fragen.
- **Batch-Freigabe durable vermerken**: wird eine Freigabe für einen Batch (mehrere Repos/PRs,
  z.B. ein templated Rollout) erteilt, dies in der ERSTEN PR/Commit-Message des Batches
  wörtlich als „Batch approved by user" vermerken, damit sie später (Retro, Audit)
  nachvollziehbar bleibt. Realfall 2026-07-15 (KD-Sitemap-Rollout, 9 Repos, 6 echte
  Prod-Deploys): ein späteres Retro (`c25d21`) konnte anhand der Artefakte keine Freigabe
  für den Batch finden — nach Nutzerangabe war er freigegeben, nur nirgends vermerkt.

## Effectiveness test (binding — falsify or cut)

Signal **G** = User-Roundtrips pro gate-pflichtiger Entscheidung (Ziel: 1).
Baseline: Session 2026-07-02 = 3 Roundtrips für 1 Entscheidungskomplex
(Merge #131). Nach ~10 Sessions messen (session-retro); wenn G nicht Richtung 1
konvergiert, Policy schneiden, nicht flicken.

## Changelog

- 2026-07-12: **SA-1 + SA-3 RATIFIZIERT (Achim, wörtlich)** — Abschnitt
  „Standing-Authorization-Klassen" ergänzt (KONZ-platform-019 B2). SA-1 (Merge
  CI-grüner PR ohne Review-Pflicht+ohne Auto-Deploy) und SA-3 (Secret-Datei-
  Hausputz ohne Inhalts-Dump) gelten ab sofort. **SA-2 zurückgestellt** bis
  KONZ-019 B1 (pfad-gescopte Review) — ID reserviert. Je Klasse >30%-Kill-Test
  (ADR-267-Muster). Ziel: den vom Classifier erzeugten Einzelwort-Zwang für
  gate-freie Aktionen abbauen, ohne einen Gate zu senken. Re-Ratifikation im
  Kapitäns-Kanal 2026-07-17 (PR #1105-Kommentar); SA-1/SA-3 werden erste
  Einträge der lotse-authorizations-Registry (Lotsen-Charta Art. 2.6).
- 2026-07-16: **Batch-Freigabe-Vermerk-Regel** ergänzt (How to apply) — nach Retro `c25d21`
  (KD-Sitemap-Rollout 2026-07-15, 9 Repos, 6 Prod-Deploys), das als ungegatet eingestuft wurde,
  weil eine erteilte Freigabe nirgends vermerkt war. Marker: „Batch approved by user" in der
  ersten PR/Commit-Message eines freigegebenen Batches.
- 2026-07-03: Von Achim ratifiziert (Session ausschreibungs-hub, wörtlich „3 go"
  auf den Freigabe-Block) — gilt org-weit als Policy.
- 2026-07-03: Initial DRAFT (Session ausschreibungs-hub).
