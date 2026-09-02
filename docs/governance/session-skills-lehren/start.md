# Lehren, Herleitungen und Historie — `/session-start`

> Begleitdoku zu `.windsurf/workflows/session-start.md`
> ([platform#2690](https://github.com/achimdehnert/platform/issues/2690), Kriterium **K5**
> Kontext-Diät). Der Skill trägt die **Anweisung**, diese Datei das **Warum**.
> Nichts hier ist gelöscht — jeder Abschnitt ist der wörtliche Text, der bis
> 2026-09-02 im Skill stand, mit Überschrift = Ursprungsstelle + Datum.
>
> **Ein Link ist kein Leser** (Advocatus Diabolus D1 des Streichplans): Regeln, die
> eine Handlung im selben Moment verbieten, sind **nicht** hierher gewandert — sie
> stehen weiter als imperative Zeile im Skill. Hier steht nur die Herleitung.

---

## runner-motiv

**Ursprung:** `session-start.md`, Präambel zu Phase 0, Stand 2026-07-18 (platform#1167).

> **Deterministischer Runner (NEU 2026-07-18 — Ausführungstreue-Programm, platform#1167):**
> Die mechanischen Unterphasen 0.0–0.9 (außer 0.4.3 Worktree-Modus + 0.8 Modell-Tier,
> beides Judgment) laufen in **einem** Skript-Aufruf. Einzelne Phasen sind damit
> strukturell nicht mehr überspringbar — das Skript läuft immer bis zur Summary durch.
> Die Einzel-Befehle leben in `platform/tools/session_start_checks.sh` (dort gepflegt,
> hier NICHT duplizieren — Retro c494a2: lange Phasenlisten werden überflogen).

---

## journal-und-repo-spalte

**Ursprung:** `session-start.md`, Phase 0.R, Erläuterungen zur Summary-Tabelle und zum
Befund-Journal (2026-08-16 / 2026-08-23).

→ **Die Spalte `Repo` nennt das Repo, um das es GEHT** — nicht das, in dem die Sitzung
  läuft (NEU 2026-08-16, [#2004](https://github.com/achimdehnert/platform/issues/2004)).
  Ein roter Deploy in `cad-hub` ist ein Befund über `cad-hub`, auch wenn er in einer
  platform-Sitzung auftaucht. Diese Unterscheidung fehlte, und der Befund blieb liegen:
  fünf offene `[deploy-health]`-Issues, bis zu 10 Tage alt, **alle in `platform`**,
  alle über andere Repos, keins bearbeitet.
→ **Der Befund-Journal-Block darunter zeigt das Alter** (`⏳ ALTBEFUND … N Laeufe,
  erstmals …`) — eine WARN-Zeile am zehnten Tag klang bis dahin wie eine am ersten.
  Ein Altbefund gehört mit seinem Alter ins Board, nicht als Neuigkeit. Vollbild:
  `python3 platform/tools/befund_journal.py --bericht`.
→ **Drei Lautstärken seit 2026-08-23** ([#2215](https://github.com/achimdehnert/platform/issues/2215)):
  `⏳ ALTBEFUND` = niemand hat je entschieden · `⏸ … ruhen bis zur Wiedervorlage` = verankert
  oder mit Verzicht abgelegt, kommt zur Frist von selbst zurück · `⏰ WIEDERVORLAGE` = die
  Frist ist abgelaufen, der Stand gehört geprüft. Verankern setzt die Frist automatisch
  (14 Tage, Verzicht 30, `--frist N` überschreibt). Ändert sich der Symptomtext, wird der
  Befund sofort wieder laut — eine Parkerlaubnis gilt dem Befund, der beim Parken vorlag.
→ Nennt der Block **Fremd-Repo-Befunde ohne Artefakt**, ist das kein Sofort-Auftrag:
  `/session-ende` Phase 0f fragt sie ab und verlangt je Befund entweder ein Issue im
  **Zielrepo** oder einen abgelegten Verzicht mit Grund.
→ **RESULT: FAIL** (einziger Hard-FAIL: pgvector-Tunnel, Phase 0.5) → Session NICHT
  fortsetzen, bis behoben — **kein** Fallback auf lokales Memory (ADR-154).

---

## warn-klassenkunde

**Ursprung:** `session-start.md`, Phase 0.R, Liste „Jede ⚠️ WARN-Zeile ist ein Befund".
Der Skill trägt die Deutung seit 2026-09-02 als Tabelle; hier stehen die vollständigen
Herleitungen mit Realfällen, Zahlen und Daten.

### 0.3 modellwechsel

  - `0.3 modellwechsel` (NEU 2026-09-02, K2 [#2690](https://github.com/achimdehnert/platform/issues/2690)):
    Maßstab ist **„bewertet mit" (assessed_with in den Policy-Kopfzeilen) ↔ „läuft mit"**
    — **nicht** Vorgänger ↔ Nachfolger. `model-changes.log` trägt nur den settings-Alias
    (z.B. `fable`, `opus`), **nicht** die Gewichtsmatrix; „läuft mit" kommt deshalb primär
    aus dem neuesten Session-Transkript (letzte assistant-Zeile mit `message.model`), die
    Alias-Tabelle ist nur der letzte Fallback und markiert sich im Bericht als Warnung.
    Zwei Befundklassen: **MAJOR** ggü. bewertet = Vollmachten suspendiert (Runbook §3a) bis
    Kapitäns-Wort, den §2-Köder in dieser Sitzung fahren, Kommentar auf
    [#1640](https://github.com/achimdehnert/platform/issues/1640) · **MINOR** = nur
    Smoke (§1) fällig, `assessed_with` im nächsten Ritual nachziehen. Ein Rücksprung
    **auf** das bewertete Modell ist **KEIN** Ereignis. Der Runner fährt Smoke (§1)
    bei Fälligkeit selbst und markiert nur bei grünem Smoke als behandelt — rot bleibt
    fällig, statt sich selbst gesundzuschreiben. Werkzeug: `tools/modellwechsel_check.py`,
    Klassifizierer ist eine Portierung aus `model_change_detector.sh`
    ([#2655](https://github.com/achimdehnert/platform/issues/2655)/[#2664](https://github.com/achimdehnert/platform/issues/2664)),
    nicht neu erfunden.

### 0.4 GUARD

  - `0.4 … GUARD(dirty/branch=…)`: fremde Session möglich — Repo NICHT stashen/switchen
    (ADR-233 + 🌀 Shared-Worktree-Kollision), read-only weiterarbeiten.

### 0.7.6 leseflaeche

  - `0.7.6 leseflaeche`: Befunde des **nächtlichen** `handover-reconcile` — meist
    Prio-Zeilen, die auf Geschlossenes zeigen. Sie sind **vor** dem Arbeitsbeginn
    nachzuziehen, nicht danach (dieselbe Klasse wie 0.7.4). Erledigt oder bewusst
    ignoriert? → `python3 platform/tools/hooks/befund_leseflaeche.py --alle-gesehen`,
    sonst erscheinen sie jede Sitzung erneut. Die Zeile `◌ … NICHT pruefbar` ist
    **kein** Befund, sondern die Abdeckungslücke: der Workflow-Token sieht die
    privaten Repos nicht (NEU 2026-08-16,
    [#2006](https://github.com/achimdehnert/platform/issues/2006)).

### 0.7 failure

  - `0.7 failure:<repos>`: je Repo Deploy-Log lesen + User informieren —
    🌀 `feedback_deploy_green_not_change_live`: run-conclusion allein belegt nicht,
    dass die Änderung live ist. Optional als error_pattern sichern (/session-ende Phase 2).

### 0.7 waiting über 24 h

  - `0.7 waiting>24h:<repos>`: **stiller Prod-Blocker** — ein Run haengt an einem
    Environment-Approval-Gate und belegt die Concurrency-Group weiter; jeder spaetere
    Deploy steht als `pending` mit 0 Jobs und erreicht Prod nie, ohne dass ein Check
    rot wird. `gh run cancel` wirkt dort NICHT. Aufloesen ueber das Gate des ALTEN Runs:
    `gh api repos/<o>/<r>/actions/runs/<id>/pending_deployments -X POST -F 'environment_ids[]=<envid>' -f state=rejected`
    (Realfall 2026-07-21 ausschreibungs-hub: Merge #159 war 9 Tage nicht live).
    **`state` erst nach einem Blick auf den Commit waehlen, nicht reflexhaft `rejected`:**
    ist der wartende Run *ueberholt* (sein Stand steckt laengst in HEAD), gehoert er
    abgelehnt — ein Approve wuerde einen alten Stand nach Prod schieben. Ist er dagegen
    der **neueste** Run, ist `approved` die richtige Antwort; `rejected` wirft dort genau
    den Deploy weg, den man haben wollte. Billigster Check:
    `gh run view <id> --json headSha,displayTitle` gegen `git log origin/main -1`.

### 0.7 bewusst abgelehnte Freigabe

  - `0.7 … bewusst abgelehnte Freigabe (kein Befund):<repos>`: **kein Handlungsbedarf.**
    Eine mit `rejected` geschlossene Environment-Freigabe zaehlt GitHub als `failure`;
    bei docs-only-Merges ist genau das der gewollte Weg (Gate zu, Concurrency-Group
    frei). Der Scan trennt das ueber den Approval-Eintrag des Runs — echte Fehlschlaege
    haben keinen. Nur wenn eine Ablehnung *nicht* beabsichtigt war, ist sie ein Befund.

### 0.7.7 gate-wirkung

  - `0.7.7 gate-wirkung`: **ein gebautes Gate hat versagt** — der Befund kam nach dem
    Bau des Gates mindestens 2× wieder. Das ist **kein** Punkt für „später mal": es heißt,
    dass eine Regel, auf die sich der Loop verlässt, nachweislich nicht trägt. Vollbild:
    `python3 platform/tools/gate_wirkung.py`. Behandlung gehört in die Retro (Phase 4,
    Punkt 5a) — hier zählt nur, dass es **gesehen** und im Board benannt wird. Zeilen mit
    `zu-frueh`/`unerprobt` sind ausdrücklich **kein** Wirksamkeits-Beleg, sondern
    „hatte noch keine Gelegenheit".

### 0.7.11 erreichbarkeit

  - `0.7.11 erreichbarkeit`: **die einzige Phase, die ein Ziel anfragt statt Zusagen zu
    vergleichen.** Jedes aktive `domain_prod` aus `infra/ports.yaml` bekommt einen HTTPS-GET.
    Zwei Befundklassen, die auseinandergehalten gehören: **5xx** = Route steht, Dienst tot
    (Reparatur im Ziel-Repo) · **NXDOMAIN** = die *Deklaration* ist falsch, der Dienst
    vielleicht gesund (Korrektur in `ports.yaml`). 401/403 sind **kein** Befund — hinter
    Cloudflare Access antwortet der Perimeter, und dass jemand antwortet, ist der Beleg.
    Ein bewusst abgeschalteter Dienst bekommt `betriebsstatus:` + `betriebsstatus_grund:`
    in `ports.yaml`; **ohne Grund ist die Ausnahme selbst der Befund**. Anlass: wedding-hub
    war 6–7 Tage tot, während Registry und Tunnel-Route übereinstimmten.

### 0.7.16 origin-tls

  - `0.7.16 origin-tls`: **0.7.11 fragt am Edge, diese Phase misst am Origin.** Eine 200
    vom Edge ist kein TLS-Beleg — Cloudflare steht auf `full`, nicht `full (strict)`, und
    liefert vor einem abgelaufenen Origin-Zertifikat eine tadellose 200 aus. Drei Klassen
    auseinanderhalten: **`abgelaufen`/`laeuft-ab`** = das Renewal ist kaputt (Reparatur auf
    dem Host, `certbot`-Token prüfen) · **`fallback-zertifikat`** = nginx antwortet mit
    seinem Platzhalter, für diesen Namen existiert am Origin **gar kein** Zertifikat
    (fehlender vhost/cert — die Domain lebt nur von Cloudflares `full`-Modus) ·
    **`nicht-messbar`** = ssh/Handshake gescheitert, ausdrücklich **kein** Grün.
    `cloudflare-origin-ca` (Laufzeit bis 2041) und `kein-tls-am-origin` (Tunnel-Host ohne
    TLS-Terminierung, z.B. `prod-b`) sind **kein** Befund. Anlass: ausschreibungs-hub
    2026-08-23 — certbot-Token seit dem 08.08. ungültig, 10 von 15 Origin-Zertifikaten
    abgelaufen, zwei Wochen lang kein einziger roter Melder.

### 0.7.17 backup-deckung

  - `0.7.17 backup-deckung`: **geht vom Host aus, nicht von einer Liste.** `backup-meter`
    prüft die Apps aus `expected-apps.json`; was dort nicht steht, ist für ihn unsichtbar —
    so lagen acht Volumes ohne Snapshot da ([#2086](https://github.com/achimdehnert/platform/issues/2086)),
    während der Meter grün war. Jedes Volume aus `docker volume ls` braucht eine von vier
    Antworten: `pgdump` (Container-Dump < 26 h) · `volumes` (Sammel-Snapshot < 26 h) ·
    `verzicht` (`governance/backup/volume-verzicht.yaml`, **mit** Grund) · `anonym`
    (Docker-Scratch, gezählt, nicht bewertet). Alles andere ist **UNGEDECKT** und der
    Befund. Drei Lagen je rotem Volume: *in Nutzung* (läuft, wird nicht gesichert —
    ins Backup-Skript), *Container steht* (`Links` zählt gestoppte mit — Dienst prüfen),
    *verwaist* (löschen oder verzichten, Owner). `NICHT messbar` = ssh/restic gescheitert,
    **kein** Grün. Erstlauf 2026-08-25: 46 Volumes, 7,2 GB, darunter drei doc-hub-Volumes
    in Nutzung ([#2284](https://github.com/achimdehnert/platform/issues/2284)).

### 0.7.18 speicher

  - `0.7.18 speicher`: **Vorlaufzeit statt Schwelle.** Je (Host, Mount) ein Tagespunkt
    im Journal, Rate = Median der Tagesdifferenzen, WARN unter **7 Tagen bis voll** oder
    unter 10 % frei. `SAMMELPHASE n/2` heißt „noch keine Rate", nicht „alles gut" — die
    10-%-Untergrenze gilt trotzdem; `vorläufig` = Rate aus einem einzigen Tagespaar.
    Alle Hosts mit ssh, auch der Offsite-Host: eine volle Offsite-Platte beendet das
    Backup lautlos. Anlass: das reparierte dev-hub-Backup schrieb ab 2026-08-24 rund
    6,3 GB/Tag auf die Root-Platte von prod — sieben Tage bis voll, kein Melder
    ([infra-deploy#5](https://github.com/achimdehnert/infra-deploy/pull/5)).

### 0.7.12 prod-wirkung

  - `0.7.12 prod-wirkung`: **zwei Zustände, die gleich aussehen und es nicht sind.**
    `RUECKSTAND:` heißt, dass hinter dem öffentlichen Namen ein anderer Stand läuft als
    in `main` — das ist der Befund. `wartet auf Prod-Freigabe (kein Befund):repo(Nd)`
    dagegen ist der **Normalfall** eines Repos mit Prod-Gate: sein Deploy geht bei push
    nur nach staging, Prod verlangt eine bewusste Freigabe, und bis zur Frist von
    **14 Tagen** ist ein Rückstand dort gewollt. Danach kippt dieselbe Zeile nach
    `RUECKSTAND:` — denn ab da ist „wartet auf Freigabe" nicht mehr von „vergessen" zu
    unterscheiden. Unterdrückt wird nichts: ein Prod-Gate schließt einen echten Fehler
    nicht aus (`hat_prod_gate` begründet das am tax-hub-Fall — Gate **und** roter Build).
    Anlass: risk-hub stand 23 Läufe lang als WARN, worin ein echter Fund untergegangen
    wäre.

### 0.4.1 BLOCK-Findings

  - `0.4.1 BLOCK-Findings`: zuerst fixen, bevor weitergearbeitet wird.

### 0.7.23 melder-register

  - `0.7.23 melder-register` (NEU 2026-09-02, [#2690](https://github.com/achimdehnert/platform/issues/2690)
    K3): fehlt einer Runner-Phase der Eintrag in `governance/melder-register.yaml`
    oder trägt sie dort `leser: UNBENANNT`, ist das ein Melder, der niemanden
    erreicht — genau die Zahl "Melder ohne Leser" aus Audit #2606. Ein
    Register-Eintrag ohne passende Runner-Phase (Karteileiche) gehört entfernt.
    Vollbild/Reparatur: `python3 platform/tools/melder_register_check.py --kurz`.

### Vierte Lautstärke `ℹ️ HINWEIS`

  - **Vierte Lautstärke `ℹ️ HINWEIS` (NEU 2026-09-02, #2690 K3):** eine Phase, deren
    Trefferquote laut `tools/befund_journal.py --praezision` über mindestens
    `mindest_laeufe` (Register-Default 5) beurteilte Läufe unter `praezision_min`
    (Default 60 %) liegt, stuft sich selbst herab — `record()` wandelt ihre
    nächste `WARN`-Zeile in `HINWEIS` um (Note-Präfix `(herabgestuft: Trefferquote
    X % über N Läufe)`). **Lesen, aber nicht als Befund ins Board zwingen:**
    solange die Trefferquote unter der Schwelle liegt, ist der Melder selbst der
    Befund (behandeln in `/session-ende`/`/session-retro`, nicht jede einzelne
    Zeile). `ℹ️ HINWEIS` zählt in der Summary-Tabelle **nicht** als `⚠️ WARN`. Die
    Herabstufungsdatei (`~/.claude/hooks/state/melder-herabgestuft.tsv`, von
    `--herabstufung` nach Phase 0.7.19 geschrieben) wirkt erst im **nächsten**
    Lauf — 0.7.19 misst spät im Lauf, `record()` liest sie ganz am Anfang.

### Block „⏳ ohne Entscheidung > 14 d"

  - **Block „⏳ ohne Entscheidung > 14 d" (NEU 2026-09-02, #2690 K3):** eigener
    Abschnitt nach dem Befund-Journal-Block, aus `tools/melder_register_check.py
    --ohne-entscheidung`. Ein Befund ohne Artefakt und ohne Verzicht, dessen
    `erstmals` länger als 14 Tage zurückliegt, steht hier — der Unterschied zu
    einem frischen `⏳ ALTBEFUND` ist die Frist, nicht nur das Alter: der Melder
    hat funktioniert, es fehlt an einer Entscheidung.

---

## troubleshooting

**Ursprung:** `session-start.md`, Phase 0.R, Block „Troubleshooting (Lessons aus den
Alt-Phasen — gelten unverändert)".

- **Runner hängt >5s vor der ersten Ausgabe-Zeile:** Shell blockiert! In CC: Session neu
  starten; in Windsurf: `/windsurf-clean`. Bis dahin NUR `Read`/`Write`/`Edit` + stabile
  MCP-Tools (`mcp__github__*`, `mcp__outline-knowledge__*`) nutzen;
  `mcp__github__get_file_contents` + `mcp__github__push_files` als Git-Workaround
  (Lesson 2026-04-05: Shell-Hang kann ganze Sessions blockieren, Edit-Tools zeigen
  dann ggf. "empty file").
- **NIEMALS `ping`** für Server-Checks — Hetzner blockt ICMP (100% packet loss ist
  NORMAL); der Runner nutzt `server_probe.py` (TCP 22/80/443). Server trotzdem nicht
  erreichbar → `ssh -o ConnectTimeout=10 -o BatchMode=yes root@88.198.191.108 "uptime"`;
  scheitert auch das: Hetzner Cloud Console → Server-Status (Lesson 2026-04-03:
  Ping-Diagnose führte zu Fehldiagnose "Server down").
- **pgvector-Tunnel:** devuser hat KEIN sudo-Passwort (AGENT_HANDOVER §2) — der Runner
  versucht erst `sudo -n systemctl start ssh-tunnel-postgres`, dann den direkten
  ssh-Tunnel (Ziel-Port aus AGENT_HANDOVER §7). Beides scheitert → mit sudo-Rechten:
  `sudo systemctl start ssh-tunnel-postgres`.
- **Stash-Semantik (0.4):** Der Runner stasht grundsätzlich NICHT (Guard statt Stash) —
  die alte Auto-Stash-Logik poppte 2× fremde Stash-Einträge (Drift 2026-06-10 +
  2026-06-22, untracked-only-Falle). Dirty Target-Repo = bewusste Handentscheidung.
- **ADR-156 rot (0.6):** MCP-Server neustarten, dann `verify-adr156.sh` erneut prüfen.
- **Neues Repo erkannt** → Eintrag in `platform/scripts/repo-registry.yaml` ergänzen.

> **Anmerkung zum Windsurf-Zweig (2026-09-02):** `/windsurf-clean` ist ein Rest der
> Windsurf-Ära. `~/.claude/policies/claude-skills.md` Z. 10 hält fest, dass Windsurf
> **nicht mehr zum Coden** genutzt wird (ausschließlich das Review-Subset, ADR-229) —
> im Skill steht deshalb nur noch der CC-Zweig „Session neu starten".

---

## worktree-ziel

**Ursprung:** `session-start.md`, Phase 0.4.3, Absatz zu `--ziel` (Stand 2026-08-04).

- **`--ziel` ist optional, aber die Antwort auf zwei Fragen, die sonst geraten werden:**
  „warum existiert dieser Branch?" (Wildwuchs) und „welche PRs gehören zu dieser Sitzung?"
  (Retro-Grenze). **Kein Zwang** — ein Pflichtfeld wäre eine Hürde vor jeder Kleinigkeit, und
  eine erzwungene Ein-Thema-Regel hätte am 2026-08-04 eine zusammenhängende Kette
  (Messung → Konzept → Code → Retro) in vier Sitzungen zerschnitten, deren Wert gerade in den
  Übergängen lag. Das Ziel bleibt über alle Aufgaben derselben Sitzung gleich; wechselt es
  wirklich, ist ein neues Ziel die ehrlichere Antwort als ein gedehntes.

**Warum 0.4.4 ein eigenes Anti-Pattern trägt** (Ursprung: `session-start.md`, Anti-Patterns,
letzter Bullet): Der Abstand ist die einzige Kollisionswarnung, die auch bei
**selbst**verschuldeter Drift greift; die Parallel-Session-Sicht (0.4) tut das nicht.

> **Rollout:** Der harte Snap-back-Guard (`main-tree-guard.sh install`) wird **erst** scharf geschaltet,
> wenn die branch-switchenden Skills (`hotfix`, `issues-abarbeiten`, `ship`) + lebende Sessions migriert
> sind — sonst bricht er laufende Abläufe. Bis dahin: Konvention + `repo-session` als Einstieg.

---

## modell-routing

**Ursprung:** `session-start.md`, Phase 0.8, Begründungsabsatz (Stand 2026-07-02).

**Vor dem ersten Arbeits-Schritt einmal bewusst routen** — nicht per Default auf dem
teuersten Modell bleiben (Policy-Realfall: $1577 in 48h für Tier-3-Arbeit auf Tier-4-Modell)

→ Mid-Session runterschalten, wenn der anspruchsvolle Teil erledigt ist (`/model`).
→ Faustregel: **Fable orchestriert, delegiert Mechanik als Sonnet-Subagents/-Issues** —
  nicht Fable die Mechanik selbst tippen lassen.

SSoT der Tabelle ist `~/.claude/policies/session-routing.md`.

---

## error-learning-template

**Ursprung:** `session-start.md`, Phase 2.5, Block „Auto-Issue-Template (für 5×+
Occurrences)". **Gestrichen 2026-09-02** (Streichkandidat S1 des K5-Streichplans).

*Beleg der Streichung:* Label `auto-detected` hat über alle Zustände **2** Issues, davon
genau **einer** aus diesem Template (#82, erstellt 2026-04-30, geschlossen 2026-08-20).
In 125 Tagen kein zweites Artefakt — das Template hat faktisch nie gefeuert. Im Skill
bleibt die Auswertungstabelle (3–4× / 5–9× / 10×+) und ein Satz zur Issue-Erzeugung.

Wortlaut, wie er bis 2026-09-02 im Skill stand:

**Auto-Issue-Template** (für 5×+ Occurrences):

```
# Owner aus dem git-Remote ableiten, nicht hardcoden:
#   OWNER=$(git remote get-url origin | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$#\1#')
mcp__github__list_issues(labels=["adr-candidate", "auto-detected"], state="open")
# Nur erstellen wenn gleiche entry_key nicht schon offen

mcp__github__create_issue(
    owner="<OWNER>", repo="platform",
    title=f"[adr-candidate] Recurring: {symptom[:60]}",
    body=f"**Occurrences:** {count}× (seit {first_seen})\n"
         f"**Last:** {last_occurred_at}\n\n"
         f"**Symptom:** {symptom}\n"
         f"**Root Cause:** {root_cause}\n"
         f"**Bisheriger Fix:** {fix}\n\n"
         f"→ Fix löst Symptom, nicht Root Cause. ADR für strukturelle Lösung nötig.",
    labels=["adr-candidate", "auto-detected", "agent-learning"]
)
```

**Status-RESOLVED Filter:** Tags mit `resolved` aus Output filtern (bereits behobene Patterns).

---

## handover-memory-reconciliation

**Ursprung:** `session-start.md`, Phase 2.6, Lesson-Blockquote (2026-06-24).

> **Lesson 2026-06-24 (iil-klickdummy):** Arbeit auf einem anderen Gerät
> (iPad/claude.ai) aktualisierte das **geteilte pgvector-Memory**, aber **nicht**
> das git-getrackte `AGENT_HANDOVER.md`. Die nächste Session auf dem Dev-Host sah
> eine als „offen" gelistete Prio, die laut Memory längst **erledigt** war — und
> hätte sie fast erneut bearbeitet (~35 KDs Doppelarbeit). Die *verursachende*
> Session läuft nicht durch *unser* `/session-ende` → ein Guard greift nur **hier
> am Start**, nicht am Ende.

---

## startklar-selbstcheck

**Ursprung:** `session-start.md`, Startklar-Checkliste, Lesson-Blockquote (2026-07-15)
und Absatz „Pflicht-Selbstcheck (2-Schritt)".

> **Lesson 2026-07-15 (Retro c494a2):** `session-ende.md` bekam 2026-07-14 eine neue
> Pflicht-Phase (0a-handover-pr), die in derselben Session, die sie brauchte, trotz
> vorliegender Skill-Kopie NICHT ausgeführt wurde — ein langes Multi-Phasen-Dokument
> wird überflogen statt Phase für Phase abgehakt. `session-start.md` hatte bis hierhin
> **gar keine** Abschluss-Checkliste trotz 14 Unterphasen (0.0–0.9) + 3 weiteren Phasen —
> das größte Ausführungstreue-Risiko dieses Skills, weil es JEDE Session zuerst durchläuft.

**Pflicht-Selbstcheck (2-Schritt, NEU 2026-07-15 — Retro c494a2-incr Befund #3):** Diese
Checkliste selbst ließ bei ihrer Erstellung 0.4.3 und Phase 3 aus, weil beide keine
wörtliche "PFLICHT"/"NEU"-Markierung im Titel tragen, obwohl beide faktisch mandatorisch
sind (0.4.3 = ADR-233-Kill-Gate, Phase 3 = das eigentliche Ergebnis des Skills). Reines
Filtern nach dem Stichwort "PFLICHT" übersieht genau solche Phasen. Richtiger Ablauf:
(1) ALLE `##`/`###`-Überschriften oben mechanisch auflisten (`grep -n "^## \|^### "`),
(2) DANN jede einzeln beurteilen, ob sie faktisch mandatorisch ist — nicht nur nach dem
Wort im Titel filtern. Bei einer neuen Pflicht-Phase diese Tabelle im selben PR erweitern,
nicht in einem Folge-Commit "irgendwann".

---

## gestrichen-mcp-quick-reference

**Ursprung:** `session-start.md`, Sektion „MCP-Server Quick-Reference".
**Gestrichen 2026-09-02** (Streichkandidat S5 des K5-Streichplans).

*Beleg der Streichung:* Die Tabellen führen `mcp0_`…`mcp5_`-Prefixe. Der Skill erklärte
sie zwei Zeilen darunter selbst als „Windsurf-Ära und environment-volatil" und benannte
`project-facts.md` als Quelle (existiert: `.windsurf/rules/project-facts.md`). Policy
`~/.claude/policies/claude-skills.md` Z. 10 bestätigt: Windsurf codet nicht mehr. Die
Tabelle war eine Kopie einer als nicht-autoritativ deklarierten Quelle. Im Skill bleibt
eine Zeiger-Zeile.

Wortlaut, wie er bis 2026-09-02 im Skill stand:

## MCP-Server Quick-Reference

> ⚠️ **Prefix ist environment-spezifisch** — immer `project-facts.md` als Quelle nehmen!

### Dev Desktop (adehnert@dev-desktop)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp1_` | orchestrator | Memory, Task-Analyse, Plans, Evaluate, Verify |

### WSL / Prod-Server (Standard-Konfiguration)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | deployment-mcp | SSH, Docker, Git, DB, DNS, SSL, System |
| `mcp1_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp2_` | orchestrator | Memory, Task-Analyse, Agent-Team |
| `mcp3_` | outline-knowledge | Wiki: Runbooks, Konzepte, Lessons |
| `mcp4_` | paperless-docs | Dokumente, Rechnungen |
| `mcp5_` | platform-context | Architektur-Regeln, ADR-Compliance |

> **Claude Code:** stabile Namen `mcp__github__*` / `mcp__orchestrator__*` /
> `mcp__outline-knowledge__*` verwenden — die `mcpN_`-Nummern sind Windsurf-Ära und
> environment-volatil. Signaturen vor Nutzung via `ToolSearch select:<name>` prüfen.

---

## changelog-historie

**Ursprung:** `session-start.md`, Sektion „Changelog". Der Skill trägt seit 2026-09-02
nur noch die letzten drei Einträge (Policy-Änderung aus
[#2696](https://github.com/achimdehnert/platform/pull/2696)); alles Ältere steht hier
wörtlich. Die beiden 2026-09-02-Einträge stehen hier in ihrer **vollen** Fassung, im
Skill gekürzt auf drei Zeilen.

- 2026-09-02: **Phase 0.7.23 `melder-register`** ergänzt
  ([#2690](https://github.com/achimdehnert/platform/issues/2690) K3 „Vorausschauende
  Wartung"). `governance/melder-register.yaml` trägt je Runner-Phase einen Leser, eine
  Wiedervorlage-Frist (Default 14 Tage) und eine Herabstufungsschwelle (60 % Trefferquote
  über mindestens 5 beurteilte Läufe) — `tools/melder_register_check.py` prüft die
  Registry gegen den Runner (`--kurz`), schreibt Selbst-Herabstufungen (`--herabstufung`)
  und meldet Befunde ohne Entscheidung älter als 14 Tage als eigenen Block
  (`--ohne-entscheidung`). Erstlauf 2026-09-02: 26 von 39 Phasen ohne Leser, ehrlich als
  `UNBENANNT` geführt statt erfunden (Audit #2606-Muster). Vierte Lautstärke `ℹ️ HINWEIS`
  eingeführt — ein herabgestufter Melder bleibt lesbar, zwingt aber keine Board-Zeile mehr.
  Startklar-Checkliste um Zeile 2h ergänzt (eine neue WARN-Klasse ohne Checklisten-Zeile
  wäre still überspringbar — Lehre c494a2).

- 2026-09-02: **Phase 0.3 `modellwechsel`** ergänzt (K2,
  [#2690](https://github.com/achimdehnert/platform/issues/2690)). Der Runner vergleicht
  jetzt `assessed_with` aus den Policy-Kopfzeilen gegen das AKTUELL laufende Modell —
  Maßstab „bewertet mit ↔ läuft mit", nicht Vorgänger↔Nachfolger (der Ist-Stand vorher:
  0 Treffer zu Modellwechsel/Rebaseline in allen drei Session-Skills, Runbook hatte 8).
  Bei Fälligkeit fährt der Runner Smoke §1 selbst und markiert nur bei grünem Smoke als
  behandelt; die Klasse (MAJOR/MINOR) folgt der Runbook-§0-Tabelle über den bereits
  bestehenden Klassifizierer aus `model_change_detector.sh` — nicht neu erfunden.
  **Nachtrag selbiger Tag (Review-Befund):** `model-changes.log` trägt nur den
  settings-Alias (`fable`/`opus`), nicht die Gewichtsmatrix — ein reiner Log-Vergleich
  hätte jeden Rücksprung fälschlich als MAJOR gemeldet. Laufendes Modell wird jetzt
  vorrangig aus dem neuesten Session-Transkript gelesen (`--laufend` > Transkript >
  Alias-Tabelle als letzter, gewarnter Fallback). Werkzeug: `tools/modellwechsel_check.py`.
  Startklar-Checkliste um 2g ergänzt (eine neue WARN-Klasse ohne Checklisten-Zeile wäre
  still überspringbar — Lehre c494a2).

- 2026-08-25: **Phasen 0.7.17 `backup-deckung` und 0.7.18 `speicher`** ergänzt
  ([#2284](https://github.com/achimdehnert/platform/issues/2284)). Beide drehen die
  Messrichtung um: nicht „stimmt die Liste mit sich selbst überein?", sondern „was sagt
  der Host?". 0.7.17 verlangt für jedes `docker volume` eine von vier Antworten und fand
  im Erstlauf 46 ungedeckte Volumes (7,2 GB), wo `backup-meter` täglich grün war. 0.7.18
  rechnet aus einem Tagesjournal die Tage bis voll und warnt sieben Tage vorher — Anlass
  war ein repariertes Backup, das die Root-Platte in sieben Tagen gefüllt hätte, ohne dass
  irgendein Melder Platten misst. Startklar-Checkliste um 2e/2f ergänzt (eine neue
  WARN-Klasse ohne Checklisten-Zeile wäre still überspringbar — Lehre c494a2).

- 2026-08-24: **Phase 0.7.16 `origin-tls`** ergänzt — misst auf dem Host, welches
  Zertifikat nginx je Domain wirklich ausliefert (TLS-Handshake gegen `127.0.0.1:443`
  mit der Domain als SNI). 0.7.11 fragt am Edge, und dort ist eine 200 kein TLS-Beleg:
  Cloudflare steht auf `full`, nicht `full (strict)`. Anlass: ausschreibungs-hub
  2026-08-23 — certbot-Token seit dem 08.08. ungültig, 10 von 15 Origin-Zertifikaten
  abgelaufen, zwei Wochen lang kein roter Melder, gefunden beiher. Der **Aussteller**
  wird mitgemessen, weil der Erstlauf drei Betriebsarten hinter derselben grünen 200
  zeigte: Let's Encrypt (kurzlebig, Renewal-Gesundheit), Cloudflare Origin CA (bis 2041,
  kein Befund) und `CN=invalid.localhost` (nginx-Platzhalter = **gar kein** Zertifikat
  für diesen Namen, Laufzeit bis 2036 — eine reine Datums-Prüfung meldet das grün).
  Erstlauf fand zwei Fälle der dritten Klasse. Startklar-Checkliste um Zeile 2d ergänzt
  (eine neue WARN-Klasse ohne Checklisten-Zeile wäre still überspringbar — Lehre c494a2).
- 2026-08-20: **Phase 0.7.7 `gate-wirkung`** ergänzt — meldet Gates, deren Befund nach dem
  Bau mindestens 2x wiederkam. Gemessen über 82 Retros: 8 von 20 Gates rückfällig,
  `claim-before-cheapest-check` 16x seit dem 2026-08-02 trotz verdrahtetem Stop-Hook und
  grünem Drill. Der Sitzungsstart ist der einzige Ort, den jede Sitzung durchläuft — die
  Retro läuft seltener als der Rückfall passiert. Startklar-Checkliste um Zeile 2b ergänzt
  (eine neue WARN-Klasse ohne Checklisten-Zeile wäre still überspringbar — Lehre c494a2).
- 2026-07-18: v3 — Deterministischer Runner `tools/session_start_checks.sh` ersetzt die
  mechanischen Einzel-Blöcke 0.0/0.1/0.2/0.4/0.4.1/0.4.2-Validate/0.5/0.5.1/0.6/0.7/0.9
  (Ausführungstreue-Programm #1167, Retro c494a2: lange Phasenlisten werden beim
  Ausführen überflogen — ein Skript-Lauf ist nicht überspringbar und endet mit
  maschinenlesbarer Summary + RESULT). Judgment-Phasen (0.4.3 Worktree, 0.8 Modell-Tier,
  Architecture Context, Phasen 1–3) bleiben im Skill. Troubleshooting-Lessons der
  Alt-Phasen in 0.R konsolidiert, kein Inhalt ersatzlos gelöscht (Lehre #1122/#1165).
  Startklar-Checkliste 12→8 Rows (alte Rows 1–7 = jetzt Runner-Summary). Runner real
  verifiziert (Lauf 2026-07-18: reproduzierte die Live-Befunde der manuellen Session).
- 2026-07-15 (Nachtrag, Retro c494a2-incr): die frisch angelegte Startklar-Checkliste ließ
  selbst 2 faktisch mandatorische Phasen aus (0.4.3 Worktree-Gate, Phase 3 Arbeitsplan) —
  beide ohne wörtliche "PFLICHT"-Markierung im Titel, weshalb der reine Stichwort-Filter
  sie überging. Rows 11+12 ergänzt, Pflicht-Selbstcheck auf 2-Schritt-Verfahren (erst alle
  Überschriften auflisten, dann einzeln beurteilen) umgestellt.
- 2026-07-15: Neue "Startklar-Checkliste" ergänzt — der Skill hatte trotz 14 Unterphasen
  (0.0–0.9) + 3 weiteren Phasen bisher KEINE Abschluss-Checkliste (anders als
  session-ende.md). Aus Retro `session-retro-2026-07-15-platform-c494a2`: eine lange,
  rein prosaische Phasenliste wird beim Ausführen überflogen statt Zeile für Zeile
  abgehakt, besonders am Session-Anfang unter Zeitdruck. Höchster Hebel aller drei
  session-xxx-Skills, weil er jede Session zuerst durchläuft.
- 2026-07-02: v2.1 — CC-first-Call-Sites vollendet: Phase 1/2/2.5 riefen noch
  Windsurf-Prefix-Tools (`mcp__platform-context__get_context_for_task`, `mcp__deployment-mcp__system_manage`,
  `mcp__outline-knowledge__search_knowledge`, `mcp__orchestrator__agent_memory`, `<orc>_`/`<gh>_`-Platzhalter) — auf
  stabile `mcp__…`-Namen umgestellt (v2 hatte nur die Warnung ergänzt, nicht die
  Aufrufe); Shell-Hang-Fallback (Z.80) + Auto-Issue-Owner (git-Remote statt
  hardcoded) mitgezogen; TODO(mcp-migration)-Marker geschlossen; orchestrator-404-
  Drift-Verweis ergänzt; Testbefehl auf `make test`.
- 2026-07-02: v2 — `mode: write` nachgetragen; Parallel-Session-Guard in 0.4
  (ADR-233 + Shared-Worktree-Drift); 0.5 sudo-freier Tunnel-Fallback (devuser ohne
  sudo); adrfw-MCP-Block environment-aware mit CC-CLI-Fallback (Signaturen-Policy);
  0.7 mit gh-Fallback (deployment-MCP optional); NEU 0.8 Modell-Tier-Routing
  (policies/session-routing.md, Fable/Opus/Sonnet-Split); Anti-Patterns + Changelog
  ergänzt (claude-skills-Policy-Pflichtsektionen).
- ≤2026-06-24: Windsurf-Ära-Stände (Phase 2.6 Reconciliation, Stash-Guards 0.4,
  Drift-Lessons) — Historie siehe git log.
