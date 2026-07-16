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

- 2026-07-16: **Batch-Freigabe-Vermerk-Regel** ergänzt (How to apply) — nach Retro `c25d21`
  (KD-Sitemap-Rollout 2026-07-15, 9 Repos, 6 Prod-Deploys), das als ungegatet eingestuft wurde,
  weil eine erteilte Freigabe nirgends vermerkt war. Marker: „Batch approved by user" in der
  ersten PR/Commit-Message eines freigegebenen Batches.
- 2026-07-03: Von Achim ratifiziert (Session ausschreibungs-hub, wörtlich „3 go"
  auf den Freigabe-Block) — gilt org-weit als Policy.
- 2026-07-03: Initial DRAFT (Session ausschreibungs-hub).
