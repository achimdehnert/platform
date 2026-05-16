# Cross-Repo Ingest- & Doku-Konvention

**Status:** PROPOSED (Ratifizierung via ADR-207)
**Datum:** 2026-05-16
**Home:** `platform` (Governance-SSoT) — Repos verlinken hierauf, kopieren nicht.
**Pilot/Herkunft:** meiki-hub `docs/_conventions/doku-strategie.md` (validiert 2026-05-16)

---

## Zweck

Verallgemeinerung der in meiki-hub bewährten Doku-Strategie auf weitere Repos —
**tiered/opt-in, nicht blanket**. Eine uniforme Ingest-Struktur für reine
Code-Repos ist leere Zeremonie; der Wert entsteht nur dort, wo **externes
Rohmaterial** eintrifft (Stakeholder-`.docx`, Prozess-Exporte, Zips,
Workshop-Transkripte).

## Scope-Tiers

| Tier | Repos (Beispiele) | Verbindlichkeit |
|---|---|---|
| **A — ingest-pflichtig** | doc-/public-sector-lastig: `meiki-hub`, `risk-hub`, `ttz-hub` | Konvention gilt |
| **B — opt-in** | Repos mit gelegentlichem Fremdmaterial | bei Bedarf, gleicher Pfad |
| **C — ausgenommen** | reine Code-/Lib-Repos ohne Fremd-Ingest | kein Inbox-Ordner |

Tier-Zuordnung wird in ADR-207 ratifiziert; Aufnahme weiterer Repos = PR gegen
diese Datei, nicht stillschweigend.

## Pfad-Schema (verbindlich für Tier A/B)

```
~/shared/<repo>/inbox/                      # einziger Eingang für Rohmaterial
~/shared/<repo>/_archiv/<YYYY-MM-DD>/        # Provenienz, außerhalb Git
~/github/<repo>/docs/                        # Ground Truth (Markdown, versioniert)
```

Bewusst **nicht** `~/shared/<repo>/<repo>-inbox` (doppelter Repo-Name).
Ein Eingang pro Repo — keine zweiten Schatten-Ordner.

## Regeln (identisch über alle Tier-A/B-Repos)

1. **Eine Doku-Wahrheit pro Repo:** `<repo>/docs/`. Repo-Identität vor
   archive/delete **immer per API auflösen** (`gh api repos/<o>/<r> --jq .id`)
   — Rename-Redirects sehen wie ein zweites Repo aus (Drift-Lehre meiki).
2. **Format-Hierarchie:** Markdown = Ground Truth · PDF = generierter Output
   bzw. regulatorische Ground-Truth (siehe pdf-first-Konvention) · `.docx` =
   **nie** canonical (nur Ingest/Austausch).
3. **Ein Ingest-Trichter + Provenienz-Archiv.** Jede Datei in `inbox/`
   verlässt sie binnen einer Session über genau einen Ausgang:
   destillieren → `docs/` · archivieren → `_archiv/` · löschen (nur
   nachweisliche Byte-Duplikate). Nie liegen lassen.
4. **Pointer statt Kopie.** Teilnehmende Repos legen *eine* dünne
   `docs/_conventions/ingest.md` an, die **hierher verlinkt** — kein
   divergierender Zweittext (Anti-Drift).
5. **Automatisierung statt Disziplin.** Periodischer Drift-Check
   (CI/Cron bzw. `session-docu`) beantwortet je Repo: „liegt Quelle X schon
   im Repo, abweichend, oder verwaist?".

## Rollout-Disziplin (bewusst konservativ)

Analog Repo-Health-Regel-Disziplin: **erst SUGGEST, dann verbindlich**.
Kein Massen-Anlegen von `inbox/`-Ordnern. Reihenfolge:
1. ADR-207 ratifiziert Schema + Tier-A-Liste.
2. Pro Tier-A-Repo *ein* PR: dünne `docs/_conventions/ingest.md`-Pointer +
   `~/shared/<repo>/inbox/README.md`.
3. Tier-B nach Bedarf, Tier-C nie.

## Offene Punkte

- ttz-hub/meiki-hub: Public-Sector-Datensouveränität — Provenienz-Archiv mit
  Klarnamen bleibt **außerhalb Git** und ggf. außerhalb geteilter Mounts;
  je Org prüfen.
- Drift-Check als wiederverwendbarer CI-Baustein: separater Folge-ADR.
