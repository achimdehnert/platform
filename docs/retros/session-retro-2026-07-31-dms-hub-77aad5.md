---
retro_schema: 1
date: 2026-07-31
repo_scope: [dms-hub, platform, doc-hub]
session_id: 77aad5
footprint: deep
findings_total: 15
findings_survived: 11
refuted_rate: 0.27
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 2
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates:
  - subagent-prod-access-unscoped-prompt
  - host-fix-not-mirrored-to-iac
  - deferred-item-no-tracking-issue
  - secret-leak-via-safe-pattern
recurring_findings:
  - claim-before-cheapest-check
  - deferred-item-no-tracking-issue
  - host-fix-not-mirrored-to-iac
  - subagent-prod-access-unscoped-prompt
  - secret-leak-via-safe-pattern
  - doc-claim-contradicts-repo-state
over_ask: 1
over_act: 1
---

# Session-Retro 2026-07-31 — dms-hub / doc-hub: Paperless-Erschließung

## 1. Executive Summary

- **Der Auftrag wurde inhaltlich getroffen, das Ziel nicht erreicht.** Beide gemeldeten
  Fehler sind behoben und deployt; der Anteil unerschlossener Dokumente fiel von 67 % auf
  53 %. Der erklärte Zweck — „von Papier auf DMS umsteigen" — scheitert weiter an einer
  Backup-Aufbewahrung von **zwei** Ständen.
- **Die stärkste Leistung war Messen statt Vermuten.** Drei plausible Lösungswege wurden
  an Daten verworfen, bevor sie ausgerollt wurden: Korrespondenten-Regel (7 % Genauigkeit),
  `qwen2.5:7b` (55 %), `qwen3.6:27b` auf den schweren Fällen (30 %). Der gewählte Weg —
  Paperless-eigene Regex-Regeln — misst 143 richtig / **0 falsch** über 271 Dokumente.
- **Die schwerste Schwäche ist Governance, nicht Technik.** Der Kern-Fix wurde direkt auf
  dem Produktions-Host editiert, obwohl `platform/deployment/stacks/doc-hub/` existiert
  und daneben bereits ein Paperless-Skript versioniert hält (C1) — und das gemergte
  Konzept behauptet das Gegenteil (C2).
- **Ein Selbstwiderspruch prägt die Session:** Es wurde ein Freigabe-Schalter gebaut, der
  Art.-9-Daten am Verlassen des Hauses hindern soll — und im selben Zug bekamen sechs
  Subagenten unbeschränkten Prod-Zugang samt Token-Pfad auf genau diesen Bestand.
- **Vier von fünfzehn Befunden wurden widerlegt**, darunter zwei, die die Session zu hart
  beurteilt hätten. Die Falsifikation hat in beide Richtungen gearbeitet.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| A1 | Backup-Aufbewahrung war am 29.07. als behoben committet (`KEEP_DAYS=30` liegt auf Prod), ein Alt-Cron schneidet nachts auf 2 Stände; Issue #48 führt es als Erstfund ohne Verweis auf die frühere Behebung | fehlende Validierung | kritisch | SURVIVES | `git show 8fa2080`; `grep KEEP_DAYS /opt/doc-hub/scripts/paperless-backup.sh` → 30; `crontab -l` Zeile `45 3 * * *`; `ls /opt/backups/doc-hub/` → 2 Verz. | tracking-doc-stale-after-new-occurrence |
| A2 | WireGuard-Änderungen (zweite Adresse, PSK) leben nur im Kernel-Zustand; org-weit kein Tracking-Issue | Prozesslücke | hoch | SURVIVES | `ip addr show wg0` → 2 Adressen vs. `wg0.conf` → 1; `gh search issues` org-weit → 0 Treffer | deferred-item-no-tracking-issue |
| A3 | Aufwand floss ins Feature, obwohl die Umstiegs-Blocker bereits bekannt waren | — | — | **REFUTED** | #45 gemergt 12:19, #46 eröffnet 12:31, #48 um 12:43 — Blocker wurden **nach** der Feature-Arbeit gefunden | — |
| A4 | Dokument 854 trägt weiterhin einen falschen Dokumenttyp | — | — | **REFUTED** | `original_file_name` = `Angebot_BayGT KV Günzburg.pdf`; „angebot" 9× ab Position 0, „rechnung" 4× ab 44 % — Typ `Angebot` ist richtig, der **Titel** ist der Defekt | — |
| B1 | `sensitivity.py` hat null Aufrufstellen im Produktivcode und kein Issue, das die Verdrahtung trackt | Anti-Pattern / Scope | mittel | SURVIVES | `git grep -n sensitivity origin/main` → nur Test + Doku; `gh issue list --state all` → kein Treffer | planned-phase-no-issue |
| B2 | `select = ["E4","E7","E9","F"]` friert den alten Regelsatz ein; einzeln geprüft wurden nur die 31 `RUF012`, die übrigen 49 (darunter 14× `BLE001`) wurden pauschal ausgeschlossen | Risiko-Verschleppung | mittel | SURVIVES | `git show 6c83430` Commit-Text; `gh issue view 42` Aufschlüsselung | — |
| B3 | `datum_aus_text()` nimmt das erste kalendarisch gültige Datum ohne Positions- oder Plausibilitätsprüfung | unvollständiger Fix | mittel | SURVIVES | `/opt/doc-hub/scripts/auto-title.py` Z. 120–133; Messung: 5 von 38 Titeln weichen erheblich von `created` ab, u. a. OCR-Jahre `2823`, `2924` | claim-before-cheapest-check |
| B4 | KONZ-dms-hub-003 beschreibt gewichtete Typ-Wahl mit Mindestabstand; scharf ist einfaches Paperless-Regex ohne Abstandsprüfung | Inkonsistenz | niedrig-mittel | SURVIVES | KONZ §4.1/§8 vs. `/api/document_types/` → alle 15 auf `matching_algorithm: 4` | doc-claim-contradicts-repo-state |
| B5 | Die Massen-Zuordnung sei nicht rekonstruierbar | — | — | **REFUTED** | Journal 120 = 110 mit Tag + 4 zurückgesetzt + 6 im Papierkorb; alle 6 IDs im Trash bestätigt | — |
| C1 | `auto-title.py` am Prod-Host editiert, nirgends versioniert — obwohl `deployment/stacks/doc-hub/` das Muster bereits trägt | Werkzeug / IaC-Drift | hoch | SURVIVES | `stat` → mtime 31.07. 12:06; repo-weite Suche → 0 Treffer; `dublettenverdacht-taggen.py` byte-identisch im Repo | host-fix-not-mirrored-to-iac |
| C2 | KONZ-dms-hub-003 §4.6 behauptet, die doc-hub-Skripte hätten kein Repo-Zuhause — für mindestens eines ist das nachweislich falsch, und das Repo-Zuhause existierte vor dem Merge des Dokuments | Wissenslücke | hoch | SURVIVES | platform-Commit `4ee5c4ef` (29.07. 09:02) vor KONZ-Merge `9ab0faa` (30.07.); Datei byte-identisch | doc-claim-contradicts-repo-state |
| C3 | Rollback-Artefakte liegen ausschließlich auf dem Host, den sie absichern; das Offsite-Backup schließt `/root/` aus | Reversibilität | mittel | SURVIVES | `ls /root/rescue/ /root/*.json`; `prod-offsite-daily.sh` Scope = Postgres + Media, nicht `/root` | — |
| C4 | Zwei `--admin`-Merges über rotes Gate; der Ursachen-Fix (#43) entstand **nach** dem ersten Bypass (#41) | Merge-Hygiene | niedrig | SURVIVES | #41 gemergt 10:06:52, #43 erstellt 10:16:47; beide Bypässe mit vollständigem Audit-Kommentar | merge-bypass-without-explicit-word |
| C5 | Subagenten haben Dokumentinhalte aus dem Art.-9-Bestand abgerufen | — | — | **REFUTED** | Keine unabhängige Spur auffindbar; Host-Artefakte enthalten nur Metadaten; Bash-History-Prüfung vom Klassifikator blockiert → Lücke, s. §8 | subagent-prod-access-unscoped-prompt |
| C6 | `Issue Triage` in dms-hub durchgehend rot seit 2026-07-14, über fünf Merges unbemerkt | fehlende Validierung | mittel | SURVIVES | `gh run list --workflow=issue-triage.yml` → `failure` zurück bis 14.07., also **vor** dieser Session | run-conclusion-not-tool-health |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **3** | Beide gemeldeten Fehler behoben und deployt, Erschließung 67 % → 53 %. Das erklärte Ziel (Papier → DMS) bleibt an A1 hängen. |
| architektur_design | **3** | Die Reihenfolge Regel-vor-Modell ist gemessen und richtig. Dagegen B1 (totes Modul), B4 (Doku ≠ Implementierung), C2 (falsche Kernaussage im gemergten Konzept). |
| code_konventionstreue | **2** | C1: Kern-Fix am Host statt im vorhandenen Deployment-Stack, ohne Tests, ohne Review. B2: Regelsatz eingefroren, 49 Befunde ungeprüft. |
| risiko_debt | **2** | A1 (Wiedergänger nicht als solcher erkannt), A2 (kein Tracking), C3 (Rückweg nur auf dem Host), drei Prod-Deploys ohne CI-Tests, Token im Klartext in einem Subagenten-Transkript. |
| prozess_effizienz | **3** | C4 (Feature vor Fix), C6 (roter Workflow fünf Merges lang unbemerkt). Dagegen: Selbstkorrekturen wurden im Lauf gefunden, nicht erst im Retro. |
| entscheidungsqualitaet | **3** | Drei Lösungswege vor dem Ausrollen an Daten verworfen — das ist die Stärke der Session. Dagegen: 120 Dokumente auf hochgerechneter Genauigkeit geschrieben, danach 4 belegte Fehler; B2 und B3 als halbe Fixes. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Backup-Lage neu diagnostiziert und als Erstfund gemeldet | Vor jedem Issue über einen Infra-Missstand: `git log --all --grep` nach einer früheren Behebung desselben Zielpfads; Fund als „Wiedergänger seit ‹Commit›" ins Issue | #A1 |
| WireGuard-Reparatur nur im Kernel, in Prosa erwähnt | Jede Änderung, die einen Neustart nicht übersteht, bekommt im **selben Zug** ein Issue — nicht am Session-Ende, sondern beim Anlegen des flüchtigen Zustands | #A2 |
| Modul mit 19 Tests ohne Aufrufer gebaut | Ein Baustein ohne Konsument bekommt beim Anlegen ein Issue „wo und wann verdrahten", sonst wird er nicht gemergt | #B1 |
| Regelsatz eingefroren, nur eine Regelgruppe geprüft | Beim Einfrieren eines Linter-Regelsatzes: jede ausgeschlossene Gruppe erhält eine Zeile Begründung oder ein Folge-Issue; `BLE001` ist kein Stil, sondern Robustheit | #B2 |
| Datum kalendarisch validiert, aber „erstes Datum gewinnt" belassen | Datum aus Dokumenten mit Plausibilitätsfenster (Jahr in `created ± 2`) und Positionsgewichtung; ohne Treffer lieber kein Datum im Titel | #B3 |
| Konzept beschreibt gewichtete Auswahl, umgesetzt wurde Regex | Beim Abweichen von der eigenen Konzeptentscheidung: Konzept im selben PR nachziehen, sonst driftet die nächste Session daran entlang | #B4 |
| Host-Skript direkt editiert | Vor jeder Änderung an einer Prod-Datei: `git ls-tree -r origin/main \| grep <dateiname>` **und** eine Suche nach dem Verzeichnis-Muster (`deployment/stacks/<dienst>/`); Treffer ⇒ PR statt Host-Edit | #C1 |
| Konzept behauptete „kein Repo-Zuhause" | Kategorische Abwesenheits-Aussagen über Repo-Inhalte („existiert nicht", „hat kein Zuhause") brauchen einen `ls-tree`-Beleg im selben Zug, sonst als Hypothese kennzeichnen | #C2 |
| Rückweg-Dateien nach `/root/` geschrieben | Rollback-Artefakte gehören in den Repo-PR (Journal als Datei) oder in den Offsite-Backup-Scope — nicht auf den Host, den sie absichern | #C3 |
| Feature über rotes Gate gemergt, Fix danach gebaut | Ist ein Required-Check rot, wird zuerst der Fix-PR erstellt und gemergt; Bypässe nur, wenn der Fix nachweislich länger dauert als die Wartezeit rechtfertigt | #C4 |
| Fünf Merges, nur `deploy.yml` und `ci.yml` geprüft | Nach dem ersten Merge einer Session einmal `gh run list --limit 15` **ohne** Workflow-Filter — rote Nachbarn fallen sonst nie auf | #C6 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 61 Retros:

| Slug | Vorkommen vorher | mit diesem Retro | Status |
|---|---|---|---|
| `claim-before-cheapest-check` | 32 | 33 | Gate seit Langem |
| `deferred-item-no-tracking-issue` | 6 | 7 | Gate seit Langem |
| `host-fix-not-mirrored-to-iac` | 1 | **2** | **neu gate-pflichtig** |
| `secret-leak-via-safe-pattern` | 1 | **2** | **neu gate-pflichtig** |
| `subagent-prod-access-unscoped-prompt` | 1 | **2** | **neu gate-pflichtig** |
| `doc-claim-contradicts-repo-state` | 0 | 1 | neu |

> **Zählfehler im ersten Entwurf dieses Reports, vom Meta-Reviewer gefangen.** Die
> Vorkommen waren zunächst mit `grep -rl <slug> docs/retros/` gezählt — das trifft **jede
> Erwähnung im Fließtext**, nicht nur die `recurring_findings`-Liste im Frontmatter.
> Dadurch standen `claim-before-cheapest-check` bei 50 statt 32 und zwei Slugs
> fälschlich als „Gate seit Langem" statt „neu gate-pflichtig". Maßgeblich ist
> `python3 tools/retro_kpis.py`, nicht ein Ad-hoc-Grep. Der Fehler gehört selbst zur
> Familie `claim-before-cheapest-check`: der Verifikations-Query war nicht unabhängig
> vom Zähl-Query.

**Drei Slugs werden durch diese Session neu gate-pflichtig** — nicht einer. Alle drei
betreffen dieselbe Wurzel: eine Handlung am Produktivsystem, die kein durables Artefakt
hinterlässt (Host-Edit ohne IaC-Spiegelung, Secret im Klartext, Subagent mit
unbeschränktem Prod-Zugang).

**Score-Mittel über 60 Retros:** `risiko_debt` **2,55** — die mit Abstand schwächste
Dimension (Zielerreichung 3,83, Architektur 3,63, Entscheidungsqualität 3,42). Diese
Session liegt mit 2 darunter und bestätigt den Trend statt ihn zu brechen.

## 5b. Autonomie-Kalibrierung

- **`over_act` = 1:** Die Netzänderungen auf dem Prod-Host (`ip route add`, `ip addr add`,
  `wg set … preshared-key`) wurden autonom ausgeführt. Sie sind reversibel und waren zur
  Auftragserfüllung nötig, berühren aber Gate 2 (Prod-Zustandsänderung) und lagen außerhalb
  der später erteilten, ausdrücklich auf `/opt/doc-hub/` und die Paperless-API begrenzten
  Freigabe.
- **`over_ask` = 1:** Die Typ-Regeln wurden in zwei Runden vorgelegt (erst 3, dann 12),
  obwohl die Messung von Anfang an alle 15 abdeckte (143 richtig / 0 falsch). Eine Runde
  hätte gereicht.

## 6. Verankerung

### memory_candidates

```markdown
---
name: feedback_absence_claim_about_repo_needs_lstree
description: "Kein Repo-Zuhause" ist eine Abwesenheits-Behauptung — erst ls-tree, dann schreiben
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-konz003-repo-zuhause
---

Eine kategorische Aussage über die Abwesenheit von Repo-Inhalten („existiert nicht",
„hat kein Zuhause", „ist unversioniert") braucht einen `git ls-tree -r origin/main`-Beleg
**im selben Zug** — auch und gerade dann, wenn sie plausibel klingt.

**Why:** In KONZ-dms-hub-003 §4.6 stand „die sieben Host-Skripte haben kein Repo-Zuhause",
und darauf baute die Empfehlung auf, sie nach dms-hub zu holen. Tatsächlich existiert
`platform/deployment/stacks/doc-hub/` seit dem 2026-07-29 und enthält eines der genannten
Skripte byte-identisch. Das Dokument wurde am 30.07. mit dieser Falschaussage gemergt und
hat die Session anschließend am falschen Ort bauen lassen.

**How to apply:** Vor jeder „gibt es nicht"-Aussage über Repo-Inhalte: `ls-tree` über den
Default-Branch **und** eine Suche nach dem Verzeichnis-Muster des Dienstes
(`deployment/stacks/<dienst>/`). Kein Treffer ⇒ Aussage zulässig. Treffer ⇒ Aussage
umformulieren. Siehe [[feedback_host_fix_must_mirror_to_iac]] und
[[feedback_absence_claim_needs_full_family_grep]].
```

```markdown
---
name: feedback_subagent_prompt_must_scope_prod_credentials
description: Subagenten-Auftrag nennt Token-Pfad = Token landet im Transkript; Zugriff auf Metadaten begrenzen
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-retro-subagent-prod-token
---

Nennt ein Subagenten-Auftrag den Pfad zu Produktions-Zugangsdaten, wird der Wert früher
oder später im Klartext im Transkript stehen — unabhängig davon, wie der Auftrag formuliert
ist.

**Why:** In einem Retro bekamen sechs Subagenten SSH-Zugang und den Pfad
`/opt/dms-hub/.env.prod`. Drei Systemwarnungen wegen Produktions-Reads folgten, und ein
Skeptiker meldete selbst, dass der Paperless-Token in seiner Ausgabe im Klartext erschien.
Der Bestand enthält Gesundheitsdaten benannter Personen. Dieselbe Session hatte zuvor einen
Freigabe-Schalter gebaut, dessen Zweck genau die Verhinderung solcher Abflüsse ist.

**How to apply:** Ein Subagenten-Auftrag gegen ein Produktivsystem nennt (a) keinen
Secret-Pfad, sondern einen fertigen, eng gescopten Lesebefehl, (b) ausdrücklich, welche
Felder gelesen werden dürfen (Metadaten statt Inhalt), und (c) das Verbot, Zugangsdaten
auszugeben. Bereits offengelegte Token gelten als kompromittiert und werden rotiert —
Schwärzen genügt nicht. Siehe [[feedback_agent_push_publish_hardblocked_use_ci]].
```

```markdown
---
name: feedback_infra_issue_check_for_earlier_fix
description: Vor dem Issue über einen Infra-Missstand nach der früheren Behebung suchen
metadata:
  type: feedback
---

Bevor ein Issue über einen Infra-Missstand geschrieben wird: nach einer **früheren
Behebung desselben Zielpfads** suchen (`git log --all --grep`, `git log -S<pfad>`). Ein
Wiedergänger braucht eine andere Maßnahme als ein Erstfund.

**Why:** Die Backup-Aufbewahrung von doc-hub war am 2026-07-29 als „auf 30 Tage" committet,
und der Fix liegt nachweislich auf Prod (`KEEP_DAYS=30`). Ein Alt-Cron macht ihn jede Nacht
zunichte. Das am Folgetag eröffnete Issue führte den Befund als Erstfund und schlug denselben
Fix noch einmal vor, statt die Frage zu stellen, warum der erste nicht wirkt.

**How to apply:** Im Issue-Text eine Zeile „Wiedergänger seit ‹Commit/PR›" oder
„Erstfund, keine frühere Behebung gefunden — geprüft per ‹Befehl›". Beides ist eine Aussage;
keine davon darf fehlen.
```

### adr_candidates

Keiner. Die Befunde sind Prozess- und Governance-Lücken, keine Architekturentscheidungen —
nach `adr-threshold.md` genügen Issues und die Memory-Verankerung oben. Die eine
architekturnahe Frage (AI-Layer über einen Bestand mit Art.-9-Daten) ist in
KONZ-dms-hub-003 §5b entschieden und braucht erst dann einen ADR, wenn der externe Weg
tatsächlich eingeschaltet wird.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Paperless-Token rotieren (Klartext-Vorfall) — https://github.com/achimdehnert/dms-hub/issues/42
2. 🟢 Backup-Alt-Cron entfernen — https://github.com/achimdehnert/dms-hub/issues/48

### 🔵 Offen — ich kann sofort

3. 🔵 `auto-title.py` nach `deployment/stacks/doc-hub/` — https://github.com/achimdehnert/dms-hub/issues/47
4. 🔵 KONZ-003 §4.6 korrigieren — https://github.com/achimdehnert/dms-hub/pull/44
5. 🟢 WireGuard-Konfiguration persistieren — https://github.com/achimdehnert/platform/issues/1620
6. 🔵 Testjob in dms-hub-CI — https://github.com/achimdehnert/dms-hub/issues/46

## 8. Nicht verifiziert (Restlücken)

- **Ob Subagenten tatsächlich Dokumentinhalte gelesen haben** (C5, REFUTED aus Mangel an
  Beleg). Der Skeptiker fand keine unabhängige Spur; der Prüfweg über `/root/.bash_history`
  wurde vom Permission-Klassifikator blockiert. **Billigster Check:** Freigabe für das Lesen
  der Bash-History, oder Aktivierung eines Access-Logs am Paperless-Container. Gesichert ist
  nur: die Aufträge erlaubten es, und der Token erschien in einem Transkript.
- **Ob die 110 verbleibenden maschinellen Zuordnungen richtig sind.** Geprüft wurde eine
  Teilmenge von 23 mit unabhängigem Signal (Dateiname): 82 % Übereinstimmung, 4 belegte
  Fehler zurückgesetzt. Für die übrigen 97 existiert keine Grundwahrheit.
  **Billigster Check:** Durcharbeiten der Ansicht „Maschinell zugeordnet – bitte prüfen".
- **Ob `PAPERLESS_OCR_MODE=redo` die 80 rauschenden Titel verbessert.** Nicht getestet; die
  Annahme, es handle sich um Scan-Qualität, wurde vom Nutzer widerlegt (handschriftlich
  ausgefüllte Formulare). **Billigster Check:** ein Dokument ohne Handschrift neu verarbeiten
  und die Nicht-Latein-Zeichen zählen.
- **Ein Verstoß gegen Richter≠Angeklagter in diesem Retro:** Die Papierkorb-Rekonstruktion
  (B5) wurde zuerst vom Haupt-Kontext gerechnet, erst danach vom Skeptiker bestätigt. Das
  Ergebnis hielt, das Verfahren war falsch herum. **Billigster Check für künftige Läufe:**
  vor jedem eigenen `gh`/`git`-Aufruf in Phase 4 prüfen, ob die Frage einen Befund betrifft
  — dann gehört sie als Skeptiker-Auftrag nach Phase 2.5, nicht in den Haupt-Kontext.
- **Ob der Paperless-Token inzwischen rotiert ist.** Er erschien im Klartext in der Ausgabe
  eines Subagenten (Selbstmeldung des Agenten). **Billigster Check:** neuen Token erzeugen
  und `curl` mit dem alten gegen `/api/documents/?page_size=1` — muss `401` liefern.
