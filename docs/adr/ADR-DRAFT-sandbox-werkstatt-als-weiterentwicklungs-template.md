---
id: ADR-000
status: proposed
decision_date: 2026-10-04
deciders: Achim Dehnert
consulted: –
informed: –
implementation_status: partial
---

# ADR-DRAFT: Adopt an autonomous sandbox workshop as the benchmarked development template for the production environment

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-10-04                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-070 (Progressive Autonomy Pattern), ADR-081 (Agent Guardrails & Code Safety), ADR-154 (Autonomous Coding Optimization) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten              |
|----------------|------------|---------------------------------------------|
| `platform`     | Primär     | `tools/sandbox/` (#3686), künftig `tools/sandbox/benchmark/`, `tools/sandbox/replay/` |
| `iilsandbox/*` | Primär     | Spiegel der Pilot-Repos, ausschließlich Sandbox-Schreibziel |
| `dev-hub`      | Sekundär   | Pilot-Repo                                  |
| `decks-hub`    | Sekundär   | Pilot-Repo                                  |
| `chat-hub`     | Sekundär   | Pilot-Repo (Org `iilgmbh`)                  |
| `mcp-hub`      | Sekundär   | Pilot-Repo (vom Owner bestätigt 2026-10-04) |

---

## Decision Drivers

- **Freigabe-Last**: Auf 317 über `pr_merge_sa.py` gemergte PRs kommen 124 PRs mit ausdrücklichem Owner-Wort (39,1 %); 295 Merge-Versuche brachen mangels Mandat ab (`~/.claude/pr-merge-sa.jsonl`, ohne Trockenläufe).
- **Analysen und Experimente hängen an Merges**: Auch reine Untersuchungen laufen heute über PRs in Produktiv-Repos und warten damit auf den Owner (platform#3685).
- **Autonomie ohne Wirkung ist jetzt technisch möglich**: `tools/sandbox/` (#3686) prüft vor jedem Lauf mechanisch, dass kein Schreibweg aus der Sandbox hinausführt, und hält ein Budget.
- **Weiterentwicklung braucht Messung**: Ohne Benchmarks optimiert ein autonomer Agent auf „viel geändert“ statt auf „besser“; ein Übernahme-Entscheid braucht Belege, keine Behauptungen.
- **Schutzregeln dürfen sich nicht selbst lockern**: Die Lotsen-Charta (Punkt 3) verbietet dem Agenten, Charta, Permissions und Regeln selbst zu ändern; der Auto-Mode-Classifier hat am 2026-10-04 das Auswerten eines Sandbox-Laufs, der Lockerungen der eigenen Freigaberegeln erarbeitete, als Self-Modification gesperrt.

---

## 1. Context and Problem Statement

Die Entwicklungsumgebung (Repos, Skills, Policies, Hooks, Merge-Werkzeug) soll schneller besser werden, ohne dass jede Untersuchung und jeder Versuch eine Owner-Freigabe braucht. Gleichzeitig hat jede Freigabe-Regel einen Realfall hinter sich (`~/.claude/policies/regel-historie.md`); pauschales Lockern würde diese Lehren verlieren.

### 1.1 Ist-Zustand

| Messgröße (Quelle: gesamtes Journal, Stand 2026-10-04, `tools/sandbox/benchmark.py`) | Wert |
|---|---|
| Verschiedene PRs, über `pr_merge_sa.py` gemergt | 317 |
| Verschiedene PRs mit Owner-Wort-Ereignis | 124 (39,1 %) |
| Merge-Abbrüche mangels Mandat (Versuche; M0 123 · M1 145 · M2 19 · M3 8) | 295 |
| Häufigste Abbruchgründe | fehlendes M1 bei W1, Ruleset-Approval, Governance-Pfade unter `.github/workflows/` |
| Hook-Auslösungen gesamt / blockierend (`gate-hits.jsonl`) | 2338 / 1359 |
| häufigster blockierender Hook | `claim-before-cheapest-check` (1117) |

Die Sandbox selbst existiert (#3686): Container mit Selbstprüfung (keine fremden Zugangsdaten, kein `~/.secrets`, kein Docker-Socket, Remotes und Token nur in der Sandbox-Org) und Budget-Wächter (Tokens, Teilagenten, Laufzeit, USD). Probelauf, Budget-Abbruch und Gegenprobe mit zu breitem Token sind belegt (platform#3685).

### 1.2 Warum jetzt

Der Owner hat die Org `iilsandbox` angelegt und als Ziel gesetzt: eine maximal autonome Entwicklungs-Sandbox, die als Weiterentwicklungs-Template für die Produktiv-Umgebung dient und deren erfolgreiche Ergebnisse schrittweise nach `achimdehnert`/`iilgmbh` übernommen werden.

---

## 2. Considered Options

### Option A: Sandbox-Werkstatt mit festen Benchmarks und Owner-Ratifikation für Schutzregeln ✅

Die Sandbox ist ein Zwilling der Produktiv-Umgebung: Repos, Skills, Policies und Hooks liegen dort als Kopie. Darin arbeitet der Agent ohne Freigaben. Code, Skills und Werkzeuge gehen mit Benchmark-Beleg als gebündelter Upstream-PR zurück. Änderungen an Schutzregeln kommen nur als einzeln ratifizierter Vorschlag zurück. Benchmarks und Replay-Suite liegen außerhalb der Schreibreichweite der Sandbox.

**Pros:**
- Volle Autonomie dort, wo sie nichts beschädigen kann.
- Jede Übernahme ist messbar besser oder wird verworfen.
- Schutzregeln bleiben beim Owner; die Sandbox liefert ihm Belege statt Bitten.

**Cons:**
- Übernahme bleibt Owner-Arbeit, wenn auch gebündelt und belegt.
- Aufbau von Benchmark-Harness und Replay-Suite kostet vorab Arbeit.

### Option B: Freigaberegeln direkt in der Produktiv-Umgebung lockern

**Pros:**
- Schnellster Effekt auf die 39 %.

**Cons:**
- Kein Beleg, dass die Lockerung keinen der Realfälle wieder öffnet → **Abgelehnt weil:** Lockerung ohne Replay-Nachweis wiederholt genau die Vorfälle, aus denen die Regeln stammen.

### Option C: Sandbox ohne Benchmarks

**Pros:**
- Sofort startklar.

**Cons:**
- Erfolg ist Meinung; Übernahme-Entscheide werden wieder Einzelprüfung → **Abgelehnt weil:** verlagert die Freigabe-Last nur, statt sie zu senken.

### Option D: Sandbox ratifiziert eigene Regeländerungen selbst

**Pros:**
- Maximale Geschwindigkeit.

**Cons:**
- Der Agent bewertet und lockert die Kontrollen, die ihn kontrollieren → **Abgelehnt weil:** widerspricht Lotsen-Charta Punkt 3 und Punkt 8; Benchmarks wären durch die bewertete Partei änderbar.

---

## 3. Decision Outcome

**Gewählte Option: Option A — Sandbox-Werkstatt mit festen Benchmarks und Owner-Ratifikation für Schutzregeln**

Option A senkt die Freigabe-Last dort, wo sie unnötig ist (Untersuchungen, Versuche, Werkzeug-Entwicklung), und ersetzt Einzelfreigaben durch einen wöchentlichen, belegten Übernahme-Stapel. B öffnet Realfälle ohne Nachweis, C misst nicht, D hebt die Kontrolle auf. „Die Sandbox schult die Realumgebung“ heißt hier: Sie erprobt Änderungen an einem Zwilling und belegt sie am Benchmark. Übernommen wird nur, was belegt ist, und Schutzregeln nur auf ausdrückliches Owner-Wort.

---

## 4. Implementation Details

### 4.1 Zwei Änderungsklassen

| Klasse | Beispiele | Weg nach Produktiv |
|---|---|---|
| **Werkstück** | Code, Tests, Skills, Werkzeuge, Doku | Upstream-PR mit Sandbox-Beleg, wöchentlich gebündelt; normale SA-M-Regeln |
| **Schutzregel** | `~/.claude/policies/`, Hooks, `settings.json`-Permissions, Rulesets, CODEOWNERS, `sa_m`-Block, Benchmarks und Replay-Suite selbst | Nur Vorschlag mit Benchmark- und Replay-Beleg, je Regel ein Issue, einzeln vom Owner ratifiziert; nie gebündelt |

### 4.2 Benchmarks

Gemessen je Lauf und wöchentlich aggregiert. Harness und Daten liegen in `platform` und werden der Sandbox nur lesend als Kopie gegeben.

| # | Benchmark | Quelle | Baseline | Ziel / Grenze |
|---|---|---|---|---|
| B1 | Owner-Unterbrechungen je gemergtem PR | `pr-merge-sa.jsonl`, verschiedene PRs; Wochenwert als Differenz zweier Messungen, weil Merge-Sätze keinen Zeitstempel tragen | 39,1 % | sinkend; Zielwert setzt der Owner nach dem Pilot |
| B2 | Aufträge mit belegtem Ergebnis ohne Eingriff, Quote und Dauer | `status.json` der Läufe | – | ≥ 80 % `fertig` |
| B3 | Übernahmequote der Sandbox-Vorschläge | Upstream-PRs mit Sandbox-Beleg | – | **Kill-Kriterium: < 1/3 nach dem Pilot** |
| B4 | Qualität: CI grün, Revert oder Fix binnen 7 Tagen nach Übernahme | `git log`, CI | – | Revert/Fix-Quote nicht höher als bei Nicht-Sandbox-PRs |
| B5 | **Sicherheit**: Realfall-Replay-Suite wird weiter blockiert | `tools/sandbox/replay/` | 100 % | **muss 100 % bleiben; jede Senkung ist ein harter Stopp** |
| B6 | Kosten je Auftrag (USD, Tokens) | `status.json` | – | im Budget aus #3685 S5 |

Die Replay-Suite enthält die historischen Vorfälle aus `regel-historie.md` und den Gate-Drills als ausführbare Fälle. Jede vorgeschlagene Schutzregel-Änderung wird gegen sie gespielt; ein Vorschlag, der einen Fall wieder durchlässt, wird nicht vorgelegt.

### 4.3 Abschottung (bestehend, #3686)

- Selbstprüfung vor jedem Lauf; Abbruch bei fremden Zugangsdaten, Remotes außerhalb `iilsandbox` oder Push-Recht des Tokens außerhalb `iilsandbox`.
- Repos als Kopie ohne Remote oder als Spiegel in `iilsandbox`; GitHub Actions in `iilsandbox` aus.
- Vor jeder Kopie von Daten aus `~/.claude` ein Secret-Scan (`gitleaks`) mit Positivkontrolle; `settings.json`, Memory und Mail-/Kontodaten werden nicht kopiert.
- Budget-Wächter je Lauf.

### 4.4 Getrennte Freigabe-Profile je Org

Freigaben gelten je Org, nicht global:

| Ebene | `iilsandbox` | `achimdehnert` / `iilgmbh` |
|---|---|---|
| Agent im Container | keine Rückfragen (`--dangerously-skip-permissions`), begrenzt durch Selbstprüfung und Budget | – |
| Host-Session (Auto-Mode) | eigener `autoMode.allow`-Eintrag: Repos, Branches, PRs und Merges nur in `iilsandbox` | unverändert |
| Merge (`pr_merge_sa.py`, `sa_m`) | eigenes Org-Profil: jede Wirkung mit M0 gedeckt, weil Actions aus und kein Prod-Pfad | unverändert (W1→M1, W2→M2, W3→M1 + Prüffrage) |
| GitHub-Rulesets | keine Pflicht-Reviews | unverändert |

Die Trennung ist nur so stark wie die Grenze dazwischen: Das Sandbox-Profil gilt ausschließlich, wenn Ziel-Repo **und** Token in `iilsandbox` liegen. Der Übergang nach `achimdehnert`/`iilgmbh` läuft immer über die Produktiv-Regeln. Die Einträge in `autoMode.allow` und `sa_m` sind Schutzregeln (4.1) und werden vom Owner gesetzt.

### 4.5 Übernahme-Ablauf

1. Lauf erzeugt `ausgang/bericht.md`, `status.json` und Patches.
2. Benchmarks B2–B6 werden automatisch aus dem Lauf berechnet.
3. Wöchentlich ein Übernahme-Stapel für den Owner: Werkstücke als PRs, Schutzregel-Vorschläge als einzelne Issues.
4. Spiegel in `iilsandbox` werden vor jedem Lauf frisch vom Original übernommen, nie umgekehrt automatisch.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform` `tools/sandbox/` | 0 Sandbox-Kern | ✅ Abgeschlossen | 2026-10-04 | #3686: Selbstprüfung, Wächter, Lokal-Modus belegt |
| `platform` | 1 Benchmark-Harness + Replay-Suite, Baseline | ⬜ Ausstehend | – | B1–B6 messbar, B5 = 100 % |
| `iilsandbox` | 2 Spiegel der Pilot-Repos, Org-Token | ⬜ Ausstehend | – | erstes Repo und Token durch den Owner |
| Pilot-Repos | 3 Pilot, 2 Wochen | ⬜ Ausstehend | – | wöchentlicher Übernahme-Stapel |
| `platform` | 4 Entscheid: ausweiten oder stoppen | ⬜ Ausstehend | – | Kill bei B3 < 1/3 oder B5 < 100 % |

---

## 6. Consequences

### 6.1 Good

- Untersuchungen und Versuche laufen ohne Freigabe durch.
- Übernahmen sind belegt und gebündelt statt einzeln erbeten.
- Lockerungen von Schutzregeln kommen mit Replay-Nachweis.

### 6.2 Bad

- Die Übernahme bleibt beim Owner; die Last sinkt, verschwindet aber nicht.
- Spiegel und Benchmarks brauchen Pflege.
- Sandbox-Läufe teilen sich das Abo-Kontingent mit der laufenden Arbeit.

### 6.3 Nicht in Scope

- Prod-Zugang, Deploys, Publish aus der Sandbox.
- Selbst-Ratifikation von Schutzregeln (Option D).
- Repos mit personenbezogenen Daten oder Behördenbezug (`meiki-lra`, `ttz-lif`).

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Benchmark wird zum Ziel statt zum Maß | Mittel | Hoch | Benchmarks außerhalb der Sandbox-Schreibreichweite; B4 und B5 als Gegengewichte |
| Secret gelangt in eine Kopie | Niedrig | Kritisch | `gitleaks` mit Positivkontrolle vor jeder Kopie, Allowlist der Quellen |
| Übernahme-Stapel wird zur neuen Freigabe-Flut | Mittel | Mittel | B3-Kill-Kriterium, Bündelung, nur belegte Vorschläge |
| Spiegel driften vom Original | Mittel | Niedrig | Frische Übernahme vor jedem Lauf |

---

## 8. Confirmation

1. **Selbstprüfung**: `tools/sandbox/selbstpruefung.py` läuft vor jedem Agenten-Start; ohne Exit 0 startet kein Lauf (Tests `tools/tests/test_sandbox_selbstpruefung.py`).
2. **Replay-Gate**: Kein Schutzregel-Vorschlag wird als Issue vorgelegt, ohne dass `tools/sandbox/replay/` mit 100 % blockierten Fällen gelaufen ist; das Ergebnis steht im Issue.
3. **Schreibreichweite**: Benchmark-Harness und Replay-Suite werden der Sandbox nur als Kopie gegeben; ein Diff an ihnen aus einem Sandbox-PR fällt unter die Governance-Pfade (`sa_m.governance_pfade`) und braucht Owner-Approval.
4. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 6 Monate.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **Sandbox** | Abgeschotteter Container plus Org `iilsandbox`, in der ein Agent ohne Freigaben arbeitet, aber nichts außerhalb verändern kann |
| **Werkstück** | Ergebnis der Sandbox, das keine Schutzregel ist: Code, Tests, Skills, Werkzeuge, Doku |
| **Schutzregel** | Regel, die Agenten begrenzt: Policies, Hooks, Permissions, Rulesets, Benchmarks |
| **Replay-Suite** | Ausführbare Sammlung historischer Vorfälle, die jede Regeländerung weiter blockieren muss |
| **SA-M** | Merge-Regel aus `autonomy-gates`: Mandat (M0–M3) muss Wirkung (W0–W3) decken |
| **Benchmark** | Feste Messgröße, an der eine Änderung als besser oder schlechter belegt wird |

---

## 9. More Information

- platform#3685: Vorschlag Sandbox-Klasse, Owner-Entscheide S1–S7
- platform#3686: Sandbox-Kern (`tools/sandbox/`)
- `~/.claude/policies/autonomy-gates.md`: fünf Gates, SA-M-Block
- ADR-070: Progressive Autonomy — diese Sandbox ist eine Stufe ohne Außenwirkung
- ADR-081: Guardrails — bleiben in Produktiv unverändert, bis ein Vorschlag ratifiziert ist

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-10-04 | Achim Dehnert | Initial: Status Proposed |

---

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 6
  - drift_check_paths:
      - platform/tools/sandbox
  - supersedes_check: true
-->
