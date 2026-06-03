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
| **(a)** Kostenneutralität | „schriftlich bestätigt" | **Aktennotiz** (DR-A unten) — pro-Person-Abrechnung API-verifiziert + mündliche Account-Team-Bestätigung; Budget-Owner-Entscheid | ✅ *für Rollout*; Restlücke: €-Sätze extern unbestätigt |
| **(b)** GOV-Souveränität | „Sign-off vorliegt" | **Aktennotiz** (DR-B unten) — *protokolliertes mündliches OK*, **kein** formaler Träger-Sign-off | ⚠️ *für bounded ALT-D-Scope* (standalone + Config-Spiegelung); Ownership-/Transfer-Schritte bleiben gesperrt |
| **(c)** Portabilität | exit-plan-Runbook + Feuerübung grün | ✅ bewiesen (PR #429, KONZ-002 §15) | ✅ |

> **Bewusste, dokumentierte Lockerung** (nicht still): (a) und (b) werden von
> „schriftlich/formal" auf **Budget-Owner-Aktennotiz** gestellt; Restrisiko vom
> Owner getragen und unten benannt. Querverweis ADR-235-Changelog 2026-06-03.

---

## Decision Records (Aktennotizen)

### DR-A — Kostenneutralität (Kill-Gate a)
- **Datum:** 2026-06-03 · **Entscheider:** Achim Dehnert (Platform-Lead / Budget-Owner)
- **Basis (verifiziert):** Enterprise-PAT-API 2026-06-03 — `consumed-licenses` = **2 Seats** (achimdehnert + iljalerch); GHAS-Committer secret_protection=2/code_security=2; Abrechnung **pro Person**, nicht pro Org/Repo → Org-Aufnahme kostenneutral, solange keine neue Person dazukommt; 4 Team-Pläne werden redundant.
- **Mündlich:** Account-Team hat seat-basierte (nicht org-/repo-basierte) Abrechnung bestätigt.
- **Entscheidung:** Kostenneutralität der Konsolidierung **akzeptiert** auf dieser Basis. Kill-Kriterium (a) bewusst via Budget-Owner-Aktennotiz erfüllt (statt externer schriftlicher Bestätigung).
- **Restlücke (benannt):** €-Sätze sind **extern nicht schriftlich** bestätigt. **Billigster Check / empfohlen:** eine Mail ans Account-Team **vor** Kündigung der 4 Team-Pläne (das ist die irreversible Kosten-Aktion).

### DR-B — GOV-Datensouveränität (Kill-Gate b)
- **Datum:** 2026-06-03 · **Protokolliert von:** Achim Dehnert
- **Inhalt:** Mündliches Souveränitäts-OK für die **standalone + gespiegelte-Config**-Anordnung von **GOV-A** (`ttz-lif`) und **GOV-B** (`meiki-lra`), von Achim übermittelt. Identität der Träger-Vertreter **anonymisiert** (Projektkonvention GOV-A/GOV-B).
- **Natur (ausdrücklich):** Dies ist die **zeitnahe Protokollierung einer mündlichen Aussage**, **kein** formaler schriftlicher Träger-Sign-off.
- **Begrenzte Exposition:** Unter ALT-D bleiben GOV-Orgs **standalone** — **kein** Ownership-/Datentransfer; gespiegelt wird ausschließlich die Security-Config (Posture-Verbesserung auf bestehenden Repos).
- **Restrisiko (benannt):** **Kein** formaler schriftlicher Träger-Sign-off auf Akte. **Billigster Check / empfohlen:** schriftlichen Sign-off einholen **vor** jeder Aktion, die GOV-Org-Governance über reine Config-Spiegelung hinaus ändert.
- **Entscheidung:** (b) für den **bounded ALT-D-Scope** (standalone + Config-Spiegelung) via dieses dokumentierten mündlichen Records als erfüllt behandelt; Restrisiko vom Platform-Lead getragen. **Jeder Ownership-/Transfer-Schritt an GOV-Orgs bleibt bis zum schriftlichen Sign-off gesperrt.**

---

## Phasen

| Phase | Inhalt | Gate (Vorbedingung) | Executor | Akzeptanz | Rollback |
|---|---|---|---|---|---|
| **S1** | **Nur `iilgmbh`-Org** in Enterprise `iilgmbh` aufnehmen (`central-ok`) | DR-A vorhanden | Owner (Web-UI/SCIM) | Org erscheint unter `enterprises/iilgmbh/organizations`; Member-Count unverändert; Seats weiterhin 2 | Org wieder entkoppeln (reversibel, keine Daten betroffen) |
| **S2** | Config 17 als Enterprise-**Default** setzen → erst `unenforced` beobachten → dann `enforced` | S1 grün; FP-Rate + blockierte Pushes + Coverage ausgewertet | Owner/CC (API `repo`-Scope) | `code-security/configurations/.../defaults` gesetzt; Drift-Audit grün; FP-Rate akzeptabel | zurück auf `unenforced`; Default entfernen |
| **S3** | Wertvolle private `achimdehnert`-Repos in Enterprise-Org migrieren (Wellen + Runbook) | S2 `enforced`; **Ziel admin-kontrolliert** (REC-8); Push-Protection am Ziel aktiv (REC-9) | Owner (Transfer-UI) | je Welle: Repo unter Enterprise-Org, Push-Protection aktiv, CI grün | Repo zurücktransferieren (gleiche Welle, Ziel = Quelle) |
| **S4** | User-Account `achimdehnert` austrocknen (Deploy-Keys/Webhooks/Package-Owner/Secrets/Integrationen) | S3-Welle verifiziert | Owner | keine prod-kritischen Artefakte mehr am User-Account | — (irreversibel → deshalb zuletzt, nur nach S3-Verifikation) |
| **GOV** | `ttz-lif`/`meiki-lra` **standalone + gespiegelte Config** (must-stay-local) | DR-B (bounded); **kein** Ownership-Move | Owner/CC (admin auf GOV-Orgs) | Security-Posture gespiegelt; CI-Gleichheits-Audit grün | Config zurücknehmen (reversibel) |
| **`pactive-de`** | Konsolidierung | ⛔ **Owner-Zustimmung Dritter** (DasRed/ghry5/philipp-eicher/ratpic83) | gesperrt | — | — |

### Harte Sperren (durch Owner-Freigabe **nicht** aufhebbar)
- **GOV-Ownership/-Transfer:** bis schriftlicher Träger-Sign-off vorliegt (DR-B Restrisiko). ALT-D verlangt das ohnehin nicht (GOV bleibt standalone).
- **`pactive-de`:** Dritt-Org, Achim nur `member` (`admin=false` verifiziert) — nur deren Owner können entscheiden. Das ist kein Sign-off-, sondern ein Eigentums-Faktum.

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
