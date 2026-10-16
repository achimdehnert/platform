# KONZ-platform-072 — Anhang: Alternativen zu Forgejo (2026-10-16)

> Entscheidungsgrundlage zu [KONZ-platform-072](../KONZ-platform-072-forgejo-pilot.md), Mandat
> [#4018](https://github.com/achimdehnert/platform/issues/4018). Auftrag, Owner-Wort 2026-10-16:
> „gibt es sinnvolle alternativen zu forgejo ? analysiere tief und gründlich“.
> Ergänzt den [Anhang Einsatzkonzept](KONZ-072-einsatzkonzept-forgejo.md) (Optionsraum §5) und
> wiederholt ihn nicht. Webquellen und Quelltexte abgerufen am **2026-10-16**, Kürzel verweisen
> auf §9. ✔ = in einer zweiten, adversarialen Prüfung direkt an Primärquelle oder Quelltext
> gegengeprüft. Ohne ✔ gilt eine Aussage als Rechercheergebnis, **(H)** als Hypothese.
> Dieser Anhang **entscheidet nichts**. Offene Owner-Entscheidungen stehen in §8.

## 0. Kurzfassung

1. **Keine Alternative löst H2.** PyPI erkennt genau vier Herausgeber an: GitHub, GitLab, Google,
   ActiveState. Ein Weg ohne GitHub führt nur über selbst betriebenes GitLab, und der ist Beta mit
   Freischaltung von Hand durch PyPI. H2 bleibt damit eine Frage des Publish-Pfads (Einsatzkonzept
   §2), nicht der Forge-Wahl.
2. **Gitea 28 ist die stärkste technische Alternative.** Es schließt vier der bekannten
   Forgejo-Lücken im freien Kern: Code-Owner-Review blockiert, auch der Instanz-Admin kann nicht
   am Schutz vorbei mergen, es gibt ein Audit-Log und echte Bot-Konten. Die Schutzregel ändern
   kann der Admin weiterhin, sichtbar nur bei eingeschaltetem Audit-Log. Gleich bleiben fehlende
   Merge Queue, fehlendes OIDC und Tokens ohne Ablauf. Dagegen: keine LTS, Sicherheitsfixes nur
   für die aktuelle Hauptversion, ein Firmenträger mit Open-Core-Grenze, keine
   Datenbank-Migration von Forgejo.
3. **STACKIT Git ist Forgejo als deutscher Dienst.** Gleiche Software wie der Pilot, deutscher
   Rechtsträger, AVV, C5. Dafür automatische Updates ohne Einfluss, keine Log-Exporte, also kein
   Audit-Ersatz. Lohnt nur, wenn „Hoheit“ den Rechtsträger meint und nicht die Kontrolle.
4. **GitLab ist nur als Premium sinnvoll.** Free hat keine Code Owners. Premium selbst betrieben
   bringt Merge Trains, Code-Owner-Pflicht, Audit Events, Service Accounts ohne Lizenzplatz und als
   einzige Option einen H2-Weg. Preis: die tragenden Funktionen hängen an einer Lizenz eines
   US-Herstellers, dazu Monatstakt und 16 GB RAM.
5. **Alle übrigen 15 Optionen scheiden aus oder sind Nische.** Harness Open Source hat Merge Queue
   und Code-Owner-Pflicht, aber das Audit-Log ist abgeschaltet. GitHub Enterprise Server und
   GitHub mit EU-Datenresidenz bringen kaum Hoheit.
6. **Vor der Forge-Frage steht die Lesart von „Hoheit“** (§6): Rechtsträger und Speicherort (A)
   oder Kontrolle über die Software (B). Bei A ist ein gemanagter deutscher Dienst stärker als
   Eigenbetrieb, bei B nur Eigenbetrieb.

## 1. Methode

Vier unabhängige Recherchen je Themenfeld (GitLab mit PyPI-Herausgeberliste, Gitea, übrige
Forges samt forge-freier Architektur, gemanagte EU-Angebote mit Rechtsrahmen), je mit Primärquelle
und messbarem Kill-Kriterium. Danach eine adversariale Gegenprüfung der tragenden Aussagen am
Quelltext und an der Herstellerdoku. Kriterien wie im Konzept: H1 Reusables über Repo-Grenzen, H2
PyPI Trusted Publishing, H3 Merge Queue oder Serialisierung, H4 Code-Owner-Review blockiert, dazu
Agenten-Betrieb, Audit, Hoheit, Betriebslast, Kosten. Nichts wurde angelegt, angefragt oder gepostet.

**Korrekturen am bisherigen Stand:**

| Stelle | Bisher | Jetzt |
|---|---|---|
| Einsatzkonzept §5 D | GitLab CE „faktisch ausgeschieden“ | Gilt für Free/CE. Premium selbst betrieben ist die einzige Option mit H2-Weg (§3.3) |
| Einsatzkonzept §5 | OneDev „Lizenzlage“ | Geklärt: MIT-Quelltext, Binärpaket mit proprietärem EE-Modul, also Open Core [O2] |
| Einsatzkonzept §5 | Gitea Cloud „US-Unternehmen, Open Core“ | Bestätigt, aber mit Region Frankfurt seit 2024 [G9] |
| Einsatzkonzept §6.3 | „Gitea v28 als Gegenoption mitdenken“ | Vertieft in §3.1 |
| Konzept §8 A2 | „GitLab: Trusted Publishing bei self-managed nicht belegt (H)“ | Belegt als Beta über PyPI-Organisationen [P2] |
| Recherche „Zuul vor Forgejo“ | Gitea-Treiber vermutet | Widerlegt: Zuul hat keinen Gitea-Treiber, Einsatzkonzept §3 bleibt richtig [Z1] ✔ |

## 2. Gesamtbild

Vergleich zum Pilot-Stand Forgejo 17. „+“ besser, „=“ gleich, „−“ schlechter als Forgejo.

| Kriterium | Forgejo 17 (Ist) | Gitea 28 OSS | STACKIT Git | GitLab Premium selbst betrieben | Harness OSS | GitHub Enterprise Server |
|---|---|---|---|---|---|---|
| H1 Reusables | mit Auflage | = | = | + (Components, ab Free) | − (Drone-Format) | + |
| H2 PyPI | nein | = nein | = nein | + Beta | = nein | = nein |
| H3 Merge Queue | Ersatz | = Ersatz | = | + Merge Trains | + | + |
| H4 Code Owner | mit Auflage | + blockiert, Admin-Merge sperrbar | = | + (Admin kann Regel ändern) | + | + |
| Audit-Log | fehlt | + ab Werk aus | − nicht exportierbar | + | − abgeschaltet | + |
| Bots, Tokens | Konten, kein Ablauf | + Bot-Konten, kein Ablauf | = | + Service Accounts, Ablauf | Ablauf möglich | + |
| `upload-artifact@v7` | scheitert | + | = | entfällt | entfällt | + |
| Release-Spur | Stable + LTS | − keine LTS | Anbieter | monatlich | unklar | jährlich |
| Upstream nimmt Agenten-Beiträge | nein | + mit Offenlegung | = | (H) | (H) | – |
| Rechtsträger | keiner | US-Firma | DE | US, börsennotiert | US | US |
| Betrieb | eigen | = | + gemanagt | − 16 GB, Monatstakt | = | − |
| Kosten | 0 | 0 | 15–101 €/Monat + Minuten | ~29 $/Mensch/Monat | 0 | ab 21 $/Nutzer/Monat (H) |

## 3. Befunde je ernsthafter Alternative

### 3.1 Gitea 28 (freier Kern)

- **Stand.** v28.1.0 vom 2026-10-06, Hauptversion etwa vierteljährlich, keine LTS. Sicherheitsfixes
  nur für die aktuelle Hauptversion, die vorige wird ohne sie gepflegt (die beiden Dokumente
  widersprechen sich darin, maßgeblich ist SECURITY.md) [G1, G12] ✔.
- **H4 schärfer als Forgejo.** `BlockOnCodeownerReviews` verlangt je CODEOWNERS-Regel eine Zustimmung
  [G3] ✔. Mit `BlockAdminMergeOverride` und leerer Ausnahmeliste kommt auch der Instanz-Admin weder
  per Web noch per API-`force_merge` noch per Direkt-Push am Schutz vorbei, Auto-Merge ebenso [G4] ✔.
  Grenze: Repo- und Instanz-Admins dürfen die Regel selbst ändern oder sich auf die Ausnahmeliste
  setzen. Sichtbar wird das nur im Audit-Log. In Forgejo überspringt der Instanz-Admin den Schutz
  ohne Regeländerung, beim Merge mit `force_merge` und sogar beim Push in den Pre-Receive-Prüfungen
  [F1] ✔, im Pilot gemessen (Konzept §11, FJ11).
- **Audit-Log** seit v28 im freien Kern, ab Werk aus, 30 Tage Aufbewahrung, JSONL-Export. Erfasst
  Tokens, Secrets, Admin-Rechte, Branch-Schutz. Nicht erfasst: Pushes, Logins, ob ein Merge den
  Schutz umging. Der Instanz-Admin kann es abschalten [G2] ✔. Für H4 ist es also nur dann ein
  Gewinn, wenn es eingeschaltet und außerhalb der Instanz gesammelt wird.
- **Identität.** Echte Bot-Konten ohne Passwort und Login seit v28 [G6]. Tokens weiter ohne Ablauf,
  Scopes je Bereich, nicht je Repo [G5] ✔.
- **Actions.** `mime_type` ist im Protokoll, v7 läuft. Die Ursache bleibt: unbekannte Felder werden
  weiter nicht verworfen, das nächste neue Feld bricht wieder [G7] ✔. Reusables nur innerhalb der
  Instanz, fremde Instanzen seit 1.27 gesperrt, shared-ci müsste gespiegelt werden. OIDC für Jobs
  offen (Meilenstein 29) [G8] ✔.
- **Sicherheit.** 143 Hinweise über GitHub seit 2026-04, 139 mit CVE-Nummer, davon 12 kritisch und
  47 hoch, mehrere zu Actions [G10] ✔. Ältere Lücken stehen auf der eigenen Website, die Zahl ist
  keine Lebenszeit-Bilanz und mit Forgejos Zählung nicht direkt vergleichbar.
- **Governance.** MIT, Träger CommitGo Inc., Lenkungsgremium halb Firma, halb gewählt. SAML,
  Org-weiter Branch-Schutz, Pflicht-2FA nur in Enterprise [G11]. KI-Beiträge mit Offenlegung
  erlaubt [G11] ✔: Fixes aus dem Pilot könnten upstream gehen, bei Forgejo nicht.
- **Wechsel.** Keine Datenbank-Migration Forgejo → Gitea, nur Repo-Import über die API. Branch-Schutz,
  Secrets und Runner neu anlegen.
- **Kill-Kriterium:** Ein Probe-Repo auf Gitea 28 scheitert an einem dieser vier Punkte:
  tag-gepinnter Workflow aus einem anderen Repo läuft · `upload-artifact@v7` grün · API-Merge des
  Instanz-Admins gegen `BlockAdminMergeOverride` abgewiesen · das anschließende Abschalten der Regel
  durch den Admin steht im Audit-Log.

### 3.2 STACKIT Git (gemanagtes Forgejo)

- **Angebot.** Forgejo-Basis, bestellbar laut Preisliste, Leistungszertifikat ab 2026-03-11, API noch
  `v1beta` [S1, S3]. Schwarz Digits, Sitz Deutschland. C5-Testat, im Kommissions-Tender SEAL-3 [S2, R4].
- **Preis.** Git-10 15,00 €/Monat, Git-100 100,80 €/Monat, Runner-Minute 0,004042 €, eigene Runner
  möglich [S3, S4]. Ob Bot-Konten als Nutzer zählen, ist offen.
- **Grenzen laut Zertifikat.** Updates automatisch ohne Termin-Einfluss, Backup-Intervall fest, Logs
  „not exportable“, kein Export für Nutzerkonten [S1]. Funktionsumfang = Forgejo, also dieselben
  Lücken wie der Pilot, nur ohne die Chance auf eigenes Audit-Log aus dem Access-Log.
- **Exit.** GPL-Software, Rückweg in den Eigenbetrieb ohne Formatwechsel.
- **Kill-Kriterium:** Instanz-Version liegt nach einem Forgejo-Sicherheitsrelease länger als 14 Tage
  zurück, oder der AVV sichert keinen Export von Nutzer- und Audit-Daten zu.

Weitere gemanagte Forgejo-Angebote: Codey (VSHN, Schweizer Recht, keine gemanagten Runner) [S5],
PikaPods (Malta, US-Unterauftragnehmer, Hobby-Niveau) [S6]. Codeberg bleibt ausgeschlossen.

### 3.3 GitLab Premium, selbst betrieben

- **Stufe.** Code Owners samt Pflicht-Freigabe, Approval Rules, Merge Trains, Push Rules und Audit
  Events auf Gruppen- und Instanzebene erst ab Premium [L1, L2] ✔, [L3, L4]. Free zeigt nur
  Anmeldeereignisse.
- **H4.** Wer am Branch „Allowed to push“ hat, umgeht die Freigaberegeln. Admins können Regeln
  ändern. Damit gleichwertig mit GitHub, nicht strenger [L5].
- **H2.** Selbst betriebenes GitLab ist bei PyPI Beta: Freischaltung von Hand durch PyPI je
  PyPI-Organisation, OIDC-Endpunkte der Instanz müssen öffentlich erreichbar sein. Keine GA-Meldung
  bis 2026-10-16 [P2, P3].
- **Agenten.** `glab` aktiv gepflegt, offizieller MCP-Server lesend und schreibend, seit 19.2 auch in
  Free, seit 19.5 GA [L7] ✔. Service Accounts belegen keinen Lizenzplatz, seit 18.11 auch in Free
  (bis 100 je Instanz), Tokens laufen nach höchstens 365 Tagen ab [L6] ✔.
- **Kosten und Last.** 29 $ je Mensch und Monat bei Jahreszahlung [L8] ✔. 16 GB RAM, monatliche
  Hauptversion, mehrere Patches im Monat [L9]. GitLab Inc. ist US-börsennotiert.
- **Übersetzung.** `include:` mit `ref` und CI/CD Components gehen ab Free. shared-ci wäre neu zu
  schreiben, Marketplace-Actions fallen weg (H, Aufwand nicht gemessen).
- **Kill-Kriterium:** PyPI bestätigt das Onboarding nicht binnen 30 Tagen nach Anfrage, oder ein
  Probe-Publish per OIDC aus der eigenen Instanz scheitert. Ohne H2 ist GitLab teurer als Forgejo
  ohne Mehrwert in der Hoheit.

Deutsche Managed-GitLab-Anbieter (NETWAYS, AlphaNodes) bieten das als Dienst [S7, S8]. Edition und
AVV-Wortlaut sind ungeprüft. OpenCoDE taugt als Veröffentlichungsort für Behördenprojekte, nicht als
Haus-Forge: Projekte müssen einer Verwaltungsstelle zuordenbar sein [S9].

### 3.4 Harness Open Source

Apache 2.0, aktiv (main zuletzt 2026-10-15), aber das jüngste Release nach Datum ist v2.28.2 vom
2026-04-20, ältere Tags tragen höhere Nummern bis v3.3.0 [H1] ✔. Im Quelltext: Pflicht-Code-Owner,
Merge Queue seit 2026-04, Ausnahmen nur per ausdrücklicher Liste. Das Audit-Log ist in der
freien Fassung ein Leer-Baustein [H2] ✔. Pipelines auf alter Drone-Technik, GitHub-Workflows mit
`workflow_call` laufen nicht (H). Träger investiert vor allem ins kommerzielle Produkt.
**Kill-Kriterium:** Kein dauerhaftes Audit-Log oder kein Pipeline-Baustein über Repo-Grenzen in
einer Zwei-Wochen-Probe. Urteil: Nische, nur wenn H3 nativ zum Muss wird.

### 3.5 GitHub Enterprise Server und GitHub mit EU-Datenresidenz

GHES hat Merge Queue und Rulesets wie heute [E1]. PyPI kennt den GHES-Herausgeber nicht, Anfrage
offen seit 2025-10-30 [P4] ✔. Lizenz jährlich beim US-Hersteller. GHE.com mit EU-Residenz ändert den
Speicherort, nicht den Zugriff nach US-Recht [R2, E2]. **Kill-Kriterium:** Ziel ist weniger
US-Abhängigkeit. Urteil: verworfen, es sei denn, die Lesart ist „Daten im eigenen Rechenzentrum“.

## 4. Verworfen

| Option | Kill-Kriterium, erfüllt | Quelle |
|---|---|---|
| Gerrit + Zuul | Fremdes Change-Modell, Zuul braucht Ansible, Nodepool, ZooKeeper. Starkes Gating, aber Betriebslast für einen Ein-Personen-Betrieb zu hoch | [Z1, Z2] |
| OneDev | Ein Hauptentwickler mit 94 von ~100 Commits in drei Monaten, Open Core | [O1, O2 ✔] |
| Phorge | kein CI | [V1] |
| Radicle | kein Code-Owner-Gate, CI-Broker 0.28 | [V2] |
| Tangled | Alpha, CI nur Nix | [V3] |
| SourceHut | öffentliche Alpha, kein PR-Modell | [V4] |
| Gogs, Kallithea | kein CI, Projekt ruht oder Ein-Personen-Pflege | [V5] |
| RhodeCode | Review-Gate nur in der kommerziellen Edition | [V6] |
| Pagure | Hauptnutzer Fedora ist zu Forgejo umgezogen | [V7] |
| Bitbucket Data Center | Data Center endet 2029-03-28, Weg führt in die Cloud | [V8] |
| Azure DevOps Server | US-Hersteller, kein Hoheitsgewinn | [V9] |
| Git ohne Forge + Woodpecker | Merge Queue, Code-Owner-Gate, Audit und Review müssten selbst gebaut werden, mit org-weitem Schreibrecht | [V10] |
| GitLab Dedicated | Ultimate-Umfang, nur auf AWS, Preis auf Anfrage, US-Rechtsträger | [L10] |
| Gitea Cloud / Enterprise | Herstellerbindung ohne Mehrwert gegenüber Gitea OSS, außer Org-weitem Branch-Schutz | [G9, G11] |

## 5. H2 quer über alle Optionen

PyPI kennt im Quelltext genau vier Herausgebertypen [P1] ✔. Nur GitLab erlaubt eigene Aussteller,
und nur für PyPI-Organisationen nach Freischaltung durch PyPI [P2] ✔. In Arbeit sind Buildkite und
CircleCI, beide nicht gemergt, dazu eine offene Anfrage für generisches OIDC und eine für
Codeberg [P5] ✔.
Neue Herausgeber nimmt PyPI erst bei breiter Nutzung auf [P6]. Für Forgejo, Gitea, Harness,
Woodpecker und GHES gibt es keinen Weg. Die Szenarien S1 (GitHub als Publish-Fassade), S4 (interne
Registry) und S3 (Token-Broker) aus dem Einsatzkonzept §2 gelten für jede Forge außer GitLab gleich.

## 6. Zwei Lesarten von Hoheit

| | A: Rechtsträger und Speicherort | B: Kontrolle über die Software |
|---|---|---|
| Frage | Kann ein US-Gericht herausverlangen? | Bestimme ich Update-Zeitpunkt, Logs, Backups, Konfiguration? |
| Stärkste Option | STACKIT Git (DE, C5, SEAL-3) | Eigenbetrieb Forgejo oder Gitea |
| Fällt durch | GHE.com, GitLab Dedicated, Gitea Cloud (US-Mutter, CLOUD Act [R2]) | jeder gemanagte Dienst |
| Preis | Monatsgebühr, kein Audit-Ersatz | Patch-Disziplin (Forgejo 11 Sicherheitsreleases in 2026) |

**Entschieden: Lesart B** (Owner-Wort 2026-10-16 13:35 UTC „AH B“, [#4018](https://github.com/achimdehnert/platform/issues/4018)).
Die gemessenen Schwächen des Pilots sind Kontrollfragen: Admin-Bypass (FJ11 F3b), Audit-Log,
Update-Takt. PyPI als Ziel liegt ohnehin bei einem US-Betreiber. Gemanagte Dienste zählen damit
nicht als Hoheitsgewinn, STACKIT Git fällt als Option 2 in §7 weg. Lesart A wird erst Pflicht,
wenn ein Auftrag sie verlangt; dann gilt sie für die Repos dieses Auftrags, nicht pauschal.

**Rechtsrahmen, knapp:** Das EU-US-Datenrahmenabkommen ist vor dem EuGH angefochten (C-703/25 P),
eine Entscheidung steht aus [R1]. Quellcode ist meist nicht personenbezogen, Commit-Metadaten,
Issues und Reviews sind es. Jeder Hoster braucht also einen AVV, ein US-Hoster zusätzlich den
Datenrahmen oder Standardklauseln. Eine allgemeine Pflicht, Quellcode für öffentliche Auftraggeber
in der EU zu hosten, war nicht zu finden (H); Pflichten folgen aus dem jeweiligen Auftrag [R3].
BSI C5:2026 und die Souveränitätskriterien C3A machen den Rechtsträger künftig vergaberelevant [R4].
Keine Rechtsberatung.

## 7. Urteil

Es gibt **drei sinnvolle Alternativen**, und jede passt zu einer anderen Lage:

1. **Gitea 28 statt Forgejo**, wenn der Pilot weiterläuft und Lesart B gilt. Gleiche API-Familie,
   gleiche Werkzeuge (gitea-mcp, `tea`), aber H4 ohne Auflage, Audit-Log und Bot-Konten. Preis:
   keine LTS, US-Firmenträger, erneuter Umbau des Pilots. Messbar mit einer Parallelprobe (T27).
2. ~~**STACKIT Git**, wenn Lesart A gilt~~ — entfällt mit Lesart B (§6). Bleibt Rückfall für
   einzelne Aufträge, die Lesart A verlangen.
3. **GitLab Premium selbst betrieben**, nur wenn H2 ohne GitHub zwingend wird. Bedingung ist das
   PyPI-Onboarding. Preis: Lizenzbindung an einen US-Hersteller und die schwerste Betriebslast.

Alles andere scheidet aus. Der Default bei Kill bleibt A3 (auf GitHub bleiben, Hoheit über den
Spiegel), wie im Konzept §8.

## 8. Offene Owner-Entscheidungen (Vorschläge, nichts davon entschieden)

| Thema | Vorschlag | Frist |
|---|---|---|
| ~~Lesart Hoheit~~ | **entschieden: B** (2026-10-16, §6) | erledigt |
| Gitea-Parallelprobe | T27 auf derselben Pilot-Maschine, lokal, ohne Secrets, rückbaubar | vor dem Gate 2027-01-15 |
| GitLab-H2 | Nur falls H2 ohne GitHub zwingend wird: PyPI-Onboarding anfragen. Die Anfrage stellt ein Mensch | offen |

**Neue Testfragen (Fortsetzung von T26):**

| # | Frage |
|---|---|
| T27 | Gitea-Parallelprobe mit den vier Punkten aus dem Kill-Kriterium §3.1 |
| T28 | Zählt STACKIT Bot-Konten als Nutzer, und liefert der AVV Export von Nutzer- und Audit-Daten? (nur Lesen der Vertragsunterlagen) |
| T29 | Fällt Gitea nach Lizenz- bzw. Versionsende ohne LTS in eine Wartungslücke, gemessen an den Daten der letzten drei Sicherheitsreleases gegen die Support-Fenster? |

## 9. Quellen (abgerufen 2026-10-16)

PyPI
- [P1] warehouse, Herausgebertypen: https://github.com/pypi/warehouse/tree/main/warehouse/oidc/models
- [P2] PyPI-Blog, Trusted Publishing für Organisationen: https://blog.pypi.org/posts/2025-11-10-trusted-publishers-coming-to-orgs/
- [P3] LWN, Stand 2026-06-09: https://lwn.net/Articles/1076205/
- [P4] GHES-Herausgeber: https://github.com/pypi/warehouse/issues/18970
- [P5] Buildkite https://github.com/pypi/warehouse/pull/20720 · CircleCI https://github.com/pypi/warehouse/pull/19349 · generisch https://github.com/pypi/warehouse/issues/19347 · Codeberg https://github.com/pypi/warehouse/issues/19786
- [P6] Neue OIDC-Herausgeber: https://discuss.python.org/t/new-oidc-providers-for-trusted-publishing/106334/36

Gitea / Forgejo
- [G1] Releases https://github.com/go-gitea/gitea/releases · Release-Management https://github.com/go-gitea/gitea/blob/main/docs/release-management.md
- [G2] Audit-Log https://github.com/go-gitea/gitea/pull/38189 · https://github.com/go-gitea/gitea/blob/main/modules/setting/audit.go
- [G3] Code-Owner-Blockade https://github.com/go-gitea/gitea/pull/34995
- [G4] Branch-Schutz https://github.com/go-gitea/gitea/blob/main/models/git/protected_branch.go · https://github.com/go-gitea/gitea/blob/main/services/pull/check.go
- [G5] Tokens https://github.com/go-gitea/gitea/blob/main/models/auth/access_token.go
- [G6] Bot-Konten https://github.com/go-gitea/gitea/pull/38966
- [G7] Artefakte https://github.com/go-gitea/gitea/blob/main/routers/api/actions/artifact.proto · https://github.com/go-gitea/gitea/pull/36786
- [G8] Reusables fremder Instanzen https://github.com/go-gitea/gitea/pull/37478 · OIDC https://github.com/go-gitea/gitea/pull/39052
- [G9] Gitea Cloud Frankfurt https://about.gitea.com/news/gitea-cloud-release-12
- [G10] Sicherheitshinweise https://github.com/go-gitea/gitea/security/advisories
- [G11] Enterprise https://about.gitea.com/products/gitea-enterprise · Governance https://github.com/go-gitea/gitea/blob/main/docs/community-governance.md · Beiträge https://github.com/go-gitea/gitea/blob/main/CONTRIBUTING.md
- [F1] Forgejo Merge-Prüfung https://codeberg.org/forgejo/forgejo/raw/tag/v17.0.0/services/pull/check.go · Pre-Receive https://codeberg.org/forgejo/forgejo/raw/tag/v17.0.0/routers/private/hook_pre_receive.go ✔
- [G12] Gitea Sicherheitspolitik https://github.com/go-gitea/gitea/blob/main/SECURITY.md ✔

GitLab
- [L1] Code Owners https://docs.gitlab.com/user/project/codeowners/
- [L2] Merge Trains https://docs.gitlab.com/ci/pipelines/merge_trains/
- [L3] Approval Rules https://docs.gitlab.com/user/project/merge_requests/approvals/rules/
- [L4] Audit Events https://docs.gitlab.com/user/compliance/audit_events/
- [L5] Geschützte Branches https://docs.gitlab.com/user/project/repository/branches/protected/
- [L6] Service Accounts https://docs.gitlab.com/user/profile/service_accounts/ · Projekt-Tokens https://docs.gitlab.com/user/project/settings/project_access_tokens/
- [L7] MCP-Server https://docs.gitlab.com/user/model_context_protocol/mcp_server/ · glab https://gitlab.com/gitlab-org/cli
- [L8] Preise https://about.gitlab.com/pricing/
- [L9] Anforderungen https://docs.gitlab.com/install/requirements/
- [L10] Dedicated https://docs.gitlab.com/subscriptions/gitlab_dedicated/

Gemanagte Angebote
- [S1] STACKIT Git Leistungszertifikat https://stackit.com/en/asset/download/34353/file/Service_Certificate_STACKIT_Git.pdf?version=14
- [S2] STACKIT Git Produktseite https://stackit.com/en/products/developer-platform/stackit-git
- [S3] STACKIT Preisliste https://stackit.com/en/asset/download/37788/file/STACKIT_price_list.pdf?version=28
- [S4] Eigene Runner https://docs.stackit.cloud/products/developer-platform/git/how-tos/pipelines-custom-runner/
- [S5] Codey https://codey.ch
- [S6] PikaPods https://www.pikapods.com/gdpr
- [S7] NETWAYS Managed GitLab https://nws.netways.de/en/managed-services/managed-gitlab/
- [S8] AlphaNodes https://alphanodes.com/managed-hosting/gitlab/gdpr-compliant
- [S9] OpenCoDE Nutzungsbedingungen https://opencode.de/en/knowledge/general-conditions/terms-of-use

Übrige Forges
- [H1] Harness https://github.com/harness/harness · [H2] Audit-Verdrahtung https://github.com/harness/harness/blob/main/audit/wire.go
- [E1] GHES Merge Queue https://docs.github.com/en/enterprise-server@3.17/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- [E2] GHE.com Datenresidenz https://docs.github.com/en/enterprise-cloud@latest/admin/data-residency/about-github-enterprise-cloud-with-data-residency
- [Z1] Zuul-Treiber (gerrit, github, gitlab, pagure, git, …, kein Gitea) https://opendev.org/zuul/zuul/src/branch/master/zuul/driver ✔
- [Z2] Gerrit code-owners https://gerrit.googlesource.com/plugins/code-owners/+/HEAD/resources/Documentation/about.md
- [O1] OneDev https://github.com/theonedev/onedev · [O2] Lizenz https://github.com/theonedev/onedev/blob/main/server-product/system/license.txt
- [V1] Phorge https://github.com/phorgeit/phorge · [V2] Radicle CI https://blog.liw.fi/posts/2026/radicle-status-quo-06/ · [V3] Tangled CI https://blog.tangled.org/ci/ · [V4] SourceHut https://sourcehut.org/
- [V5] Kallithea https://kallithea-scm.org/ · [V6] RhodeCode https://rhodecode.com/features/community-vs-enterprise · [V7] Pagure https://fedoramagazine.org/whats-next-for-pagure-io/
- [V8] Atlassian Data Center Ende https://www.atlassian.com/licensing/data-center-end-of-life · [V9] Azure DevOps Server https://visualstudiomagazine.com/articles/2025/12/09/on-premises-azure-devops-server-reaches-ga.aspx · [V10] Woodpecker https://github.com/woodpecker-ci/woodpecker

Recht
- [R1] Rechtsmittel C-703/25 P, Amtsblatt https://eur-lex.europa.eu/eli/C/2025/6610/oj/eng
- [R2] CLOUD Act, 18 U.S.C. § 2713 https://www.law.cornell.edu/uscode/text/18/2713
- [R3] OZG § 4 https://www.gesetze-im-internet.de/ozg/__4.html · EGovG § 16a https://www.gesetze-im-internet.de/egovg/__16a.html
- [R4] EU-Kommission, souveräne Cloud-Beschaffung https://commission.europa.eu/news-and-media/news/commission-advances-cloud-sovereignty-through-strategic-procurement-2026-04-17_en · BSI C5:2026 https://heise.de/-11247658
