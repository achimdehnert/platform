# KONZ-platform-072 — Anhang: Einsatzkonzept Forgejo (2026-10-16)

> Entscheidungsgrundlage zu [KONZ-platform-072](../KONZ-platform-072-forgejo-pilot.md), Mandat
> [#4018](https://github.com/achimdehnert/platform/issues/4018). Auftrag, Owner-Wort 2026-10-16:
> „H2 -> was sind die sinnvollen szenarien? H3 -> alternativen -> analysiere tief und gründlich das
> "forgejo-ökosystem" und erarbeite ein optimales konzept zum einsatz von forgejo“.
> Ergänzt den [Anhang vom 2026-10-15](KONZ-072-vergleich-github-forgejo.md) und wiederholt ihn nicht.
> Webquellen abgerufen am **2026-10-16**, Kürzel in eckigen Klammern verweisen auf §10.
> Dieser Anhang **entscheidet nichts**. Offene Owner-Entscheidungen stehen in §9.

## 0. Kurzfassung

1. **Zwei Prämissen des Konzepts waren falsch.** Eine Merge Queue ist auf GitHub nirgends aktiv
   (§1, H3). PyPI schließt nicht „self-managed“ aus, sondern selbst betriebene Identitätsanbieter
   ohne eigenes Sicherheitsteam (§2, H2).
2. **H2 blockiert nicht den Forge-Umzug, sondern nur den Publish-Pfad.** Empfohlen: öffentliche
   Pakete über einen GitHub-Spiegel als Publish-Fassade (S1), interne Pakete in die
   Forgejo-Registry (S4), ein eigener Token-Broker als Reserve (S3). H2 bleibt „fällt nicht“.
3. **H3 lässt sich als Parität formulieren.** Auf GitHub laufen heute Auto-Merge und
   Pflicht-Checks ohne Up-to-date-Zwang. Das bildet Forgejo nativ ab. Mit zwei Meldern fiele H3
   mit Auflage (O1). Eine externe Queue (gitea-mq) bleibt Reserve für platform.
4. **Das Ökosystem trägt, verlangt aber Eigenleistung.** Kein Audit-Log, keine echten Bot-Konten,
   Tokens ohne Ablauf, ein unprotokollierter Admin-Bypass, elf Sicherheitsreleases in 2026 ohne
   eigene CVE-Nummern. Codeberg scheidet als Hosting und als Spiegel aus (KI-Klausel).
5. **v16 endet am 2026-10-29.** Der Pilot läuft auf einer Version ohne Patches, wenn bis dahin
   keine Release-Spur gewählt ist.
6. **Optimales Einsatzkonzept: „Hoheit in Schichten“.** Zuerst Forgejo als geprüft
   wiederherstellbarer Spiegel aller Repos (Exit-Fähigkeit). Parallel eine Forge-neutrale
   Agentenschicht. Ein Hybrid-Umzug vertraulicher Repos nur nach Gates. Ein Vollumzug nur bei
   einem benannten Auslöser (§6).

## 1. Methode und Prämissen-Prüfung

**Methode.** Vier getrennte Recherchen in eigenem Kontext: H2 (PyPI), H3 (Merge Queue),
Ökosystem (zehn Themen) und ein „frischer Kopf“ ohne Kenntnis von KONZ-072. Je Option ein
Kill-Kriterium. Kernaussagen anschließend ein zweites Mal an der Quelle geprüft (§10, markiert ✔).

**Abruf-Falle.** Codeberg liefert automatisierten HTML-Abrufern absichtlich Unsinnstext.
Belastbar sind nur die Codeberg-API und Raw-Dateien. Restrisiko: Einzelne Codeberg-Inhalte einer
Teilrecherche könnten aus Unsinnstext stammen. Alle Stichproben waren korrekt.

| Prämisse im Konzept | Befund 2026-10-16 | Folge |
|---|---|---|
| `merge_group` wird in platform genutzt (C17) | GraphQL `mergeQueue` auf main = null, Ruleset ohne Merge-Queue-Regel, Up-to-date-Zwang aus, 0 Läufe mit `merge_group`. Die „4 Workflows“ sind 2 Dateien, doppelt gezählt über zwei Klone. ADR-270 stellte die Queue am 2026-07-09 zurück [Q1] ✔ | C17 und H3 korrigieren (§3) |
| PyPI schließt self-managed aus (C13) | Ausschlussgrund ist „home-grown IdP“ ohne Sicherheitsteam [P1]. Seit 2025-11-10 Beta für GitLab self-managed über PyPI-Organisationen [P8] | H2-Begründung präzisieren |
| 28 Workflows mit Trusted Publishing | Lokale Klone: 24 Repos, 26 Publish-Workflows. 6 öffentliche Repos (8 Workflows), **18 private Repos publizieren auf das öffentliche PyPI** | Paketschnitt öffentlich/intern ist eine Owner-Frage (§9). Lücke zu 28: vermutlich nicht geklont (Hypothese) |
| Codeberg als Alternative (§9 Out-of-the-Box) | Nutzungsbedingungen §2(1)7 seit 2026-06-29: keine Projekte, die überwiegend von KI-Werkzeugen „including … Claude“ geschrieben sind [W1] ✔ | Codeberg auch als Spiegel ausgeschlossen |
| Pilot-Version 16.0.6 | v17.0.0 am 2026-10-15, **v16 EOL 2026-10-29**, v15 LTS bis 2027-07-15. Kein Downgrade [W2] ✔ | Release-Spur entscheiden (§9) |
| Admin-Bypass gemessen (FJ11) | Steht im Code (`services/pull/check.go`: `if doer.IsAdmin { … }`), nicht in der Doku [W3] | Auflage zu H4 bleibt, Audit-Ersatz nötig |
| „Merge-Berechtigte können Review-Anfrage entfernen und trotzdem mergen“ (Frischer Kopf, Sekundärquelle) | Widerspricht der Messung FJ11 Zeile F5: Anfrage entfernt (204), Merge danach abgewiesen (405 „Does not have enough approvals“) | **nicht übernommen**, die Messung gilt |

## 2. H2 — PyPI: sinnvolle Szenarien

**Lage.** PyPI kennt als Trusted Publisher GitHub Actions, GitLab CI/CD, Google Cloud und
ActiveState [P2]. Selbst betriebene Anbieter sind „not eligible“ [P1]. Der Antrag für Codeberg
ist seit 2026-04-02 offen, Codeberg kann die Anforderungen derzeit nicht erfüllen [P4]. Generisches
OIDC ist offen, die Maintainer sind skeptisch [P7]. PEP 740 verlangt kein Trusted Publishing, die
PyPI-Policy für Attestations schon [P13, P14]. Die Forgejo-Registry kann nicht zu pypi.org
weiterleiten [P25], Paket-Tokens lassen sich nicht auf Repos begrenzen [P23]. Der LiteLLM/Telnyx-
Vorfall im April 2026 lief über ein gestohlenes Token [P26].

| Szenario | Sicherheit gegen heute | Aufwand / Betrieb | Hoheit | Kill-Kriterium (Test < 1 h, ohne echte Pakete) |
|---|---|---|---|---|
| **S1** Forgejo führend, GitHub-Spiegel als Publish-Fassade | ≈ gleich, Attestations bleiben. Neu: Spiegel-Token mit Schreibrecht, abzusichern per Tag-Schutz oder Environment-Review | gering / gering | Publish-Pfad bleibt bei GitHub | Ein per Push-Mirror gespiegelter Tag startet den Publish-Workflow nicht |
| **S2** Projekt-Token als Forgejo-Secret | niedriger: langlebig, ohne Attestations | gering–mittel / Rotation je Paket | voll | Ein Workflow auf einem ungeschützten Branch kann das Secret lesen |
| **S3** Eigener Token-Broker (OIDC prüfen, Token per `pypitoken` auf Projekt und 15 min beschränken) | zwischen S2 und heute | mittel / ein kritischer Dienst | voll | TestPyPI akzeptiert ein abgeleitetes Token mit abgelaufenem `not_after` |
| **S4** Interne Pakete in die Forgejo-Registry | für interne Pakete höher (nicht mehr öffentlich). Pflicht: expliziter Index, nie `--extra-index-url` | mittel / gering | maximal | `uv sync` mit Lese-Token aus der Registry scheitert im Docker-Build eines Hubs |
| **S5** Warten auf PyPI | gleich | keiner | keine | Antrag Codeberg bis 2027-03-31 ohne inhaltlichen Fortschritt |
| **S6** Manuell durch den Owner | gemischt, ohne Attestations | gering / hoch für den Owner | voll | > 2 Releases pro Woche. Stichprobe: ein Paket allein 7 Releases seit 2026-07-18 [P27] |

**Empfehlung.** S1 für öffentliche Pakete, S4 für interne, S3 als Reserve, S2 höchstens als
befristete Brücke, S6 nur als Notfall. Kill-Tests in der Reihenfolge S1 → S4 → S3.

**Schnittfrage.** 18 private Repos veröffentlichen auf das öffentliche PyPI. Ihr Code ist über
die Paketdateien faktisch öffentlich (Hypothese je Paket, hängt am sdist). Für jedes Paket ist zu
entscheiden: öffentlich bleiben (S1) oder intern werden (S4). Diese Frage stellt sich auch ohne
Forgejo.

**Folge für §13.** H2 bleibt „fällt nicht“. Sie blockiert aber nur den Publish-Pfad, nicht den
Forge-Umzug.

## 3. H3 — Merge Queue: Alternativen

**Ist auf GitHub (Messung platform, 01.–16.10.2026, 258 Merges) [Q1].** Keine Merge Queue, kein
Up-to-date-Zwang. 55 % der PRs wären beim Merge veraltet gewesen. Spitze 12 Merges pro Stunde,
bis zu 15 offene PRs gleichzeitig, Median der Lebensdauer eines PRs 16,5 min.

**Forgejo [Q2–Q4].** Auch v17.0.0 hat keine Merge Queue und kein `merge_group`. Das Issue ist
offen, ohne Milestone, laut Maintainer am 2026-06-29 ohne Design-Konsens. Gitea hat ebenfalls
keine. Mit „Block merge if outdated“ plus Auto-Merge aktualisiert Forgejo einen veralteten PR
**nicht** selbst, der Auftrag hängt bis zu einem Update (`POST …/pulls/{index}/update`).

**Kosten der Serialisierung (platform-Daten, Obergrenze).** Aktualisieren sich alle veralteten
PRs nach jedem Merge, kostet das +246 % CI-Läufe. Aktualisiert sich nur der vorderste: +55 %.

| Option | Mechanismus | Aufwand | Kill-Kriterium |
|---|---|---|---|
| **O1** Parität | Auto-Merge ohne Outdated-Block, plus Melder für roten main und für Auto-Merges, die > 30 min grün liegen | Stunden | ≥ 2 nachgewiesene Merge-Rennen in 30 Tagen auf GitHub (roter main-Lauf eines Pflicht-Checks bei grünem PR-Head) |
| **O2** Updater nur für den vordersten PR | Outdated-Block an, ein Workflow aktualisiert den ältesten geplanten PR. Agenten aktualisieren nie selbst | 1–2 Tage | Ein veralteter, geplanter PR mergt nach Update und grüner CI nicht ohne erneutes Scharfschalten |
| **O3** gitea-mq [Q5] | Externe Queue, testet PR ⊕ main. Polling alle 30 s, Postgres, 8 Beitragende | ~1 Tag, ein Dienst mehr | 3 eingereihte PRs mergen nicht binnen 3 × (CI-Dauer + 60 s) ohne Handgriff |
| **O4** shunt [Q6] | Batch plus Bisektion | Binary, 1 Autor, seit 2026-09-05 inaktiv | Bei 5 PRs mit 1 rotem wird der rote nicht allein ausgeworfen oder es braucht > 7 Batch-Läufe |
| **O5** eigener Dienst | Platform Agent, frei gestaltbar | ≥ 1 Woche, dauerhaft eigen | O3 oder O4 bestehen ihren Smoke-Test |
| **O6** Konflikte strukturell vermeiden | Generierte Indizes erst nach dem Merge, Registries als Fragment-Verzeichnisse, zentrale Nummernvergabe | Stunden–Tage je Datei | Die bekannten Hotspot-Dateien erklären < 25 % der Konflikt-Commits in 30 Tagen |
| **O7** platform bleibt auf GitHub | Hybrid, wie bei H2 ohnehin denkbar | Zwei-Forge-Pflege | Owner entscheidet, dass platform aus anderem Grund umziehen muss |

Verworfen: Zuul (kein Gitea/Forgejo-Treiber), Bors, Kodiak, Mergify und verwandte (GitHub- oder
GitLab-gebunden), Trunk-based ohne PRs (widerspricht H4).

**Befund.** Text-Konflikte sind nicht der Haupttreiber: Die 15 meistberührten Dateien machen rund
12 % aller Datei-Berührungen aus. Das Restrisiko sind semantische Konflikte. Sie verhindert nur
ein Test des kombinierten Stands (O3, O4). Dieses Restrisiko trägt GitHub heute genauso.

**Empfehlung.** H3 umformulieren zu „Parität zum GitHub-Ist: Auto-Merge nach grünen Pflicht-Checks
ohne Up-to-date-Zwang, plus Melder für roten main und für hängende Auto-Merges“. Dann fällt H3 mit
Auflage (zwei Melder). O1 als Standard, sobald sein Kill-Kriterium negativ ausfällt. O3 als
Reserve nur für platform, einmal per Smoke-Test prüfen. O2 meiden. O6 lohnt sich unabhängig
davon.

## 4. Ökosystem-Befunde

| Thema | Befund | Bedeutung für Agenten-Betrieb | Quelle |
|---|---|---|---|
| Release-Takt | Seit v9 pünktlich. Stable vier Majors pro Jahr, je ~3 Monate Pflege. LTS v15 bis 2027-07-15, nächste LTS v19 am 2027-04-15 | Upgrades sind Pflicht, Spur bewusst wählen | [W2] ✔ |
| Trägerschaft | Kein eigener Rechtsträger, Domains bei Codeberg e.V., Trägerorganisation offen. 5 Personen schreiben 50 % der Commits, Security-Team 3 Personen | Kein Vertragspartner, nur GPL-Software | [W4, W5] |
| KI-Regeln | Forgejo nimmt keine Beiträge von Coding-Agenten an. Codeberg verbietet überwiegend KI-geschriebene Projekte | Upstream-Meldungen nur durch Menschen. Codeberg fällt weg | [W6, W1] ✔ |
| Audit-Log | Fehlt. Wunsch offen, Umsetzungsversuch am 2026-08-09 geschlossen. Gitea hat eines seit v28 | Admin-Handlungen bleiben unprotokolliert. Ersatz nötig | [W7, W8] ✔ |
| Identität | Bots sind normale Konten mit Login. Tokens ohne Ablauffeld. Repo-gebundene Tokens ab v15 nur für `repository`/`issue`. Kurzlebige JWTs über „Authorized Integrations“ ab v16. Admins können per `sudo` im Namen anderer handeln | Je Agent ein Konto, Rotation per Skript, kein Agent als Admin | [W9, W10] |
| Admin-Bypass | Instanz-Admin überspringt den Branch-Schutz bedingungslos, ohne Spur | Auflage zu H4 ist tragend | [W3] |
| Sicherheit | 11 Sicherheitsreleases in 2026, darunter CVE-2026-89094 (CVSS 9.9). Forgejo vergibt keine eigenen CVEs, Vorankündigung 5–7 Tage vorher | CVE-Scanner allein reichen nicht. Abo der Ankündigungen und Patch-Fenster | [W11, W12] ✔ |
| Actions | `secrets:` in `workflow_call` abgelehnt, falsches Grün für nie gebaute Commits, API meldet „merged“ ohne Branch-Bewegung, Jobs auf privilegierte Runner lenkbar, kein `workflow_run`. Den v7-`mime_type`-Fehler hat upstream niemand gemeldet | Eigene Merge-Nachkontrolle, privilegierte Runner nur auf Repo-Ebene | [W13] |
| Werkzeuge | forgejo-mcp (~163 Tools, ohne Lesemodus), gitea-mcp mit `--read-only`, rubicon/forgejo-mcp nur lesend und additiv. CLI `fgj` am nächsten an `gh`. Kein GraphQL, keine Checks-API, keine Rulesets | `gh`-Werkzeuge nur teilweise portierbar, Rechteschnitt je MCP-Konto | [W14, W15] |
| Föderation | Experimentell, nur Nutzer folgen. Einschalten kann die Domain dauerhaft für Föderation unbrauchbar machen | Ausgeschaltet lassen | [W16] |
| Referenzen | Fedora produktiv seit 2026-03-24 auf v15 LTS als eigener Build, Zeitplan rutschte mehrfach. NL code.overheid.nl auf v15 LTS. CH nur Lesespiegel. Keine deutsche Behörde | LTS-Spur ist die Praxis der großen Betreiber | [W17, W18] |
| Betrieb | Keine Hardware-Angaben, keine Hochverfügbarkeit in der Doku. Backup = DB-Dump, `data/` und Konfigurationsdatei mit den Instanz-Schlüsseln, ohne die ein Restore wertlos ist | Backup enthält Geheimnisse, getrennt verschlüsseln. Restore üben | [W19] |

## 5. Optionsraum

| Option | Hoheit | Migration | Betrieb | Kill-Kriterium |
|---|---|---|---|---|
| A Vollumzug Forgejo | ++ | −− | − | Owner lehnt langlebige Publish-Tokens ab und S1/S3 scheitern |
| B Hybrid: vertrauliche Repos auf Forgejo, Öffentliches und PyPI auf GitHub | + | − | o | > 20 % der vertraulichen Repos ziehen zur Laufzeit Workflows oder Actions aus GitHub |
| C Forgejo als Hoheitsspiegel mit Restore | + | ++ | + | Restore eines repräsentativen Repos samt Issues, PRs, Reviews dauert > 4 h oder verliert Review-Inhalte |
| D GitLab CE self-managed | + | −− | −− | Pflicht-Freigaben durch Code Owner gibt es nur in Premium [X1]. Faktisch ausgeschieden |
| E Bleiben + Forge-neutrale Agentenschicht | o | + | + | Nach 2 Wochen gehen die fünf häufigsten Agenten-Operationen nicht mit identischem Aufruf gegen beide Forges |
| F Managed EU-Forgejo | + | − | + | Anbieter liefert keinen AVV nach Art. 28 DSGVO oder erlaubt keine eigenen Runner |
| G GitHub mit EU-Datenresidenz | − | o | ++ | Ziel ist „weniger US-Abhängigkeit“, nicht „EU-Speicherort“ |

Nicht vertieft: Codeberg (KI-Klausel), Radicle (keine ausgereifte CI), SourceHut (Alpha),
Gitea Cloud (US-Unternehmen, Open Core), OneDev (Lizenzlage).

**Hoheit in fünf Schichten.** Git-Inhalt ist kaum gebunden, Forge-Metadaten mittel, Prozess
(Workflows, Regeln, Code-Owner) und Identität (Bots, Trusted Publishing) hoch, rechtlicher
Zugriff extern. Ein Umzug adressiert die äußerste Schicht und kostet in Prozess und Identität.
Den billigsten Hoheitsgewinn bringt Exit-Fähigkeit: Spiegel plus geübter Restore.

## 6. Einsatzkonzept: Hoheit in Schichten

**Zielbild (12–18 Monate).** GitHub bleibt Schaufenster und Publish-Kanal für Öffentliches. Eine
eigene Forgejo-Instanz in der EU auf der LTS-Spur ist (a) geprüft wiederherstellbarer Spiegel
**aller** Repos und (b) nach bestandenen Gates Primärort für vertrauliche Repos. Entscheidungen,
Freigaben und Regeln liegen als Dateien im Repo. Agenten arbeiten über eine Forge-neutrale
Schicht. Reihenfolge: **C sofort → E parallel → B gegated → A nur bei Auslöser.**

| Stufe | Inhalt | Ergebnis |
|---|---|---|
| 0 Klärung | Zwei Fragen: Gibt es Ablagevorgaben behördlicher Auftraggeber für Quellcode? Meint das Ziel „weniger US-Abhängigkeit“ oder „EU-Speicherort“? | Entscheidet, ob B nötig ist |
| 1 Exit-Fähigkeit (C) | Forgejo LTS, nur intern erreichbar. Pull-Spiegel aller Repos, Metadaten-Export, verschlüsselte Offsite-Kopie | Restore-Übung mit Stoppuhr |
| 2 Lock-in stoppen | Keine neuen Marketplace-Actions ohne Pin und Alternative. Freigaben als Datei im Repo | Die Schuld wächst nicht weiter |
| 3 Workflow-Diät + Schatten-CI | Workflows auf dünne Hüllen um `make`-Ziele. Schattenläufe auf Forgejo-Runnern | Portabilitätsquote messbar |
| 4 Agentenschicht (E) | Eine Schnittstelle mit GitHub- und Forgejo-Backend. Je Rolle ein Konto: Autor ohne Merge-Recht, Merge-Bot nur nach erfüllter Freigabe | Gleicher Agentenaufruf, zwei Forges |
| 5 Hybrid-Umzug (B) | Vertrauliche Repos auf Forgejo primär, ohne Rückspiegel | Hoheit für den vertraulichen Teil |
| 6 Jahresreview (A) | Vollumzug nur bei Auslöser EG6 | Bewusste Nicht-Entscheidung |

**Bausteine je Stufe.**

1. **Release-Spur.** LTS wie Fedora und NL: v15 LTS neu aufsetzen, Wechsel auf v19 im Q2 2027.
   Preis: Funktionen aus v16/v17 fehlen, darunter Authorized Integrations, Webhooks für Job-Status
   und Fixes der Artefakt-API. Alternative: Stable mit vier Upgrades pro Jahr.
2. **Identität.** Je Agent ein eigenes Konto mit repo-gebundenem Token, Rotation per Skript. Kein
   Agent und keine Automatisierung als Instanz-Admin (Auflage H4). Ab v16 kurzlebige JWTs.
3. **Audit-Ersatz.** Access-Log zentral und manipulationsarm sammeln. Git-Historie und
   PR-Timeline regelmäßig abgleichen. Admin-Konto nur im Vier-Augen-Prinzip. Gitea v28 als
   Gegenoption mitdenken (Wechselkosten ungeprüft).
4. **CI.** shared-ci öffentlich und ohne Secrets. Artefakt-Actions auf v4 deckeln. Unabhängige
   Merge-Nachkontrolle: gebauter SHA gegen Head-SHA. Privilegierte Runner nur auf Repo-Ebene und
   flüchtig.
5. **Patch-Pfad.** Abo der Sicherheitsankündigungen. Einspielen erst nach Freigabe (Prod-Gate).
   Frist ≤ 14 Tage nach Release.
6. **Härtung.** Föderation aus, `OFFLINE_MODE` an, Registrierung aus, E-Mail-Adressen privat.
   Release-Binaries mit Signaturprüfung lokal vorhalten.
7. **MCP.** Lesende Agenten über einen Server mit Schreibschutz, schreibende über ein eng
   geschnittenes Konto. Alternative: ein schmaler eigener Server mit 10–15 Operationen.

**Was nie.** GitLab CE als Ziel. Codeberg für eigenen Code. Big-Bang-Umzug aller Orgs. Ein Agent
mit Merge-Recht als Instanz-Admin. Eine öffentlich erreichbare Instanz ohne Patch-Routine. Ein
Backup, das nie wiederhergestellt wurde.

**Einsatz-Gates (messbar, EG statt G, um die Pilot-Gates G0–G2 nicht zu überladen).**

| Gate | Vor Stufe | Kriterium |
|---|---|---|
| EG1 Exit belegt | 3 | 7 Tage in Folge alle Spiegel ≤ 24 h Rückstand. 1 Restore inklusive Issues, PRs, Reviews in ≤ 4 h ohne Inhaltsverlust |
| EG2 Bedarf belegt | 5 | Auftraggeber bestätigt Ablagevorgabe **oder** Owner bestätigt das Ziel „weniger US-Abhängigkeit“ schriftlich |
| EG3 CI portabel | 5 | ≥ 90 % der Workflows der betroffenen Repos laufen im Schatten grün, je ≤ 10 geänderte Zeilen, 0 Laufzeit-Bezüge auf GitHub-Repos |
| EG4 Agenten-Parität | 5 | ≥ 95 % Erfolg über 50 Agenten-Operationen. Negativtest: Merge ohne Pflichtfreigabe scheitert |
| EG5 Betrieb tragbar | 5, 6 | 2 Monate ≤ 2 h Wartung pro Monat. Patches ≤ 14 Tage. 0 Datenverlust |
| EG6 Vollumzug-Auslöser | 6 | Einer davon: PyPI akzeptiert Forgejo-OIDC. Der EuGH kippt den EU-US-Datenrahmen (C-703/25 P) [X2]. GitHub erhebt Gebühren für selbst gehostete Runner [X3] |

**Verhältnis zum Pilot.** Der laufende Pilot (G1, G2) misst Stufe 3 und 4 im Kleinen. Stufe 1
ist eine eigene Entscheidung und nicht Teil des Mandats #4018. Sie braucht Owner-Wort.

## 7. Neue Testfragen (Fortsetzung von T1–T16)

| # | Frage |
|---|---|
| T17 | Trägt der Pilot nach Neuaufbau auf v15 LTS dieselben Ergebnisse, oder fehlen v16/v17-Funktionen hart? |
| T18 | Hinterlässt `force_merge` durch den Instanz-Admin eine Spur in PR-Timeline oder Merge-Commit? Zeigt das Access-Log bei `sudo` den Admin oder den Zielnutzer? |
| T19 | Laufen gitea-mcp (`--read-only`) und forgejo-mcp gegen die Pilotinstanz, und welche Tools fallen aus? |
| T20 | Wie viele der 133 Werkzeugdateien nutzen nur REST-Endpunkte mit Forgejo-Gegenstück? |
| T21 | Tritt falsches Grün oder falsches „merged“ im Pilot auf? Merge-Nachkontrolle als Gate-Test |
| T22 | Bekommt ein Bot-Konto ohne Passwort-Login per Admin-API ein repo-gebundenes Token, auch bei 2FA-Pflicht für alle? |
| T23 | Stellt der Restore nach offizieller Anleitung Tokens, 2FA und Pakete wieder her? (ergänzt T14) |
| T24 | Erkennt ein CVE-Scanner eine Forgejo-Lücke ohne eigene CVE-Nummer? |
| T25 | Wo genau entsteht der v7-`mime_type`-Fehler? Ein Upstream-Issue darf laut AI-Agreement nur ein Mensch einreichen |
| T26 | Kill-Tests S1, S4, S3 (§2) und O1, O3 (§3) |

## 8. Korrekturen zum Anhang vom 2026-10-15

| Anhang sagt | Stand 2026-10-16 |
|---|---|
| v17.0 geplant, noch nicht veröffentlicht | v17.0.0 am 2026-10-15, EOL 2027-01-28. v16 EOL 2026-10-29 |
| Ablauf von Access-Tokens offen (T10) | Laut Code kein Ablauffeld. Live-Test steht aus |
| CLI `fj` v0.6.0 | `fj` v0.7.0 vom 2026-10-16, `fgj` am nächsten an `gh`, `berg` archiviert |
| Admin-Bypass nur gemessen | Im Code belegt, nicht in der Doku |
| Artefakte: v3 oder gepatchter v4 | Der Fork endet bei v5. Zu v7/`mime_type` gibt es kein Upstream-Issue |
| Reusables nur aus öffentlichen Repos | Zusätzlich: `secrets:` in `workflow_call` wird abgelehnt |
| Codeberg: private Repos nur für FLOSS | Zusätzlich: Verbot überwiegend KI-geschriebener Projekte |

## 9. Offene Owner-Entscheidungen (Vorschläge, nichts davon entschieden)

| Thema | Vorschlag | Frist |
|---|---|---|
| Release-Spur | v15 LTS neu aufsetzen (Spur der großen Betreiber) oder v17 Stable mit Upgrade alle ~3 Monate. **Entschieden 2026-10-16: v17** (Owner-Wort „FJ17 V17“, Konzept §13) | vor 2026-10-29 |
| H3-Wortlaut | Umformulieren auf Parität (§3). Dann fällt H3 mit Auflage | vor G2-Ende 2026-10-29 |
| Paketschnitt | Je Paket der 18 privaten Repos: öffentlich (S1) oder intern (S4) | vor Stufe 5 |
| Stufe 0 | Zwei Klärungsfragen (§6) | offen |
| Stufe 1 | Hoheitsspiegel aller Repos mit Restore-Drill als eigener Auftrag | offen |

## 10. Quellen (abgerufen 2026-10-16, ✔ = in einer zweiten Prüfung direkt an API oder Raw-Datei gegengeprüft)

**PyPI (H2)**
- [P1] PyPI, Trusted Publishers Internals: https://docs.pypi.org/trusted-publishers/internals/
- [P2] PyPI, Adding a Trusted Publisher: https://docs.pypi.org/trusted-publishers/adding-a-publisher/
- [P4] pypi/warehouse#19786 (Codeberg): https://github.com/pypi/warehouse/issues/19786
- [P7] pypi/warehouse#19347 (Generic OIDC): https://github.com/pypi/warehouse/issues/19347
- [P8] PyPI-Blog 2025-11-10, Trusted Publishers für Organisationen: https://blog.pypi.org/posts/2025-11-10-trusted-publishers-coming-to-orgs/
- [P13] PyPI, Producing attestations: https://docs.pypi.org/attestations/producing-attestations/
- [P14] PEP 740: https://peps.python.org/pep-0740/
- [P16] pypitoken, Restrictions: https://pypitoken.readthedocs.io/en/latest/reference.html
- [P17] Forgejo, PyPI-Registry: https://forgejo.org/docs/latest/user/packages/pypi/
- [P19] Forgejo, Repository Mirrors: https://forgejo.org/docs/latest/user/repo-mirror/
- [P23] Forgejo, Token-Scopes: https://forgejo.org/docs/latest/user/token-scope/
- [P25] forgejo/forgejo#5806: https://codeberg.org/forgejo/forgejo/issues/5806
- [P26] PyPI-Blog 2026-04-02, Incident Report: https://blog.pypi.org/posts/2026-04-02-incident-report-litellm-telnyx-supply-chain-attack/
- [P27] PyPI-JSON-API, Release-Zählung je Paket (Messung 2026-10-16)

**Merge Queue (H3)**
- [Q1] Messung platform: GitHub-API (GraphQL `mergeQueue`, Ruleset, Läufe mit `merge_group`, PR-Liste 01.–16.10.), [ADR-270](../../adr/ADR-270-merge-automation-fleet-tiered.md) ✔
- [Q2] Forgejo-Issue #5102: https://codeberg.org/forgejo/forgejo/issues/5102 ✔
- [Q3] Forgejo v16.0.6, `services/automerge/`, `services/pull/`: https://codeberg.org/forgejo/forgejo/src/tag/v16.0.6/
- [Q4] Release Notes v17.0.0: https://codeberg.org/forgejo/forgejo/src/branch/forgejo/release-notes-published/17.0.0.md
- [Q5] gitea-mq: https://github.com/Mic92/gitea-mq
- [Q6] shunt: https://github.com/rbtr/shunt

**Ökosystem**
- [W1] Codeberg Terms of Use §2(1)7: https://codeberg.org/codeberg/org/src/branch/main/TermsOfUse.md ✔
- [W2] Forgejo Release-Plan: https://forgejo.org/docs/latest/admin/release-schedule/ ✔
- [W3] Forgejo v16.0.6, `services/pull/check.go`: https://codeberg.org/forgejo/forgejo/src/tag/v16.0.6/services/pull/check.go
- [W4] Forgejo Discussions #482 / #484: https://codeberg.org/forgejo/discussions/issues/482 · https://codeberg.org/forgejo/discussions/issues/484
- [W5] Forgejo Sustainability: https://codeberg.org/forgejo/sustainability
- [W6] Forgejo AI Agreement: https://codeberg.org/forgejo/governance/src/branch/main/AIAgreement.md ✔
- [W7] Forgejo-Issue #6982 (Audit-Log), PR #13118: https://codeberg.org/forgejo/forgejo/issues/6982 · https://codeberg.org/forgejo/forgejo/pulls/13118 ✔
- [W8] Gitea PR #38189 (Audit-Log): https://github.com/go-gitea/gitea/pull/38189 ✔
- [W9] Forgejo, Token-Scopes: https://forgejo.org/docs/latest/user/authentication/token-scope/
- [W10] Forgejo, Authorized Integrations: https://forgejo.org/docs/latest/user/api/authorized-integrations/
- [W11] Forgejo Security Announcements: https://codeberg.org/forgejo/security-announcements
- [W12] NVD CVE-2026-89094: https://nvd.nist.gov/vuln/detail/CVE-2026-89094 ✔
- [W13] Forgejo-Issues #14674, #14728, #14214, #13868, #7722: https://codeberg.org/forgejo/forgejo/issues/ (+ Nummer) ✔
- [W14] MCP: https://git.b4mad.industries/agentic-forges/forgejo-mcp · https://gitea.com/gitea/gitea-mcp · https://github.com/rubicon/forgejo-mcp
- [W15] CLIs: https://codeberg.org/romaintb/fgj · https://codeberg.org/forgejo-contrib/forgejo-cli
- [W16] NVD CVE-2026-90679 (Föderation): https://nvd.nist.gov/vuln/detail/CVE-2026-90679
- [W17] Fedora: https://communityblog.fedoraproject.org/fedora-chooses-forgejo/ · https://forge.fedoraproject.org/api/v1/version
- [W18] Niederlande: https://developer.overheid.nl/blog/2026/04/24/we-gaan-samen-code-overheid-bouwen · https://code.overheid.nl/api/v1/version
- [W19] Forgejo, Backup: https://forgejo.org/docs/latest/admin/setup/backup/

**Frischer Kopf**
- [X1] GitLab Code Owners (Premium, Ultimate): https://docs.gitlab.com/user/project/codeowners/
- [X2] EU-US-Datenrahmen, Berufung C-703/25 P: https://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/20251201-european-court-of-justice-to-review-challenge-to-eu-us-data-privacy-framework
- [X3] GitHub verschiebt Gebühr für selbst gehostete Runner: https://www.techzine.eu/news/devops/137396/github-bends-to-criticism-and-delays-paid-self-hosting-of-runners/

**Lücken.** Live-Verhalten von O1–O4 und S1–S4 nur per Quelltext oder Doku belegt. Aufwände je
Stufe sind Schätzungen ohne Messung. Rechtliche Einordnung ist keine Rechtsberatung. Die Lücke
zwischen 26 gemessenen und 28 genannten Publish-Workflows ist ungeklärt.
