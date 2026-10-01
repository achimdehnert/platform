# Gate-Klassen: Substanz oder Redaktion

> Auftrag: [platform#3645](https://github.com/achimdehnert/platform/issues/3645), Kriterium 1.
> Stand 2026-09-30. Die Einstufung ist ein Vorschlag und per PR änderbar.

## Regel

Ein Auftrag ist erledigt, wenn er im Zielkontext fehlerfrei durchläuft
(`policies/zielzustand.md`, Abschnitt „Fertig heißt, es läuft").

- **Substanz** — ein roter Check heißt: der Auftrag ist nicht erledigt. Beheben im selben PR.
- **Redaktion** — ein roter Check hält den Merge **nicht** auf und erzeugt **keinen**
  eigenen Folge-PR und kein eigenes Issue. Entweder im laufenden PR miterledigen,
  wenn es eine Minute kostet, oder als Kommentar an die
  [Nacharbeitsliste #3646](https://github.com/achimdehnert/platform/issues/3646) —
  sie wird einmal täglich in einem PR abgearbeitet.
- **Melder** — misst den Zustand der Flotte, nicht den PR. Rot ist ein Fund, kein Merge-Hindernis.

Formal sperrt nur, was im Ruleset `main-required-checks` steht (Spalte „Pflicht",
gelesen 2026-09-30). Ein Verweis auf #3646 erfüllt die Pflicht-Prüfung
„Aufgeschobene Arbeit braucht einen Anker", weil sie jede Issue-Referenz als Anker zählt
(`tools/deferral_anchor_check.py`, Muster `ANKER`).

## Inventar (PR-Trigger, platform)

| Workflow | Job | Pflicht | Klasse |
|---|---|---|---|
| `guardian.yml` | guardian | ✅ | Substanz |
| `ci-security.yml` | gitleaks secret scan | ✅ | Substanz |
| `tools-tests.yml` | pytest tools/tests/ + CI-tote Testorte | ✅ | Substanz |
| `aufschub-anker-gate.yml` | Aufgeschobene Arbeit braucht einen Anker | ✅ | Redaktion (Anker = #3646 genügt) |
| `tools-tests.yml` | Gate-Verankerung (Drill · Positivkontrolle · Messpunkt) | | Substanz |
| `deploy-sh-gate.yml` | Syntax + Migrations-Vertrag | | Substanz |
| `validate-workflows.yml` | Validate Syntax | | Substanz |
| `silent-failure-lint.yml` | Stille Fehlschläge in Workflows | | Substanz |
| `secrets-inventory-lint.yml` | Inventar gegen Schema + Zahlen | | Substanz |
| `secrets-inventory-lint.yml` | Wertfrei? rotation-log.jsonl | | Substanz |
| `ruleset-waechter.yml` | Vier-Augen-Pflicht noch scharf | | Substanz |
| `infra-hosts-audit.yml` | hosts.yaml Schema + Frische + Runner-Label-Pins | | Substanz |
| `registry-consistency.yml` | Registry-Konsistenz prüfen | | Substanz |
| `registry-lint.yml` | tenancy_mode Pflicht-Feld | | Substanz |
| `renovate-config.yml` | validate | | Substanz |
| `mcp-quality.yml` | Static Analysis · MCP Quality Checks · Tests · Orchestrator MCP Tests · Quality Gate | | Substanz |
| `mcp-quality.yml` | Documentation Check | | Redaktion |
| `cc-skill-dist-doctor.yml` | generate → doctor == Drift 0 (HEAD) | | Substanz |
| `skill-mcp-signatures.yml` | lint | | Substanz |
| `workflow-tool-ref-gate.yml` | estimate_job-Aufruf-Form in ship.md/backup.md | | Substanz |
| `adr-guard.yml` | Check ADR number uniqueness | | Substanz |
| `konz-guard.yml` | Check KONZ number uniqueness | | Substanz |
| `adr-validate.yml` | adr | | Substanz |
| `adr-validate.yml` | Platform-specific ADR checks | | Redaktion |
| `adr-validate.yml` | ADR index freshness | | Redaktion |
| `preflight-spiegel.yml` | spiegel | | Substanz |
| `platform-make-checks.yml` | betrieb-check | | Substanz |
| `handover-append-only.yml` | Auslagern verschluckt keine offenen Vorgaenge | | Substanz |
| `handover-append-only.yml` | AGENT_HANDOVER_LOG.md nur ergaenzt | | Redaktion |
| `handover-append-only.yml` | AGENT_HANDOVER.md unter dem Byte-Deckel | | Redaktion |
| `handoff-banner-gate.yml` | Live-Status-Banner/Rezenz in geänderten Handoff-Dateien | | Redaktion |
| `handover-freshness-advisory.yml` | freshness | | Redaktion |
| `adr-review.yml` | AI Review · Ensure Labels | | Redaktion |
| `adr-dual-review.yml` | Dual-Tool Review | | Redaktion |
| `context-reviewer.yml` | context-review | | Redaktion |
| `schliess-bezug.yml` | Nennt dieser PR ein Issue, ohne es zu schliessen? | | Redaktion |
| `serielle-prs-advisory.yml` | Serielle-PRs-Abgleich (advisory) | | Redaktion |
| `test-claim-check.yml` | test-claim-check | | Redaktion |
| `regel-ritual.yml` | ritual | | Redaktion |
| `handover-reconcile.yml` | reconcile | | Melder |
| `registry-live-reconcile.yml` | Drift-Kennzahl messen · Sink Dry-Run | | Melder |
| `pypi-coldstart-watch.yml` | coldstart | | Melder |
| `pypi-fleet-health.yml` | health | | Melder |
| `dependabot-automerge.yml` | automerge | | Werkzeug |
| `scaffold-tests.yml` | Test-Scaffold PR für neue Repos | | Werkzeug |

Summe: 51 Jobs, 4 Pflicht; 0 Pflicht-Prüfungen, die Redaktion **erzwingen**, sobald
der Anker auf #3646 zeigen darf.
