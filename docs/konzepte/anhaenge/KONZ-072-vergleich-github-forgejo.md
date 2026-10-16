# KONZ-platform-072 — Anhang: GitHub gegen voll ausgebautes Forgejo, belegt (2026-10-15)

> Entscheidungsgrundlage zu [KONZ-platform-072](../KONZ-platform-072-forgejo-pilot.md), Auftrag
> [#4023](https://github.com/achimdehnert/platform/issues/4023). Verglichen wird GitHub mit einem
> Forgejo, das voll ausgebaut ist: Actions, Runner, Renovate, Woodpecker, Registry und Mirror.
> Es gibt nur öffentliche Quellen und keine internen Daten. Alle Quellen wurden am **2026-10-15**
> abgerufen, die Kürzel in eckigen Klammern verweisen auf §9.

## 0. Methode und Grenzen

- **Primärquellen im Volltext.** Das sind Herstellerdoku, Quelltext, Issue-Tracker und
  Lizenzdateien. Die Forgejo-Doku hat den Stand v16.0 („Latest v16.0.6“). Die Zitate wurden gegen
  den Doku-Quelltext `codeberg.org/forgejo/docs` geprüft (Commit `6b64d95`, 2026-10-13). Zu
  Optionen, die die Doku nicht beschreibt, ist die Oberflächen-Sprachdatei des Zweigs
  `v16.0/forgejo` die Quelle [F14].
- **„Doku schweigt“** heißt: Die Primärquelle sagt dazu nichts. Solche Punkte werden nicht
  geraten, sondern stehen in §8.
- **Nicht gelesen** ist die Forgejo-Doku v17.0. v17.0 ist laut Releaseplan für 2026-10-15
  vorgesehen, stand am Abruftag aber noch nicht auf der Release-Seite [F29, F31].
- **Urteile** messen jeden Punkt an den Hürden aus KONZ-072 §13:
  - **H1:** Reusables laufen über Repo-Grenzen, tag-gepinnt.
  - **H2:** PyPI erkennt Forgejo als Trusted Publisher an.
  - **H3:** Es gibt eine Merge Queue oder eine gleichwertige Serialisierung.
  - **H4:** Ein Code-Owner-Review blockiert technisch.

  Die Werte sind **ja** (die Hürde fällt laut Quellen), **teilweise** (fällt mit Ersatz oder
  Abstrichen) und **nein** (fällt nicht). Ein **—** heißt, dass der Punkt die Hürde nicht berührt.
  Dafür steht in der letzten Spalte ein Urteil zur Gleichwertigkeit mit GitHub.

## 1. Urteilsmatrix

| Punkt | H1 | H2 | H3 | H4 | gleichwertig zu GitHub |
|---|---|---|---|---|---|
| 2. Actions-Kompatibilität mit Runner und Woodpecker | teilweise | nein | nein | — | teilweise |
| 3. Branch-Regeln und Merge Queue | — | — | teilweise | teilweise | teilweise |
| 4. Security-Scanning | — | — | — | — | teilweise |
| 5. Packages | — | nein | — | — | teilweise |
| 6. Ersatz für Dependabot | — | — | — | — | teilweise |
| 7. Betrieb und Kosten | — | — | — | — | teilweise |

**Kernaussage.** Kein Punkt erreicht volle Gleichwertigkeit. Ein harter Ausschluss ist nur H2. Für
H1, H3 und H4 gibt es laut Doku einen Weg, jeder davon mit Abstrichen, die nur ein Test beziffert
(§8). Gegenüber §13 von KONZ-072 ist H1 hier strenger bewertet, mit „teilweise“ statt „laut Doku
ja“. Die Begründung steht in §2.

## 2. Actions-Kompatibilität mit Runner und Woodpecker

| Aspekt | GitHub | Forgejo | Quelle |
|---|---|---|---|
| Anspruch | Referenz | „designed to be familiar … but it is not designed to be compatible“. Workflows laufen mit „some minimal changes“. Die Liste der Unterschiede ist laut Forgejo „may be incomplete“ | F01 |
| Workflow-Ordner | `.github/workflows` | `.forgejo/workflows`. Fehlt der Ordner, liest Forgejo `.github/workflows` | F04 |
| Trigger | unter anderem `merge_group` und `workflow_run` | dokumentiert sind push, issues, issue_comment, pull_request, pull_request_target, release, schedule, workflow_call und workflow_dispatch. Zu `merge_group` und `workflow_run` schweigt die Doku | F02, G04 |
| Context | `github.*` | `forgejo.*`, dazu `github` als Alias. „Some keys in the `github` context are missing“, welche, sagt die Doku nicht | F01, F02 |
| `permissions:` | steuert den Token | auf Job-Ebene „ignored“. Der Token lässt sich nicht feiner einstellen | F01, G13 |
| OIDC | `permissions: id-token: write` | eigener Schlüssel `enable-openid-connect`, Issuer `<instanz>/api/actions` | F01, F06, G05 |
| Reusables | `jobs.<id>.uses`, auch aus privaten Repos | `owner/repo/path@ref` oder volle URL. „The target repository must be a public repository“. Fremde Instanzen werden nicht expandiert | F02, G06 |
| `concurrency` | Workflow- und Job-Ebene | nur Workflow-Ebene, „best-effort“ | F02 |
| `services` | ja | nur mit dem Docker-Backend, nicht mit LXC | F03 |
| Cache | Dienst von GitHub | liegt beim Runner, „makes no guarantees that a cache will be populated“ | F03, F07 |
| Artefakte | `upload-artifact@v4` | „you must use v3 or patched v4“. Der Spiegel meldet „@v4 will not work from this mirror“. Den gepatchten Fork nennt Forgejo „Temporary fork until v4 supports GHES“ | F03, R01, R02 |
| Herkunft der Actions | github.com | Kurznamen werden mit `DEFAULT_ACTIONS_URL` ergänzt (Standard data.forgejo.org). Empfohlen sind volle URLs und SHA-Pins | F02, F05 |
| Runner | gehostet oder self-hosted | Forgejo Runner v13.2.0 vom 2026-09-18, „Stable“, GPL-3.0-or-later. Backends sind docker, lxc und host | R03, R04, F08 |
| Runner-Sicherheit | — | „Forgejo Runner performs remote code execution“. Im host-Modus gibt es „no isolation at all“. Geladene Images werden „never updated“. Empfohlen ist der ephemeral mode, den Forgejo bei der Registrierung mit `--ephemeral` erzwingt. LXC hat keine Ressourcenlimits | F07, F08, F09, F11 |
| Fork-PRs | Freigabe einstellbar | Die erste Freigabe gilt für alle späteren PRs desselben Autors. Bei `pull_request` gibt es keine Secrets und nur einen Lese-Token | F10, F20 |
| Mirror als Auslöser | — | Der Pull-Mirror-Sync erzeugt im Quelltext ein Push-Ereignis (`SyncPushCommits` → `HookEventPush`). Die Doku schweigt | F25 |
| Woodpecker | — | Forgejo ist eingebaut unterstützt. Die Forge-Matrix nennt Push, Tag, Pull Request und Release, ein Deploy-Ereignis löst Woodpecker selbst aus. Woodpecker hat eine eigene YAML-Syntax („executes commands inside a specified container“) und nennt keine GitHub-Actions-Kompatibilität. Lizenz Apache-2.0, aktuell 3.19.0 vom 2026-10-07 | W01, W02, W03, W04, W05 |

**Urteil.**
- **H1 teilweise.** Reusables über Repo-Grenzen sind dokumentiert und tag-pinnbar, aber nur aus
  öffentlichen Ziel-Repos [F02]. Der Aufrufer hat zudem mehrere bekannte Unterschiede: Er ignoriert
  `permissions:`, dem Context fehlen Schlüssel, und Artefakte brauchen v3 oder einen Fork [F01,
  F03]. Ein Reusable läuft also nicht unverändert, und wie viele Zeilen sich ändern, misst erst G1.
- **H2 nein.** Forgejo hat zwar OIDC, PyPI nimmt diesen Aussteller aber nicht an (§5).
- **H3 nein.** Ein Gegenstück zu `merge_group` ist nicht dokumentiert [F02]. Workflows, die eine
  Merge Queue bedienen, haben auf Forgejo keinen Auslöser.
- **Woodpecker, H1 nein.** Die Syntax ist eine eigene [W03]. Reusables im Sinne von GitHub müssten
  neu gebaut werden. Woodpecker taugt deshalb höchstens als zweite CI und nicht als Ersatz für
  shared-ci.
- **Gleichwertigkeit teilweise.** Die Kernfunktionen sind vorhanden, Forgejo erklärt aber selbst,
  dass es nicht kompatibel ist [F01].

## 3. Branch-Regeln und Merge Queue

| Aspekt | GitHub | Forgejo | Quelle |
|---|---|---|---|
| Pflicht-Approvals | ja | ja, auf eine Positivliste aus Nutzern und Teams beschränkbar | F14, G07 |
| Pflicht-Statuschecks | ja, „strict“ verlangt einen aktuellen Branch | Muster, eine Zeile je Muster. Die Syntax der Muster nennt die Doku nicht. Passt kein Muster, muss der letzte Commit trotzdem grün sein | F14, G07 |
| veralteter Branch | Teil von „strict“ | eigene Option „Block merge if pull request is outdated“ | F14 |
| Code-Owner | Pfadmuster wie in gitignore. Die Merge-Sperre ist optional einschaltbar („require approval from a code owner“) | Datei im Wurzelverzeichnis, in `docs/` oder in `.forgejo/`, Muster als Go-Regex. Laut Doku fordert die Datei nur ein Review **an**. Eine eigene Sperre „Code-Owner-Approval nötig“ nennt die Doku nicht | F13, G08 |
| Merge-Sperre über Review-Anfragen | — | „Block merge on official review requests“ und „Block merge on rejected reviews“ | F14 |
| Admins | Bypass-Listen | Admins sind nur gebunden, wenn „Enforce this rule for repository admins“ gesetzt ist | F14, G10 |
| weitere Optionen | — | signierte Commits, geschützte Dateimuster, Positivlisten für Push und Merge, Verwerfen veralteter Approvals | F14 |
| org-weite Regeln | Rulesets, je nach Plan. Zwei GitHub-Seiten widersprechen sich, ob Team reicht | keine. Branch-Schutz gibt es in der API nur pro Repo | G10, G11, F12, F15 |
| Merge Queue | in öffentlichen Org-Repos, privat nur mit Enterprise Cloud. Braucht `merge_group` | keine. Feature-Wunsch #5102 ist offen. Es gibt Auto-Merge („Auto merge when all checks succeed“) | G09, I01, F14 |
| Automatisierungs-Identität | GitHub App, Installation-Token mit einer Stunde Laufzeit. `GITHUB_TOKEN` ist ein App-Token | kein App-Konzept. „Authorized Integrations“ melden sich per JWT an, aber „authenticated as the user who owns“ sie. OAuth2-Apps haben „administrative rights“, Scopes gibt es nicht. Ob Access-Tokens ablaufen, sagt die Doku nicht. Der Actions-Token hat Schreibrecht im eigenen Repo, und Änderungen damit lösen keinen Workflow aus | G12, G13, F16, F17, F18, F19 |
| API und CLI | REST/GraphQL, `gh` | Swagger-API, als Version ausgewiesen „+gitea-1.22.0“, also Gitea-kompatibel und nicht GitHub-kompatibel. CLI `fj` aus forgejo-contrib | F15, F21, K04 |

**Urteil.**
- **H3 teilweise.** Eine Merge Queue gibt es nicht [I01]. Die Kombination aus „outdated“-Sperre und
  Auto-Merge [F14] serialisiert. Abgeleitet, nicht gemessen: Das kostet je PR einen Update-Lauf
  (T8). Gitea hat den gleichen Stand [I08].
- **H4 teilweise.** Ein technischer Block ist über „Block merge on official review requests“ plus
  Approval-Positivliste möglich [F14]. CODEOWNERS fordert laut Doku aber nur an [F13]. Ob diese
  Anfragen als „official“ zählen, sagt keine Quelle, das klärt der Testfall G2.
- **Gleichwertigkeit teilweise.** Es fehlen org-weite Regeln, eine eigene Bot-Identität und eine
  Merge Queue [F15, G12, I01]. Einzelne Optionen sind dafür als eigener Schalter vorhanden, etwa die
  Sperre für veraltete Branches und geschützte Dateimuster [F14].

## 4. Security-Scanning

| Aspekt | GitHub | Forgejo | Quelle |
|---|---|---|---|
| alle Pläne, auch privat | Dependency Graph und Dependabot Alerts. Dependabot security und version updates stehen unter „Available for all GitHub plans“ | nichts eingebaut. Die Doku kennt weder Code Scanning noch Secret Scanning, Dependency Alerts oder SARIF | G01, G02, Forgejo-Doku-Quelltext (§0) |
| Code Scanning und CodeQL | öffentlich ja, privat nur mit Code Security (30 USD pro aktivem Committer und Monat, nur Team oder Enterprise) | keins. Eine SARIF-Ansicht ist offener Wunsch #3669, eine Code-Scanning-API offener Wunsch #12667, PR-Annotationen offener Wunsch #7654 | G01, G03, I02, I03, I04 |
| Secret Scanning und Push Protection | öffentlich ja, privat nur mit Secret Protection (19 USD pro aktivem Committer und Monat) | keins. Forgejo-Tokens haben kein Präfix, „gitleaks or trufflehog can't tell a Forgejo token apart from a commit hash“ (#14640) | G01, G03, I05 |
| CodeQL außerhalb von GitHub | — | Die CLI-Lizenz erlaubt CI-Analysen nur, wenn das quelloffene Repo „hosted and maintained on GitHub.com“ ist. Private Codebasen nur mit bezahlter GHAS-Lizenz. Ob diese Lizenz auch eine andere Forge abdeckt, sagen die Terms nicht | S08 |
| Ersatz per Actions | — | Trivy (Apache-2.0), gitleaks-CLI (MIT, die Action braucht für Orgs einen Lizenzschlüssel), osv-scanner (Apache-2.0), pip-audit (Apache-2.0), Semgrep CE (LGPL-2.1, nur innerhalb einer Funktion oder Datei; die Regeln nur „for your own internal business purposes“) | S01–S07 |

**Urteil.** H1 bis H4 sind nicht berührt. **Gleichwertigkeit teilweise.** In privaten Repos ohne
bezahlte GHAS-Produkte schrumpft der Abstand auf Dependency Graph und Dependabot Alerts [G01]. Diese
beiden hat Forgejo nicht. Scanner laufen dort als CI-Job, aber ohne Ergebnisansicht. CodeQL fällt
aus Lizenzgründen weg [S08].

## 5. Packages

| Aspekt | GitHub | Forgejo | Quelle |
|---|---|---|---|
| Registry-Typen | npm, RubyGems, Maven, Gradle, NuGet, Container. **Keine PyPI-Registry** | 23 Typen, darunter PyPI, Container (OCI), npm und Generic | G14, F26 |
| Sichtbarkeit | neue Pakete privat. Öffentliche Pakete kostenlos | folgt der Sichtbarkeit von Org oder Nutzer. Lässt sich instanzweit sperren | G14, G15, F26 |
| freies Kontingent privat | Team: 2 GB Speicher und 10 GB Transfer, geteilt mit Artefakten. Container-Registry „currently free“ | keine Kontingente in der Doku, die Grenze ist der eigene Speicher | G15, F28 |
| Push aus CI | `GITHUB_TOKEN`, an das Repo gebunden | Der automatische Token ist laut Maintainer „primarily meant to provide read access“. Für Packages gibt es keine Lösung („a separate problem“). Ein Weg sind Authorized Integrations, deren Rechte „same as those for access tokens“ sind | F20, I06, I07, F16 |
| Token-Scopes | — | `write:package` ist laut Doku „currently the same as `read:package`“ | F17 |
| PyPI-Registry im Detail | — | Upload per twine, mit 2FA nur per persönlichem Token. Eine Version lässt sich nicht überschreiben. Die Doku warnt, `--extra-index-url` mache „vulnerable to dependency confusion attacks“ | F27 |
| PyPI-Veröffentlichung per Trusted Publishing | GitHub Actions ist Publisher | nicht möglich. PyPI kennt GitHub Actions, Google Cloud, ActiveState und GitLab CI/CD, bei GitLab „Self-managed instances are not supported“. Zu Codeberg ist die Diskussion offen, PyPI verlangt dort „a stronger key protection/PKI management story“ | P01, P02, P03, P04 |

**Urteil.**
- **H2 nein.** PyPI nennt Forgejo nicht und schließt selbst betriebene GitLab-Instanzen ausdrücklich
  aus [P01]. Selbst für die gehostete Instanz Codeberg ist die Aufnahme offen [P02, P03]. Abgeleitet:
  Ein selbst betriebenes Forgejo veröffentlicht auf PyPI nur mit einem langlebigen API-Token.
- **Gleichwertigkeit teilweise.** Forgejo bietet als Registry mehr Typen, auch PyPI. Die Schwäche
  ist das Schreiben aus CI ohne persönlichen Token, das erst ein Test belegt (§8).

## 6. Ersatz für Dependabot

| Aspekt | GitHub (Dependabot) | Forgejo (Renovate) | Quelle |
|---|---|---|---|
| Plattform | eingebaut. Läuft als dynamischer Workflow | eigene Plattform `forgejo` seit Renovate 41.41.0, vorher Synonym von `gitea` | N05 |
| Einschränkungen | — | dokumentiert ist nur: natives Auto-Merge ab Forgejo v10.0.0. „Features awaiting implementation – none“ | N01 |
| Token | App | PAT mit `repo` und `user`, ab Forgejo 1.20 zusätzlich `issue` und `organization`, für Pakete `read:packages` | N01 |
| Betrieb | gehostet | self-hosted als CLI oder Docker, verarbeitet alle Repos und endet. Den Takt stellt der Betreiber. Mend-Cloud unterstützt Forgejo nicht. Lizenz AGPL-3.0 | N03, N04, N06 |
| Spiegel | — | Autodiscover überspringt Repos, die „a `mirror`“ sind | N01 |
| Vulnerability-PRs | Dependabot security updates | `vulnerabilityAlerts` nur auf GitHub. Ersatz `osvVulnerabilityAlerts` ist „experimental“, nur für direkte Abhängigkeiten und lädt die OSV-Datenbank lokal | N02 |
| Auto-Merge | ja | `platformAutomerge` auf Forgejo unterstützt, `platformCommit` nur auf GitHub | N02 |
| Dependabot selbst | — | dependabot-core steht unter MIT, unterstützt aber kein Forgejo. Die CLI „does not create PRs“ | N07 |

**Urteil.** H1 bis H4 sind nicht berührt. **Gleichwertigkeit teilweise.** Version-Updates
funktionieren gleichwertig. Bei Sicherheits-Updates fehlt die Alert-Quelle, und der OSV-Ersatz ist
experimentell [N02]. Dazu kommen Betrieb und Takt in eigener Hand.

## 7. Betrieb und Kosten

| Aspekt | GitHub | Forgejo | Quelle |
|---|---|---|---|
| Lizenz und Preis | Free 0 USD. Team „$4 USD per user/month for the first 12 months*“, die Fußnote war im Abruftext nicht lesbar | GPLv3+ seit v9.0, keine Lizenzkosten | G19, F32 |
| Actions-Minuten privat | Free 2.000, Team 3.000. Self-hosted und öffentliche Repos kostenlos | Runner auf eigener Hardware | G16 |
| Self-hosted-Gebühr | 0,002 USD pro Minute angekündigt (2025-12-16), dann „postponing … to re-evaluate“, ohne neues Datum | entfällt | G18 |
| Gehostete Runner | Linux 2-core 0,006 USD pro Minute | keine. Codeberg bietet Actions nur „in limited fashion“ | G17, K02 |
| Releases und Support | SaaS | quartalsweise. Die LTS (Q1-Release) bekommt 15 Monate Fixes, sonst rund 3 Monate. Aktuell v16.0.6 und LTS v15.0.10 bis 2027-07-15. Kein Downgrade, Major-Versionen bringen Breaking Changes | F29, F30, F31 |
| Installation | — | offiziell Binary und Docker. Datenbank SQLite, MySQL/MariaDB oder PostgreSQL. Die Doku nennt **keine** RAM- oder CPU-Anforderungen | F33, F34 |
| Backup | SaaS | `forgejo dump` packt Dateien und Datenbank. Einen `restore`-Befehl gibt es nicht | F35 |
| Mirror | — | Pull-Mirror nur beim Anlegen. Intervall standardmäßig 8 h, mindestens 10 min. Laut Quelltext „mirror repository is read-only“. Der Push-Mirror schreibt per Force-Push | F22, F23, F24 |
| Datenstandort | standardmäßig USA. EU nur über Enterprise Cloud mit Datenresidenz, mit Ausnahmen (Billing, Support, Copilot, Secret-Scanning-Prüfungen) | beim Eigenbetrieb dort, wo der Betreiber hostet | G20, G21 |
| gehostete Alternativen | — | Codeberg erlaubt private Repos nur „for things required for FLOSS projects“ und gibt keine Verfügbarkeitsgarantie. Kommerziell gibt es etwa Codey ab 39 CHF/EUR im Monat | K01, K03 |

**Urteil.** H1 bis H4 sind nicht berührt. **Gleichwertigkeit teilweise.** Bei Lizenz,
Minutenpreisen und Datenstandort liegt Forgejo vorn. Dafür gehen Patch-Takt, Backup ohne
Restore-Befehl, Runner-Härtung und Hardware-Sizing auf den Betreiber über. Ein Sizing-Wert ist nicht
dokumentiert. Codeberg scheidet für geschäftliche private Repos nach seinen Nutzungsbedingungen aus
[K01].

## 8. Offen, nur per Test klärbar

| # | Frage | Punkt | Gate in KONZ-072 |
|---|---|---|---|
| T1 | Wie viele Zeilen ändern sich, bis ein tag-gepinntes Reusable aus einem öffentlichen Repo grün läuft (`permissions:`, fehlende Context-Schlüssel, Artefakte)? | 2 | G1 |
| T2 | Werden `merge_group` und `workflow_run` still ignoriert oder abgewiesen? | 2 | G1 |
| T3 | Laufen Workflows mit `permissions: id-token: write` ohne Änderung, und greift dabei `enable-openid-connect`? | 2 | G1 |
| T4 | Funktionieren `actions/upload-artifact@v4` von github.com oder der Fork `forgejo/upload-artifact`, und wie verhält sich `actions/cache`? | 2 | G1 |
| T5 | Startet ein Pull-Mirror-Sync wirklich Workflows, und unter welchem Akteur? | 2, 7 | G1 |
| T6 | Unter welchem Namen erscheinen Statuschecks aus Actions, und gelten die Muster als Glob? | 3 | G2 |
| T7 | Zählen CODEOWNERS-Anfragen als „official review requests“ und blockieren damit den Merge? | 3 | G2 (H4) |
| T8 | Hält „outdated“ zusammen mit Auto-Merge einen PR fest, und unter wessen Identität läuft der Merge? | 3 | neu (H3) |
| T9 | Erfüllt eine Authorized Integration die Positivlisten für Push, Merge und Approval? | 3 | neu |
| T10 | Laufen Forgejo-Access-Tokens ab, oder lässt sich ein Ablaufdatum setzen? | 3, 7 | neu (K4) |
| T11 | Kann eine Authorized Integration mit `write:package` aus CI in die PyPI- und Container-Registry schreiben? | 5 | neu |
| T12 | Läuft Renovate auf der Ziel-Version mit Dashboard, Labels und Auto-Merge, und erzeugt `osvVulnerabilityAlerts` bei Lock-Dateien Fix-PRs? | 6 | neu |
| T13 | Erkennt eine eigene gitleaks-Regel Forgejo-Tokens ohne Fehlalarm-Flut, und genügt ein roter Scanner-Job als Merge-Gate? | 4 | neu |
| T14 | Stellt `dump` plus Rückspielen eine Instanz samt Packages vollständig wieder her (Restore-Drill)? | 7 | neu |
| T15 | Welchen Ressourcenbedarf haben Forgejo, Registry und Runner unter realer Last? | 7 | neu |
| T16 | Wie ist der Team-Preis von GitHub nach 12 Monaten, und welche Rulesets gelten im Team-Plan org-weit? Zwei Seiten widersprechen sich, ein Blick in die Abrechnung klärt es | 3, 7 | neu |

## 9. Quellen (alle abgerufen 2026-10-15)

Stand der Forgejo-Doku ist v16.0 (Latest v16.0.6). Die Zitate wurden gegen den Quelltext
`codeberg.org/forgejo/docs`, Commit `6b64d95` vom 2026-10-13, geprüft. Renovate-Doku: Version
44.164.2. Woodpecker-Doku: 3.19.x. Seiten ohne eigenes Datum gelten mit dem Stand des Abruftags.

**Forgejo-Doku und -Quelltext**
- F01 https://forgejo.org/docs/latest/user/actions/github-actions/
- F02 https://forgejo.org/docs/latest/user/actions/reference/
- F03 https://forgejo.org/docs/latest/user/actions/advanced-features/
- F04 https://forgejo.org/docs/latest/user/actions/overview/
- F05 https://forgejo.org/docs/latest/user/actions/actions/
- F06 https://forgejo.org/docs/latest/user/actions/security-openid-connect/
- F07 https://forgejo.org/docs/latest/admin/actions/
- F08 https://forgejo.org/docs/latest/admin/actions/configuration/
- F09 https://forgejo.org/docs/latest/admin/actions/security/
- F10 https://forgejo.org/docs/latest/user/actions/security-pull-request/
- F11 https://forgejo.org/docs/latest/admin/actions/registration/
- F12 https://forgejo.org/docs/latest/user/protection/
- F13 https://forgejo.org/docs/latest/user/pull-requests-and-git-flow/
- F14 https://codeberg.org/forgejo/forgejo/raw/branch/v16.0/forgejo/options/locale/locale_en-US.ini
- F15 https://codeberg.org/swagger.v1.json (Version `16.0.0-dev-785…+gitea-1.22.0`)
- F16 https://forgejo.org/docs/latest/user/authorized-integrations/
- F17 https://forgejo.org/docs/latest/user/token-scope/
- F18 https://forgejo.org/docs/latest/user/oauth2-provider/
- F19 https://forgejo.org/docs/latest/user/actions/basic-concepts/
- F20 https://forgejo.org/docs/latest/user/actions/security/
- F21 https://forgejo.org/docs/latest/user/api-usage/
- F22 https://forgejo.org/docs/latest/user/repo-mirror/
- F23 https://forgejo.org/docs/latest/admin/config-cheat-sheet/
- F24 https://codeberg.org/forgejo/forgejo/raw/branch/v16.0/forgejo/routers/web/repo/githttp.go
- F25 https://codeberg.org/forgejo/forgejo/raw/branch/v16.0/forgejo/services/actions/notifier.go
- F26 https://forgejo.org/docs/latest/user/packages/
- F27 https://forgejo.org/docs/latest/user/packages/pypi/
- F28 https://forgejo.org/docs/latest/user/packages/container/
- F29 https://forgejo.org/docs/latest/admin/release-schedule/
- F30 https://forgejo.org/docs/latest/admin/upgrade/
- F31 https://forgejo.org/releases/
- F32 https://forgejo.org/faq/
- F33 https://forgejo.org/docs/latest/admin/installation/
- F34 https://forgejo.org/docs/latest/admin/installation/binary/
- F35 https://forgejo.org/docs/latest/admin/command-line/

**Issues (Status am Abruftag)**
- I01 https://codeberg.org/forgejo/forgejo/issues/5102 (Merge Queue, offen)
- I02 https://codeberg.org/forgejo/forgejo/issues/3669 (Security-Tab/SARIF, offen)
- I03 https://codeberg.org/forgejo/forgejo/issues/12667 (Code-Scanning-API, offen)
- I04 https://codeberg.org/forgejo/forgejo/issues/7654 (SARIF-Annotationen, offen)
- I05 https://codeberg.org/forgejo/forgejo/issues/14640 (Token-Präfix, offen)
- I06 https://codeberg.org/forgejo/forgejo/issues/6904 (Actions-Token und Packages, geschlossen)
- I07 https://codeberg.org/forgejo/forgejo/issues/3571 (Authorized Integrations statt Repo-Scope, geschlossen)
- I08 https://github.com/go-gitea/gitea/issues/36392 (Gitea-Merge-Queue, offen)

**Forgejo Runner und Actions-Spiegel**
- R01 https://code.forgejo.org/actions
- R02 https://code.forgejo.org/forgejo/upload-artifact
- R03 https://code.forgejo.org/forgejo/runner/releases
- R04 https://code.forgejo.org/forgejo/runner

**Woodpecker**
- W01 https://woodpecker-ci.org/docs/administration/configuration/forges/forgejo
- W02 https://woodpecker-ci.org/docs/administration/configuration/forges/overview
- W03 https://woodpecker-ci.org/docs/usage/workflow-syntax
- W04 https://github.com/woodpecker-ci/woodpecker/blob/main/LICENSE
- W05 https://github.com/woodpecker-ci/woodpecker/releases

**Renovate und Dependabot**
- N01 https://docs.renovatebot.com/modules/platform/forgejo/
- N02 https://docs.renovatebot.com/configuration-options/
- N03 https://docs.renovatebot.com/getting-started/running/
- N04 https://docs.renovatebot.com/mend-hosted/overview/
- N05 https://github.com/renovatebot/renovate/pull/37075
- N06 https://github.com/renovatebot/renovate/blob/main/license
- N07 https://github.com/dependabot/dependabot-core

**Scanner und CodeQL**
- S01 https://github.com/aquasecurity/trivy/blob/main/LICENSE
- S02 https://github.com/gitleaks/gitleaks/blob/master/LICENSE
- S03 https://github.com/gitleaks/gitleaks-action
- S04 https://github.com/google/osv-scanner/blob/main/LICENSE
- S05 https://github.com/pypa/pip-audit/blob/main/LICENSE
- S06 https://github.com/semgrep/semgrep
- S07 https://semgrep.dev/legal/rules-license (v1.0, 2024-12-13)
- S08 https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md

**GitHub**
- G01 https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security
- G02 https://docs.github.com/en/code-security/getting-started/github-security-features
- G03 https://github.com/enterprise/advanced-security
- G04 https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- G05 https://docs.github.com/en/actions/reference/security/oidc
- G06 https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows
- G07 https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- G08 https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- G09 https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- G10 https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- G11 https://docs.github.com/en/organizations/managing-organization-settings/creating-rulesets-for-repositories-in-your-organization
- G12 https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app
- G13 https://docs.github.com/en/actions/concepts/security/github_token
- G14 https://docs.github.com/en/packages/learn-github-packages/introduction-to-github-packages
- G15 https://docs.github.com/en/billing/concepts/product-billing/github-packages
- G16 https://docs.github.com/en/billing/concepts/product-billing/github-actions
- G17 https://docs.github.com/en/billing/reference/actions-runner-pricing
- G18 https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/
- G19 https://github.com/pricing
- G20 https://docs.github.com/en/enterprise-cloud@latest/admin/data-residency/about-github-enterprise-cloud-with-data-residency
- G21 https://docs.github.com/en/enterprise-cloud@latest/admin/data-residency/about-storage-of-your-data-with-data-residency

**PyPI**
- P01 https://docs.pypi.org/trusted-publishers/adding-a-publisher/
- P02 https://github.com/pypi/warehouse/issues/19786 (offen)
- P03 https://discuss.python.org/t/making-codeberg-a-trusted-publisher/107350 (Beitrag 2026-05-14)
- P04 https://discuss.python.org/t/new-oidc-providers-for-trusted-publishing/106334 (Beitrag 2026-03-02)

**Hosting und Werkzeuge**
- K01 https://codeberg.org/codeberg/org/src/branch/main/TermsOfUse.md (letzter Commit 2026-07-21)
- K02 https://docs.codeberg.org/ci/actions/
- K03 https://codey.ch/
- K04 https://codeberg.org/forgejo-contrib/forgejo-cli (v0.6.0, 2026-07-19)
