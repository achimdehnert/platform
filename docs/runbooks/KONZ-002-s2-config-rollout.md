# Runbook — KONZ-002 S2: Enterprise-Security-Config scharfstellen

> Detaillierung von **S2** aus [`KONZ-002-consolidation-rollout.md`](./KONZ-002-consolidation-rollout.md).
> Governance: **[ADR-236](../adr/ADR-236-altd-enterprise-boundary.md)** §2.2 (amended).
> Stand: 2026-06-03. Mutiert **enterprise-weit** → Schritte gegated, unenforced zuerst (reversibel).

## Ziel (ADR-236 §2.2)

- **Schlanke Config** (NUR `secret_scanning` + `push_protection`) als **apply-to-all** über alle Member-Orgs — vermeidet CodeQL-Blast-Radius auf Nicht-Code-Repos (B3).
- **Config 17** (volle Suite) NUR als **Default-for-new** + Opt-in.
- Reihenfolge: **erst `unenforced` beobachten → dann `enforced`**.

## Ausgangslage (Session-verifiziert C4/C5/C6 — vor Run frisch nachprüfen)

| Fakt | Stand | Beleg |
|---|---|---|
| Config **17** „GitHub recommended" (volle Suite enabled) | auf **3 `bahn-sqf`-Repos**, **kein** Default-for-new | C4/C5/C6 |
| Config **251700** „initial" (custom, identische Suite) | auf **0 Repos** | C-Session |
| **Schlanke** (nur Secret-Scan + Push-Protection) Config | **existiert nicht** → muss erstellt werden | — |
| Member-Orgs (apply-to-all-Scope) | `bahn-sqf`, `iilgmbh`, `meiki-lra`, `ttz-lif` (S1 + GOV-Amendment) | live verifiziert 2026-06-03 |

> **GOV-Hinweis:** seit dem ADR-236-Amendment sind `ttz-lif`/`meiki-lra` Member-Orgs → ihre Repos fallen jetzt in den apply-to-all-Scope. Das ist eine **Posture-Verbesserung** (Secret-Scan/Push-Protection), **kein** Ownership-/Datentransfer und vom Träger-Sign-off (volle Mitgliedschaft) gedeckt. Trotzdem: GOV-Repos im `unenforced`-Fenster gesondert auf False-Positives beobachten.

## Endpoints (admin:enterprise — vor Run gegen Live-Schema verifizieren)

- List: `GET enterprises/iilgmbh/code-security/configurations`
- Create: `POST enterprises/iilgmbh/code-security/configurations`
- Default-for-new: `PUT enterprises/iilgmbh/code-security/configurations/{id}/defaults`
- Attach: `POST enterprises/iilgmbh/code-security/configurations/{id}/attach`

## Phasen

| Step | Aktion | Gate | Executor | Reversibel? |
|---|---|---|---|---|
| **S2.0** | **Schlanke Config erstellen** — `secret_scanning=enabled`, `secret_scanning_push_protection=enabled`, alles andere `not_set`/`disabled` (KEIN code_scanning/CodeQL). Name z.B. `slim-prevention`. | Payload gegen Live-Schema verifiziert | CC/Owner (PAT admin:enterprise) | ja (Config löschen) |
| **S2.1** | **Config 17 als Default-for-new** setzen (`defaults`-Endpoint, default_for_new_repos). | S2.0 grün | CC/Owner | ja (Default entfernen) |
| **S2.2** | **Schlanke Config apply-to-all, `enforcement: unenforced`** (attach scope=all). | S2.0/2.1 grün | CC/Owner | **ja** (detach / Config entfernen) |
| **S2.3** | **Beobachten** (Fenster ≥ X Tage): False-Positive-Rate, blockierte Pushes, Coverage, GOV-Repos separat. | Daten gesammelt | CC (read) | n/a |
| **S2.4** | **`enforcement: enforced`** flippen — nur nach Auswertung (FP akzeptabel, Coverage vollständig). | S2.3 ausgewertet, FP-Rate ok | **Owner** (bewusste Freigabe) | ja (zurück auf `unenforced`) |

## Ausführungs-Status (2026-06-03)

- **S2.0 ✅** `slim-prevention` (id **251767**) angelegt: `secret_scanning`+`secret_scanning_push_protection`=enabled, `code_scanning_default_setup`=disabled, `enforcement=unenforced`.
- **S2.1 ✅** Config 17 = **Default-for-new** (`default_for_new_repos=all`) — verifiziert über `…/configurations/defaults`.
- **S2.2 ✅** `slim-prevention` apply-to-all (`attach scope=all`, async) — 9 Repos `attached` beim Erst-Check (Coverage in S2.3 verifizieren).
- **💰 Kostenneutralität bestätigt:** Secret-Protection-Committer **2 → 2** (vor/nach Attach) — bestätigt die Committer-Mechanik (Treiber = Personen, nicht Repo-Zahl).
- **S2.3 ⏳ offen — Auswertung geplant ~2026-06-05** (lokal): Beobachtungsfenster (≈2 Tage). Auswertung muss **lokal** laufen (Live-Daten + Enterprise-PAT) — **kein Remote-Job möglich** (Remote-Agent hat keinen PAT-/Enterprise-API-Zugriff). Trigger: lokale CC-Session „S2.3 auswerten" + PAT-Freigabe → Committer-Count (Baseline 2) / Coverage (slim id 251767 attached vs. alle Repos der 4 Orgs) / FP (GOV separat) → S2.4-Entscheidungsvorlage.
- **S2.4 ⛔ offen:** `enforced` = bewusste Owner-Entscheidung nach S2.3-Auswertung.

> **S2.3 Schlüssel-Metrik:** Secret-Protection-**Committer-Count** weiter beobachten (Baseline 2). Steigt er beim Aktivieren des Scannings über die Zeit, ist das ein **Kostensignal** → vor `enforced` bewerten; bei Bedarf detach (reversibel).

## Gates / Auswertungskriterien (D1)
- `unenforced→enforced` **erst** nach: FP-Rate gemessen, Anzahl blockierter Pushes, Repos ohne Config (Coverage-Lücke), abweichende Rulesets, GOV-FP separat.
- Kein „silent enforce" — S2.4 ist eine bewusste Owner-Entscheidung mit Datenlage.

## Rollback
- Jede Phase reversibel: Attachment lösen (`unenforced` kennt keine Blocks), Default entfernen, Config löschen. Kein Repo-Inhalt betroffen.

## Akzeptanz (S2 done)
- [ ] Schlanke Config existiert + apply-to-all `enforced` über alle 4 Member-Orgs.
- [ ] Config 17 = Default-for-new.
- [ ] Drift-Audit grün (Ist = Soll), FP-Rate dokumentiert.
- [ ] GOV-Repos ohne Souveränitäts-relevante Nebenwirkung (nur Posture).

## Nicht in Scope / Leitplanken
- Kein `enforced` ohne ausgewertetes `unenforced`-Fenster.
- Payloads/Endpoints vor Ausführung gegen Live-API-Schema verifizieren (kein Schema-Raten).
- Enterprise-PAT-Nutzung nur mit Freigabe.

## Changelog
- 2026-06-03: Initial — S2-Detail (schlanke Config apply-to-all unenforced→enforced; Config 17 default-for-new; GOV jetzt im Scope; Gates/Rollback).
