# Laufzeit der Sitzungs-Skills — Messung, Ursachen, Eingriffe

> Begleitdoku zu `.windsurf/workflows/session-start.md`, `session-ende.md` und
> `session-retro.md` ([platform#3373](https://github.com/achimdehnert/platform/issues/3373)).
> Der Skill trägt die **Anweisung**, diese Datei die **Messung und das Warum**.
>
> Zielzustand des Auftrags: die drei Skills laufen spürbar schneller, **ohne** Prüftiefe zu
> verlieren. Jede Pflicht-Phase, jede Checklisten-Zeile und jedes Melder-Urteil bleibt —
> gekürzt wurde ausschließlich **Wartezeit**, nie eine Prüfung.

---

## 1. Warum das überhaupt gemessen werden musste

Vor diesem Auftrag gab es zu keinem der drei Skills eine Zahl. „Der Sitzungsstart dauert" war
ein Eindruck, und ein Eindruck optimiert die Phase, die am lautesten aussieht — nicht die, die
die Zeit frisst. Die erste Messung hat das prompt bestätigt: die beiden Phasen, die im Skill-Text
am ausführlichsten begründet sind (0.7 Deploy-Scan, 0.7.13 Skill-Drift), kosteten zusammen
22,6 s, während zwei kaum kommentierte Zeilen (0.7.12, 0.7.4) allein 69,5 s brauchten.

Deshalb ist die Messung **im Lauf geblieben**, nicht nur im PR: beide Runner enden mit einer
`LAUFZEIT:`-Zeile (Gesamtdauer + fünf teuerste Phasen), `SESSION_CHECKS_TIMING=voll` gibt jede
Phase einzeln aus. Eine neue teure Phase fällt damit beim nächsten Start auf und nicht erst,
wenn jemand den Start wieder „zäh" findet.

## 2. `/session-start` — Befund und Eingriff

**Messung** (Hetzner-Arbeitsrechner, `target=platform`, Wanduhr über den gesamten Runner-Aufruf):

| Lauf | Modus | Wanduhr |
|---|---|---|
| A | vorher (Stand `67e6866a`, sequenziell) | **263,3 s** |
| K | nachher (Vorlauf 8 / ssh 3 / git 1) | **108,3 s** — −59 % |

Abnahme ist **nicht** die Zahl, sondern der Zeilenvergleich: alle **44** Phasen tragen in
Lauf K denselben Status wie in Lauf A, und die Notizen der Melder-Phasen tragen dieselben
Messwerte. Die `LAUFZEIT:`-Zeile liest sich danach auch wieder sinnvoll — teuerste Posten in
Lauf K: `0.7.1b host-kopien 29,2 s` (Ende der ssh-Spur), `0.4.5 auto-reap 25,4 s` und
`0.2 platform-sync 23,9 s` (beide im sequenziellen Kopf), alles Übrige unter 9 s.

**Die zeitdominierenden Schritte** (Lauf A, absteigend; 44 Phasen gesamt):

| Phase | Lauf A | Art | im Vorlauf? |
|---|---|---|---|
| 0.7.12 prod-wirkung | 35,7 s | ssh + gh je Repo | ja (ssh-Spur) |
| 0.7.4 prio-referenzen | 33,8 s | ein gh-Aufruf je Prio-Referenz (77) | ja |
| 0.7.27 sichtbarkeits-drift | 27,0 s | gh-Code-Suche + `git fetch` | ja (git-Spur) |
| **0.4.5 auto-reap** | **26,0 s** | mutiert Worktrees | **nein, mit Absicht** |
| 0.7.18 speicher | 25,6 s | ssh je Host inkl. Offsite | ja (ssh-Spur) |
| **0.2 platform-sync** | **22,4 s** | `git pull` + Symlinks + project-facts | teilweise |
| 0.7 deploy-scan | 12,9 s | 3 gh-Aufrufe je Repo, 10 Repos | ja, je Repo einzeln |
| 0.7.1 deploy-script | 12,4 s | ssh je Host | ja (ssh-Spur) |
| 0.7.13 skill-dist | 9,7 s | `git fetch` je Lane | ja (git-Spur) |
| **0.4.4 basis-abstand** | **8,1 s** | liest Leases, die 0.4.5 abräumt | **nein, mit Absicht** |
| übrige 34 Phasen | zusammen ≈ 50 s | — | überwiegend ja |

**Root Cause in einem Satz:** 44 Phasen liefen nacheinander, obwohl ab 0.4.2 **keine** auf das
Ergebnis einer anderen wartet und fast jede auf Netz wartet — gh-API, ssh, TLS-Handshakes, HTTP.
Die Wartezeiten addierten sich, statt sich zu überlagern.

**Eingriff — der Vorlauf-Schnitt.** Direkt nach Phase 0.4.1 startet der Runner alle
nachfolgenden Melder nebenläufig (`vorlauf`), geerntet wird an der angestammten Phasenstelle
(`ernte`). Reihenfolge der Summary, Wortlaut jeder Notiz und jeder `record`-Aufruf bleiben
unverändert; nur die Wartezeit läuft übereinander statt hintereinander.

**Was bewusst NICHT in den Vorlauf ging** — und warum das keine Auslassung ist:

| Nicht nebenläufig | Grund |
|---|---|
| 0.0–0.2 | `git pull` in `$PLATFORM_DIR`: die Werkzeuge danach sollen den frischen Stand ausführen |
| 0.4 / 0.4.1 | ziehen weitere Repos (`pull --rebase`) |
| 0.4.4 → 0.4.5 | `abstand` liest die Leases, die `reap` danach abräumt — Reihenfolge ist die Aussage |
| 0.5 | startet den pgvector-Tunnel (einziger Hard-FAIL) |
| Heilung in 0.7.5 / 0.7.13 | nur die **Vor**messung läuft nebenläufig; geheilt und nachgemessen wird sequenziell |
| Schreibschritt in 0.7.19 | `--herabstufung` schreibt die Datei, die `record` im nächsten Lauf liest |

Damit bleibt ein **Boden von rund 62 s** (0.1 bis 0.4.1), der ohne einen Eingriff in die
Semantik nicht kleiner wird. Innerhalb von 0.2 laufen `sync-workflows.sh` und
`gen_project_facts.py` jetzt nebeneinander — sie hängen beide nur am frisch gezogenen Stand,
nicht aneinander.

## 3. Drei Spuren statt einer — teuer gelernt

Die erste Fassung hatte **eine** Spur mit acht Plätzen. Sie war schnell (90,6 s) und **falsch**:

| Beobachtung im Lauf | Ursache |
|---|---|
| 0.7.12 „Melder nicht auswertbar", 0.7.18 „Melder nicht gelaufen" | `ernte` hatte gar nicht gewartet (s. u.) |
| 0.7.1b bricht mit `'utf-8' codec can't decode byte 0xfc` ab | acht ssh-Werkzeuge gleichzeitig, jedes mit mehreren Verbindungen: sshd nimmt nur begrenzt viele gleichzeitige Anmeldungen an (`MaxStartups`) und wirft darüber hinaus zufällig ab |
| 0.7.13 `commands:UNGEPRUEFT` | drei `doctor.py`-Läufe machen je ein `git fetch` im selben Repo und streiten um dieselbe Ref-Sperre |

**Der wichtigste Fehler war keiner von Parallelität, sondern von Bash:** `warte_auf` benutzte
`wait <pid>`, die Phasen ernten aber als `VAR=$(ernte k)`. In dieser Kommandosubstitution ist
der Auftrag **kein Kind der Subshell** — `wait` kehrt sofort zurück, ohne gewartet zu haben.
Die Phase las die noch leere Ausgabe und meldete „nicht gelaufen", während das Werkzeug daneben
weiterlief. Beweis: die `.rc`-Dateien von `prio-ref` und `sicht-drift` trugen einen Zeitstempel
**nach** dem Ende des Runners (`SESSION_CHECKS_VORLAUF_BEHALTEN=1`). Seitdem wartet `warte_auf`
zusätzlich auf die `rc`-Datei, die der Auftrag als Letztes schreibt und die von jeder Shell aus
sichtbar ist.

**Konsequenz — drei Spuren mit eigener Breite:**

| Spur | Breite | Wer | Schalter |
|---|---|---|---|
| `frei` | 8 | gh-API, HTTP, rein lokale Prüfer | `SESSION_CHECKS_PARALLEL` |
| `ssh` | 3 | die neun Werkzeuge, die Verbindungen zu Prod-Hosts öffnen (per `grep` bestimmt, nicht geschätzt) | `SESSION_CHECKS_PARALLEL_SSH` |
| `git` | 1 | `cc-skill-dist/doctor.py` (je Lane), `sichtbarkeits_drift_melder.py` — beide mit `git fetch` in `$PLATFORM_DIR` | `SESSION_CHECKS_PARALLEL_GIT` |

`SESSION_CHECKS_PARALLEL=1` schaltet den Vorlauf ganz ab: `ernte` führt den Befehl dann an
seiner Phasenstelle aus, also exakt im alten Ablauf. Das ist der Vergleichsmaßstab für jede
weitere Messung — gleicher Code, ein Schalter.

**Und eine dritte Falle, die nichts mit Netz zu tun hatte:** die erste Umsetzung drosselte am
**Startpunkt** — `vorlauf` blockierte, solange die Spur voll war. Damit hielt die schmale
ssh-Spur (3 Plätze, 9 Aufträge) den Start aller übrigen Aufträge auf: 0.7.4 lief danach immer
noch seine vollen 33,5 s allein, weil es erst startete, als die ssh-Spur fast durch war
(157,2 s gesamt statt 108,3 s). Jetzt sammeln die `vorlauf*`-Funktionen nur ein;
`_vorlauf_loslegen` startet je Spur so viele Arbeiter, wie sie breit ist, und jeder geht seine
Aufträge der Reihe nach durch. Der Hauptlauf blockiert nie.

Beide Betriebsarten sind gegen eine kleine Positivkontrolle geprüft (fünf Schlafaufträge über
drei Spuren, zwei absichtlich scheiternde): Ausgaben korrekt zugeordnet, Exit-Codes
durchgereicht, `2>&1` nur dort gemischt, wo die Phase es vorher auch tat — 3 s nebenläufig
gegen 7 s sequenziell. Dabei fiel ein Bash-Fallstrick auf, der im Lauf sonst erst bei der
ersten Spur zugeschlagen hätte: in `local a="$1" b="${M[$a]}"` wertet bash den Index aus,
**bevor** `a` gesetzt ist — unter `set -u` bricht die Funktion mit „a ist nicht gesetzt" ab.
Zwei `local`-Zeilen statt einer.

**Die Lehre, die über diesen Auftrag hinausreicht:** eine Optimierung, die einen Melder leiser
macht, ist keine Optimierung. Die Zeile bleibt gelb, der Inhalt verschwindet — und genau das ist
die Klasse Fehler, die am längsten unentdeckt bleibt. Deshalb ist die Abnahme dieses Umbaus
**nicht** die Laufzeit, sondern der Zeilenvergleich der Summary gegen den sequenziellen Lauf.

## 4. Ein Fehler, der beim Umbau auffiel (0.7.28)

0.7.28 las seinen Exit-Code als `GL_OUT=$(… | tail -1); GL_RC=$?` — das ist der Status von
`tail`, also immer 0. Die drei Zweige darunter (124 = Zeitlimit → SKIP, 2 → SKIP, 1 → WARN)
waren damit seit ihrem Bau unerreichbar: **jede** Lage fiel in den PASS-Zweig, auch ein
Zeitlimit. Der Umbau konnte das nicht mitnehmen, ohne einen bekannt kaputten Vertrag
festzuschreiben; `warte_auf` liefert jetzt den Status des Melders selbst. Folge: die Phase
kippt dort auf WARN, wo sie vorher stumm PASS meldete.

## 5. `/session-ende` — Befund und Eingriff

Dieselbe Mechanik, dieselben Schnitte, **ohne ssh-Spur**: keines der Werkzeuge dieses Laufs
öffnet eine Verbindung zu den Prod-Hosts (geprüft über `drift_check.py`,
`session_abgleich.py`, `verankerung_pruefer.py`, `agent_handover_freshness_check.py`,
`doctor.py`, `befund_journal.py` — die zwei `ssh`-Treffer im Prüfer stehen in Doku-Texten).

**Messung** (`target=platform`, Wanduhr über den gesamten Runner-Aufruf):

| Lauf | Modus | Wanduhr |
|---|---|---|
| G | vorher (Stand `67e6866a`) | **302,5 s** |
| M | nachher (Vorlauf 8 + nebenläufiges `drift_check.py`) | **94,9 s** — −69 % |

Alle 11 Phasen tragen denselben Status wie vorher, mit **einer** Ausnahme: E.5 (Zusagen) stand
in Lauf G auf ⚠️, seither auf ✅. Das ist kein Effekt des Umbaus — der Prüfer liefert dieselbe
Bewertung, wenn man ihn danach dreimal einzeln und in der alten Aufrufform gegen denselben PR
laufen lässt. Der Melder ist ausdrücklich advisory (dokumentierte Präzision 0,50) und fragt
GitHub nach dem Stand der Tracking-Issues, der sich zwischen den Läufen geändert haben kann.

Zeitdominierend sind hier die Zeitbudgets, nicht die Phasenzahl:

| Phase | Budget / Kosten | Eingriff |
|---|---|---|
| E.6 Template-Drift | `timeout 480`, gemessen 254 s | Vorlauf **und** `drift_check.py` selbst nebenläufig (s. u.) |
| E.5 Zusagen | bis 3 PRs × 120 s **nacheinander** | PR-Liste im Vorlauf; die LLM-Läufe laufen untereinander nebenläufig |
| E.10 Sitzungs-Abgleich | `timeout 180` | Vorlauf |
| E.2 Handover-PRs | 60 s + **im Fallback** weitere 90 s | beide Suchen laufen im Vorlauf mit; ausgewertet wird der Fallback unverändert nur, wenn die Body-Suche leer blieb |
| E.1 Deploy-Status | 60 s je berührtem Repo | je Repo ein eigener Auftrag |
| E.9 dist-drift | 3 × `timeout 120` | je Lane ein Auftrag |
| E.7 Dirty-Repos | ein `git status` je Repo unter `$GITHUB_DIR` | Vorlauf |
| **E.8 Worktree-Hygiene** | — | **nicht** nebenläufig: `git worktree prune` verändert den Baum |

E.2 kostet dabei bewusst **einen gh-Aufruf mehr pro Sitzung**: der Datei-Fallback läuft immer
mit, statt im Bedarfsfall eine zweite Wartezeit von bis zu 90 s aufzumachen.

**Die Phase allein nebenläufig zu starten genügte hier nicht.** Nach dem Vorlauf brauchte der
Lauf noch 263,8 s — davon 254,3 s für E.6 allein und 9,5 s für die übrigen zehn Phasen
zusammen (vorher ≈ 53 s). Der Hauptverursacher war damit kein Ablauf mehr, sondern **ein
Werkzeug**: `scripts/drift_check.py` prüft die Repos der Registry nacheinander, und jede
Prüfung ist fast nur Wartezeit auf die GitHub-API. `check_repo` hält keinen Zustand — kein
Cache, keine veränderliche Modulvariable —, also laufen die Repos jetzt über einen
`ThreadPoolExecutor`:

| Lauf | Modus | Wanduhr | Ausgabe |
|---|---|---|---|
| `DRIFT_CHECK_PARALLEL=1` | sequenziell | **259,1 s** | Vergleichsmaßstab |
| Standard (6) | nebenläufig | **91,9 s** — −65 % | **zeichengleich**, bis auf die Minute im Kopf |

Die Breite ist klein und über `DRIFT_CHECK_PARALLEL` einstellbar: GitHub drosselt oberhalb
einer gewissen Gleichzeitigkeit, und ein gedrosselter Aufruf liefert `None` statt eines
Inhalts — also eine Drift, die keine ist. Eingesammelt wird in Reihenfolge der Registry, nicht
in Reihenfolge des Eintreffens; Ausgabe-Reihenfolge und -Wortlaut bleiben deshalb gleich.

## 6. `/session-retro` — kein Runner, sondern Wartepunkte

Die Retro hat kein Skript, das man messen könnte; ihre Laufzeit steckt in **Runden**: jeder
Subagent, auf den gewartet wird, bevor der nächste startet, ist eine eigene Wartezeit. Bei
Footprint `full` waren das bis zum 2026-09-22 drei Finder (Phase 2) und bis zu drei Skeptiker
(Phase 3), jeweils nacheinander — **sechs** Wartepunkte auf dem kritischen Pfad, plus die
Sammel-Befehle aus Phase 1 einzeln abgesetzt.

Die Dimensionen wissen nichts voneinander, und die Skeptiker ziehen ihre Belege ohnehin
unabhängig neu (Eiserne Verify-Regel). Phase 2 und Phase 3 starten ihre Subagenten deshalb
jeweils in **einer** Nachricht, Phase 1 bündelt ihre Sammel-Befehle. Kritischer Pfad: **6 → 2**.

Was dabei ausdrücklich **nicht** angefasst wurde: das Agenten-Budget aus 0.1 (es zählt Agenten,
nicht Runden), die Zahl der Dimensionen, die Widerlegungsbahn 3b, die Streichbahn 7, der
Meta-Agent in 5 und die 20 Zeilen der Abschluss-Checkliste — sie hat eine 21. dazubekommen.
Die einzige Reihenfolge-Pflicht in Phase 1 bleibt die Frisch-Checkout-Regel: `git fetch` vor
jedem `log`/`show` **desselben** Repos; zwischen verschiedenen Repos gibt es keine.

## 7. Wo der Boden liegt

| Skill | Gemessen | Nicht weiter verkürzbar ohne Semantik-Eingriff |
|---|---|---|
| `/session-start` | 263,3 s → **108,3 s** | ≈ 62 s Kopf (0.1–0.4.1) + die langsamste ssh-Dreiergruppe (≈ 30 s) |
| `/session-ende` | 302,5 s → **94,9 s** | E.6 bleibt mit 86 s die Einzelphase, an der alles hängt |
| `/session-retro` | 6 → **2** Wartepunkte | zwei Agenten-Runden plus die Phasen, die der Lotse selbst macht (0, 3.5, 4, 7) |

Wer weiter will, muss an die Inhalte: `0.4.5 auto-reap` (25 s) ließe sich nebenläufig starten,
wenn man in Kauf nimmt, dass `sichtbarkeits_drift_melder.py` dabei lokale Klone zählt, die
gerade abgeräumt werden. Das ist ein Tausch von Laufzeit gegen Melder-Genauigkeit und gehört
dem Owner vorgelegt, nicht still entschieden — Refs
[#3379](https://github.com/achimdehnert/platform/issues/3379) mit den drei möglichen Antworten.
