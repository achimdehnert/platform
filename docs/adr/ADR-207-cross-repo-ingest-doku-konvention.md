---
id: ADR-207
title: "Cross-Repo Ingest- & Doku-Konvention (tiered, opt-in)"
status: Proposed
date: 2026-05-16
deciders: Plattform-Governance
---

# ADR-207 — Cross-Repo Ingest- & Doku-Konvention

## Kontext

In meiki-hub entstand 2026-05-16 eine validierte Doku-Strategie (eine
Doku-Wahrheit pro Repo, Format-Hierarchie MD>PDF>docx, ein Ingest-Trichter +
Provenienz-Archiv). Die Frage: auf andere Repos verallgemeinern? Und in
welcher Form, ohne die Multi-Repo-Drift zu reproduzieren, die wir gerade
beseitigt haben?

Risiken einer naiven Verallgemeinerung:

- **Blanket-Rollout** erzeugt leere `inbox/`-Ordner in reinen Code-Repos —
  Zeremonie ohne Wert.
- **N-fach kopierter Konventionstext** driftet garantiert (genau das
  wiederkehrende Anti-Muster: divergierende Zweitstände).
- **Repo-Identität aus Remote-Namen** abgeleitet → in dieser Session wurde
  über einen Rename-Redirect versehentlich ein Live-Repo archiviert.

## Entscheidung

1. **Eine SSoT-Konvention im `platform`-Repo:**
   `docs/governance/cross-repo-ingest-doku.md`. Teilnehmende Repos verlinken
   per dünnem Pointer, kopieren den Text **nicht**.
2. **Tiered/opt-in statt blanket.** Tier A (ingest-pflichtig): `meiki-hub`,
   `risk-hub`, `ttz-hub`. Tier B opt-in. Tier C (reine Code-Repos)
   ausgenommen. Aufnahme weiterer Repos = PR gegen die Konvention.
3. **Pfad-Schema** `~/shared/<repo>/inbox/` + `~/shared/<repo>/_archiv/<datum>/`
   + `~/github/<repo>/docs/` (Ground Truth). Bewusst **nicht**
   `<repo>/<repo>-inbox` (doppelter Name).
4. **Rollout-Disziplin:** erst diese ADR ratifizieren, dann pro Tier-A-Repo
   *ein* Pointer-PR. Kein Massen-Anlegen.
5. **Pflichtregel:** Repo-Identität vor `archive`/`delete`/`rename` immer per
   API auflösen (`gh api repos/<o>/<r> --jq .id`).

## Konsequenzen

**Positiv:** eine wartbare Quelle; kein Drift durch Pointer-Modell; Aufwand
nur dort, wo Rohmaterial real anfällt; die meiki-Drift-Lehren werden
plattformweit kodifiziert.

**Negativ / offen:** Tier-Zuordnung ist eine fortlaufende Pflegeaufgabe;
Public-Sector-Datensouveränität (ttz/meiki) erfordert je Org Prüfung, ob das
Provenienz-Archiv auf geteilten Mounts liegen darf; Drift-Check als
wiederverwendbarer CI-Baustein ist Folge-ADR.

## Status / nächste Schritte

- [ ] Ratifizierung dieser ADR (Plattform-Governance)
- [ ] Tier-A-Repos: je 1 Pointer-PR (`docs/_conventions/ingest.md` + `shared/<repo>/inbox/README.md`)
- [ ] Folge-ADR: Drift-Check als CI-Baustein
