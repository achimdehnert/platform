---
concept_id: KONZ-platform-014
title: Deploys & Approvals Board
pipeline_status: idea
tier: T3
owner: Achim Dehnert <pg@dehnert.team>
spec_refs: []                      # kein ADR-211-Spec-Objekt betroffen — reine Ops-UI über GitHub-API, keine Genesor-Spec
adr_threshold: org-weiter ADR      # nur falls Stufe B (org-weiter Deploy-Approve-Token) gebaut wird; Stufe A/B-lite = kein ADR
review_by: 2026-10-08
kill_criteria: "Stufe B: wenn im ersten vollen Quartal nach Go-Live <20% der Prod-Approvals über den Board-Button (statt GitHub-UI) laufen ODER in irgendeinem 60-Tage-Fenster 0 Board-Approves — Rückbau + Widerruf des Schreib-Tokens. Board gesamt: wenn /operations/approvals/ in 30 aufeinanderfolgenden Tagen 0 authentifizierte Views hat — Feature einfrieren."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: dev-hub/apps/operations/services_approvals.py, commit_or_pr: "dev-hub#115", opened_in_session: true}
  - {claim_id: C2, source_path: dev-hub/config/settings/base.py:427, commit_or_pr: "dev-hub#115", opened_in_session: true}
  - {claim_id: C3, source_path: dev-hub/config/settings/production.py:59, commit_or_pr: "dev-hub#115", opened_in_session: true}
  - {claim_id: C4, source_path: dev-hub/apps/operations/views.py:200, commit_or_pr: "dev-hub#115", opened_in_session: true}
  - {claim_id: C5, source_path: dev-hub/apps/operations/urls.py:13, commit_or_pr: "dev-hub#115", opened_in_session: true}
  - {claim_id: C6, source_path: dev-hub/apps/releases/services.py, commit_or_pr: "ADR-099", opened_in_session: true}
  - {claim_id: C7, source_path: "grep pending_deployments über dev-hub+platform → nur Docstring-Referenz, kein Mechanismus", commit_or_pr: "n/a (E2-negativ)", opened_in_session: true}
created: 2026-07-08
---

# KONZ-platform-014 — Deploys & Approvals Board

## 1 Executive Summary

**Kernthese:** Der Incident vom 2026-07-08 (ein GitHub-Environment-Approval stand **3 Tage
unsichtbar** auf `waiting` und blockierte via Concurrency-Group alle Folge-Deploys) war ein
**Sichtbarkeits-**, kein Bequemlichkeits-Problem. Die bereits gebaute **Stufe A** (read-only
Aggregations-Board, dev-hub PR #115) schließt genau diesen Gap. Der als „in Arbeit" im Code
referenzierte, aber nie geschriebene Fahrplan wird hiermit nachgezogen und liefert die
entscheidungsreife Einstufung der Folgestufen.

**Empfehlung in einem Satz:** Als Nächstes **Stufe B-lite** bauen (**In-App-Sichtbarkeits-Eskalation
auf devhub.iil.pet selbst** — globales Nav-Badge mit Anzahl STALE-Approvals + Dashboard-Card,
**null Schreib-Scope, keine externen Kanäle**) — sie holt den Board-Zustand aus der einen
Unter-Route heraus in jede devhub-Seite und deckt den realen Incident-Modus vollständig ab. Die
ursprünglich angedachte **Stufe B
(One-Click-Approve via `pending_deployments`)** wird **hinter ein Entscheidungs-Gate gestellt**,
nicht gebaut: Ihr einziger einzigartiger Mehrwert (Batch-Freigabe blockierter Ketten) wiegt den
Preis — ein org-weiter Deploy-Approve-Schreib-Token über zwei Orgs — nach adversarialer Prüfung
**nicht auf**, solange nicht drei Vorbedingungen erfüllt sind (§13).

## 2 Scope & Evidenzbasis

**In-Scope:** Der Lebenszyklus des Approvals-Boards in `dev-hub/apps/operations` und die Frage,
ob/wie serverseitige GitHub-Deployment-Freigaben eingeführt werden.
**Out-of-Scope:** Die Deploy-Pipeline selbst (ADR-021/120/156), Branch-Protection-Policy
(KONZ-platform-004), die Concurrency-Group-Semantik als solche.

Belegbasis (alle Dateien in dieser Session geöffnet, s. `evidence_manifest`):

| ID | Beleg | Aussage |
|----|-------|---------|
| C1 | `services_approvals.py` (E2) | Stufe-A-Service existiert: httpx, `ORGS=["iilgmbh","achimdehnert"]`, 120s-Cache, STALE ab >6h, Repo-Liste live (nicht hardcodiert), Fehler je Repo geschluckt. Docstring nennt Stufe B ausdrücklich als *nicht enthalten*. |
| C2/C3 | `base.py:427`, `production.py:59` (E2) | Es gibt **einen** geteilten `GITHUB_TOKEN` (prod via `read_secret`), genutzt von `services_approvals.py` **und** `services.py` (SSH/Ops). |
| C4 | `views.py:200` (E2) | `ApprovalsBoardView(LoginRequiredMixin, HTMXMixin, TemplateView)` — **kein** `StaffRequiredMixin` (Kontrast: `WindsurfView` ist staff-restricted). |
| C5 | `urls.py:13` (E2) | Route `operations/approvals/` verdrahtet. |
| C6 | `releases/services.py` (E2) | Muster-Vorlage (httpx + `settings.GITHUB_TOKEN`), das der Stufe-A-Service kopiert. |
| C7 | grep `pending_deployments` (E2-negativ) | Der Stufe-B-Mechanismus existiert **nirgends** im Code — nur als Docstring-Referenz. Kein vorbestehender Mechanismus, gegen den wir doppelt bauen würden. |

## 3 Infrastruktur-Fit

Stufe A folgt bestehenden Konventionen (App `apps/operations`, kein neuer Django-App, kein
Celery/Beat — bewusst, vgl. dev-hub #51-Reasoning: kein Beat-Eintrag ohne echten periodischen
Task). Der Cache ist Default-`LocMemCache` (pro Gunicorn-Worker getrennt) — für Stufe A
ausreichend; für Stufe B-lite muss das Nav-Badge den STALE-Zähler pro Request billig kennen — es
liest denselben 120s-Cache-Eintrag wie das Board (kein Extra-API-Call pro Seitenaufruf), **relevant** (§7).

## 4 Steelman (stärkstes Pro-Stufe-B-Argument)

Stufe B liefert etwas, das **weder Stufe A noch die GitHub-UI** können: Entscheidung *und*
Handlung im selben Kontext, inklusive **Batch-Freigabe einer blockierten Kette in korrekter
Reihenfolge**. Beim Deep-Link kennt der Approve-Button in GitHub nur *einen* Run, nicht die durch
die Concurrency-Group blockierte Kette; wer über den Deep-Link freigibt, entscheidet blind für ein
Glied und muss für jedes weitere raus-suchen-zurück. Unter Incident-Druck (Stau aufgedeckt, Prod
wartet) ist die teure Größe *Zeit-bis-Handlung × Fehlerrate* — Tab-Wechsel und Run-Verwechslung
sind die Quelle des *zweiten* Incidents. Und: den Schreib-Token im Ruhezustand sauber einzuführen
(least-privilege, Audit-Log, Review-Zeit) ist billiger und sicherer, als ihn im nächsten Feuer
unter Druck nachzurüsten.

*(Ehrliches Zugeständnis des Steelman selbst: Stufe B hätte den konkreten 3-Tage-Incident
**nicht** verhindert — der war reine Unsichtbarkeit, die Stufe A löst.)*

## 5 Konzeptdefinition — die Stufen

| Stufe | Was | Schreib-Scope | Status |
|-------|-----|---------------|--------|
| **A** | Read-only Aggregations-Board (`/operations/approvals/`): wartende Approvals (STALE >6h), offene PRs, letzte Deploys, Deep-Links | keiner | ✅ gebaut+gemergt (dev-hub #115) |
| **B-lite** | **In-App-Sichtbarkeits-Eskalation auf devhub selbst**: globales Nav-Badge (Anzahl STALE `waiting`-Approvals, org-weit) auf jeder devhub-Seite + Hero-Card im Operations-Dashboard. Klick → Board → Deep-Link → Mensch approved in GitHub. **Keine externen Kanäle.** | keiner | 🔵 **empfohlen als Nächstes** |
| **B** | **One-Click-Approve** im Board: Button → serverseitiger `POST /repos/{repo}/actions/runs/{run_id}/pending_deployments` | **org-weiter Deploy-Approve-Token** | ⛔ **gegated** (§13-Vorbedingungen) |
| **C** | **Ketten-Freigabe** — mehrere blockierte Runs einer Kette in korrekter Reihenfolge in einem Rutsch (der einzige echte B-Mehrwert; *nicht* zu verwechseln mit der Batch-Run-Klasse §5.1) | wie B | ⛔ nur nach B |

### 5.1 Run-Klassen: online vs batch (quer zu allen Stufen)

Ein Deploy/Job ist **nicht** dasselbe wie ein anderer — die Erwartung an *Dauer* und *Dringlichkeit*
trennt zwei Klassen, und das Board muss sie trennen, sonst ist die STALE-Logik falsch:

| Klasse | Erwartung | „hängt/braucht Aufmerksamkeit" ab | Beispiel |
|--------|-----------|-----------------------------------|----------|
| **online** | läuft in Maximalgeschwindigkeit durch (Minuten) | schon nach **kurzer** Wartezeit → sofort-Alarm | Web-Deploy, App-Restart, interaktiver Job |
| **batch** | läuft **legitim lang** (Stunden, z.B. 12 h) | erst wenn es die *erwartete* Laufzeit deutlich überschreitet | Daten-Pipeline, Import, Langläufer |

**Belegte Ist-Lage (kein Live-Defekt — Über-Diagnose vermieden):** Der STALE-Badge ist eine
globale 6h-Schwelle (C1, `STALE_HOURS = 6`), **angewandt ausschließlich** in `_get_waiting_runs`
auf `status=waiting`-Runs (verifiziert: `is_stale` nur Zeile 156, Filter `status=waiting` Zeile 137;
`last_deploys` und laufende Runs tragen **kein** STALE). Konsequenz: ein *laufender* 12h-**Batch**
ist `in_progress` und wird heute **nie** fälschlich als STALE markiert — der „Fehlalarm für 12h-Batch"
tritt in der aktuellen Stufe A **nicht** auf. Ein wartender *Approval* bei 6h+ ist zudem
unabhängig von der Job-Klasse legitim hinweiswürdig.

**Wo online/batch tatsächlich beißt (vorausschauend, Befund B-6):** Die Trennung wird erst
relevant, sobald das Board **(a)** *laufende* Runs zeigt (dann braucht ein Langläufer eine
klassen-abhängige „hängt"-Schwelle, sonst wird der 12h-Batch rot) **oder (b)** die Approval-STALE-
Schwelle nach dem *blockierten Ziel* differenziert — ein Approval vor einem online-Deploy ist
dringender (Minuten) als eins vor einem Nacht-Batch (Stunden). Beides ist heute nicht gebaut;
B-6 ist damit eine **latente** Design-Anforderung für die Board-Erweiterung, kein Bug im Ist-Stand.

**Klassifikationsquelle (Design-Input, H — zu entscheiden):** Woran erkennt das Board die Klasse?
Optionen: (i) Workflow-/Job-Namenskonvention (`*-batch`, `*-online`), (ii) eine explizite Kennung
im Workflow (Label/Input/Env), (iii) eine zentrale Registry (repos.json/ports.yaml-Analogon).
Ohne verlässliche Quelle bleibt die Schwelle global — deshalb ist die Quelle Teil der Entscheidung,
nicht eine Implementierungsnebensache.

## 6 Adversariale Analyse

### 6.1 Konfliktmatrix (drei unabhängige, sich gegenseitig blinde Agenten)

| Dissens | Position A | Position B | Auflösung |
|---------|-----------|-----------|-----------|
| **Hat Stufe B einzigartigen Nutzen?** | Steelman: ja — Batch-Approve blockierter Ketten, das kann sonst nichts | Advocatus Diabolus: nein — spart nur Sekunden; In-App-Badge+Deep-Link (B-lite) dominiert für den Incident-Modus | **Teilweise beide:** der *Batch*-Nutzen (Stufe C) ist real und einzigartig; der *Einzel*-One-Click-Nutzen ist marginal. → B nur als Vehikel für C rechtfertigbar, nicht für sich. |
| **Kann eine GitHub App approven?** | Maintainer-2028: GitHub App = beste Token-Option (auto-rotiert, kein PAT-Waise) | Advocatus Diabolus: GitHub Apps können i.d.R. **nicht** als Environment-Required-Reviewer gelistet werden → `pending_deployments`-Approve schlägt fehl → erzwingt menschen-eigenen PAT | **UNGEKLÄRT — H, entscheidungsblockierend.** Billigster Check: §13-PRE-1. Kippt die gesamte Token-Empfehlung. |
| **Attribution** | — | Diabolus + Maintainer einig: der API-Approver ist der **Token**, nicht der Board-Klicker → GitHub-Audit-Log liest „Token-Owner approved" | **Konsens:** Segregation-of-Duties wird zum Theater, wenn der handelnde Mensch nicht separat erfasst wird. Harte Vorbedingung §13-PRE-3. |

### 6.2 Advocatus-Diabolus-Pflichtfragen

- **Doppelquelle / zweite Wahrheit:** Der Board-Approve-Pfad läuft heute auf `LoginRequiredMixin`
  (C4) — der *effektive* Approver-Kreis würde damit „jeder, der sich in devhub einloggen kann",
  **nicht** die benannte Environment-Reviewer-Liste. Das superseded still GitHubs Reviewer-ACL
  durch eine schwächere, parallele ACL ohne Audit-Parität. → **Governance-Fork.**
- **„Sichtbar machen" < „verhindern"?** Hier ist *sichtbar machen* (Stufe A/B-lite) **stärker**
  als der Handlungs-Shortcut: der Incident war Unsichtbarkeit, nicht Klick-Distanz.
- **Manuelle Pflicht ohne Enforcement:** Attribution des Menschen (PRE-3) ist eine Pflicht, die
  nur greift, wenn das Board sie erzwingt (Log-Event mit `actor`) — sonst ist sie Deklaration.
- **Blast-Radius:** Ein geleakter org-weiter Deploy-Approve-Token = „approve anything, anywhere,
  in zwei Orgs" → RCE-äquivalent in Prod. Auf den **geteilten** `GITHUB_TOKEN` aufzusatteln (C2/C3)
  würde jeden bestehenden Konsumenten (auch SSH/Ops) mit Deploy-Approve-Macht ausstatten. → **Nie.**

## 7 Deep-Dive — Token-Optionen für Stufe B

| Opt | Ansatz | Blast-Radius | Rotation/Owner | Attribution | Bewertung |
|-----|--------|--------------|----------------|-------------|-----------|
| (a) | `GITHUB_TOKEN` um `deployments:write` erweitern | **maximal** — alle bestehenden Konsumenten erben Approve-Macht | Owner unklar, wird selten rotiert | Token-Owner | ❌ **verworfen** (Konsens aller drei Lenses) |
| (b) | Separater, dedizierter minimal-scoped Approve-PAT | eng, aber menschen-eigen | PAT-Ablauf bricht Board still; „PAT-Waise" wenn Person geht | menschen-eigen (kann Reviewer sein ✓) | 🟡 Fallback, wenn (c) technisch scheitert |
| (c) | **GitHub App** (deployments-scoped, über beide Orgs installiert) | eng, auto-rotierte Kurzzeit-Tokens | kein Waise, Private-Key ist selbst Rotations-Objekt | **evtl. NICHT als Reviewer möglich** (H, PRE-1) | 🟢 bevorzugt **falls PRE-1 grün**, sonst tot für den Approve-Akt |
| (d) | Kein Schreib-Scope — In-App-Badge auf devhub + Deep-Link (B-lite) | **null** | — | GitHub-nativ (Mensch klickt) | ✅ **empfohlener Ist-Weg** |

**Cache-Konsequenz für B-lite:** Das Nav-Badge braucht **keinen** Dedup-Speicher (es zeigt einen
Live-Zähler, verschickt nichts). Es liest den bestehenden 120s-Board-Cache-Eintrag und rendert die
Anzahl STALE-Approvals — pro Request O(1), kein Extra-GitHub-Call. Der per-Worker-`LocMemCache` (§3)
ist dafür ausreichend (jeder Worker hält seinen eigenen 120s-Snapshot; Badge-Zähler darf leicht
divergieren, das ist unkritisch). **Ein `NotifiedApproval`-Modell/geteilter Cache ist nur nötig,
falls je ein *externer* Push dazukäme — bewusst nicht Teil dieses Konzepts.**

## 8 Alternativen

1. **Nichts weiter bauen (Stufe A genügt).** Ehrlich tragbar — A löst den Incident. Schwäche:
   rein Pull; niemand schaut proaktiv, der nächste 3-Tage-Stau bleibt möglich, bis jemand das
   Board zufällig öffnet. B-lite schließt genau diese Restlücke billig.
2. **Direkt Stufe B (One-Click) bauen.** Verworfen: löst den Incident nicht, öffnet den
   Governance-Fork (§6.2) und den org-weiten Blast-Radius, bevor PRE-1..3 geklärt sind.

## 9 Out-of-the-Box

- **STALE-Eskalation im Board statt Approve:** Das Badge könnte ab >24h die Farbe/Dringlichkeit
  eskalieren und optional den Run **auto-canceln** (mit Deploy-Scope, aber *cancel* statt *approve*
  — kein SoD-Bruch, da cancel keine Freigabe ist). Entschärft den Concurrency-Stau ohne
  Approve-Token, alles innerhalb devhub. (Backlog.)
- **Reviewer-Parität statt paralleler ACL:** Statt eigener Board-ACL die Environment-Reviewer-Liste
  *lesen* und den Board-Button nur denen zeigen, die auch GitHub-Reviewer sind — schließt den
  Governance-Fork by design. Vorbedingung für ein etwaiges Stufe B.

## 10 Befunde

| ID | Befund | Schwere | Beleg |
|----|--------|---------|-------|
| B-1 | Stufe-A-Board läuft auf `LoginRequiredMixin`, nicht staff-restricted — für eine reine Lese-Ansicht vertretbar, für Stufe B ein Governance-Fork | mittel (hoch bei B) | C4 |
| B-2 | Ein geteilter `GITHUB_TOKEN` für Ops + Approvals — Scope-Erweiterung würde Blast-Radius org-weit vergrößern | hoch (nur bei Opt a) | C2/C3 |
| B-3 | GitHub-App-als-Reviewer ist ungeklärt und kippt die Token-Empfehlung | hoch | H (PRE-1) |
| B-4 | Attribution kollabiert auf Token-Owner ohne separates `actor`-Feld | hoch (nur bei B) | Konsens 6.1 |
| B-5 | KONZ-014 war im Code als „in Arbeit" referenziert, aber nie geschrieben → dieses Doc schließt die Artefakt-Lücke | niedrig | C1, C7 |
| B-6 | Globale 6h-STALE-Schwelle ist **latent** klassen-blind: heute unkritisch (STALE nur auf `status=waiting`, verifiziert Z.156/137 — laufende Batches nie STALE), wird aber zum Defekt, sobald das Board laufende Runs zeigt oder Approval-Dringlichkeit nach Ziel differenziert (§5.1) | niedrig (latent) | C1 (`STALE_HOURS=6`, Z.156/137) |

## 11 Top-5-Risiken

| # | Risiko | Wahrsch. | Impact | Gegenmaßnahme |
|---|--------|----------|--------|---------------|
| R1 | Org-weiter Approve-Token leakt → Prod-RCE in zwei Orgs | niedrig | kritisch | Stufe B gar nicht ohne PRE-1..3; nie Opt (a); minimal-scoped Identität |
| R2 | SoD-Theater: Audit-Log schreibt Token-Owner statt echtem Freigeber | hoch (bei B) | hoch | PRE-3: `actor`-Feld erzwingen; Reviewer-Paritäts-Filter (§9) |
| R3 | Board wird De-facto-Pflichtpfad; fällt es aus (Token abgelaufen/App-Key), ist Prod-Deploy blockiert | mittel | hoch | Deep-Link-Fallback nie entfernen; Kill-Gate misst Nutzung |
| R4 | GitHub ändert `pending_deployments`/Reviewer-Semantik → Board approved, was GitHub ablehnen würde (oder umgekehrt) | niedrig | mittel | Vertrag dünn halten; Fehler sichtbar rendern statt schlucken (anders als Lese-Pfad) |
| R5 | Nav-Badge auf jeder devhub-Seite feuert pro Request einen GitHub-Call → Rate-Limit/Latenz | mittel (bei naiver Impl) | mittel | Badge liest **nur** den bestehenden 120s-Board-Cache, nie direkt die API (§7) |

## 12 Empfehlungen (konkret)

- **REC-1 (bauen):** Stufe B-lite in `dev-hub/apps/operations` — **In-App-Sichtbarkeits-Eskalation
  auf devhub, keine externen Kanäle.** Konkret: (a) globales Nav-Badge in `templates/base.html`
  (neben dem bestehenden „Approvals"-Link, C4/C5), das die Anzahl STALE-`waiting`-Approvals aus dem
  120s-Board-Cache liest und rot rendert wenn >0; (b) eine Hero-Card im Operations-Dashboard
  (`operations/dashboard.html`) mit derselben Zahl + Direktlink aufs Board. Neuer Helper
  `get_stale_count()` in `services_approvals.py` (liest denselben Cache-Eintrag, kein Extra-Call).
  **Null Schreib-Scope, kein neues Modell, kein externer Push.**
- **REC-2 (härten, unabhängig von B):** `ApprovalsBoardView` von `LoginRequiredMixin` auf das
  N8b-Staff-Pattern (dev-hub PR #109, `StaffRequiredMixin`) heben — die Ops-Ansicht ist kein
  Allerwelts-Login-Inhalt.
- **REC-3 (nicht bauen, gaten):** Stufe B bleibt gesperrt bis PRE-1..3 (§13) grün. Wenn gebaut:
  Opt (c)/(b), **nie** (a); `actor`-Attribution Pflicht; Reviewer-Paritäts-Filter; dedizierter
  org-weiter ADR für den Token (adr_threshold).
- **REC-4 (Doc-Hygiene):** Nach Merge dieses Konzepts die Docstring-Referenz in
  `services_approvals.py` von „(KONZ-platform-014, in Arbeit)" auf den finalen Stand ziehen.
- **REC-5 (klassen-bewusste STALE-Schwelle, B-6 — bedingt/vorausschauend):** Erst nötig, wenn das
  Board um *laufende* Runs erweitert wird oder Approval-Dringlichkeit nach Ziel differenzieren soll
  (nicht für das Ist-Badge, §13). Dann `STALE_HOURS` von einer Konstante auf eine **klassen-abhängige**
  Schwelle heben (online: Minuten; batch: > erwartete Laufzeit). Voraussetzung ist die
  Klassifikationsquelle (§5.1) — Owner-Entscheidung zuerst, dann Impl.

## 13 Entscheidung + Kill-Gate + Vorbedingungen

**Entscheidung:** Stufe B-lite (REC-1) + Härtung (REC-2) freigeben; Stufe B/C **vertagt** hinter
Vorbedingungen. **Reihenfolge:** REC-2 (Staff-Härtung) ist unabhängig und sofort machbar. Das
Nav-Badge (REC-1) darf **sofort** scharf gestellt werden — es zählt STALE-`waiting`-Approvals, und
die sind heute klassen-unabhängig legitim hinweiswürdig (B-6 ist *latent*, kein Live-Fehlalarm,
§5.1). REC-5 (klassen-bewusste Schwelle) wird **erst** nötig, wenn das Board um *laufende* Runs
erweitert wird oder die Approval-Dringlichkeit nach Ziel differenzieren soll — dann muss das Badge
mitziehen, sonst würde es an dem Punkt Rauschen tragen.

**Offene Owner-Entscheidung (gated REC-5):** Klassifikationsquelle online vs batch (§5.1 —
Namenskonvention / Workflow-Kennung / zentrale Registry). Ohne sie bleibt die Schwelle global.

**Vorbedingungen für ein etwaiges Stufe B (alle drei, sonst kein Bau):**
- **PRE-1 (billiger Check, entscheidungsblockierend):** Verifizieren, ob eine **GitHub App** (bzw.
  ihr Installations-Token) `POST .../pending_deployments` als *Approver* ausführen kann, oder ob
  GitHub nur menschen-eigene Reviewer zulässt. Check: GitHub-Docs „Review custom deployment
  protection rules" / API-Test mit einer Test-App an einem Wegwerf-Environment. Ergebnis kippt
  Opt (c)↔(b).
- **PRE-2:** Owner-Entscheidung (Achim), dass ein org-weiter Deploy-Approve-Token über iilgmbh +
  achimdehnert überhaupt gewollt ist (Security-Config-Gate) — plus dedizierter ADR.
- **PRE-3:** Board erfasst pro Approve ein Audit-Event mit dem **echten handelnden Menschen**
  (`actor`), nicht nur dem Token.

**Kill-Gate (messbar, datiert):**
- Stufe B (falls je gebaut): <20% der Prod-Approvals über den Board-Button im ersten vollen
  Quartal **oder** 0 Board-Approves in irgendeinem 60-Tage-Fenster → Rückbau + Token-Widerruf.
- Board gesamt: 0 authentifizierte Views über 30 aufeinanderfolgende Tage → einfrieren.
- **Exception-Budget:** eine einmalige Verlängerung um 30 Tage zulässig, dokumentiert im
  Frontmatter (`review_by` fortschreiben), danach Auto-Sunset (I3).

**Ehrliche Enforcement-Grenze:** `review_by`/`kill_criteria` wirken erst, wenn ein
Lifecycle-Gate sie liest — bis dahin Review-Gate, kein Exit-Code.
