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
depends_on: [KONZ-platform-014]
tags: [approvals, deploy, review-policy, segregation-of-duties, fail-closed, hitl, codeowners, environments]
scope:
  include_paths:
    - "**/.github/CODEOWNERS"
    - "**/.github/workflows/deploy.yml"
    - "dev-hub/apps/operations/**"
---

# ADR-267: Review-Requirement für Deploy-Approvals — deterministisches Fail-Closed-Gate + HITL-Lern-Vorschlagsschicht (Cross-Repo)

- **Status:** accepted *(2026-07-08, Owner-Entscheidung für die Struktur; Umsetzung inkrementell, s. §Umsetzung. Enforcement-Grenze: dieses ADR beschreibt das Modell — scharf wird es erst mit den unter §Umsetzung genannten GitHub-/Code-Änderungen.)*
- **Datum:** 2026-07-08
- **Entscheider:** Achim Dehnert
- **Verwandt:** KONZ-platform-014 (Deploys & Approvals Board), dev-hub#117 (Stufe A/B-lite), dev-hub#118 (Stufe B One-Click-Approve)

## Zusammenfassung

Das Deploys-&-Approvals-Board (KONZ-platform-014) erlaubt ab Stufe B, wartende
Deployments **cross-repo** (achimdehnert + iilgmbh) freizugeben. Damit stellt sich
die Governance-Frage: **Welche Deploys brauchen eine menschliche Zweitmeinung
(Reviewer `wirdigital`), welche nicht?** Owner-Setzung: **wichtige Entscheidungen
sind reviewpflichtig; reine Docs-Updates o.ä. nicht.**

Dieses ADR trifft zwei harte Entscheidungen:

1. **Das „reviewpflichtig?"-Gate ist deterministisch und fail-closed** — eine
   deklarative Pfad-Policy, verankert **GitHub-nativ** (Environment-Required-Reviewer
   + `paths-ignore`/CODEOWNERS), **nicht** ein lernendes/probabilistisches Modell.
   Eine Sicherheitskontrolle, die im Zweifel *offen* fällt, ist ein Governance-Loch.
2. **Der „Lern"-Wunsch wird als reine Vorschlags-Schicht (HITL) realisiert** — sie
   beobachtet die Audit-Spur und **schlägt** Policy-Verfeinerungen zur **menschlichen
   Ratifizierung** vor. Sie **verschiebt das Gate nie autonom** und entscheidet **nie**
   eine einzelne Freigabe.

## Kontext & Problem

- **Auslöser:** KONZ-platform-014 Stufe B (dev-hub#118) führt One-Click-Approve über
  den bestehenden **achimdehnert-`GITHUB_TOKEN`** ein (führend: achimdehnert + iilgmbh).
  `wirdigital` ist **menschlicher** Zweitmeinungs-Reviewer, keine Token-Identität.
- **Adversariale Vorbelastung (KONZ-014 §6):** Ein Board-Approve droht, den effektiven
  Approver-Kreis auf „jeder Staff in devhub" auszuweiten und GitHubs Reviewer-ACL durch
  eine schwächere Parallel-ACL zu ersetzen (Governance-Fork). Segregation-of-Duties darf
  nicht zum Theater werden.
- **Offene Frage:** *Wo* verlangt ein Deploy die Zweitmeinung? Ohne klare Regel entweder
  Reibung (alles reviewpflichtig) oder Löcher (Wichtiges rutscht als „docs-only" durch).

## Entscheidungstreiber

- **Fail-closed:** Unbekannt/unklassifiziert ⇒ **reviewpflichtig** (nie das Gegenteil).
- **Determinismus & Auditierbarkeit:** Jede Gate-Entscheidung muss reproduzierbar und
  nachvollziehbar sein (Security-Kontrolle).
- **Single Source of Truth:** Keine zweite Wahrheit im devhub-Board — die Regel lebt dort,
  wo der Deploy real gated (GitHub).
- **Cross-Repo:** gilt für alle Repos in achimdehnert + iilgmbh, nicht repo-lokal.
- **Adaptivität ohne Autonomie:** Regel-Pflege soll lernen dürfen — aber nur *vorschlagend*.

## Betrachtete Optionen

| Option | Gate-Mechanismus | Bewertung |
|--------|------------------|-----------|
| **A — Reiner Lern-Mechanismus** | ML/Heuristik klassifiziert & wendet an | ❌ **verworfen**: probabilistisches Gate für eine Sicherheitskontrolle, fällt im Zweifel offen (False-Negative ⇒ Wichtiges ohne Review). Cold-Start, Drift, schwer auditierbar. |
| **B — Nur GitHub-nativ** | Environment-Rules + CODEOWNERS + `paths-ignore`, keine devhub-Schicht | 🟡 robust & minimal, aber keine Sichtbarkeit/Adaptivität; Regelpflege rein manuell. |
| **C — Deterministisch (fail-closed) + HITL-Lern-Vorschlag** | GitHub-natives Gate; devhub zeigt Klassifikation an; Lerner schlägt Regeländerungen vor, Mensch ratifiziert | ✅ **gewählt**: deterministisches Gate **und** die gewünschte Adaptivität, ohne die Sicherheit probabilistisch zu machen. |

## Entscheidung

**Option C.**

1. **Deterministische Pfad-Policy als Gate (fail-closed).** Ein Deploy ist
   *nicht* reviewpflichtig **nur** wenn *alle* geänderten Pfade seines
   auslösenden Commits/PRs auf einer expliziten **Review-frei-Allowlist** liegen
   (z.B. `docs/**`, `*.md`, `mkdocs.yml`, `**/CHANGELOG.md`). Jeder Pfad außerhalb
   ⇒ **reviewpflichtig**. Leere/unbekannte Diff-Info ⇒ **reviewpflichtig**.
2. **Verankerung GitHub-nativ (SSoT).** Die Regel wird dort erzwungen, wo der Deploy
   gated: (a) `production`-Environment mit **Required Reviewer** (`wirdigital`) für
   reviewpflichtige Deploys; (b) docs-only-Änderungen laufen über einen Deploy-Pfad,
   der das reviewpflichtige Environment nicht berührt (`paths-ignore` / getrennter Job)
   **oder** über CODEOWNERS-Ausnahme. Das devhub-Board **umgeht** diese ACL nie —
   `current_user_can_approve` bleibt die letzte Instanz (dev-hub#118).
3. **devhub-Board klassifiziert nur advisorisch.** Das Board *zeigt* pro wartendem
   Deploy ein Badge „docs-only / reviewpflichtig" (aus den geänderten Pfaden berechnet)
   — als Orientierung, **nicht** als Gate. Fehlt die Diff-Info, zeigt es „reviewpflichtig".
4. **HITL-Lern-Vorschlagsschicht.** Ein Mechanismus wertet die `ApprovalAction`-Audit-Spur
   (dev-hub#118) + Klassifikations-Historie aus und **schlägt** Policy-Verfeinerungen vor
   („Pfad `X` war in N Freigaben stets docs-only-Schnellfreigabe — in die Allowlist
   aufnehmen?"). Vorschläge landen als **PR gegen die Allowlist-Datei** (menschlicher
   Review/Merge) — Muster wie ADR-188 B2 (Vorschlag→Diff→Accept/Reject). **Kein Auto-Apply.**

**Kernsatz:** Das Gate ist deterministisch + fail-closed; der Lerner schlägt nur
Regeländerungen zur menschlichen Ratifizierung vor — er entscheidet nie eine einzelne
Freigabe.

## Konsequenzen

**Positiv:**
- Sicherheitskontrolle bleibt deterministisch, auditierbar, fail-closed.
- SSoT in GitHub; das Board erzeugt keine zweite ACL.
- Reibungsarm für docs-only, ohne Löcher bei Wichtigem.
- Adaptivität (Owner-Wunsch) ohne autonome Gate-Verschiebung.
- Cross-Repo einheitlich (eine Allowlist-Konvention, GitHub-nativ pro Repo).

**Negativ / Kosten:**
- Allowlist muss gepflegt werden (der Lerner mildert das, ersetzt es nicht).
- Pfad-basierte Klassifikation ist grob — ein „docs-only"-Commit, der heimlich Code
  ändert, muss durch die Allowlist-Enge (nur echte Doc-Globs) verhindert werden; im
  Zweifel fail-closed.
- devhub-Klassifikation braucht die Diff/PR-Info pro Run (zusätzliche GitHub-Calls,
  gecacht wie das Board).

## Umsetzung (inkrementell, cross-repo)

1. **Allowlist-Konvention** in `platform/policies/` (`review-free-paths.yml` o.ä.),
   pro Repo via CODEOWNERS/Environment-Rules gespiegelt. *(erste konkrete Änderung)*
2. **GitHub-Environment-Härtung**: `wirdigital` als Required Reviewer auf reviewpflichtigen
   Environments; docs-only-Pfad ohne diese Anforderung.
3. **devhub-Advisory-Badge** in `apps/operations` (Board zeigt Klassifikation, fail-closed).
4. **HITL-Vorschlagsschicht** auf Basis `ApprovalAction` — als eigener, gegateter Schritt.

**Ehrliche Enforcement-Grenze:** Bis Schritt 1–2 gemergt sind, ist dies ein *Modell*, kein
erzwungenes Gate. Kein Schritt wird solo gemergt, der org-weites Deploy-/Approve-Verhalten
ändert (autonomy-gate `autonomous-no-human-review`).

## Adversariale Betrachtung

- **„Team erfüllt formal, umgeht praktisch"**: Pfad-basiert (nicht label-basiert) ⇒ schwerer
  zu gamen als ein `review:skip`-Label; die Allowlist enthält nur echte Doc-Globs.
- **„Lerner schleicht das Gate auf"**: strukturell ausgeschlossen — Vorschläge sind PRs mit
  menschlichem Merge; der Lerner hat keinen Schreibpfad auf die aktive Policy.
- **„Board wird zweite ACL"**: das Board klassifiziert nur advisorisch; das echte Gate ist
  GitHubs Reviewer-ACL (`current_user_can_approve`).

## Kill-Gate / Review

- **review_by:** 2026-10-08.
- **Kill-Kriterium:** Wenn im ersten vollen Quartal nach Enforcement die Allowlist zu >30%
  „False-Reviewpflichtig"-Reibung erzeugt (docs-only fälschlich reviewpflichtig) **oder**
  ein einziger reviewpflichtiger Deploy fälschlich als docs-only durchrutscht (fail-open-
  Vorfall) → Policy zurück auf „alles reviewpflichtig" + Neuentwurf. Der Fail-Open-Vorfall
  ist das harte Abbruchkriterium (Sicherheit vor Bequemlichkeit).
- **Lern-Schicht-Kill:** Werden ihre Vorschläge in 60 Tagen zu <20% ratifiziert (zu viel
  Rauschen) → Schicht abschalten, deterministische Policy bleibt.
