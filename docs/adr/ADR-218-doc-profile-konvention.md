---
id: ADR-218
title: "Doc-Profile als Plattform-Konvention (Doku-Pflicht-Katalog je Projekttyp)"
status: proposed
date: 2026-05-21
deciders: [Achim Dehnert]
consulted: [self-advocatus-diabolus]
informed: [meiki-lra, bahn-sqf, ttz-lif, iilgmbh, achimdehnert]
domains: [governance, documentation, compliance, klickdummy]
supersedes: []
amends: []
depends_on: [ADR-211, ADR-213]
related: [ADR-207, ADR-209]
tags: [doc-profile, documentation, governance, lastenheft, pflichtenheft, compliance, dsfa, ozg, bsi, wibe, bitv]
---

# ADR-218 — Doc-Profile als Plattform-Konvention

## Status

**proposed** — mit pre-integriertem advocatus-diabolus-Review (Pattern aus
ADR-216/-217). Tritt mit erster Repo-Instanziierung (geplant: meiki-hub) in
Kraft.

## Kontext

Die 6 Klickdummy-Repos (meiki-hub, bahn-sqf/sqf-hub, bahn-sqf/pg-hub,
ttz-hub, risk-hub, plus künftige) und Plattform-Apps brauchen Dokumentation,
deren *Pflicht-Katalog je Projekttyp variiert*:

- **LRA-Pilot** (meiki-hub) — DSGVO + BayDSG + OZG + BITV + BSI-Grundschutz
  Pflicht; EVB-IT-Vergabe oder intern offen.
- **Konzern-Pilot** (bahn-sqf) — KRITIS-Schutzbedarf, interne
  Compliance-Reviews, Investitionsrechnung Pflicht; keine OZG-Bindung.
- **Forschung** (ttz-hub) — Förderauflagen, Daten-Anonymisierung statt
  Personenbezug-DSFA; keine Vergabe.
- **Kommerzielles SaaS** (risk-hub) — ROI-Case, ISO 27001 statt BSI, ggf.
  EU-Kunden → BITV-relevant.

Ohne deklariertes Profil tritt ein typisches Anti-Pattern auf:

- **Compliance-Lücke nach Audit**: „BSI-Schutzbedarf fehlt" wird erst bei
  Audit-Termin gemerkt.
- **Doku-Overengineering**: alle Repos schreiben ein WiBe, auch wenn keine
  Investitionsrechnung nötig.
- **Inkonsistenz zwischen Klickdummy und Doku**: Use-Cases laufen aus der
  Spec, Spec aus der Doku.
- **Stakeholder-Frust**: „Ich kriege Pflichtenheft-Skelett, aber das passt
  nicht zu meinem Projekt."

### Trigger für diese ADR

User-Frage 2026-05-21:

> „ich kann mir vorstellen, dass die dokumentation je nach projekt typ,
> kunde, … variiert. sollen wir das vorab festlegen oder als task parallel
> mit festlegen?"

Antwort als Entscheidung: **beides** — Profil vorab, Inhalte parallel.

## Entscheidungs-Vorschlag

**Repo-deklariertes `doc-profile.yaml` mit plattform-globalem
Pflicht-Katalog-Schema und externem Check.**

### Drei Bestandteile

1. **`platform/docs/conventions/doc-profile-schema.yaml`** — Plattform-Schema:
   - Definition von 4 Initial-Profilen (`lra-pilot`, `konzern-pilot`,
     `forschung`, `saas`)
   - Pro Profil: Pflicht-Tiers (A0, A, A-api, B, C, D, 08-Betrieb) ×
     Pflicht-Status (`required` / `optional` / `na`)
   - Pflicht-Frontmatter-Felder je Tier (z.B. `dsfa.kategorie`,
     `bsi.schutzbedarf`)
   - SSoT: Plattform; gepinnter Worktree gleicher Mechanik wie
     `klickdummy.md`-Policy

2. **Repo-lokales `<repo>/docs/doc-profile.yaml`** — Instanz:
   ```yaml
   profile: lra-pilot
   projektphase: discovery        # discovery | spec | build | rollout | maintain
   auftraggeber: lra
   stakeholder_extern: [guenzburg, traunstein]
   vergabe:
     modus: offen                  # intern | evb-it | offen | freihaendig
     wibe_pflicht: true
   ```
   Überschreibungen einzelner Tier-Pflichten möglich (`overrides.<tier>`)
   mit Begründung — `doc-profile-check.sh` warnt bei Override ohne `reason`.

3. **`platform/scripts/checks/doc_profile_check.sh`** — externer
   Adversarial-Check (analog `klickdummy_registry.sh`):
   - Liest `registry/repos.yaml` + `<repo>/docs/doc-profile.yaml`
   - Verifiziert je deklariertem Profil die Pflicht-Tiers existieren
     (Datei + Mindestinhalt)
   - Exit 0 = konform, 1 = Verstoß, 2 = Setup-Fehler
   - Nightly-Job + PR-Hook im jeweiligen Repo

### Vier Initial-Profile (Schema-Auszug)

| Tier / Pflicht | `lra-pilot` | `konzern-pilot` | `forschung` | `saas` |
|---|---|---|---|---|
| A0 Spec-Basis | ✅ | ✅ | ✅ | ✅ |
| A Use-Cases | ✅ | ✅ | ✅ | ✅ |
| A-api OpenAPI | ✅ | ✅ | ⚠ optional | ✅ |
| B Lastenheft | ✅ | ✅ | Projekt-Antrag | Product-Spec |
| B Pflichtenheft | wenn evb-it | wenn extern | – | – |
| C C4-Diagramme | ✅ | ✅ | ✅ | ✅ |
| C SLOs (RPO/RTO) | ✅ | ✅ KRITIS | ⚠ | ✅ |
| C BITV 2.0 | ✅ | wenn Endkunden-UI | ⚠ | wenn EU-Kunden |
| D DSFA | ✅ je FV | ✅ Mitarbeiter | ⚠ Anonymisierung | ✅ |
| D OZG | ✅ | – | – | – |
| D BSI-Schutzbedarf | ✅ | ✅ KRITIS | ⚠ | ISO 27001 |
| D WiBe | wenn >Schwelle | ✅ Invest. | – | ROI-Case |
| 08 Betrieb | ✅ vor GoLive | ✅ | ⚠ | ✅ |

### Profile sind erweiterbar

Neue Profile (z.B. `polit-stiftung`, `kommune-klein`) per Plattform-PR auf
das Schema. Repo-spezifische *Abweichung* ohne neues Profil:
`overrides.<tier>` mit `reason:`.

## Advocatus-Diabolus-Review (pre-integriert)

| Einwand | Antwort |
|---|---|
| „Variantenexplosion: 4 Profile sind zu wenig / zu viel" | 4 ist die heute beobachtete Stakeholder-Streuung. Schema ist erweiterbar; Plattform-PR-Threshold = `klickdummy.md`-Pattern (Changelog-bump). |
| „Was, wenn ein Repo zwischen Profilen pendelt?" | `projektphase` ist orthogonal zum Profil — Phasenwechsel löst kein Profil-Wechsel aus. Profil-Wechsel nur per ADR (cross-cutting). |
| „Doppelt geschriebene Doku — Spec im Klickdummy + Use-Cases in Tier A" | Tier A0/A sind **auto-generiert** aus Klickdummy-Spec (`gen-doc-from-spec.py`). Pflicht-Check prüft nur Existenz + Mindestinhalt, nicht manuelle Pflege. |
| „Compliance-Tiers können nicht aus Spec abgeleitet werden" | Korrekt — D ist *handgeschrieben*. Schema markiert D-Tiers als `auto_generatable: false`. |
| „Wer pflegt das Schema?" | Plattform-Ebene, gleiches Modell wie `klickdummy.md`-Policy: Symlink in gepinnten Worktree, PR-getrieben, Changelog-bump. |
| „Drift Profil-Schema vs. Repo-Instanz" | Schema-Version in `doc-profile.yaml` (`schema_version: 1`); Check prüft Kompatibilität. |
| „Wann gilt es?" | Sobald `<repo>/docs/doc-profile.yaml` existiert. Repos ohne Profil sind aus dem Check ausgenommen (kein Vacuous Pass — sondern keine Pflicht). |
| „Was passiert in monorepo-artigen Repos (mehrere Projekte)?" | `doc-profile.yaml` ist mehrfach erlaubt unter `<repo>/projects/<projektname>/doc-profile.yaml`. Schema unterstützt das (`monorepo: true`). |
| „Konflikt mit klickdummy.md-Policy?" | Nein — `klickdummy.md` regelt Klickdummy-Spec-Cores, `doc-profile.yaml` regelt die *darüber-/daneben* liegenden Doku-Schichten. Beide referenzieren A0/A. |

## Konsequenzen

- ✅ **Compliance-Lücke verhindert**: Profil-Pflicht erzwingt vorab die
  rechtlich nötigen Tiers (DSFA, BSI, OZG, BITV, WiBe je nach Profil).
- ✅ **Kein Overengineering**: optional/n.a.-markierte Tiers bleiben weg.
- ✅ **Wiederverwendbar** über alle 6+ Klickdummy- und Plattform-Repos.
- ✅ **Drift-sicher**: externer Adversarial-Check `doc_profile_check.sh`
  meldet fehlende Pflicht-Artefakte (ADR-211-Pattern).
- ⚠ **Plattform-Wartungsaufwand**: Schema lebt zentral, Änderungen brauchen
  Plattform-PR. Mitigation: Profile sind orthogonal zu Repos — Schema-Edits
  selten.
- ⚠ **Bootstrap-Phase**: Repos ohne Profil bleiben aus dem Check raus
  (kein Big-Bang-Enforcement). Migration repo-by-repo.
- ⚠ **Profil-Wahl ist Entscheidung**: ein Repo, das fälschlich `forschung`
  deklariert, bekommt keine OZG-Pflicht aufgedrückt. Mitigation: Profil-Wahl
  ist im ADR-Threshold-Bereich (vgl. Adv.D.: „Profil-Wechsel nur per ADR").

## Implementierungsplan

1. **Plattform-PR (diese ADR)**:
   - `docs/adr/ADR-218-doc-profile-konvention.md`
   - `docs/conventions/doc-profile-schema.yaml`
   - `scripts/checks/doc_profile_check.sh`
   - `policies/doc-profile.md` (für `~/.claude/policies/`-Sync via
     ADR-209)
2. **meiki-hub-PR (Pilot-Instanziierung)**:
   - `docs/doc-profile.yaml` (profile: `lra-pilot`, vergabe.modus: `offen`)
   - `docs/05-spezifikation/A0/`-Skeleton (Tier A0 vorbereitet,
     Mindestdateien angelegt — Inhalt iterativ)
3. **Rollout nach Pilot-Stabilität**: bahn-sqf/sqf-hub + bahn-sqf/pg-hub
   (konzern-pilot), ttz-hub (forschung), risk-hub (saas) — pro Repo
   eigener PR mit Profil-Instanz + Skeleton.

## Refs

- ADR-211 Klickdummy-Rahmen (Spec-Basis Tier A0/A)
- ADR-213 Cross-Repo-ADR-Ref-Format (für Profil-Referenzen)
- ADR-207 Cross-Repo-Doku-Konvention (orthogonal)
- ADR-209 Policy-Auto-Sync (Mechanismus für `policies/doc-profile.md`)
- `policies/klickdummy.md` (Schwester-Policy)
