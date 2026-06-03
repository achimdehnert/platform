---
concept_id: KONZ-platform-002
title: Enterprise-Konsolidierung der IIL-Org-Topologie (Governance + native Secret-Prevention an einer Kontrollebene)
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []          # keine ADR-211-Spec; Bezug = ADR-235 (Secret-Prevention-Posture) + platform#412
adr_threshold: org-weiter ADR   # Cross-Repo, Security-Perimeter, Lizenz, neue Boundary (Enterprise-Topologie), Reversal der "public native / private CI-Fallback"-Aufteilung aus ADR-235
review_by: 2026-07-15
kill_criteria: "Wenn bis 2026-08-15 (a) das GitHub-Account-Team die Kostenneutralität (Seats=Personen, nicht Orgs/Repos) NICHT schriftlich bestätigt, ODER (b) für ttz-lif/meiki-lra kein Daten-Souveränitäts-Sign-off vorliegt → Migrationsspur sunset; Fallback = per-Org 'Secret Protection' (Team) + ADR-235 CI-gitleaks bleibt Layer 1 außerhalb bahn-sqf."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "API graphql enterprise(slug:iilgmbh).organizations", commit_or_pr: "1 node: bahn-sqf", opened_in_session: true}
  - {claim_id: C2, source_path: "API enterprises/iilgmbh/consumed-licenses", commit_or_pr: "2 consumed / 2 purchased: achimdehnert, iljalerch", opened_in_session: true}
  - {claim_id: C3, source_path: "API enterprises/iilgmbh/settings/billing/advanced-security", commit_or_pr: "secret_protection=2, code_security=2 committers", opened_in_session: true}
  - {claim_id: C4, source_path: "API enterprises/iilgmbh/code-security/configurations/17", commit_or_pr: "secret_scanning/push_protection/validity/code_scanning/dependabot=enabled", opened_in_session: true}
  - {claim_id: C5, source_path: "API .../configurations/17/repositories", commit_or_pr: "3 repos, alle bahn-sqf", opened_in_session: true}
  - {claim_id: C6, source_path: "API .../code-security/configurations/defaults", commit_or_pr: "[] (kein Default für neue Repos)", opened_in_session: true}
  - {claim_id: C7, source_path: "API orgs/{iilgmbh,ttz-lif,meiki-lra,pactive-de}.plan.name", commit_or_pr: "team (alle 4); bahn-sqf=enterprise", opened_in_session: true}
  - {claim_id: C8, source_path: docs/adr/ADR-235-org-secret-prevention-posture.md, commit_or_pr: "status: accepted", opened_in_session: true}
created: 2026-06-03
---

# KONZ-platform-002 — Enterprise-Konsolidierung der IIL-Org-Topologie

## 1. Executive Summary

Die GitHub-Topologie ist zersplittert: Die Enterprise `iilgmbh` enthält **nur** `bahn-sqf` (C1); vier weitere Orgs (`iilgmbh`, `ttz-lif`, `meiki-lra`, `pactive-de`) laufen auf **separaten Team-Plänen außerhalb** der Enterprise (C7); der User-Account `achimdehnert` hält 54 Repos und kann keiner Enterprise beitreten. Die Enterprise hat bereits die richtige Security-Config (17 „GitHub recommended", volle Suite enabled, C4) — aber sie ist nur auf **3 bahn-sqf-Repos** angewandt (C5) und **nicht** Default für neue Repos (C6). Verifiziert: Enterprise rechnet **pro Person** ab (2 Seats: achimdehnert + iljalerch; 2 GHAS-Committer — C2/C3), **nicht** pro Org/Repo. Daraus folgt: Orgs in die Enterprise aufzunehmen ist **kostenneutral** und macht die vier Team-Pläne redundant. Vorschlag: (1) Team-Orgs in die Enterprise aufnehmen, (2) Config 17 als Enterprise-Default + apply-to-all, (3) wichtige private `achimdehnert`-Repos in eine Enterprise-Org migrieren, User-Account austrocknen. Wirkung: native Push-Protection (pre-history) wird **Layer 1 überall**; ADR-235 CI-gitleaks (C8) demotet zu Defense-in-depth. Schärfster offener Punkt: Daten-Souveränität von `ttz-lif`/`meiki-lra` beim Org-Ownership-Wechsel.

## 2. Scope & Evidenzbasis

**In Scope:** Org→Enterprise-Mitgliedschaft, Enterprise-Security-Config-Default/Apply, Repo-Migration User→Org, Lifecycle des `achimdehnert`-Accounts.
**Out of Scope:** Konkrete Repo-für-Repo-Transferreihenfolge (eigener Runbook), CI/CD-Secret-Rotation pro Repo (operativ), die €-Sätze des GHEC-Vertrags (nicht API-lesbar — nur Mengen C2/C3 verifiziert).
**Evidenz:** C1–C8 sind diese Session **per GitHub-API gelesen** (Enterprise-PAT), nicht erinnert. €-Preise = `H` (Hypothese, billigster Check: GitHub-Billing-Dashboard / Account-Team).

## 3. Infrastruktur-Fit

| Aspekt | Ist (verifiziert) | Soll | Beleg |
|---|---|---|---|
| Enterprise-Member-Orgs | nur `bahn-sqf` | + iilgmbh, ttz-lif, meiki-lra (pactive-de optional) | C1 |
| Security-Config-Reichweite | 3 Repos, kein Default-for-new | apply-to-all + Default | C4/C5/C6 |
| Billing-Treiber | 2 Seats + 2 GHAS-Committer (Personen) | unverändert (gleiche 2 Personen) | C2/C3 |
| Team-Pläne (4 Orgs) | aktiv, parallel zur Enterprise | redundant → kündbar nach Aufnahme | C7 |
| User-Account `achimdehnert` | 54 Repos, kein nativer Schutz möglich | austrocknen; Rest via ADR-235 CI-gitleaks | C8 |

## 4. Steelman (warum das die richtige Richtung ist)

Eine Enterprise existiert bereits, ist bezahlt (2 Seats) und trägt die ideale Security-Config — sie wird nur nicht genutzt. Der teuerste Teil (Lizenz, Config-Design) ist erledigt; es fehlt reine **Zuweisung** (C4/C5/C6). Da die Abrechnung personen- und nicht org-/repo-gebunden ist (C2/C3), bringt Konsolidierung den stärksten Gate (native Push-Protection, pre-history) **kostenneutral** auf alle Repos und eliminiert gleichzeitig vier redundante Team-Pläne (C7) — Sicherheit *und* Vereinfachung *und* Ersparnis in einem Zug. Die per-Repo-/CI-gitleaks-Arbeit (ADR-235) war Symptombehandlung einer fehlenden Kontrollebene; diese liefert die Ebene.

## 5. Konzeptdefinition

**Kernthese:** Eine einzige Kontrollebene (Enterprise `iilgmbh`) mit Config 17 als erzwungenem Default ersetzt die zersplitterte per-Org/per-Repo-Schalterei; native Push-Protection wird Layer 1 überall, CI-gitleaks (ADR-235) wird Defense-in-depth.

**Sequenz (jede Stufe ein eigenes Gate):**
- **S1 — Orgs aufnehmen.** `iilgmbh`, `ttz-lif`, `meiki-lra` als Member-Orgs der Enterprise; `pactive-de` optional. *Gate:* Account-Team bestätigt Kostenneutralität (C2/C3-Annahme) **bevor** Team-Pläne gekündigt werden.
- **S2 — Config scharf stellen.** Config 17 (oder eine schlanke Ableitung, s. Befund B3) als **Enterprise-Default für neue Repos** + **apply-to-all** über alle Member-Orgs. *Gate:* erst `enforcement: unenforced` (Repos dürfen abweichen) → beobachten → dann `enforced`.
- **S3 — Repos migrieren.** Priorisierte private `achimdehnert`-Repos in die passende Enterprise-Org (Default-Ziel: org `iilgmbh`) transferieren; sie erben die Config. *Gate:* pro Repo Runbook (Redirects, CI-Secrets neu setzen, Deploy-Pfade, Package-Refs).
- **S4 — Austrocknen.** `achimdehnert` nur noch für Privates/Experimente; verbleibende Repos behalten ADR-235 CI-gitleaks als Layer 1.

**SSoT-Prüfung:** Erzeugt keine zweite Wahrheit — die Enterprise-Config wird die *eine* Quelle der Security-Posture; ADR-235 wird per Amendment darauf verwiesen (Enterprise = L1-Mechanismus, CI-gitleaks = Fallback/User-Account). Die Repo-Registry (`scripts/repo-registry.yaml`) muss nach Transfers die neuen Owner abbilden.

## 6. Adversariale Analyse

> Inline (Steelman in §4). Unabhängiger 3-Agenten-Fan-out (Steelman/Diabolus/Maintainer-2028) + Konfliktmatrix bzw. externe Zweitmeinung (`/adr-handoff-extern`) = nächste Schärfe-Stufe vor dem ADR — hier nicht ausgeführt (keine Multi-Agent-Anforderung).

**Advocatus Diabolus:**
- *Souveränitäts-Falle:* Ein Org-Ownership-Wechsel von `ttz-lif`/`meiki-lra` in eine zentrale Enterprise verschiebt **Administrations- und Audit-Hoheit** — bei Behörden-/LRA-Workloads (CLAUDE.md) potenziell ein Compliance-Problem, **unabhängig** davon, dass Secret-Scanning GitHub-intern läuft. „native ist GitHub-intern" beantwortet die Datenschutz-Frage, **nicht** die Governance-Frage „wer darf die Org verwalten".
- *Kostenneutralität ist behauptet, nicht vertraglich belegt:* C2/C3 zeigen *Mengen* (2/2), nicht den GHEC-Vertrag. Ein „pro Seat"-Modell kann Mindestabnahmen / GHAS-Add-on-Linien haben, die beim Hochskalieren der Committer (neue Personen) springen. „kostenneutral" ist bis zum Account-Team-OK ein `H`.
- *„apply-to-all" ist ein scharfes Messer:* Config 17 schaltet **auch Code Scanning (CodeQL)** auf jedem Repo — Actions-Minuten + mögliche rote Checks auf Nicht-Code-/Legacy-Repos. „Sichtbar machen" (Config gesetzt) ≠ „funktioniert überall ohne Reibung".
- *Migration ist irreversibel-ish:* Repo-Transfer bricht hartkodierte Remotes, Actions-Secrets (werden **nicht** mittransferiert), Deploy-Pfade (`/opt/<repo>`), Package-Referenzen (`achimdehnert/...@main` in ~14 Reusable-Callern). Formal erfüllt, praktisch rote CI über Nacht.

**Maintainer-2028:** „Warum sind manche Repos unter `achimdehnert`, manche unter `iilgmbh`-org, manche unter der Enterprise? Wenn die Migration auf halbem Weg stehenblieb, ist die Topologie schlimmer als vorher — drei Wahrheiten statt einer. Gibt es einen erzwungenen Endzustand oder nur einen guten Vorsatz?"

## 7. Deep-Dive

- **Config-Mechanik:** `default_for_new_repos` (C6 leer) + `attach scope=all` sind getrennte Schalter; beides nötig, sonst greift die Config nur auf Alt- *oder* Neu-Repos.
- **Enforcement-Stufen:** GitHub-Configs kennen `enforced`/`unenforced` — S2 startet bewusst `unenforced` (Beobachtung) vor `enforced` (Drift-Schutz).
- **GHAS-Committer-Skalierung:** Treiber sind **distinct active committers** (90-Tage), aktuell 2 (C3). Mehr Repos ≠ mehr Committer, solange dieselben 2 Personen pushen — der Kostenpfad bleibt flach, bis eine 3. Person dazukommt.
- **User-Account-Restmenge:** 54 Repos; nicht alle migrationswürdig (Archiv/Experiment). Auswahlkriterium: privat **und** aktiv **und** wertvoll → Migrationskandidat; Rest bleibt unter ADR-235 L2.

## 8. Alternativen

| ID | Ansatz | Für | Gegen | Verdikt |
|---|---|---|---|---|
| **ALT-A** *(radikal kleiner)* | Keine Org-Moves. Config 17 nur auf bahn-sqf vollständig + ADR-235 CI-gitleaks bleibt überall sonst Layer 1. | null Migrationsrisiko; sofort | private Org-/User-Repos bleiben ohne native Prävention; vier Team-Pläne bleiben | Fallback / Kill-Gate-Ziel |
| **ALT-B** *(technisch)* | Orgs bleiben standalone; „Secret Protection" **pro Org** (Team) kaufen + per-Org-Config. | keine Ownership-Verschiebung (gut für Souveränität) | N Billing-Stränge + N Admin-Punkte; teurer als Enterprise-Seats; kein zentraler Default | Teil-Lösung für Government-Orgs |
| **ALT-C** *(organisatorisch — Vorschlag)* | Konsolidierung in die Enterprise (S1–S4). | kostenneutral, eine Kontrollebene, spart Team-Pläne | Ownership-Shift (Souveränität), Migrationsaufwand | Gewählt für Nicht-Government-Orgs |
| **ALT-D** *(hybrid)* | Nur Nicht-Government-Orgs (iilgmbh, pactive-de) konsolidieren; `ttz-lif`/`meiki-lra` standalone mit per-Org Secret Protection (ALT-B). | trennt Souveränitäts-Risiko sauber ab | zwei Betriebsmodelle | **Empfohlene Synthese** |

## 9. Out-of-the-Box

- **OOTB-1 — GitHub-as-Code:** Enterprise-Config-Zuweisung + Org-Mitgliedschaft deklarativ (Terraform `github` provider / Safe-Settings) → Drift-resistent, reviewbar, statt Klick-Ops.
- **OOTB-2 — Default-only + Backfill-Skript:** Statt „apply-to-all" (großer Blast-Radius) nur `default_for_new` setzen + ein idempotentes Backfill-Skript, das Repos gestaffelt anhängt (kleinere, beobachtbare Wellen).
- **OOTB-3 — Souveränitäts-Sidecar:** Government-Orgs *nicht* in die Enterprise; stattdessen denselben Config-Inhalt per-Org spiegeln (ALT-B), die Gleichheit per CI-Audit (ADR-235-Meter erweitern) erzwingen → zentrale *Posture* ohne zentrale *Ownership*.

## 10. Befunde

| ID | Befund | Schwere | Evidenz |
|---|---|---|---|
| B1 | Enterprise nutzt 1/5 möglicher Orgs; Config auf 3/viele Repos; kein Default-for-new | hoch | C1/C5/C6 |
| B2 | 4 redundante Team-Pläne parallel zur personen-basierten Enterprise-Abrechnung | mittel (Kosten) | C2/C3/C7 |
| B3 | Config 17 schaltet Code Scanning mit → „apply-to-all" verursacht CodeQL-Last/Reibung auf Nicht-Code-Repos | mittel | C4 |
| B4 | Government-Org-Ownership-Shift = Governance/Souveränitäts-Risiko, von „native=intern" NICHT adressiert | hoch | CLAUDE.md (H), C7 |
| B5 | Repo-Transfer trägt Actions-Secrets nicht mit; Deploy-Pfade/Package-Refs brechen | mittel | H (Runbook nötig) |

## 11. Top-5-Risiken

1. **Souveränität (B4):** Behörden-Org unter zentrale Enterprise → Compliance-Bruch. *Mitigation:* ALT-D/OOTB-3 — Government-Orgs draußen lassen, Posture spiegeln.
2. **Kosten-Annahme falsch:** „pro Person" hat versteckte Mindestabnahme. *Mitigation:* Account-Team-Sign-off als S1-Gate (Kill-Criteria).
3. **Halbe Migration (Maintainer-2028):** drei Wahrheiten statt einer. *Mitigation:* erzwungener Endzustand + Registry-Reconcile + datiertes Migrationsfenster.
4. **CI-Sturz nach Transfer (B5):** Secrets/Pfade/Package-Refs. *Mitigation:* pro-Repo-Runbook + Transfer in Wellen, nicht Big-Bang.
5. **CodeQL-Reibung (B3):** rote Checks org-weit. *Mitigation:* schlanke Secrets-only-Config für Blanket-Apply, Voll-Suite nur wo gewollt.

## 12. Empfehlungen

- **REC-1:** **ALT-D** wählen — Enterprise-Konsolidierung für `iilgmbh`(+`pactive-de`); `ttz-lif`/`meiki-lra` **standalone** mit gespiegelter Config (OOTB-3), bis ein Souveränitäts-Sign-off vorliegt.
- **REC-2:** S2 mit **schlanker „Secret Scanning + Push Protection"-Config** für apply-to-all; Config 17 (inkl. CodeQL) nur als Default-for-new / opt-in pro Code-Repo (adressiert B3).
- **REC-3:** S1 erst nach **schriftlicher Kostenbestätigung** des GitHub-Account-Teams; Team-Pläne erst **nach** bestätigter Aufnahme kündigen (adressiert B2/Risk-2).
- **REC-4:** Migration als **Runbook + Wellen** (3–5 Repos/Welle), Actions-Secrets-Checkliste, Package-Ref-grep (`achimdehnert/...@main` in Reusable-Callern) **vor** Transfer (adressiert B5).
- **REC-5:** ADR-235 **Amendment** + neuer **org-weiter ADR** „Enterprise als Security-Kontrollebene" sobald REC-1/-3-Gates grün; ADR-235-Meter um „native enabled?" je Enterprise-Repo erweitern (OOTB-3-Enforcement).

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (vorgeschlagen):** ALT-D als Richtung; Umsetzung **gated**, nicht sofort. Kein Org-Move / kein Team-Plan-Kündigen vor den S1/S2-Gates.

**Kill-Gate (messbar):** siehe Frontmatter `kill_criteria` — bis **2026-08-15** Kostenbestätigung **und** Government-Sign-off; sonst Sunset auf ALT-A (bahn-sqf voll + ADR-235 CI-gitleaks bleibt L1 außerhalb). Exception-Budget: 1× Verlängerung bis 2026-09-15 mit benanntem Grund.

**30/60/90:**
- **30:** Account-Team-Kostenbestätigung (S1-Gate); schlanke Secrets-Config in der Enterprise anlegen (B3); ADR-235-Amendment-Draft.
- **60:** `iilgmbh`(+`pactive-de`) aufnehmen; Config als Default-for-new + apply-to-all `unenforced`; 1. Migrations-Welle (3 Repos) als Runbook-Pilot.
- **90:** `enforced` schalten; Government-Souveränitäts-Sign-off klären (REC-1); Team-Pläne der aufgenommenen Orgs kündigen; Meter-Erweiterung live.
