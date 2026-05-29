# Policy: Doc-Profile

**Trigger words:** doc-profile, dokumentationsprofil, lastenheft, pflichtenheft,
projekttyp, doku-pflicht, dsfa-pflicht, ozg-pflicht, bsi-pflicht, wibe-pflicht,
bitv-pflicht, iso27001, doku-katalog

## Rule

Jedes Klickdummy- oder Plattform-Repo, das eine **strukturierte Doku-Suite**
(Lastenheft, Pflichtenheft, Compliance-Tiers, …) führt, **deklariert ein
Projekttyp-Profil** in `docs/doc-profile.yaml`. Daraus folgt ein **fixer
Pflicht-Tier-Katalog** (Plattform-Schema). Volle Begründung:
`platform/docs/adr/ADR-218`.

## Wann gilt das

- **Vor** der Erstellung einer Dokumenten-Suite (Lastenheft, DSFA, BSI, WiBe,
  …) — das Profil entscheidet, welche Tiers überhaupt Pflicht sind.
- **Sobald** ein Repo `docs/doc-profile.yaml` enthält, wird es vom
  Plattform-Check `doc_profile_check.sh` adversarial verifiziert.

## Wann NICHT

- Reine Code-Repos ohne Doku-Suite (z.B. Library, Tooling, MCP-Server) — kein
  Profil nötig.
- Wegwerf-Repos, Forks, Spike-Branches.
- Repos, die ihre Doku komplett extern führen (z.B. Outline-only) — Profil
  optional, nur sinnvoll als Inhaltsverzeichnis.

## Vier Initial-Profile

| Profil | Wann | Pflicht-Cores (Auszug) |
|---|---|---|
| `lra-pilot` | LRA / öffentliche Verwaltung mit Bürger-UI | DSFA + OZG + BSI + BITV |
| `konzern-pilot` | DB / KRITIS-Konzern | BSI-KRITIS + WiBe + DSFA-Mitarbeiter |
| `forschung` | TTZ / Förder-Projekte | Anonymisierung + Projekt-Antrag |
| `saas` | kommerzielles SaaS | ROI + ISO 27001 + DSFA |

Schema: `platform/docs/conventions/doc-profile-schema.yaml`.

## Repo-Instanz (Beispiel meiki-hub)

```yaml
profile: lra-pilot
projektphase: discovery       # discovery | spec | build | rollout | maintain
auftraggeber: lra
stakeholder_extern: [guenzburg, traunstein]
vergabe:
  modus: offen                # intern | evb-it | offen | freihaendig
  wibe_pflicht: true
```

Override eines Pflicht-Tiers nur mit `reason`:

```yaml
overrides:
  "07/wibe":
    status: na
    reason: "Investitionsvolumen unter Schwelle (Genehmigung 2026-05-Q2)"
```

## Profil-Wechsel = ADR

Ein Repo wechselt **nicht ohne ADR** das Profil (Cross-Repo-Auswirkung auf
Pflicht-Tiers, Compliance-Implikation). Phasen-Wechsel innerhalb eines
Profils (`projektphase: discovery → spec → build`) ist **kein** ADR-Trigger.

## Mechanik (SSoT)

Diese Datei ist die versionierte SSoT. `~/.claude/policies/doc-profile.md` ist
ein **Symlink** in den gepinnten platform-Worktree (kein Kopier-Sync) —
`inject_policies.py`/`claude-policy` lesen den Symlink unverändert. Änderung
nur per **platform-PR + Changelog-Bump**; der gepinnte Worktree zieht beim
nächsten Refresh nach (ADR-209-Pattern).

## Changelog

- 2026-05-21: Initial. Aus ADR-218 abgeleitet (Trigger: User-Frage zur
  projekt-typ-abhängigen Doku-Variation).
