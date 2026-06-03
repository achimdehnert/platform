---
concept_id: KONZ-platform-002
title: Enterprise-Konsolidierung der IIL-Org-Topologie (Governance + native Secret-Prevention an einer Kontrollebene)
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []          # keine ADR-211-Spec; Bezug = ADR-235 (Secret-Prevention-Posture) + platform#412
adr_threshold: org-weiter ADR   # Cross-Repo, Security-Perimeter, Lizenz, neue Boundary (Enterprise-Topologie), Reversal der "public native / private CI-Fallback"-Aufteilung aus ADR-235
review_by: 2026-07-15
kill_criteria: "Wenn bis 2026-08-15 (a) das GitHub-Account-Team die Kostenneutralität (Seats=Personen, nicht Orgs/Repos) NICHT schriftlich bestätigt, ODER (b) für ttz-lif/meiki-lra kein Daten-Souveränitäts-Sign-off vorliegt, ODER (c) Portabilität nicht BEWIESEN ist (make exit-plan erzeugt für ≥1 Org einen vollständigen Runbook UND ≥1 Exit-Feuerübung grün) → keine Org-Aufnahme; Migrationsspur sunset; Fallback = per-Org 'Secret Protection' (Team) + ADR-235 CI-gitleaks bleibt Layer 1 außerhalb bahn-sqf."
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
  - {claim_id: C9, source_path: "API enterprises/iilgmbh consumed-licenses logins + graphql ownerInfo.samlIdentityProvider", commit_or_pr: "Logins ohne _iilgmbh-Suffix + persönl. Account Member → kein EMU; samlIdentityProvider=null → kein SSO-Lock-in → Exit machbar (nicht kostenlos)", opened_in_session: true}
created: 2026-06-03
---

# KONZ-platform-002 — Enterprise-Konsolidierung der IIL-Org-Topologie

## 1. Executive Summary

Die GitHub-Topologie ist zersplittert: Die Enterprise `iilgmbh` enthält **nur** `bahn-sqf` (C1); vier weitere Orgs (`iilgmbh`, `ttz-lif`, `meiki-lra`, `pactive-de`) laufen auf **separaten Team-Plänen außerhalb** der Enterprise (C7); der User-Account `achimdehnert` hält 54 Repos und kann keiner Enterprise beitreten. Die Enterprise hat bereits die richtige Security-Config (17 „GitHub recommended", volle Suite enabled, C4) — aber sie ist nur auf **3 bahn-sqf-Repos** angewandt (C5) und **nicht** Default für neue Repos (C6). Verifiziert: Enterprise rechnet **pro Person** ab (2 Seats: achimdehnert + iljalerch; 2 GHAS-Committer — C2/C3), **nicht** pro Org/Repo. Daraus folgt: Orgs in die Enterprise aufzunehmen ist **kostenneutral** und macht die vier Team-Pläne redundant. Vorschlag: (1) Team-Orgs in die Enterprise aufnehmen, (2) Config 17 als Enterprise-Default + apply-to-all, (3) wichtige private `achimdehnert`-Repos in eine Enterprise-Org migrieren, User-Account austrocknen. Wirkung: native Push-Protection (pre-history) wird **Layer 1 überall**; ADR-235 CI-gitleaks (C8) demotet zu Defense-in-depth. Schärfster offener Punkt: Daten-Souveränität von `ttz-lif`/`meiki-lra` beim Org-Ownership-Wechsel. **Querschnitts-Prinzip (Vertiefung 2026-06-03):** Konsolidierung **mit Portabilität by construction** — da Orgs/Repos später wieder austreten können müssen (Kunden/Behörden), ist Exit-Readiness eine *abgeleitete, getestete, getaggte* Eigenschaft (`make exit-plan`, `exit_class`-Tagging, Coupling-Indirektion, Exit-Feuerübung), kein gepflegtes Dokument. Verifiziert: kein EMU/kein SAML → Exit machbar, aber nicht kostenlos (C9).

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

### Portabilität by construction (Exit-Readiness — Vertiefung 2026-06-03)

Reframe nach Advocatus-Diabolus-Pass: **nicht „Exit dokumentieren", sondern Portabilität als *abgeleitete, getestete, getaggte* Eigenschaft.** Statische Exit-Dokumente sind am Exit-Tag veraltet (Drift-Theater); der echte Lock-in ist *operativ*, nicht die Enterprise-Mitgliedschaft.

- **OOTB-4 — Exit als *ausführbares* Artefakt:** `make exit-plan ORG=<org>` fragt den **Live-Zustand** ab und **generiert** den aktuellen Detach-/Transfer-Runbook on-demand. **Vollständiges Inventar (R1-Schärfung, REC-4/5/6):** Repos · Actions-/Dependabot-Secrets + Org-/Repo-**Variables** · **Environments** + Deployment-Protection-Rules · **OIDC-Trusts** · Webhooks · **GitHub Apps**-Installations + fine-grained PATs + deploy keys · **Packages/Container-Registry** · **Pages** · branch-protection/**Rulesets** · code-scanning-Setup + Dependabot-Config · reusable-Workflow-Refs · externe Deploy-Ziele · **DNS/URL-Abhängigkeiten**. Secrets werden nach **Name vs. Wert vs. Rotation vs. Re-Provisioning-Quelle** getrennt (Werte wandern bei Transfer NICHT mit). Immer korrekt (aus der Realität abgeleitet), nie veraltet. (Philosophie wie ADR-234 „derived invariant" + ADR-235-Meter.)
- **OOTB-5 — Coupling-Indirektion statt Mitgliedschafts-Portabilität:** Teuerste Fessel ist der hartkodierte Owner-Name (`achimdehnert/<org>/...@main` in ~14 Reusable-Callern). Lösung: *eine* repointbare Alias-/Pin-Stelle → „Org wechselt Owner" = 1-Stellen-Repoint statt 14-Repo-Bruch. Senkt den realen 90%-Schmerz (B6). **Absicherung (R1, X-AD-6):** diese Stelle ist versioniert, review-pflichtig und fallbackfähig — sonst wird aus 14 Bruchstellen *eine* kritische zentrale.
- **OOTB-6 — Org als portabler Tenant (GitHub-as-Code):** deklarativer Org-Deskriptor (Member, Config, Billing-Owner, Deps) in Git (Terraform `github` / Safe-Settings). **Exit = denselben Deskriptor unter neuem Parent neu anwenden** — ein Replay, keine Operation am offenen Herzen.
- **OOTB-7 — Exit-Feuerübung:** periodisch einen echten Exit gegen eine **Wegwerf-Org** proben. Geprobte Reversibilität schlägt jedes Dokument; ein nie getesteter Runbook scheitert am Tag X.
- **OOTB-8 — `exit_class` als *abgeleitete Policy*, nicht als Label (R1-Schärfung, REC-2/9/20):** **eine** deklarative SSoT pro Org → `exit_class → {placement, allowed_features, required_checks, exit_tests}` plus `{Begründung, Owner, review_by, Abweichungen}`. Platzierung (in-Enterprise vs. standalone-gespiegelt), **Feature-Allowlist** (REC-9: `exit-likely`/`must-stay-local` dürfen **kein** EMU/SSO/Enterprise-only/nicht-exportierbares-Secret/ungeprüftes-App-Coupling), CI-Audit und Runbook-Generierung werden **alle daraus abgeleitet** — sonst entsteht genau die zweite Wahrheit (AD-1/M28-1), die das Tagging vermeiden soll. ALT-D wird damit vom Sonderfall zur generellen, abfragbaren Regel.
- **OOTB-9 — Owner-Sukzession:** Break-Glass-Owner-Verfahren + ≥1 dritter Recovery-Owner — **getestet** (Minimalrechte, regelmäßige Probe, Entzugspfad, Auditnachweis), nicht nur als Dokument (R1, X-REC-13). Die am wenigsten geplante „Migration raus" ist die eigene (Bus-Faktor 2, B7).

**Bewusste Dosierung (Lock-in vs. Portabilität ist eine echte Spannung):** `exit-likely`/`must-stay-local`-Orgs → maximale Portabilität, **minimale** Lock-in-Features (kein EMU, kein erzwungenes SSO, nur Config-Spiegel). `central-ok`-Orgs → volle Enterprise-Zentralisierung (Enforcement, ggf. SSO) **+ nur leichtere Portabilitäts-Baseline** (dokumentierte Rebuild-Fähigkeit statt voller Exit-Test-Maschinerie — schützt die Zwei-Personen-Kapazität, R1 X-AD-14). Die Spannung wird **pro Org-Klasse aufgelöst**, nicht weggeredet.

## 10. Befunde

| ID | Befund | Schwere | Evidenz |
|---|---|---|---|
| B1 | Enterprise nutzt 1/5 möglicher Orgs; Config auf 3/viele Repos; kein Default-for-new | hoch | C1/C5/C6 |
| B2 | 4 redundante Team-Pläne parallel zur personen-basierten Enterprise-Abrechnung | mittel (Kosten) | C2/C3/C7 |
| B3 | Config 17 schaltet Code Scanning mit → „apply-to-all" verursacht CodeQL-Last/Reibung auf Nicht-Code-Repos | mittel | C4 |
| B4 | Government-Org-Ownership-Shift = Governance/Souveränitäts-Risiko, von „native=intern" NICHT adressiert | hoch | CLAUDE.md (H), C7 |
| B5 | Repo-Transfer trägt Actions-Secrets nicht mit; Deploy-Pfade/Package-Refs brechen | mittel | H (Runbook nötig) |
| B6 | **Echter Lock-in ist operativ, nicht strukturell** — hartkodierte `achimdehnert/<org>/...@main`-Refs, Deploy-Pfade, Secrets; „aus Enterprise raus" ist nur die einfachen 10% | hoch | H (grep Reusable-Caller) |
| B7 | **Bus-Faktor 2** — Enterprise hat nur 2 Owner (achimdehnert + iljalerch); die unplanbarste „Migration raus" ist der eigene Ausfall | hoch | C2 |
| B8 | Exit ist **machbar** (kein EMU: Logins ohne `_iilgmbh`-Suffix, persönl. Account als Member; kein SAML) — aber **nicht** kostenlos (Detach + Posture lokal neu + Ownership-Transfer) | mittel | C9 |

## 11. Top-Risiken

1. **Souveränität (B4):** Behörden-Org unter zentrale Enterprise → Compliance-Bruch. *Mitigation:* ALT-D/OOTB-3/OOTB-8 — `exit-likely`/`must-stay-local` standalone, Posture spiegeln.
2. **Operative Scheinportabilität (B6):** Mitgliedschaft portabel gemacht, Coupling nicht → Exit bricht trotzdem 14 Repos. *Mitigation:* OOTB-5 Coupling-Indirektion + OOTB-4 abgeleiteter Exit-Plan.
3. **Owner-Sukzession / Bus-Faktor 2 (B7):** *Mitigation:* OOTB-9 Break-Glass + 3. Recovery-Owner.
4. **Kosten-Annahme falsch:** „pro Person" hat versteckte Mindestabnahme. *Mitigation:* Account-Team-Sign-off als S1-Gate.
5. **Halbe Migration (Maintainer-2028):** drei Wahrheiten statt einer. *Mitigation:* erzwungener Endzustand + Registry-Reconcile + datiertes Fenster.
6. **CI-Sturz nach Transfer (B5) / CodeQL-Reibung (B3):** *Mitigation:* Runbook+Wellen; schlanke Secrets-only-Config für Blanket-Apply.

## 12. Empfehlungen

- **REC-1:** **ALT-D, verallgemeinert via `exit_class` (OOTB-8)** — nicht „Government manuell draußen", sondern jede Org taggen (`central-ok | exit-likely | must-stay-local`); ein Gate steuert Platzierung. Konkret heute: `iilgmbh`(+`pactive-de`) = `central-ok` → konsolidieren; `ttz-lif`/`meiki-lra` = `must-stay-local` → standalone + gespiegelte Config (OOTB-3); `bahn-sqf` = `exit-likely` (Kundenprojekt) → in Enterprise, aber portabel halten (OOTB-5/6).
- **REC-2:** S2 mit **schlanker „Secret Scanning + Push Protection"-Config** für apply-to-all; Config 17 (inkl. CodeQL) nur als Default-for-new / opt-in pro Code-Repo (adressiert B3).
- **REC-3:** S1 erst nach **schriftlicher Kostenbestätigung** des GitHub-Account-Teams; Team-Pläne erst **nach** bestätigter Aufnahme kündigen (adressiert B2/Risk-2).
- **REC-4:** Migration als **Runbook + Wellen** (3–5 Repos/Welle), Actions-Secrets-Checkliste, Package-Ref-grep (`achimdehnert/...@main` in Reusable-Callern) **vor** Transfer (adressiert B5).
- **REC-5:** ADR-235 **Amendment** + neuer **org-weiter ADR** „Enterprise als Security-Kontrollebene" sobald REC-1/-3-Gates grün; ADR-235-Meter um „native enabled?" je Enterprise-Repo erweitern (OOTB-3-Enforcement).
- **REC-6 (Portabilität by construction):** **vor** der ersten Org-Aufnahme (a) `make exit-plan ORG=<org>` als abgeleiteten Report bauen (OOTB-4), (b) hartkodierte `achimdehnert/...@main`-Refs auf *eine* repointbare Stelle ziehen (OOTB-5, adressiert B6), (c) Org-Deskriptoren als GitHub-as-Code (OOTB-6); **eine** Exit-Feuerübung gegen eine Wegwerf-Org (OOTB-7) als Akzeptanz-Beweis.
- **REC-7 (Owner-Sukzession):** Break-Glass-Verfahren + ≥1 dritter Recovery-Owner einrichten (OOTB-9, adressiert B7) — unabhängig von der Konsolidierungs-Entscheidung sofort wertvoll.

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (vorgeschlagen):** ALT-D als Richtung; Umsetzung **gated**, nicht sofort. Kein Org-Move / kein Team-Plan-Kündigen vor den S1/S2-Gates.

**Kill-Gate (messbar):** siehe Frontmatter `kill_criteria` — bis **2026-08-15** (a) Kostenbestätigung, (b) Government-Sign-off **und** (c) Portabilität *bewiesen* statt behauptet: `make exit-plan` erzeugt für ≥1 Org einen vollständigen Runbook **und** ≥1 Exit-Feuerübung lief grün. Fehlt (c) → „Exit-Readiness" ist Theater (AD-2/AD-4) → keine Org-Aufnahme. Sonst Sunset auf ALT-A. Exception-Budget: 1× Verlängerung bis 2026-09-15 mit benanntem Grund.

**30/60/90:**
- **30:** Account-Team-Kostenbestätigung (S1-Gate); schlanke Secrets-Config in der Enterprise anlegen (B3); ADR-235-Amendment-Draft.
- **60:** `iilgmbh`(+`pactive-de`) aufnehmen; Config als Default-for-new + apply-to-all `unenforced`; 1. Migrations-Welle (3 Repos) als Runbook-Pilot.
- **90:** `enforced` schalten; Government-Souveränitäts-Sign-off klären (REC-1); Team-Pläne der aufgenommenen Orgs kündigen; Meter-Erweiterung live.

## 14. Externe Review-Runde 1 — Rückfluss (2026-06-03)

Cross-Provider-Zweitmeinung (Steelman → 3 Rollen → OOTB) auf KONZ-002. Befund: stark, fast rauschfrei. Externe IDs als `X-…`. **Step-5-Tagging** (nur `[valid]` fließt ein, als Änderung mit eigener Begründung — nicht wörtlich):

| Externe ID(s) | Verdikt | Aktion (wo eingearbeitet) |
|---|---|---|
| X-PRO-1…7 | `[valid-confirm]` | bestätigen Richtung; keine Änderung |
| X-AD-1, X-M28-1 | `[valid]` | **OOTB-8** → `exit_class` als abgeleitete Policy `{placement, allowed_features, required_checks, exit_tests}` (gegen zweite Wahrheit) |
| X-AD-3/4/5, X-M28-3/5 | `[valid]` | **OOTB-4** → vollständiges Lock-in-Inventar (Secrets/Variables/Environments/OIDC/Apps/PATs/deploy-keys/Packages/Pages/Rulesets/DNS/Alert-Historie); Secret Name≠Wert≠Rotation |
| X-AD-7, X-AD-13, X-M28-8 | `[valid]` | **OOTB-8** → Feature-Allowlist by `exit_class`; `bahn-sqf`(exit-likely) härteste No-EMU/No-SSO-Tests (D3 unten) |
| X-AD-2, X-AD-12, X-M28-4/9, X-REC-7/8/17/18 | `[valid]` | **D2 unten** — Souveränität = *Governance-Sign-off vor technischem Mirror*; Mirror-Governance + „mandatory" präzisiert |
| X-AD-8, X-M28-2, X-REC-10/16 | `[valid]` | **D1 unten** — Kill-Gate/Feuerübung mit objektiven Akzeptanzkriterien + periodisch+risikobasiert |
| X-M28-6, X-REC-3 | `[valid]` | **D3 unten** — Platzierungs-Gate *unmittelbar vor* irreversibler Aktion (eigene ADR-210-Konvention, intern übersehen) |
| X-AD-9/10/11 | `[valid]` | **D1** — Kosten-Gate granular, `unenforced`-Metriken, User-Account-Done-Kriterien |
| X-AD-6, X-REC-14 | `[valid]` | **OOTB-5** Nachtrag: repointbare Stelle = versioniert/review-pflichtig/fallbackfähig (zentraler Bruchpunkt absichern) |
| X-AD-14 | `[valid]` | **REC-1** Dosierung: `central-ok` leichtere Baseline (Zwei-Personen-Kapazität schützen) |
| X-PRO-7, X-M28-7, X-REC-13 | `[valid]` | **OOTB-9** Nachtrag: Owner-Sukzession *getestet* (Minimalrechte, Probe, Entzugspfad) |
| OOTB-Ansatz 4 (Exit-Escrow), Ansatz 2 (Golden-Org-Factory), Ansatz 5 (Feature-Allowlist) | `[valid]` | Escrow → REC-6-Erweiterung; Factory → OOTB-6-Konkretisierung (klein halten); Allowlist → OOTB-8 |
| OOTB-Ansatz 3 (Managed-Governance-Service kaufen) | `[out-of-scope/deferred]` | Vendor-Lock-in + Souveränität; Add-on-Prüfung später, nicht Kernentscheidung |
| OOTB-Ansatz 1 (Thin-Enterprise-Core) | `[valid-as-fallback]` | bleibt Fallback-Modell für GOV (≈ ALT-B/D), nicht für central-ok |

**Gefolgerte Deltas (fließen in den ADR ein, wenn KONZ→ADR promoted):**
- **D1 — Messbare Akzeptanzkriterien.** „exit-plan vollständig" = alle Inventar-Posten aus OOTB-4 erkannt + offene manuelle Schritte gelistet. „Feuerübung grün" = Wegwerf-Org aufgebaut, Workflows laufen, Security-Baseline wirkt, bekannter Test-Secret blockt, Drift-Audit grün, Rückbau dokumentiert. `unenforced→enforced` erst nach Auswertung: False-Positive-Rate, blockierte Pushes, Repos ohne Config, abweichende Rulesets, Coverage. Kosten-Gate getrennt: Seat-Preis · GHAS-Committer · Wegfall 4 Team-Pläne · Standalone-GOV-Kosten · Exit-Kosten. User-Account-Done: keine prod-kritischen privaten Repos/deploy-keys/Webhooks/Package-Owner/Secrets/Integrationen mehr.
- **D2 — Souveränität ist Governance, nicht Technik.** Ein grünes CI-Mirror-Audit ist **kein** Compliance-Nachweis. Reihenfolge: **fachlicher Behörden-Sign-off zuerst** (Admin-Rechte, Audit-Rechte, Support/Provider-Zugriff, Vertrags-/Tenant-Grenzen, lokale Durchsetzungsmacht) → *dann* zählt technische Gleichheit. **Mirror-Governance:** bei CI-Ungleichheit definiert — wer benachrichtigt, wer ändern darf, Frist, Block-Schwelle, Eskalation wenn die zentrale Stelle **keine** Owner-Rechte hat. „mandatory" für GOV = nur echt, wenn lokale Owner prozessual/vertraglich verpflichtet sind + Abweichung release-blockierend.
- **D3 — Gate am irreversiblen Rand.** Das Platzierungs-/`exit_class`-Gate läuft **unmittelbar vor** Org-Aufnahme, Repo-Transfer, Enterprise-Feature-Aktivierung und `unenforced→enforced` — nicht nur periodisch in CI (eigene ADR-210-Lehre, vom Review zu Recht eingefordert). `bahn-sqf`(exit-likely, in Enterprise) löst bei jeder neuen Enterprise-Abhängigkeit automatisch eine Exit-Prüfung aus.

**Annahme-Kriterium der überarbeiteten Fassung (X-REC-20):** annahmereif, sobald **eine** deklarative Policy `exit_class → placement + allowed_features + required_checks + exit_tests` existiert **und** ≥1 Feuerübung + ≥1 GOV-Mirror-Driftfall erfolgreich dagegen geprüft sind.
