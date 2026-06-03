# Runbook — KONZ-002 Enterprise-Konsolidierung: Rollout (ALT-D)

> Operativer Ausführungsplan zu **[KONZ-platform-002](../konzepte/KONZ-platform-002-enterprise-consolidation.md)** (Richtung **ALT-D**).
> Governance-Bezug: **[ADR-235](../adr/ADR-235-org-secret-prevention-posture.md)** (Secret-Prevention-Posture).
> Stand: 2026-06-03 · Owner: Achim Dehnert · **Rollout vom Owner freigegeben** (für reversible/eigene Phasen).

## Grundprinzip

Die irreversiblen Org-Operationen (Org-Aufnahme, Repo-Transfer, Account-Teardown)
sind **Web-UI/SCIM-Schritte** — nicht per API ausführbar (`POST enterprises/.../organizations`
= 404; Transfer/Delete braucht Owner-Rolle; aktueller Token ohne `delete_repo`).
**Rollenteilung:** dieser Runbook + die Artefakte werden gepflegt (Claude Code);
die gegateten UI-Schritte führt der **Owner** je Phase aus. Jede Phase hat ein
**Gate** (Vorbedingung), einen **Executor** und einen **Rollback-Pfad**.

## Gate-Status (Kill-Gate KONZ-002)

| Gate | Kriterium (Original) | Stand 2026-06-03 | Bewertung |
|---|---|---|---|
| **(a)** Kostenneutralität | „schriftlich bestätigt" | **Schriftliche Bestätigung liegt vor** (DR-A) — owner-attestiert, abgelegt in Privatunterlagen (nicht repo-verlinkbar) | ✅ **erfüllt** (attestiert); Restlücke: Beleg nicht im Repo |
| **(b)** GOV-Souveränität | „Sign-off vorliegt" | **Formaler Träger-Sign-off liegt vor** (DR-B) — owner-attestiert, schriftlich, in Privatunterlagen | ✅ **erfüllt** (attestiert); GOV-Hard-Lock **aufgehoben**; Restlücke: Beleg nicht repo-verlinkt |
| **(c)** Portabilität | exit-plan-Runbook + Feuerübung grün | ✅ Inventar+Detektion bewiesen (PR #429); Reversibilität D1-„dokumentiert" (Einbahn-Exit-Befund) | ✅ (D1-grün) |

> **Aktualisierung 2026-06-03 (Stufe 2):** (a)/(b) sind nicht mehr nur mündlich/Aktennotiz,
> sondern als **schriftliche Belege** vom Owner attestiert (in Privatunterlagen). Disziplin-Vermerk:
> *attestiert ≠ repo-verifiziert* — Belege liegen nicht im Repo; bei Audit Kopie nachzureichen
> (billigster Check). Querverweis ADR-235-Changelog 2026-06-03.

---

## Decision Records (Aktennotizen)

### DR-A — Kostenneutralität (Kill-Gate a)
- **Datum:** 2026-06-03 · **Entscheider:** Achim Dehnert (Platform-Lead / Budget-Owner)
- **Basis (verifiziert):** Enterprise-PAT-API 2026-06-03 — `consumed-licenses` = **2 Seats** (achimdehnert + iljalerch); GHAS-Committer secret_protection=2/code_security=2; Abrechnung **pro Person**, nicht pro Org/Repo → Org-Aufnahme kostenneutral, solange keine neue Person dazukommt; 4 Team-Pläne werden redundant.
- **Schriftlicher Beleg (Update 2026-06-03):** Eine **schriftliche Kostenbestätigung** liegt vor, vom Owner **attestiert** und in dessen Privatunterlagen abgelegt (nicht repo-verlinkbar).
- **Entscheidung:** Kill-Kriterium (a) **erfüllt** (schriftlich, owner-attestiert) — nicht mehr nur Aktennotiz.
- **Restlücke (benannt):** Beleg liegt **nicht im Repo** → *attestiert, nicht repo-verifiziert*. **Billigster Check:** (anonymisierte) Kopie nach `~/shared/` legen oder bei Audit nachreichen.

### DR-B — GOV-Datensouveränität (Kill-Gate b)
- **Datum:** 2026-06-03 · **Protokolliert von:** Achim Dehnert
- **Inhalt:** **Formaler Datensouveränitäts-Sign-off der Trägerorganisation(en)** für **GOV-A** (`ttz-lif`) und **GOV-B** (`meiki-lra`). Identität der Träger **anonymisiert** (Projektkonvention GOV-A/GOV-B).
- **Natur (Update 2026-06-03):** **Schriftlicher Träger-Sign-off** liegt vor (nicht mehr nur mündlich), vom Owner **attestiert**, abgelegt in dessen Privatunterlagen.
- **Wirkung:** Kill-Kriterium (b) **erfüllt**. Die **GOV-Hard-Lock ist aufgehoben** — sowohl Ownership-Fragen als auch eine zentral betriebene Audit-/Eingriffsrolle auf GOV-Orgs sind durch den Sign-off gedeckt. (Unter ALT-D bleiben GOV-Orgs ohnehin standalone; es findet kein Ownership-/Datentransfer statt.)
- **Restlücke (benannt):** Beleg liegt **nicht im Repo** → *attestiert, nicht repo-verifiziert*. **Billigster Check:** (anonymisierte) Kopie nach `~/shared/` legen oder bei Audit nachreichen.
- **Entscheidung:** (b) erfüllt via formalem Träger-Sign-off. **Verbleibende GOV-Vorsicht** (kein Hard-Lock mehr, aber Sorgfalt): Souveränitäts-relevante Änderungen weiterhin im Scope des Sign-offs halten.

---

## Phasen

| Phase | Inhalt | Gate (Vorbedingung) | Executor | Akzeptanz | Rollback |
|---|---|---|---|---|---|
| **S1** | **Nur `iilgmbh`-Org** in Enterprise `iilgmbh` aufnehmen (`central-ok`) | DR-A vorhanden | Owner (Web-UI/SCIM) | Org erscheint unter `enterprises/iilgmbh/organizations`; Member-Count unverändert; Seats weiterhin 2 | Org wieder entkoppeln (reversibel, keine Daten betroffen) |
| **S2** | Config 17 als Enterprise-**Default** setzen → erst `unenforced` beobachten → dann `enforced` | S1 grün; FP-Rate + blockierte Pushes + Coverage ausgewertet | Owner/CC (API `repo`-Scope) | `code-security/configurations/.../defaults` gesetzt; Drift-Audit grün; FP-Rate akzeptabel | zurück auf `unenforced`; Default entfernen |
| **S3** | Wertvolle private `achimdehnert`-Repos in Enterprise-Org migrieren (Wellen — Detail-Checkliste: [`KONZ-002-s3-repo-transfer.md`](./KONZ-002-s3-repo-transfer.md)) | S2 `enforced`; **Ziel admin-kontrolliert** (REC-8); Push-Protection am Ziel aktiv (REC-9) | Owner (Transfer-UI) | je Welle: Repo unter Enterprise-Org, Push-Protection aktiv, CI grün | Repo zurücktransferieren (gleiche Welle, Ziel = Quelle) |
| **S4** | User-Account `achimdehnert` austrocknen (Deploy-Keys/Webhooks/Package-Owner/Secrets/Integrationen) | S3-Welle verifiziert | Owner | keine prod-kritischen Artefakte mehr am User-Account | — (irreversibel → deshalb zuletzt, nur nach S3-Verifikation) |
| **GOV** | `ttz-lif`/`meiki-lra` **standalone + gespiegelte Config** (must-stay-local) | DR-B Sign-off ✅ vorhanden | Owner/CC (admin auf GOV-Orgs) | Security-Posture gespiegelt; CI-Gleichheits-Audit grün | Config zurücknehmen (reversibel) |
| **`pactive-de`** | Konsolidierung | ⛔ **Owner-Zustimmung Dritter** (DasRed/ghry5/philipp-eicher/ratpic83) | gesperrt | — | — |

### Harte Sperren
- **GOV-Ownership/-Transfer:** ~~bis schriftlicher Träger-Sign-off vorliegt~~ → **aufgehoben (2026-06-03):** formaler Träger-Sign-off liegt vor (DR-B, owner-attestiert). ALT-D bewegt GOV-Orgs ohnehin nicht. Sorgfalt: Änderungen im Scope des Sign-offs halten.
- **`pactive-de`:** ⛔ **bleibt gesperrt** — Dritt-Org, Achim nur `member` (`admin=false` verifiziert); nur deren Owner können entscheiden. Eigentums-Faktum, kein Sign-off-Thema.

## Reihenfolge / Sequencing
1. **DR-A/DR-B festschreiben** (dieses Dokument) — erledigt.
2. **S1 → S2 → S3 → S4** strikt sequenziell; jede Phase erst nach grünem Vorgänger-Gate.
3. **GOV** parallel möglich (nur Config-Spiegelung), aber jede Eskalation über Config hinaus → schriftlicher Sign-off zuerst.
4. **`pactive-de`** ausgeklammert bis Dritt-Owner-Entscheid.

## Status `pipeline_status`
Bleibt vorerst **`idea`**: der `adr_threshold` von KONZ-002 verlangt einen org-weiten
**ALT-D-ADR** (neue Enterprise-Boundary + Reversal der ADR-235-Aufteilung) — der ist
der nächste Governance-Schritt **vor** S1. Dieser Runbook ist die operative Vorbereitung,
nicht der Boundary-ADR.

## Changelog
- 2026-06-03: Initial — Rollout-Plan ALT-D; DR-A/DR-B (Aktennotizen, Gate a/b via Budget-Owner-Record); Phasen S1–S4 + GOV + pactive-de mit Gates/Executor/Rollback.
