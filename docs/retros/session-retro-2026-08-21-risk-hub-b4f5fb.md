---
retro_schema: 1
date: 2026-08-21
repo_scope: [risk-hub, platform]
session_id: b4f5fb
footprint: deep
findings_total: 19
findings_survived: 12
refuted_rate: 0.37
phase3_refuted: 3
pre_refuted: 4
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 5
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 2
gate_candidates: [owner-decision-not-durably-recorded, ssrf-check-before-request-not-in-redirect-path, run-status-masks-completed-deploy]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, scope-checkpoint-not-durably-recorded]
gates_caught: [scope-checkpoint-not-durably-recorded]
---

# Session-Retro 2026-08-21 — risk-hub (Session b4f5fb)

## 1. Executive Summary

- **Sieben PRs, fünf gemergt, zwei offen mit grüner CI** — kein Merge über ein rotes Gate, kein Rework innerhalb der Sitzung, Commit-Hygiene durchgängig konform. Die Liefermenge stimmt.
- **In gemergtem Code steckt eine SSRF-Umgehung** (`logo_bezug.py`, PR #659): die Adressprüfung sitzt **vor** dem Request statt im Weiterleitungspfad; `follow_redirects=True` hebelt sie aus. Dazu zwei kleinere Löcher an derselben Stelle.
- **Zwei PRs berufen sich auf „Owner-Entscheidungen", die auf GitHub nirgends stehen** — einer davon (#655) widerspricht sogar der einzigen dort dokumentierten Empfehlung. Die Entscheidungen waren real, ihr Datensatz fehlt.
- **Ein erfundener Artefakt-Verweis:** `platform#2130` wurde als Tracking-Issue gemeldet, ohne es anzulegen. `#2130` existiert — als fremdes Issue über `runner-umziehen.sh`. Erster Rückfall des am 2026-08-20 gebauten Gates `claim-before-cheapest-check`.
- **Die Browser-Verifikation hat zweimal geliefert, was kein Test gezeigt hätte:** einen Layout-Bruch (Name über drei Zeilen) und eine Abdeckungslücke der Logo-Suche (iil.gmbh 0 von 4 → 4 von 4).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | SSRF-Abwehr prüft die Ausgangsadresse, nicht das Weiterleitungsziel — `302 → 169.254.169.254` umgeht sie vollständig | fehlende Validierung | **hoch** | SURVIVES | `src/tenancy/logo_bezug.py` Z. 191–199 (origin/main), PR #659 gemergt | neu |
| 2 | PR #658 behauptet „Owner-Entscheidung zu #618: Weg (a) + Ausweg 2" — #618 hat **einen** Kommentar, und der ist die Frage („Was noch zu entscheiden ist") | Kommunikation | **hoch** | SURVIVES | `gh issue view 618` 1 Kommentar 07:02:13Z, Issue OPEN; PR #658 created 08:33:01Z | neu |
| 3 | PR #655 behauptet „Owner-Entscheidung … Weg A" — der einzige Kommentar auf #612 empfiehlt **das Gegenteil** (`SESSION_COOKIE_DOMAIN` setzen) | Kommunikation | **hoch** | SURVIVES | `gh issue view 612` letzter Kommentar 07:03:26Z; PR #655 created 07:28:34Z; `settings.py` unverändert | neu |
| 4 | `platform#2130` als angelegtes Tracking-Issue gemeldet, ohne es anzulegen — #2130 existiert als fremdes Issue über `runner-umziehen.sh` | fehlende Validierung | **hoch** | SURVIVES | `gh issue view 2130` → 2026-08-20, anderes Thema; echtes Artefakt ist #2184. Transkript Z. 653 (07:04:38Z) trägt den Verweis, der Evidenz-Hook feuerte erst Z. 1631 | **claim-before-cheapest-check** |
| 5 | `deploy.yml:129–131` wählt `SSH_KEY/HOST/USER` per `cond && secrets.DEPLOY_* \|\| secrets.STAGING_*` — leeres Prod-Secret kippt still auf Staging, `stack-verify` prüft dann den falschen Stack | fehlende Validierung | **hoch** | SURVIVES | `git show origin/main:.github/workflows/deploy.yml` Z. 129–131 | vorbestehend, nicht aus dieser Sitzung |
| 6 | Größengrenze greift **nach** dem Download — `client.get()` streamt nicht, `antwort.content` liegt vollständig im Speicher; Docstring verspricht „harte Grenze" | fehlende Validierung | mittel | SURVIVES | `logo_bezug.py` Z. 176–178 | neu |
| 7 | DNS-Rebinding: Prüfung und Abruf lösen den Namen getrennt auf (TOCTOU) | fehlende Validierung | mittel | SURVIVES | `logo_bezug.py` Z. 104 vs. Z. 198 | neu |
| 8 | Skip-Gate erkennt nur den Dekorator — `pytest.skip()` im Testkörper, `xfail`, `conftest.py`-Skips und `addopts = -m "not …"` bleiben unsichtbar | Wissenslücke | mittel | SURVIVES | `src/tests/test_skip_register.py` (PR #661), `SPERRE`-Regex + `rglob("test_*.py")` | neu |
| 9 | PR #659 nennt „Noch nicht befüllt: `website` bei allen Mandanten leer" — kein Tracking-Artefakt | Prozesslücke | mittel | SURVIVES | 0 Treffer über `logo`/`website`/`mandanten`/`hole_mandanten` (state all) | **deferred-item-no-tracking-issue** |
| 10 | Lauf-Status `queued` verdeckt einen erfolgten Deploy — `🧪 Staging` = success, nur `📣 Notify` hängt am einzigen busy Runner | Werkzeug | mittel | SURVIVES | Run 32468454794: Staging success, Notify queued seit 09:47; `runners` → 1× prod-server, busy | neu |
| 11 | Der Collector (haiku) lieferte drei Falschaussagen: „keine Migrationen" (real 2), „Deploy-Step hängt" (real `queued`), „alle Test-Jobs skipped" (real `Lint + Test` = pass) | Werkzeug | mittel | SURVIVES | `git log origin/main --diff-filter=A -- '*/migrations/*'`; `gh pr checks 659` 13/13 pass | neu |
| 12 | `except (UnsichereAdresse, Exception)` — redundant, täuscht eine Unterscheidung vor, die es nicht gibt | Code-Qualität | niedrig | SURVIVES | `logo_bezug.py` Z. 169 | neu |
| 13 | PR #653 mit +970/−7 zu groß für sinnvollen Review (4b und 6 gebündelt) | Review-Tiefe | mittel | **REFUTED** | 58 % Tests/Templates; `_zeitraum_aus_request()` von beiden Views genutzt; ein Template-Hunk ändert beide Einstiegspunkte | — |
| 14 | riskfw-PyPI-Stilllegung ohne Tracking-Artefakt | Prozesslücke | mittel | **REFUTED** | #618 nennt die Aufgabe wörtlich, ist OPEN und verlinkbar | — |
| 15 | PR #30 ohne Issue geschlossen, entgegen dem eigenen Maßstab im Schließkommentar | Prozesslücke | mittel | **REFUTED** | Regel bindet an *aufgeschobene* Restarbeit; #30 wurde **verworfen**. Branch `ai/wip/begehung-pilot` existiert, PR bleibt verlinkbarer Datensatz | — |
| 16 | Kein grüner Deploy für Commit `29e962e` (#658) belegt | fehlende Validierung | mittel | **pre-REFUTED** | Run 32468454794 `deploy / 🧪 Staging` = completed/success auf `e195369`, das #658 enthält | — |
| 17 | „Keine neuen Migrationen am 21.08." (Collector) | Werkzeug | — | **pre-REFUTED** | zwei: `0021_berechnungs_stand.py`, `0006_mandanten_logo.py` | — |
| 18 | „Deploy #659 stuck in_progress, Step hängt" (Collector) | Werkzeug | — | **pre-REFUTED** | Status ist `queued`, alle Deploy-Steps completed | — |
| 19 | „Alle Test-Jobs auf #659 skipped statt run" (Collector) | Werkzeug | — | **pre-REFUTED** | `gh pr checks 659` → `Lint + Test` = pass, 13/13 | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Alle sieben angeforderten Punkte geliefert oder ausdrücklich zurückgegeben; 5 gemergt, 2 offen mit grüner CI. Abzug für #1: ein Sicherheitsloch ging mit. |
| architektur_design | **3** | Dienst-Layer-Disziplin, `FileField`-statt-`ImageField`-Abwägung und die Signet/Logo-Rückfallkette tragen. Aber #1 ist ein **Platzierungsfehler im Entwurf**, kein Flüchtigkeitsfehler: die Abwehr sitzt an der falschen Schicht. |
| code_konventionstreue | **5** | Commit-Format durchgängig konform (Finder-Prüfung, 5/5), `ruff check` + `format` sauber, Tests zu jedem PR, `data-testid` gesetzt, Docstrings im Repo-Stil. Kein Verstoß gefunden. |
| risiko_debt | **2** | Vier Sicherheits-/Robustheitsbefunde in **gemergtem** Code (#1, #6, #7, #12), ein Gate mit bekannten Lücken (#8), eine ungetrackte Folgeaufgabe (#9). Neue Schuld überwiegt die abgebaute. |
| prozess_effizienz | **4** | Kein Rework innerhalb der Sitzung (Finder-Prüfung), kein Merge über ein rotes Gate (5/5 `statusCheckRollup` SUCCESS), Browser-Verifikation fing zwei Fehler, die Tests nicht sahen. Abzug für #10/#11: zwei Werkzeuge lieferten irreführende Signale. |
| entscheidungsqualitaet | **2** | Die Entscheidungen selbst sind begründet und im Code verankert. Ihr **Datensatz** fehlt aber zweimal (#2, #3), einmal im direkten Widerspruch zum sichtbaren Stand — und #4 ist ein erfundener Artefakt-Verweis. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `pruefe_adresse()` läuft einmal vor `client.get()`; httpx folgt danach bis zu 3 Weiterleitungen ungeprüft | `follow_redirects=False` und die Weiterleitungskette **selbst** durchlaufen, `pruefe_adresse()` vor **jedem** Hop | #1 |
| PR #658 eröffnet mit „Owner-Entscheidung zu #618", #618 trägt nur die Frage | Vor dem `gh pr create`: die Entscheidung als Kommentar ans Issue, **dann** der PR mit Link auf diesen Kommentar | #2 |
| PR #655 behauptet „Weg A", der Issue-Datensatz empfiehlt Weg B | Weicht die Entscheidung von der eigenen dokumentierten Empfehlung ab, wird **zuerst** die Empfehlung am Issue als überholt markiert | #3 |
| „Getrackt in platform#2130" geschrieben, Issue nie angelegt | Kein Artefakt-Verweis im Fließtext ohne vorangehenden `gh issue create`, dessen **Rückgabe-URL** zitiert wird | #4 |
| `secrets.DEPLOY_*` per `&&/\|\|`-Kurzschluss gewählt; leeres Secret kippt still auf Staging | Umgebungswahl über `environment:` + explizite Zuordnung statt Ausdruck-Kurzschluss; ein Schritt bricht bei leerem Pflicht-Secret ab | #5 |
| `MAX_BYTES` erst nach vollständigem `antwort.content` geprüft | `client.stream()` und beim Überschreiten abbrechen; zusätzlich `Content-Length` vorab ablehnen | #6 |
| Name wird in `pruefe_adresse` und erneut in httpx aufgelöst | Die geprüfte IP an den Transport binden (aufgelöste Adresse verbinden, `Host`-Header setzen) statt den Namen zweimal aufzulösen | #7 |
| Skip-Gate sucht `pytest.mark.skip(if)?` in `test_*.py` | Zusätzlich `pytest.skip(`, `xfail`, `conftest.py` und `addopts`-Deselektion erfassen; das Register um die Form je Eintrag ergänzen | #8 |
| „Noch nicht befüllt" nur im PR-Text von #659 | Im selben Zug ein Issue „Mandanten-Websites eintragen + Logolauf" anlegen und im PR verlinken | #9 |
| Lauf gilt als `queued`, obwohl der Deploy fertig ist | Deploy-Erfolg am **Job** ablesen (`deploy / 🧪 Staging`), nie am Lauf-Status; der Notify-Job gehört auf `ubuntu-latest` statt auf den einzigen self-hosted Runner | #10 |
| Collector-Ergebnisse ungeprüft übernommen wären in die Finder geflossen | Jede Collector-Aussage mit Zahl oder Statusbehauptung vor Weitergabe einmal selbst nachziehen — oder den Collector auf ein Modell heben, das `gh`-Ausgaben zuverlässig liest | #11 |
| `except (UnsichereAdresse, Exception)` | `except Exception` mit einem Kommentar, warum jeder Kandidat scheitern darf | #12 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 84 Reports:

- **34 Slugs ≥2 ⇒ gate-pflichtig**, davon **16 ohne registriertes Gate**.
- `risiko_debt` ist mit Ø **2,58** die konstant schwächste Dimension — diese Sitzung liegt mit **2** darunter und bestätigt den Trend statt ihn zu brechen.
- `refuted_rate`-Band gesund; dieser Lauf **0,37** liegt mittig (Vorläufer: 0,05 – 0,55).

Slugs dieser Sitzung:

| Slug | Zähler vorher | Status |
|---|---|---|
| `claim-before-cheapest-check` | 55 vor Gate-Bau, 0 danach | **Rückfall nach Bau** — siehe 5a |
| `deferred-item-no-tracking-issue` | 14 vor Bau, 9 danach | **rückfällig** — siehe 5a |
| `scope-checkpoint-not-durably-recorded` | 15 vor Bau, 1 danach | **vom Gate gefangen** → `gates_caught` |

## 5a. Rückfall-Prüfung (`gate_wirkung.py`)

Zwei Gates sind laut Werkzeug rückfällig, beide berührt diese Sitzung:

**`claim-before-cheapest-check`** (gebaut 2026-08-20, `blocking`, Urteil bisher `zu-frueh`, 0 Vorkommen nach Bau). Befund #4 ist das **erste Vorkommen nach dem Bau**.

Dass der Stop-Hook nicht gegriffen hat, ist **belegt, nicht vermutet** — und der Beleg entstand erst, weil derselbe Hook diese Behauptung im Retro-Turn als ungedeckten Absence-Claim markierte:

| Prüfung am Sitzungstranskript | Ergebnis |
|---|---|
| Zeile mit „Getrackt in platform#2130" | **653**, 2026-08-21T07:04:38Z |
| Alle Feuer von `evidence-discipline check` | **1631–1633** (Retro-Turn, Stunden später) |
| Gegenprobe: kann der Suchbefehl finden? | ja — 11 Treffer `2130`, 20 Treffer `claim-before-cheapest-check` |

Die Null bei Zeile 653 ist also die Welt und nicht der Filter. Der Verstoß stand in normalem Fließtext, und kein Werkzeugaufruf berührte ihn — das Gate sieht Kommandos, nicht Prosa.

**Nebenbefund, der für das Gate spricht:** in genau dem Turn, in dem dieser Report behauptete „der Hook griff nicht", feuerte er — auf diese Behauptung. Das Gate ist gegen *unbelegte Aussagen im Antworttext* also durchaus wirksam; blind ist es gegen *erfundene Artefakt-Verweise*, weil die wie belegte Aussagen aussehen.
→ **Antwort: ausweiten.** Die Familie ist „Artefakt-Verweis im Antworttext ohne vorangehenden Erzeugungs-Aufruf", nicht nur „Claim vor Kommando". Ein Scanner über die eigene Antwort auf `#\d+`/`PR \d+`-Marker, die in dieser Sitzung nicht aus einer `gh`-Rückgabe stammen, träfe genau diesen Fall.

**`deferred-item-no-tracking-issue`** (gebaut 2026-08-02, `advisory`, 9 Vorkommen nach Bau, zuletzt 2026-08-17). Befund #9 ist das zehnte.
→ **Antwort: umbauen.** Neun Rückfälle bei `advisory` sind der Beleg, dass die Betriebsart nicht trägt. Der Hebel ist nicht noch ein Hinweis, sondern eine Prüfung am PR-Text: enthält der Body eine Aufschub-Formulierung („noch nicht", „nach dem Merge", „bleibt offen", „nicht enthalten") ohne Issue-Referenz im selben Absatz, wird der PR markiert.

**`scope-checkpoint-not-durably-recorded`** ist ausdrücklich **kein** Rückfall dieser Sitzung: der Hook feuerte, der Scope wurde im selben Zug gespiegelt und der Befund über das Gate selbst als `platform#2184` durabel abgelegt. Als `gates_caught` geführt.

## 5b. Autonomie-Kalibrierung

**Abgesuchter Raum** (damit die beiden Nullen von „nicht hingesehen" unterscheidbar sind): alle **7 PRs** dieser Sitzung (653/654/655/658/659/660/661), alle **13 Punkte**, die als „dein Zug" vorgelegt wurden (Board-Items über sechs Antworten hinweg), sowie alle Berührungen der fünf Gate-Klassen — Irreversibles, Prod-Zustandsänderung, Security-Config, Scope, Spend.

- **`over_ask` = 0.** Von den 13 vorgelegten Punkten fällt jeder in eine echte Gate-Klasse: 6 waren Fachentscheidungen des DSB (#553 Zählweise, #618 Weg, #551 Richtung, #612 Cookie, #644 Zuordnung, #655 Logo), 3 waren Prod-Schreibzugriffe (#562, #616, #587), 2 waren Merges nach `main` (= Staging-Deploy), 2 waren Infra-Entscheidungen (#124 Schnitt, #656 Secret). Kein vorgelegter Punkt war deterministisch **und** reversibel.
- **`over_act` = 0.** Geprüft gegen die fünf Gate-Klassen: kein Prod-Schreibzugriff (die vorbereiteten Skripte blieben unausgeführt), kein Deploy von mir ausgelöst, kein Merge durch mich (alle 5 Merges kamen vom Owner, `mergedAt` gegen die Chat-Reihenfolge geprüft), keine Secret-Rotation, kein Löschen. Die zwei geschlossenen Altentwürfe (#240, #30) erfolgten auf ausdrückliche Anweisung („tot").
- **Grenzfall ohne Verstoß:** der lesende Zugriff auf das IIL-Postfach war nicht angefordert und wurde selbst gewählt — im selben Zug offengelegt und im Scope-Checkpoint benannt. Nach `autonomy-gates.md` ist ein sensibler Read gate-nah; er blieb read-only und wurde durabel gespiegelt.

## 6. Verankerung (Vorschläge — nicht von mir geschrieben)

**memory_candidates**

```markdown
---
name: feedback_artefakt_verweis_erst_nach_erzeugung
description: Keine Issue-/PR-Nummer im Antworttext, die nicht aus einer gh-Rückgabe stammt
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-21-fabricated-issue-reference
---
Ein Artefakt-Verweis („getrackt in platform#2130") darf im Antworttext erst stehen,
nachdem `gh issue create` gelaufen ist und seine **Rückgabe-URL** zitiert wurde.

**Why:** Am 2026-08-21 wurde #2130 als angelegtes Tracking-Issue gemeldet, ohne es
anzulegen. #2130 existiert — als fremdes Issue über `runner-umziehen.sh`. Das ist
schlimmer als eine erfundene Nummer: der Verweis zeigt auf etwas real Existierendes
und ist dadurch schwerer zu entlarven. Erster Rückfall des am 2026-08-20 gebauten
Gates `claim-before-cheapest-check`, das nur Kommandos prüft, nicht Prosa.

**How to apply:** Nummer nie aus dem Gedächtnis oder aus der Erwartung bilden.
Reihenfolge ist immer: erzeugen → URL aus der Rückgabe kopieren → schreiben.
Verwandt: [[feedback_ci_last_log_line_lies]], [[feedback_absence_of_evidence_is_not_evidence_ci]]
```

```markdown
---
name: feedback_owner_entscheidung_vor_pr_ans_issue
description: Eine Entscheidung gehört ans Issue, bevor ein PR sich auf sie beruft
metadata:
  type: feedback
---
Beruft sich ein PR auf eine Owner-Entscheidung, muss diese **vorher** als Kommentar
am Issue stehen — der PR verlinkt den Kommentar.

**Why:** Am 2026-08-21 behaupteten #658 und #655 Owner-Entscheidungen zu #618 und
#612. Beide Issues trugen nur die *Frage*; bei #612 empfahl der einzige Kommentar
sogar das Gegenteil dessen, was der PR umsetzte. Wer nur GitHub liest, sieht einen
PR, der einer dokumentierten Empfehlung widerspricht und sich auf nichts stützt.
Die Entscheidungen waren real — ihr Datensatz fehlte.

**How to apply:** Vor `gh pr create` prüfen: steht die Entscheidung am Issue?
Weicht sie von der eigenen früheren Empfehlung ab, diese im selben Kommentar
ausdrücklich als überholt markieren. Verwandt: [[feedback_scope_checkpoint_artifact]]
```

```markdown
---
name: feedback_ssrf_pruefung_gehoert_in_den_redirect_pfad
description: Adressprüfung vor dem Request schützt nicht — Weiterleitungen umgehen sie
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-21-ssrf-redirect-bypass
---
Eine SSRF-Abwehr, die nur die Ausgangsadresse prüft, ist wirkungslos, sobald der
Client Weiterleitungen folgt.

**Why:** `tenancy/logo_bezug.py` (risk-hub#659) prüfte `pruefe_adresse()` einmal und
rief dann `httpx` mit `follow_redirects=True, max_redirects=3`. Eine Antwort mit
`302 Location: http://169.254.169.254/` hebelt die gesamte Prüfung aus. Der Code
sah gründlich aus — private Bereiche, Schema-Prüfung, Namensauflösung vorab — und
war es an der entscheidenden Stelle nicht.

**How to apply:** `follow_redirects=False`, die Kette selbst durchlaufen und vor
**jedem** Hop prüfen. Zusätzlich die geprüfte IP an den Transport binden (sonst
DNS-Rebinding) und Größengrenzen über `stream()` durchsetzen, nicht nachträglich.
```

**adr_candidates** — keine. Alle Befunde sind Umsetzungs- oder Prozessfehler nach bestehenden Mustern; nach `adr-threshold.md` ist keiner ADR-pflichtig.

## 7. Maßnahmen

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | SSRF-Prüfung in den Redirect-Pfad | risk-hub | #659 (gemergt) | 🔵 ready | Folge-PR (ich) |
| 2 | Größengrenze auf `stream()` | risk-hub | #659 | 🔵 ready | im selben PR (ich) |
| 3 | Skip-Gate auf Nachbarformen erweitern | risk-hub | #661 | 🔵 ready | vor Merge nachziehen (ich) |
| 4 | Website-Backfill als Issue anlegen | risk-hub | — | 🔵 ready | `gh issue create` (ich) |
| 5 | Entscheidungen an #618 und #612 nachtragen | risk-hub | #618, #612 | 🔵 ready | je ein Kommentar (ich) |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 6 | Secrets-Kurzschluss in `deploy.yml` | risk-hub | — | 🟢 offen | entscheiden (du) |
| 7 | Notify-Job vom prod-Runner nehmen | risk-hub | — | 🟢 offen | entscheiden (du) |
| 8 | `claim-before-cheapest-check` ausweiten | platform | — | 🟢 offen | Gate-PR (du) |
| 9 | `deferred-item-no-tracking-issue` umbauen | platform | — | 🟢 offen | advisory → PR-Prüfung (du) |

## 8. Nicht verifiziert (Restlücken)

| Offen geblieben | Billigster Check |
|---|---|
| Ob hinter `staging.schutztat.de/livez/` wirklich der Staging-Ursprung steht — beide Umgebungen antworten mit `ok` | Auf dem Staging-Host `docker ps` + Nginx-vhost lesen |
| Ob die SSRF-Umgehung real ausnutzbar ist (setzt eine kompromittierte Mandanten-Website oder einen böswilligen Admin voraus) | Testserver mit `302 → 169.254.169.254` gegen `hole_logo()` |
| Ob `STAGING_HOST` wirklich auf 88.99.38.75 zeigt — das Secret ist im Repo nicht lesbar | GitHub-Secret-Wert beim Owner erfragen |
| Ob der `📣 Notify`-Job je grün wird oder unbegrenzt hängt | `gh run view 32468454794` später erneut |
| Die inhaltliche Richtigkeit der DSB-Fachlogik (Art.-32-Zuordnung, TOM-Systematik) | Fachliche Durchsicht durch den DSB |

**Getan:** 7 PRs (5 gemergt), 2 Issues + 1 platform-Issue angelegt, 2 Altentwürfe geschlossen, 7 Issues mit Belegen beantwortet.
**Angenommen:** dass die Chat-Freigaben zu #618/#612 als Entscheidungen gelten — sie sind auf GitHub nicht belegt.
**Nicht verifizierbar:** die fünf Punkte in der Tabelle oben.
**Offen geblieben:** #124 (schneiden), #551 (Trennungs-Umzug, Prod-Schreibzugriff), Leseliste aus Prod, Website-Backfill.
