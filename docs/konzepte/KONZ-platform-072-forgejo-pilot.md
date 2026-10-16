---
concept_id: KONZ-platform-072
title: Forgejo als Alternative zu GitHub — Pilot am Spiegel, Umzug erst nach Hürden-Messung
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []   # keine SoR-Spec: Infrastruktur-/Governance-Konzept, kein Fachmodul (ADR-211 greift nicht)
adr_threshold: kein ADR   # Pilot ist lokal, ohne Secrets, rückbaubar; ein Komplettumzug braucht einen org-weiten ADR (siehe §13)
review_by: 2027-01-15
kill_criteria: "Cross-Repo-Reusable aus dem shared-ci-Spiegel läuft bis 2026-11-15 nicht grün ODER < 95 % der main-Commits haben in 14 Tagen einen Forgejo-Lauf zum selben SHA ODER bis 2027-01-15 keine schriftliche Entscheidung (dann gilt Abbruch + Rückbau)"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "lokal: gh repo list je Org (achimdehnert, iilgmbh, ttz-lif, meiki-lra, iilsandbox)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C2, source_path: "lokal: grep über ~/github/*/.github/workflows/*.y*ml", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C3, source_path: "lokal: grep gh-CLI/api.github.com in tools/, .claude/, dev-hub/apps", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C4, source_path: "iilgmbh/ausschreibungs-hub: .github/workflows/*.yml", commit_or_pr: "lokaler Checkout", opened_in_session: true}
  - {claim_id: C5, source_path: "ttz-lif/ttz-hub: .github/workflows/*.yml (inkl. deploy.yml)", commit_or_pr: "lokaler Checkout", opened_in_session: true}
  - {claim_id: C6, source_path: docs/adr/archive/ADR-111-private-package-distribution.md, commit_or_pr: e8f0d08b, opened_in_session: true}
  - {claim_id: C7, source_path: docs/adr/ADR-309-platform-umzug-iilgmbh-dann-privat.md, commit_or_pr: e8f0d08b, opened_in_session: true}
  - {claim_id: C8, source_path: "extern: discuss.python.org/t/new-oidc-providers-for-trusted-publishing/106334", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C9, source_path: "extern: forgejo.org/docs/latest/user/actions/security-openid-connect/", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C10, source_path: "extern: git.frostfs.info/TrueCloudLab/frostfs-testcases/pulls/339 (CODEOWNERS-Semantik)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C11, source_path: "extern: code.forgejo.org/forgejo/runner/issues/63 (Reusable Workflows)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C12, source_path: "extern: forgejo.org/docs/latest/user/actions/reference/ §jobs.<job_id>.uses (Docs v16.0)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C13, source_path: "extern: docs.pypi.org/trusted-publishers/adding-a-publisher/", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C14, source_path: "extern: codeberg.org/forgejo/forgejo options/locale/locale_en-US.ini (pulls.blocked_by_outdated_branch, pulls.auto_merge_when_succeed; kein merge-queue-Schlüssel)", commit_or_pr: "Branch forgejo, 2026-10-15", opened_in_session: true}
  - {claim_id: C15, source_path: "extern: codeberg.org/forgejo/forgejo options/locale/locale_en-US.ini (settings.protect_approvals_whitelist_enabled, settings.block_on_official_review_requests)", commit_or_pr: "Branch forgejo, 2026-10-15", opened_in_session: true}
  - {claim_id: C16, source_path: "lokal: gh repo view iilgmbh/shared-ci (visibility PUBLIC)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C17, source_path: "lokal: grep merge_group über ~/github/*/.github/workflows/*.y*ml (nur platform, platform-pinned)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C18, source_path: "lokal: Forgejo-Serverlog artifactsv4.go 'unknown field \"mime_type\"' + extern: codeberg.org/forgejo/forgejo routers/api/actions/artifact.proto (Branch forgejo, ohne mime_type)", commit_or_pr: "Branch forgejo, 2026-10-15", opened_in_session: true}
  - {claim_id: C19, source_path: "lokal: Pilot-Job env (GITHUB_SERVER_URL vor/nach Runner-Adresswechsel)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C20, source_path: "iilgmbh/ausschreibungs-hub: .github/workflows/ci.yml (on: pull_request, workflow_dispatch)", commit_or_pr: "5e047b2c", opened_in_session: true}
created: 2026-10-15
---

# KONZ-platform-072 — Forgejo als Alternative zu GitHub

> Externe Quellen (C8–C11) stammen aus einer Websuche vom 2026-10-15. Sie gelten als Suchergebnis
> (E4, Confidence mittel) und wurden nicht im Volltext gelesen. Vor jeder Umzugsentscheidung
> werden sie gegen die Primärdoku geprüft (REC-1). Die Prüfung G0 (C12–C17) stützt sich auf die
> Primärdoku und den Forgejo-Quelltext. Sie ersetzt C9–C11 für die Hürdentabelle in §13.

## 1. Executive Summary

**Empfehlung: pilotieren.** Kein Umzug, sondern eine Messung, ob die vier harten Hürden auf
Forgejo fallen. Im Pilot spiegelt ein **lokaler** Forgejo-Stack ohne Secrets die Repos
`ausschreibungs-hub` (bieterpilot) und `shared-ci` von GitHub. Ein eigener Runner fährt die CI
parallel. Deployt wird nicht, GitHub bleibt maßgeblich. Die größte Stärke liegt in der
Datenhoheit: alle Repos ohne US-Anbieter, privat ohne Preisstufe. Das größte Risiko: Die
Governance-Schicht (133 Werkzeugdateien, App `lotse-autor`, Rulesets) hängt an GitHub-Semantik.
Ein halber Zustand mit zwei Wahrheiten wäre schlimmer als jede der beiden Plattformen allein.
Die wichtigste Unsicherheit ist, ob Forgejo Reusable Workflows über Repo-Grenzen hinweg trägt.
Davon hängen 167 Aufrufe ab. Sie ist das erste Gate.

## 2. Scope & Evidenzbasis

**Input:** Owner-Frage vom 2026-10-15, ob Forgejo eine Alternative zu GitHub mit allen Repos,
Orgs und Actions ist. Pilot-Kandidaten des Owners: bieterpilot und die Org ttz-lif.

**Gemessen (C1–C5), Stand 2026-10-15:**

| Größe | Wert |
|---|---:|
| aktive Repos / Orgs | 77 / 5 (achimdehnert 33, iilgmbh 32, meiki-lra 6, iilsandbox 5, ttz-lif 1) |
| Repos mit Workflows (lokal) | 82 |
| Workflow-Dateien auf gehosteten `ubuntu`-Runnern / `self-hosted` | 337 / 31 |
| Aufrufe von `iilgmbh/shared-ci`-Reusables | 167 |
| Workflows mit `id-token: write` / mit `pypa/gh-action-pypi-publish` | 28 / 29 |
| `workflow_call` / `actions/create-github-app-token` / `merge_group` | 59 / 6 / 4 |
| Dependabot / Renovate / CODEOWNERS | 30 / 25 / 12 |
| Werkzeugdateien mit `gh`-CLI oder `api.github.com` | 133 |

**Extern (C8–C11):** Laut einem Thread im Python-Forum (C8) erkennt PyPI als Trusted Publisher
nur GitHub, GitLab, Google Cloud und ActiveState an. Forgejo Actions gibt seit v15 OIDC-Token aus
(C9). CODEOWNERS fordert in Forgejo Reviews nur an. Blockieren muss die Branch-Protection, und
Merge-Berechtigte können eine Anfrage entfernen (C10). Für Reusables über Repo-Grenzen fand die
Suche keinen Beleg (C11). Für eine Merge Queue in Forgejo ebenfalls nicht.

**Annahmen / nicht prüfbar:** Den Treiber hat der Owner nicht genannt (Q1, §5.2). Kapazität und
Hosting-Ort des Runners sind ungemessen. Wie oft Pull-Mirror-Syncs in Forgejo Actions auslösen,
ist ungeprüft (H).

**Bestehender Mechanismus geprüft:** Zu Forgejo oder Gitea gibt es im Repo nur ADR-111 Z. 78 (C6).
Dort ist Gitea als **Paket-Registry** verworfen, eine Forge wurde nicht bewertet. Kein Werkzeug,
kein Host, kein offener PR zum Thema.

## 3. Infrastruktur-Fit

| Baustein | Relevant? | Wiederverwenden | Erweitern | Risiko | Kommentar |
|---|---:|---|---|---|---|
| ADR-211 / I1 Spec-first / Klickdummy, F11/F17/F18/F19 | nein | — | — | — | kein Fachmodul, keine Spec |
| I2 Prod-Sicherheit | ja | Pilot ohne Secrets, ohne Deploy | — | mittel | ttz-hub `deploy.yml` enthält `appleboy/ssh-action` mit Prod-Secret (C5) und darf nie gespiegelt laufen |
| I3 Off-Ramp + TTL | ja | `review_by`, Kill-Gate | Rückbau-Runbook | mittel | Zwischenzustand ist das Hauptrisiko (M28) |
| ADR-308 Sandbox-Werkstatt (iilsandbox) | ja | Isolationsmuster | Forgejo-Org als Sandbox | niedrig | keine Außenwirkung |
| ADR-309 platform privat | indirekt | — | — | — | löst das Sichtbarkeitsproblem schon auf GitHub. Kein Argument für Forgejo |
| `iilgmbh/shared-ci` | ja | Spiegel + Tag-Pin | — | hoch | 167 Aufrufe, Gate G1 |
| Renovate | ja | 25 Configs laufen weiter | Forgejo-Plattform-Modus | niedrig | Ersatz für Dependabot |
| `adr-threshold` | ja | — | — | — | Pilot kein ADR, Umzug org-weiter ADR |

## 4. Steelman

Heute liegen alle 77 Repos bei einem US-Anbieter. Das gilt auch für die 6 Repos des
Landratsamt-Projekts. Eine eigene Instanz holt Code, CI-Logs und Artefakte unter eigene
Kontrolle. Der Umbau hat schon begonnen: 31 Workflows laufen auf eigenen Runnern. Die CI-Logik
ist in `shared-ci` gebündelt. Wird es einmal portiert, folgen die 167 Aufrufer weitgehend mit (H).
Forgejo stellt seit v15 OIDC-Token aus (C9). Für PyPI fehlt also die Anerkennung, nicht die
Technik, und die 28 Veröffentlichungs-Workflows könnten übergangsweise auf GitHub bleiben.
Ersetzt eine Forge-neutrale Zwischenschicht die 133 `gh`-Aufrufe, sinkt die Abhängigkeit vom
Anbieter dauerhaft. Das lohnt sich auch dann, wenn der Umzug nie kommt.

## 5. Konzeptdefinition

**5.1 Kernthese.** Dieses Konzept sagt: *Forgejo ersetzt GitHub erst, wenn ein Pilot ohne
Secrets mindestens drei der vier harten Hürden mit Beleg genommen hat. Bis dahin bleibt GitHub
die einzige Wahrheit.*

**5.2 Problem.**
- *Beobachtung:* Repos, CI, Governance und Agenten-Werkzeuge hängen vollständig an GitHub (C1–C3).
- *Interpretation:* Ein Wechsel ist nicht an den Repos teuer, die Forgejo importiert. Teuer ist die
  Automatisierungsschicht darüber.
- *Hypothese:* Der Treiber der Frage ist Datenhoheit, der Projekte mit Behörden-Bezug wegen.
- *Offene Frage Q1:* Wäre der Treiber Kosten oder die Sichtbarkeit von platform, lösen ADR-309
  und der Bezahlplan das billiger. Der Pilot misst Machbarkeit, nicht Nutzen.

**5.3 Zielbild.** Am Gate steht eine Tabelle mit vier Hürden, je mit Beleg „fällt / fällt nicht“.
Die Umzugsfrage wird damit eine Rechenaufgabe statt eine Meinungsfrage.

**5.4 Nicht-Ziele.** Kein Deploy von Forgejo. Kein Issue- oder PR-Betrieb auf Forgejo. Kein
Pflicht-Check aus Forgejo-Läufen. Keine Umstellung von Werkzeugen. Keine Repos aus `meiki-lra`
oder `ttz-lif`. Kein öffentlich erreichbarer Host.

**5.5 Artefakte**

| Artefakt | Neu/Geändert | Owner | Normativ? | Generiert? | Lebenszyklus | Risiko |
|---|---|---|---:|---:|---|---|
| dieses Konzept | neu | Achim Dehnert | ja | nein | bis Gate 2027-01-15 | Verwaisung (M28) |
| lokaler Forgejo-Stack (Compose, Daten außerhalb des Repos) | neu | Achim Dehnert | nein | nein | Rückbau am Gate | Patchstand |
| Pull-Spiegel `shared-ci` (öffentlich, ohne Token) | neu | Achim Dehnert | nein | ja | Rückbau am Gate | — |
| Push-Abgleich `ausschreibungs-hub` (Host-Cron, 10 min, FJ8) | neu | Achim Dehnert | nein | ja | Rückbau am Gate | Cron läuft still nicht mehr |
| Messprotokoll (Hürdentabelle, SHA-Abdeckung) | neu | Achim Dehnert | ja | teils | bis Gate | — |

**5.7 Prozessmodell.** `idea` (dieses Doc) → `pilot` (Gates G0–G2, §5.9) → Gate 2027-01-15:
Abbruch + Rückbau **oder** org-weiter ADR für Stufe 2. Ohne Entscheidung gilt Abbruch.

**5.8 Enforcement-Modell**

| Regel | Level | Mechanismus | Owner | Ausnahme? | Ablaufdatum nötig? |
|---|---|---|---|---:|---:|
| keine Secrets im Pilot-Stack | Runtime-Guard | Stack startet ohne Secrets-Mount; Forgejo hält kein GitHub-Token, der Host liest GitHub mit seinem vorhandenen Zugang | Owner | nein | nein |
| Spiegel ist schreibgeschützt | Runtime-Guard | `shared-ci`: Pull-Mirror. `ausschreibungs-hub`: Branch-Schutz auf `main`, nur das Abgleich-Konto schreibt, nur Fast-Forward | Owner | nein | nein |
| `deploy.yml` läuft nie | Runtime-Guard | Der Abgleich legt `.forgejo/workflows/ci.yml` an. Damit liest Forgejo `.github/workflows` nicht mehr. Belegt im ersten Lauf: nur `ci.yml` wurde ausgelöst | Owner | nein | nein |
| GitHub bleibt maßgeblich | Governance | Forgejo-Läufe sind nie Required Check; keine Issues/PRs auf Forgejo | Owner | nein | Gate |
| kein öffentlicher Endpunkt | Runtime-Guard | Bindung an localhost | Owner | nein | nein |
| Gate-Entscheidung | Review-Gate | `review_by` + Kill-Kriterium „keine Entscheidung = Abbruch“ | Owner | nein | 2027-01-15 |

Ehrliche Grenze: Ein Lifecycle-Gate, das `review_by` liest, fehlt. Die Frist wirkt nur über die
Gate-Zeile im Handover, ist also ein Review-Gate und kein Exit-Code.

**5.9 Minimal Viable Concept**

- **G0 – Schreibtischprüfung, 1 h:** Primärdoku zu Forgejo Actions (Reusables über Repo-Grenzen,
  Mirror-Trigger, Merge Queue) und die Trusted-Publisher-Liste von PyPI lesen. Ergebnis als
  Zeilen in der Hürdentabelle. Fällt H1 laut Doku sicher nicht, endet das Konzept hier.
- **G1 – Reusables über Repo-Grenzen, bis 2026-11-15:** Der lokale Forgejo-Stack spiegelt
  `shared-ci` und `ausschreibungs-hub`. `ci.yml` von ausschreibungs-hub läuft auf dem eigenen
  Runner und ruft `_ci-python.yml` tag-gepinnt aus dem shared-ci-Spiegel auf. Erfolg: grüner Lauf
  mit höchstens 10 geänderten Zeilen in der Workflow-Kopie. `deploy.yml` läuft nicht, weil es
  keine Secrets gibt.
- **G2 – Parität, 14 Tage:** Mindestens 95 % der main-Commits haben einen Forgejo-Lauf zum selben
  SHA, und das Ergebnis stimmt mit GitHub überein. Dazu der Testfall: Ein Merge ohne
  Code-Owner-Approve wird abgewiesen (Bot-Konto + Branch-Protection).
  **Messverfahren (FJ8, Owner-Wort 2026-10-15 „FJ8 go“):** Ein Host-Cron holt GitHub-`main` alle
  10 Minuten und legt darauf einen Overlay-Commit `fj-overlay: <GitHub-SHA>`. Erster Elternteil ist
  der GitHub-SHA, zweiter der alte Forgejo-Stand, also ein Fast-Forward. Der Overlay fügt nur
  `.forgejo/workflows/ci.yml` hinzu: `ci.yml` aus GitHub, mit Push-Trigger und Kompat-Aufruf.
  Jeder Push löst damit einen Lauf aus. Gezählt wird „GitHub-SHA hat einen Forgejo-Lauf“ über den
  ersten Elternteil. Der Ersatz für einen Pull-Spiegel war nötig, weil ein privates Repo sonst ein
  GitHub-Token in Forgejo braucht und `ci.yml` keinen Push-Trigger hat (C20).
- **Bewusst nicht drin:** Deploy, PyPI-Veröffentlichung, Werkzeug-Umbau, Renovate auf Forgejo.
- **Rückbau, unter 1 h:** Cron-Zeile entfernen, Compose-Stack und Datenvolumen löschen. Ein
  Token muss nicht widerrufen werden. Das Repo bleibt unberührt, weil der Stack außerhalb liegt.

**5.10 Full Concept, nur nach Gate.** Stufe 2: `shared-ci` wird Forge-neutral.
Werkzeug-Zwischenschicht für `gh`. Bot-Konto statt App. Renovate auf Forgejo. Eigener
Runner-Pool. Veröffentlichung auf PyPI per Token oder bleibt auf GitHub. Stufe 3: Umzug je Org,
`iilsandbox` zuerst, `meiki-lra` und `ttz-lif` zuletzt und nur mit Freigabe der jeweiligen
Auftraggeber.

## 6. Adversariale Analyse

Drei getrennte Gegenprüfer liefen am 2026-10-15 in eigenem Kontext: Steelman, Advocatus
Diabolus und Maintainer-2028.

**😈 Advocatus Diabolus.** Die fünf stärksten Gegenargumente:
(1) Reusables über Repo-Grenzen sind unbelegt, und 167 Aufrufe hängen daran. *Neuer Failure-Mode.*
(2) Fällt PyPI Trusted Publishing weg, kehren 28 Workflows zu langlebigen Tokens zurück. Das ist
ein Security-Rückschritt. *Neuer Failure-Mode.*
(3) Der Governance-Kern hat kein belegtes Gegenstück: das Ruleset mit `lotse-autor` und
Owner-Approve, die Merge Queue und ein blockierender Code-Owner-Review. *Governance-Lücke.*
(4) Der Pilot misst womöglich nur, ob der Spiegel auslöst, nicht ob die CI gleichwertig ist (H).
(5) Parallelbetrieb verdoppelt die Hook-Pflege. *Operationalisierungsrisiko.*
Dazu zwei Punkte: „GitHub führend“ setzt sich nicht von selbst durch. Und ein Spiegel mit eigenen
Secrets und Runner ist eine eigene Grenze, kein passiver Spiegel. Beides ist in §5.8 als
Runtime-Guard umgesetzt: keine Secrets, Pull-Mirror, nur localhost.

**🔮 Maintainer 2028.** Verrotten wird der Zwischenzustand: driftende CI-Kopien, deren rote Läufe
ans Ignorieren gewöhnen. Ein abgelaufenes Spiegel-Token, nach dem Forgejo alten Code als aktuell
zeigt. Forgejo und Runner mehrere Major-Versionen zurück. Ein nie geprobter Restore. Löschen
würde er alles, was nach dem Gate ohne Entscheidung weiterläuft. Daraus wurden die Regeln
„keine Entscheidung = Abbruch“, „ein Pilot-Repo bis zum Gate“, Token höchstens 90 Tage und ein
Rückbau-Runbook ab Tag 1.

**Konfliktmatrix (Synthese)**

| Thema | Steelman | Diabolus | Maintainer-2028 | Auflösung |
|---|---|---|---|---|
| Pilot-Repo | ausschreibungs-hub, misst die tragenden Bausteine | ttz-hub beweist zu wenig, ausschreibungs-hub hat Prod-Secrets | ttz-hub hinterlässt weniger Altlast | **ausschreibungs-hub + shared-ci als Spiegel ohne Secrets.** Das misst H1 und vermeidet das Prod-Risiko. ttz-hub verworfen |
| Deploy im Pilot | 5 Deploys von Forgejo als Beleg | „kein Deploy“ nur behauptet | — | kein Deploy. Erzwungen dadurch, dass es keine Secrets gibt. Deploy erst in Stufe 2 |
| Laufzeit | — | 14-Tage-Paritätsmessung | Gate 2027-04-15 | Gate 2027-01-15 (90 Tage, Template-Standard). G1 schon am 2026-11-15 |
| Umzugsschwelle | 3 Kriterien belegen die Pro-Seite | 5 Kill-Kriterien | ≥ 3 von 4 Hürden | ≥ 3 von 4 Hürden (§13) |
| Hosting | eigener Host (Hoheit) | öffentliche Angriffsfläche | Patch-Fristen | Pilot nur lokal. Ein Host erst in Stufe 2 |

## 7. Deep-Dive

1. **SSoT/Drift:** Maßgeblich bleibt GitHub. Forgejo-Läufe sind abgeleitete Messdaten. Drift
   zeigt sich als SHA-Lücke (G2).
2. **Boundary:** Der Pilot setzt eine neue, lokale Grenze ohne Außenwirkung. Ein Umzug wäre eine
   org-weite Grenze und damit ADR-pflichtig.
3. **Governance:** Ausnahmen gibt es keine. Jede zweite Pilot-Repo-Aufnahme ist Owner-Wort.
4. **Security:** Kein neuer Secret. Forgejo hält kein GitHub-Token (FJ8). Gelesen wird mit dem
   vorhandenen Zugang des Hosts.
   Kein Prod-Secret, kein offener Port.
5. **Datenschutz:** Gespiegelt werden nur iilgmbh-Repos ohne Personendaten (H, Stichprobe vor G1).
   Keine Repos aus `meiki-lra` oder `ttz-lif`.
6. **Testbarkeit:** Ein roter Lauf ist ein Befund, wenn GitHub grün ist. Ein legitimer Override
   ist eine dokumentierte Workflow-Anpassung (≤ 10 Zeilen).
7. **CI/CD & Betrieb:** Forgejo-Läufe sind rein informativ. Der Rückbau ist der Rollback.
8. **Migration:** Rein gespiegelt. Kein Repo zieht im Pilot um.
9. **Messbarkeit:** echte Metriken sind SHA-Abdeckung, Ergebnis-Übereinstimmung, geänderte
   Workflow-Zeilen je Repo und Hürden gefallen/nicht gefallen. Die Repo-Zahl im Spiegel wäre
   eine Vanity-Metrik.

## 8. Alternativen

| Alternative | Idee | einfacher | gefährlicher | Urteil |
|---|---|---|---|---|
| A1 radikal kleiner | nur Backup-Spiegel aller Repos nach Forgejo, ohne CI | ja, ohne Runner | nein | als **Nebenprodukt** behalten. Löst die Hoheit über das Backup, nicht über den Betrieb |
| A2 technisch | GitHub Enterprise Server / GitLab self-managed | GitLab: PyPI Trusted Publishing bei self-managed nicht belegt (H) | Lizenz- und Betriebslast | später als Vergleich, falls H3/H4 auf Forgejo scheitern |
| A3 organisatorisch | auf GitHub bleiben. Sichtbarkeit über ADR-309 lösen, Hoheit über den Spiegel A1 | ja | Anbieterbindung bleibt | **Standard bei Kill.** |

## 9. Out-of-the-Box

| Ansatz | Vorteil | Nachteil | Urteil |
|---|---|---|---|
| Forge-neutrale `gh`-Zwischenschicht zuerst | lohnt sich auch ohne Umzug | Arbeit ohne sichtbaren Nutzen | in Stufe 2, nicht im Pilot |
| Codeberg statt Eigenbetrieb | kein Betrieb | Actions dort nur eingeschränkt gehostet (C8), fremde Infrastruktur | verworfen |
| Shadow-Mode statt Pilot-Repo | misst alle Repos passiv | 77 Spiegel, Altlast | verworfen (M28) |
| Hybrid dauerhaft | Veröffentlichung + Governance auf GitHub, Code-Hoheit auf Forgejo | zwei Wahrheiten | nur als Stufe-2-Option, wenn H2 nicht fällt |

## 10. Befunde

| ID | Rolle | Kategorie | Befund | Evidenz | Schweregrad | Confidence | Teil |
|---|---|---|---|---|---|---|---|
| PRO-1 | Steelman | Hoheit | Alle 77 Repos liegen bei einem Anbieter, eigene Runner gibt es schon für 31 Workflows | C1, C2 | positiv | hoch | Ziel |
| AD-1 | Diabolus | ARCH | 167 Aufrufe hängen an Reusables über Repo-Grenzen, ein Beleg für Forgejo fehlt | C2, C11 | hoch | mittel | G1 |
| AD-2 | Diabolus | SEC | 28 Workflows verlieren PyPI Trusted Publishing | C2, C8 | hoch | mittel | Stufe 2 |
| AD-3 | Diabolus | GOV | Code-Owner-Review in Forgejo nur anfordernd, Anfrage entfernbar | C10 | hoch | mittel | G2 |
| AD-4 | Diabolus | MIG | 133 Werkzeugdateien sprechen GitHub-API | C3 | mittel | hoch | Stufe 2 |
| AD-5 | Diabolus | SEC | ttz-hub-Deploy enthält Prod-SSH-Secret | C5 | mittel | hoch | Pilotwahl |
| M28-1 | Maintainer | OPS | Zwischenzustand ohne Entscheidung verrottet | H | hoch | mittel | §13 |
| DOC-1 | Synthese | Präzedenz | ADR-111 verwarf Gitea nur als Registry, nicht als Forge | C6 | niedrig | hoch | §2 |

## 11. Top-5-Risiken

1. **Zwei Wahrheiten** (M28-1): Jemand kommentiert auf Forgejo, und der Status pro Commit
   zerfällt. *Fix:* Issues und PRs im Forgejo-Repo abschalten. *Restunsicherheit:* niedrig.
2. **H1 fällt nicht** (AD-1): Dann ist ein Umzug ein Neubau von shared-ci. *Fix:* G1 als erstes
   Gate mit Datum. *Restunsicherheit:* hoch, genau dafür ist der Pilot da.
3. **Security-Rückschritt PyPI** (AD-2): *Fix:* Die Veröffentlichung bleibt auf GitHub, bis PyPI
   Forgejo anerkennt. *Restunsicherheit:* hängt von PyPI ab.
4. **Governance-Lücke** (AD-3): *Fix:* Testfall in G2. Scheitert er, ist ein Umzug der
   Governance-Repos (platform, Liste L) ausgeschlossen.
5. **Token-Ablauf / Patchstand** (M28): *Fix:* Seit FJ8 gibt es kein Token mehr. An seine Stelle
   tritt ein still stehender Abgleich. Den zeigt das Messlog als Lücke (G2). Der lokale Stack ohne
   Port senkt den Patch-Druck.

## 12. Empfehlungen

| REC | Bezug | Änderung | Aufwand | Verifikation / Akzeptanz |
|---|---|---|---|---|
| REC-1 | AD-1, AD-2, AD-3 | G0: Hürdentabelle H1–H4 in §13 aus der Primärdoku füllen | S | jede Zeile mit URL der Primärdoku |
| REC-2 | AD-1, AD-5 | G1: lokaler Compose-Stack, Pull-Spiegel `shared-ci` + `ausschreibungs-hub`, Runner, `ci.yml`-Lauf | M | grüner Lauf, Diff ≤ 10 Zeilen |
| REC-3 | AD-3 | G2: Bot-Konto + Branch-Protection, Testfall „Merge ohne Approve“ | S | Merge technisch abgewiesen |
| REC-4 | M28-1 | Gate-Zeile im Handover mit Datum 2027-01-15 und Token-Ablauf | S | Zeile sichtbar im Session-Start |
| REC-5 | AD-4 | erst nach dem Gate: `gh`-Aufrufe zählen und nach Ersetzbarkeit klassifizieren | M | Tabelle je Datei |

## 13. Entscheidung + Kill-Gate + 30/60/90

**Empfehlung: pilotieren.** Begründung: Die Frage lässt sich nur mit G1 beantworten, und G1
kostet wenig, solange der Stack lokal und ohne Secrets läuft. Stärke: rückbaubar in unter
einer Stunde. Schwäche: Die Hürden H2 (PyPI) und H3 (Merge Queue) misst der Pilot nicht, sie
klärt nur G0 auf dem Papier. Sofortmaßnahme: G0. Unsicherheit: der Treiber (Q1). Threshold:
Für den Pilot ist kein ADR nötig. Ein Umzug ab Stufe 2 braucht einen org-weiten ADR.

**Umzugsschwelle:** Ein Komplettumzug kommt nur infrage, wenn mindestens 3 der 4 Hürden mit
Beleg fallen:

| Hürde | Frage | Status | Beleg |
|---|---|---|---|
| H1 | Reusables über Repo-Grenzen laufen tag-gepinnt | **fällt mit Auflage** (G1 gemessen, Owner-Wort 2026-10-15 „K1A go“): shared-ci braucht für Forgejo artifact v4 und Forge-neutrale Composite-Refs, Kostenposten Stufe 2 | C12: `uses: org/repo/<pfad>@<ref>` ist erlaubt, das Ziel-Repo muss öffentlich sein. shared-ci ist öffentlich (C16) |
| H2 | PyPI erkennt Forgejo als Trusted Publisher an | **fällt nicht** | C13: PyPI kennt nur GitHub Actions, Google Cloud, ActiveState, GitLab CI/CD. Self-managed-Instanzen sind ausgeschlossen |
| H3 | Merge Queue oder gleichwertige Serialisierung | **nur Ersatz** | C14: keine Merge Queue in der Oberfläche. Ersatz: „blockiert, weil veraltet“ plus Auto-Merge nach grünen Checks. Das kostet je PR einen Update-Lauf. Genutzt wird `merge_group` heute nur in platform (C17) |
| H4 | Code-Owner-Review blockiert technisch | laut Doku ja, Testfall G2 offen | C15: Approvals lassen sich auf eine Positivliste beschränken, dazu „Block merge on official review requests“ |

**G0-Ergebnis (2026-10-15):** Höchstens 3 von 4 Hürden fallen, und das nur, wenn der Ersatz für H3
zählt. H2 fällt auf Forgejo nicht. Damit ist ein Komplettumzug nur als Hybrid denkbar, bei dem die
PyPI-Veröffentlichung auf GitHub bleibt (§9 „Hybrid dauerhaft“). H1 fällt laut Doku. Das Konzept
endet also nicht nach G0, G1 bleibt sinnvoll.

**Tiefenvergleich (2026-10-15, [#4023](https://github.com/achimdehnert/platform/issues/4023)):**
[Anhang GitHub gegen Forgejo](anhaenge/KONZ-072-vergleich-github-forgejo.md) mit Quellen,
Urteil je Punkt gegen H1–H4 und den Testfragen T1–T16. Der Anhang bewertet H1 strenger mit
„teilweise“, weil der Aufrufer `permissions:` ignoriert, dem Context Schlüssel fehlen und Artefakte
v3 oder einen Fork brauchen. Die Tabelle oben bleibt bis zur Entscheidung des Owners unverändert.

**Kill-Gate (jedes Kriterium stoppt allein):**

| Kriterium | Status | Beleg |
|---|---|---|
| K1: G1 bis 2026-11-15 nicht grün | nicht ausgelöst: G1 grün mit Kompat-Kopie, zählt laut Owner-Wort 2026-10-15 „K1A go“. Bestätigt per Push-Lauf 9/9 im Abgleich (FJ8) | [#4018](https://github.com/achimdehnert/platform/issues/4018#issuecomment-6195829170), C18–C20 |
| K2: SHA-Abdeckung in G2 < 95 % über 14 Tage | offen | — |
| K3: bis 2027-01-15 keine schriftliche Entscheidung → Abbruch + Rückbau | offen | — |
| K4: zwei verpasste Wartungsfristen (Forgejo-Patch ≤ 30 Tage; Token-Rotation entfällt seit FJ8) | offen | — |

**G1-Messung (2026-10-15, Forgejo 16.0.6, Runner 13.2.0):** Ein Lauf mit unverändertem
`shared-ci@v1.1.25` wird auf Forgejo nie grün. Die Tests laufen durch (1097 passed), aber
`upload-artifact` v7 sendet bei `CreateArtifact` das Feld `mime_type`, und Forgejo antwortet mit
HTTP 500, weil es das Feld nicht kennt (C18). Auch `artifact.proto` auf Forgejo-`main` enthält das
Feld nicht. Ein Upgrade hilft also nicht. Mit einer Kopie `shared-ci-kompat@v1.1.25-fj1`, die nur
auf Forgejo liegt und artifact v4.6.2/v4.3.0 statt v7/v8 nutzt (4 Zeilen), lief `ci.yml` vollständig
grün: 9/9 Jobs, Coverage-Gate 85,25 % über hochgeladene und wieder geladene Artefakte. Der Aufrufer
weicht in 1 Zeile ab. Artefakte brauchen damit kein v3, v4 genügt. Drei weitere Befunde:

- Der Runner gibt seine Registrier-Adresse als `GITHUB_SERVER_URL` an die Jobs weiter. Endet sie
  nicht auf `.localhost`, hält `@actions/artifact` die Instanz für GHES und bricht ab (C19).
  Für einen Host in Stufe 2 heißt das: v4-Artefakte gehen nur mit Fork oder Patch.
- Die Composite-Actions in `_ci-python.yml` stehen auf `iilgmbh/shared-ci/…@main` und kommen von
  github.com, nicht aus dem Spiegel. H1 gilt damit nur für den Reusable selbst. Volle Hoheit
  braucht ein Forge-neutrales shared-ci (Stufe 2).
- `ci.yml` in ausschreibungs-hub läuft nur bei `pull_request` und `workflow_dispatch`, nicht bei
  einem Push auf main (C20). G2 kann die Parität deshalb nicht über „Lauf je main-Commit“ messen
  und braucht ein anderes Messverfahren.

**Exception-Budget:** Keines. Ein zweites Pilot-Repo vor dem Gate braucht Owner-Wort mit Datum.

**30/60/90:** 30 Tage (bis 2026-11-15): G0 und G1. 60 Tage: G2-Messung und Testfall H4.
90 Tage (2027-01-15): Hürdentabelle auswerten. Dann folgt ein org-weiter ADR für Stufe 2 oder
Abbruch, Rückbau und A3 mit A1.
