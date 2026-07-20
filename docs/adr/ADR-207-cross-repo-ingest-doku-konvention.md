---
id: ADR-207
title: "Cross-Repo Ingest- & Doku-Konvention (tiered, opt-in)"
status: accepted
decision_date: 2026-05-16
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

## Reversibilität & Risiken (Amendment 2026-05-17, aus adr-review)

- **Reversibilität:** Rücknahme ist billig und lokal — Pointer-Datei
  (`docs/_conventions/ingest.md`) + `shared/<repo>/inbox/` je Repo löschen,
  diese ADR auf `superseded` setzen. Kein Code, kein Service, keine
  Daten-Migration; Provenienz-Archiv bleibt unberührt. Kosten ≈ N kleine
  Revert-PRs (N = Tier-A-Repos).
- **Blast-Radius bei Tier-Fehlzuordnung:** Ein Code-Repo fälschlich in Tier A
  → leerer, ungenutzter `inbox/`-Ordner (kosmetisch, kein Funktionsbruch).
  Ein ingest-relevantes Repo fälschlich in Tier C → Rohmaterial landet
  weiter ad hoc (Status quo ante, kein Regress). Fehlzuordnung ist also
  **nicht schadhaft, nur suboptimal** und per 1-Zeilen-PR an dieser Datei
  korrigierbar.
- **Daten-Souveränität (kritisch, ttz-lif / meiki-lra):** Provenienz mit
  Klarnamen/Sozialdaten darf **nicht** ungeprüft auf einen org-fremd
  geteilten Mount. Verbindlich: für `ttz-lif`/`meiki-lra` liegt
  `_archiv/` auf einem **org-lokalen, nicht quergeteilten** Pfad; die
  Tier-A-Aufnahme dieser Repos steht unter dem Vorbehalt einer
  DSFA-/Mount-Prüfung je Org (kein Default-Rollout dorthin).
- **Lizenz/Compliance:** Drittinhalte im `_archiv/` werden nicht
  weiterverteilt (außerhalb Git, kein Publish) — kein Lizenz-Transfer.

## Status / nächste Schritte

**Status: `Accepted` (2026-05-17)** — ratifiziert durch Plattform-Governance
(PR #175). Konvention `docs/governance/cross-repo-ingest-doku.md` ist damit
verbindlich; Rollout bewusst konservativ (erst SUGGEST):

- [x] Ratifizierung dieser ADR (Plattform-Governance)
- [ ] Tier-A-Repos: je 1 Pointer-PR (`docs/_conventions/ingest.md` + `shared/<repo>/inbox/README.md`)
- [ ] ttz-lif/meiki-lra **nur nach** DSFA-/Mount-Prüfung (siehe Daten-Souveränität) — kein Default-Rollout
- [ ] Folge-ADR: Drift-Check als CI-Baustein
