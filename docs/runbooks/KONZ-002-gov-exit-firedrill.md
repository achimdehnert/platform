# Runbook — KONZ-002 GOV-Exit-Feuerübung (`central-gov` Handover-Readiness)

> Beweist den `exit_tests: handover-readiness` der Klasse **`central-gov`**
> ([`governance/exit-classes.yaml`](../governance/exit-classes.yaml)).
> Governance: **[ADR-236](../adr/ADR-236-altd-enterprise-boundary.md)** §6 (Rest-Risiko).
> Stand: 2026-06-03. **Drill auf Wegwerf-Org — NIE an `ttz-lif`/`meiki-lra` selbst.**

## Warum (das schärfste offene Rest-Risiko)

Seit dem ADR-236-Amendment sind `ttz-lif`/`meiki-lra` **in der Enterprise**
(`central-gov`). Die Souveränität ist damit **nicht mehr strukturell** (Standalone-
Trennung) gesichert, sondern **vertraglich** — ein **Single Point** am Träger-
Sign-off. Wird der Sign-off widerrufen (Vertragsende, Behörden-Übergabe, Audit-
Auflage), **muss** die GOV-Org an die Trägerorganisation **rückgabefähig** sein.
„Rückgabefähig" ist eine *getestete*, nicht behauptete Eigenschaft — analog zur
ersten Exit-Feuerübung (die Gate (c) war). Solange dieser Drill nicht grün lief,
ist `central-gov` ein **ungetesteter Exit** (genau der Theater-Fehler, den KONZ-002
vermeiden will).

**Abgrenzung zur 1. Feuerübung (2026-06-03):** die testete *Repo*-Transfer
`bahn-sqf → pactive-de`. **Diese hier** testet den **Org-Level-Exit aus der
Enterprise** + Übergabe an eine *Träger-kontrollierte* Zieldomäne.

## Hypothesen, die der Drill falsifizieren/bestätigen muss

| # | Hypothese | warum kritisch |
|---|---|---|
| H1 | Eine Org lässt sich **aus der Enterprise herauslösen** (Owner-Aktion / oder nur via GitHub-Support?) | wenn nur Support → Exit ist nicht unilateral, Träger-SLA nötig |
| H2 | Beim Herauslösen geht die **Enterprise-Security-Config verloren** (REC-9: Push-Protection extern nicht per Toggle reaktivierbar) | Träger braucht eigenes GHAS/Secret-Protection sonst Posture-Lücke beim Handover |
| H3 | **Ownership** geht vollständig an die Träger-Zieldomäne (kein Rest-Zugriff der alten Enterprise/Admins) | sonst ist „Souveränität zurückgegeben" nur behauptet |
| H4 | **Repo-Secrets** gehen verloren, Variables überleben (wie 1. Drill) | Re-Provisioning-Last beim Träger einplanen |

## Drill-Ablauf (Wegwerf-Org)

> Spiegelt die 1.-Drill-Mechanik: anlegen → provisionieren → exit-plan → Handover proben → verifizieren → Rückbau. **Lehre aus 1. Drill (REC-8):** Ziel der Übergabe muss **admin-kontrolliert** sein, sonst Einbahn-Exit. Wegwerf-Org NICHT in eine Fremd-Org transferieren, in der man nur `member` ist.

1. **Setup:** Wegwerf-Org `gov-exit-drill` anlegen, in die Enterprise `iilgmbh` aufnehmen (= `central-gov`-Zustand nachstellen). 1 Demo-Repo mit Secret + Variable + reusable-Workflow-Ref.
2. **Baseline:** `central-gov`-Posture aktiv? `gh api repos/<org>/<repo> --jq '.security_and_analysis'` (Push-Protection an).
3. **Inventar:** `GH_TOKEN=<enterprise-pat> python3 tools/exit-plan.py gov-exit-drill --out /tmp/gov-exit.md` → §0 zeigt `central-gov`-Policy; §1/§2 listen das Transfer-fragile State.
4. **Handover proben:** Org aus der Enterprise herauslösen **und** Ownership an eine **separate, admin-kontrollierte Träger-Ziel-Domäne** übergeben (Owner-/Web-UI; H1 verifizieren — geht es self-service oder nur via Support?).
5. **Verifizieren (Akzeptanz, alle grün = handover-readiness ✅):**
   - H3: alte Enterprise/Admins haben **keinen** Zugriff mehr; Ziel-Domäne hat volle Owner-Kontrolle.
   - H2: Security-Posture am Ziel — Push-Protection-Status nach Exit dokumentiert (aktiv? oder Lücke ohne Träger-GHAS?).
   - H4: Secrets weg / Variables da; Re-Provisioning-Liste erstellt.
   - Repo-History + Redirects intakt; reusable-Refs identifiziert.
6. **Rückbau:** Wegwerf-Org + Ziel-Artefakte löschen (Owner-Rolle nötig — sonst selbst ein Exit-Befund, REC-8).

## Akzeptanzkriterien (Gate „handover-readiness grün")

- [ ] H1 beantwortet: Org-Exit-Mechanik dokumentiert (self-service vs. Support-Pfad + Dauer/SLA).
- [ ] H3 bewiesen: vollständiger Kontrollübergang, **kein Rest-Zugriff** der Quelle.
- [ ] H2 dokumentiert: Posture-Zustand am Ziel (inkl. ggf. Träger-GHAS-Bedarf).
- [ ] H4 dokumentiert: Re-Provisioning-Liste (Secrets) + Variables-Überleben bestätigt.
- [ ] Sauberer Rückbau gelungen (Owner-Rolle am Ziel vorhanden).
- [ ] Lessons zurückgeflossen → `central-gov`-Definition + ADR-236 §6 + ggf. REC-Update.

## Output

- Protokoll nach `~/shared/gov-exit-drill-protocol-<datum>.md`.
- Bei grün: `governance/exit-classes.yaml` — `central-gov`-Deviation „GOV-Exit-Feuerübung steht aus" → „verifiziert <datum>"; ADR-236 §6 Rest-Risiko entsprechend entschärfen.
- Bei rot: Befund ist ein **Souveränitäts-Lock-in** → eskalieren (Träger-SLA / vertragliche Exit-Klausel nachschärfen), ADR-236 §6 verschärfen.

## Nicht in Scope / Sicherheits-Leitplanken
- **Keine** Aktion an `ttz-lif`/`meiki-lra` selbst — ausschließlich Wegwerf-Org.
- Enterprise-PAT-Nutzung nur mit ausdrücklicher Freigabe (read-only exit-plan + Org-Ops).
- Org-Erstellung/-Exit ist Web-UI/SCIM (API begrenzt) → Owner-Schritte.

## Changelog
- 2026-06-03: Initial — GOV-Exit-Feuerübungsplan (central-gov handover-readiness); H1–H4, Drill-Ablauf, Akzeptanzkriterien.
