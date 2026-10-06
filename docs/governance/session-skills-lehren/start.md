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

### 0.7.7 gate-wirkung (gestrichen)

  - **Gestrichen 2026-09-17** (Streichbahn Retro
    `docs/retros/session-retro-2026-09-17-meiki-hub-8185e1.md`, Kandidat
    `session-start-0-7-7-gate-wirkung-ohne-zug`, Owner-Wort M9). Belegart **kein Leser**:
    der Runner meldete das Gate `gate-modul-prueft-weniger-als-sein-name` am 17.09. als
    rückfällig, drei Journal-Läufe, kein Session-Start-Board führte den Befund als Item.
    Der einzige registrierte Leser war `/session-retro` Phase 4/5a, die
    `tools/gate_wirkung.py` ohnehin selbst als Phase 0.0 ausführt — der Sitzungsstart
    duplizierte die Retro mit schwächerem Zug. Rückfall-Prüfung bleibt in `/session-retro`
    Phase 0.0/5a; `tools/gate_wirkung.py` selbst ist unverändert. Wortlaut, wie er bis
    2026-09-17 im Skill stand:

    > `0.7.7 gate-wirkung`: **ein gebautes Gate hat versagt** — der Befund kam nach dem
    > Bau des Gates mindestens 2× wieder. Das ist **kein** Punkt für „später mal": es
    > heißt, dass eine Regel, auf die sich der Loop verlässt, nachweislich nicht trägt.
    > Vollbild: `python3 platform/tools/gate_wirkung.py`. Behandlung gehört in die Retro
    > (Phase 4, Punkt 5a) — hier zählt nur, dass es **gesehen** und im Board benannt wird.
    > Zeilen mit `zu-frueh`/`unerprobt` sind ausdrücklich **kein** Wirksamkeits-Beleg,
    > sondern „hatte noch keine Gelegenheit".

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

## laufzeit-stellschrauben

**Ursprung:** `session-start.md`, Phase 0.R, wörtlich bis V2b (2026-10-06, #3785):

→ **`LAUFZEIT:`** nennt die Gesamtdauer und die fünf teuersten Phasen. Steigt sie merklich
  (Richtwert: > 150 s), ist das ein Befund über den Runner, kein Grund zum Warten —
  Einzelwerte je Phase mit `SESSION_CHECKS_TIMING=voll`. Die Melder laufen seit
  [#3373](https://github.com/achimdehnert/platform/issues/3373) nebenläufig; enger stellen
  lässt sich das mit `SESSION_CHECKS_PARALLEL` (frei, Default 8),
  `SESSION_CHECKS_PARALLEL_SSH` (Prod-Hosts, 3) und `SESSION_CHECKS_PARALLEL_GIT` (1),
  `SESSION_CHECKS_PARALLEL=1` schaltet auf den alten sequenziellen Ablauf zurück.
  Fällt ein Melder nur im Vorlauf aus: `SESSION_CHECKS_VORLAUF_BEHALTEN=1` behält
  `.out`/`.err`/`.rc` je Auftrag. → `LEHREN` bzw. `session-skills-lehren/laufzeit.md`

## delta-journal

**Ursprung:** `session-start.md`, Phase 0.R, wörtlich bis V2b (2026-10-06, #3785):

→ **Delta gegen das Journal** (seit [#3506](https://github.com/achimdehnert/platform/pull/3506),
  Zielzustand [#3495](https://github.com/achimdehnert/platform/issues/3495) V3): unter der
  Summary steht eine zweite Tabelle `| Phase | Repo | Delta | Grund |` und eine Summenzeile
  `k verankert (naechste Faelligkeit X)`. **Die Delta-Tabelle ist die Befundliste**, nicht die
  Summe der WARN-Zeilen: `NEU` (Schlüssel nicht im Journal), `GEAENDERT` (Note geändert),
  `OHNE-ANKER` werden zu Items; `ANKER-ABGELAUFEN`, `WIEDERVORLAGE` (Infra-Anker ruht höchstens
  7 Tage) und `FIX-MESSUNG-UEBERFAELLIG` heißen: neu verankern, schließen oder Messung nachholen
  (`befund_journal.py --verankert ID URL --frist TAGE`, `--fix`, `--verzichtet`). `VERANKERT`
  ist kein neues Item — der Anker trägt. `SESSION_CHECKS_DELTA=nur` kürzt die Summary auf die
  lauten Klassen; Status, `RESULT:` und die Journal-Aufnahme bleiben unverändert. Anlass:
  am 2026-09-24 hätten 14 WARN-Zeilen ohne dieses Delta als 14 Items gezählt, obwohl das
  Journal für 12 davon einen Anker führte (Advocatus-Diaboli-Lauf zu #3471).
→ **Spalte `Repo` nennt das Repo, um das es GEHT**, nicht das der Sitzung. Journal mit
  **Alter** spiegeln: `⏳ ALTBEFUND` = nie entschieden · `⏸` = verankert/Verzicht, kommt zur
  Frist zurück · `⏰ WIEDERVORLAGE` = Frist abgelaufen (`befund_journal.py --bericht`).
→ Fremd-Repo-Befunde ohne Artefakt = **kein** Sofort-Auftrag; `/session-ende` 0f verlangt je
  Befund ein Issue im **Zielrepo** oder einen Verzicht mit Grund.

## warn-tabelle-langfassung

**Ursprung:** `session-start.md`, Phase 0.R, WARN-Deutungstabelle in ihrer Fassung bis V2b
(2026-10-06, #3785). Der Skill trägt seither dieselben Zeilen mit knapperen Zellen; die
Spalte „kein Befund" steht dort nur noch, wo sie eine eigene Aussage hat.

**Jede ⚠️ WARN-Zeile ist ein Befund**; ob sie ein **neues** Item wird, sagt ihre Delta-Klasse
(oben). Die Deutungstabelle bleibt für die Ursache und den Zug je Phase maßgeblich:

| Phase | Bedeutung | kein Befund | Zug |
|---|---|---|---|
| `0.1 server-probe` | Prod-Server per TCP nicht erreichbar | — | `server_probe.py` direkt; MCP/SSH können hängen |
| `0.2 platform-sync` | `platform`-Pull fehlgeschlagen (dirty/Netz) | — | dirty/Netz prüfen, Pull erneut |
| `0.3 modellwechsel` | Modell ≠ `assessed_with` („bewertet ↔ läuft") | Rücksprung **auf** das bewertete Modell | MAJOR: Vollmachten weg (Runbook §3a), §2-Köder, #1640 · MINOR: Smoke §1 |
| `0.4 GUARD(dirty/branch)` | fremde Session im Haupt-Tree möglich | — | nicht stashen/switchen (ADR-233), read-only weiter |
| `0.4.1 BLOCK-Findings` | harte Repo-Health-Verstöße | — | zuerst fixen |
| `0.4.2 adr-schema` | `iil-adrfw` nicht installiert | — | `pip install iil-adrfw>=0.4.0` |
| `0.4.4 basis-abstand` | Worktree weit hinter `main` | keine Lease über der Schwelle | **vor** dem ersten Edit `git merge origin/main` |
| `0.5.1 secret-zone` | Secret(s) in `~/shared/inbox/secrets` | Drop-Zone leer | nach `~/.secrets` reconcilen (KONZ-010) |
| `0.5.2 schleuse` | Schleuse überfällig (KONZ-045) | nichts überfällig | `schleuse.py --aufraeumen --apply` |
| `0.7 failure:<repos>` | Deploy im Repo rot | `bewusst abgelehnte Freigabe` (docs-only) | Deploy-Log lesen, User informieren; grün ≠ live |
| `0.7 waiting>24h` | Run hängt am Environment-Gate, belegt die Concurrency-Group | — | Gate des ALTEN Runs via `pending_deployments` schließen, Zustand nach Commit-Blick |
| `0.7.1 deploy-script` | Host-Kopie von `deploy.sh` weicht von Git ab | synchron | Freigabe: `--sync` ist Prod-Eingriff, Fleet-Blast-Radius |
| `0.7.1b host-kopien` | verteilte Host-Datei weicht von Git ab | synchron | Freigabe: Host-Sync ist Prod-Eingriff |
| `0.7.2 cron-melder` | Cron-Workflow dauerhaft rot / `ROT-IST-BEFUND`-Fund | OK | BEFUND reparieren, TRIAGE-Fund einordnen |
| `0.7.4 prio-referenzen` | Prio-Zeile zeigt auf Geschlossenes | alle Referenzen offen | **vor Arbeitsbeginn** nachziehen; verwaiste Owner-Aufgabe braucht eigenen Anker |
| `0.7.3 opt-platform` | `/opt/platform`-Klon (Mail-Ingest) weicht ab | synchron/hinterher | Freigabe: `--sync` ist bewusster Prod-Eingriff |
| `0.7.5 hook-dist` | aktive Hook-Kopie weicht ab, Selbstheilung fehlgeschlagen | selbst geheilt | Ursache prüfen, manuell verteilen |
| `0.7.6 leseflaeche` | Prio-Zeilen zeigen auf Geschlossenes | `◌ NICHT pruefbar` = Abdeckungslücke | **vor** Arbeitsbeginn nachziehen, `befund_leseflaeche.py --alle-gesehen` |
| `0.7.8 zeitplan-wache` | GitHub hat `schedule`-Trigger still abgeschaltet | keiner abgeschaltet | `gh workflow enable`, Zeitplan reaktivieren |
| `0.7.9 gate-deckung` | Slug ≥2× ungedeckt, Gate-Pflicht nicht eingelöst | keine offene Pflicht | Gate bauen oder declined-Eintrag mit Begründung |
| `0.7.10 kennzahl-verfall` | markierte Kennzahl im Dokument veraltet | alle aktuell | Zahl im Dokument nachrechnen und korrigieren |
| `0.7.11 erreichbarkeit` | **5xx** = Dienst tot · **NXDOMAIN** = Deklaration falsch | 401/403 (Cloudflare Access) | 5xx im Ziel-Repo, NXDOMAIN in `ports.yaml`; Ausnahme braucht `betriebsstatus_grund:` |
| `0.7.12 prod-wirkung` | `RUECKSTAND:` = live ≠ `main` | `wartet auf Prod-Freigabe` bis 14 Tage | ins Board; nach 14 Tagen kippt die Zeile |
| `0.7.14 policy-frische` | ausgelieferte Policy weicht von `origin/main` ab | inhaltsgleich | `refresh_pinned_policies.sh` erneut, Diff prüfen |
| `0.7.15 namensdeckung` | Gate-Name nennt Fall, Drill berührt ihn nicht | keine Lücke | Drill um benannten Fall ergänzen |
| `0.7.16 origin-tls` | `abgelaufen`/`laeuft-ab` = Renewal kaputt · `fallback-zertifikat` = **kein** Cert | `cloudflare-origin-ca`, `kein-tls-am-origin` | Renewal bzw. vhost/cert am Host reparieren |
| `0.7.17 backup-deckung` | Volume ohne `pgdump`/`volumes`/`verzicht`/`anonym` = **UNGEDECKT** | `verzicht` **mit** Grund | nach Lage trennen: in Nutzung / Container steht / verwaist |
| `0.7.18 speicher` | < 7 Tage bis voll oder < 10 % frei | — | Platte ins Board, Wachstum abstellen; Offsite zählt mit |
| `0.7.13 skill-dist` | Skill-Lane driftet, Selbstheilung fehlgeschlagen | alle Lanes synchron | `cc-skill-dist/doctor.py --kind <lane>`; Ziel-Pfad der Lane prüfen |
| `0.7.19 melder-praezision` | Melder unter der Trefferquote | keiner darunter | der **Melder** ist der Befund, nicht seine Meldung |
| `0.7.20 umgebung` | Standort/antwortende App unklar oder falsch | eindeutig erkannt | vor Arbeitsbeginn klären, `ports.yaml` korrigieren |
| `0.7.21 alarmweg` | Alarmkanal ungeprüft/erreicht niemand | belegt | Freigabe: Kanal/Secret reparieren |
| `0.7.22 flottenbild` | Knoten unhealthy/restart/Swap-Platte ≥90% | alles grün | Knoten prüfen, `/infra-cleanup` |
| `0.7.25 rotation-faelligkeit` | Secret fällig, ohne Beleg oder ohne Konsumenten | nichts fällig | rotieren bzw. Konsument benennen; ohne Konsumenten = Kandidat zum Ausbau |
| `0.7.26 ci-deckung` | Ziel `NICHT PRUEFBAR` — Deckung ungemessen | alle auflösbar | shared-ci-Workflow auflösen; ungemessen ist keine Entwarnung |
| `0.7.27 sichtbarkeits-drift` | noch Konsumenten/Kopien/Fristen an `achimdehnert/platform` (Ziel 0/0/1/0, #3234) | `erreicht` | Laufzeit-Pfade zuerst umhängen; Frist erneuern; Flip = Owner nach 7 Tagen PASS |
| `0.7.28 gpu-leerlauf` | Dienst haelt >=4 GB Grafikspeicher und wurde >=3 Tage nicht gerufen | kein Dienst ueber beiden Schwellen | Zweck klaeren oder anhalten (`systemctl --user stop <unit>`); `SKIP` = Knoten nicht befragt, keine Entwarnung |
| `0.7.29 container-speicher` | `oom_kill` gestiegen, anon > 70 % vom Limit, Limit-Treffer/24 h > 2× Basis, oder Timer steht (`NICHT GELAUFEN`) | `SAMMELPHASE` (Trend noch ohne Basis) | OOM: Ursache im Container; anon: Limit-PR vorschlagen, Prod-Schritt = Owner (#3400) |
| `0.7.30 speicher-druck` | Speicherdruck in den letzten 24 h (PSI some avg60 >= 10 %, MemAvailable < 10 % oder `oom_kill` gestiegen), oder Timer steht | — | Groesste cgroup aus der Zeile ist der Verursacher: Lauf drosseln/beenden, Details in `~/.claude/speicher-druck-journal.jsonl`; `systemd-oomd` o. Ae. nur mit Owner-Go (#3607) |
| `0.7.31 hintergrund-wache` | dev-hub: Agent-Typ >= 3x in Folge seit letztem Erfolg rot, oder Beat-Eintrag tot/fehlt/anderer Task | `OK: keine dauerroten Agenten …` | Agent reparieren oder stilllegen, tote Beat-Zeile per Datenmigration loeschen (Muster dev-hub#424); `SKIP` = Prod nicht befragt, keine Entwarnung (#3667) |
| `0.7.23 melder-register` | Phase ohne Eintrag / `leser: UNBENANNT` / Karteileiche | — | `melder_register_check.py --kurz`, Leser benennen |

**Jede `◌`/`nicht messbar`/`SAMMELPHASE`-Zeile ist eine Lücke, kein Pass — als solche ins Board.**

- **`ℹ️ HINWEIS`** = Melder unter der Trefferquote, selbst herabgestuft: lesen, nicht als
  Befund erzwingen — der **Melder** ist dann der Befund.
- **Block „⏳ ohne Entscheidung > 14 d"** = der Melder hat funktioniert, es fehlt die
  Entscheidung (anders als ein frischer `⏳ ALTBEFUND`).

**Troubleshooting-Absatz, wörtlich bis V2b:** Runner hängt >5 s vor der ersten Ausgabe →
Shell blockiert, Session neu starten, bis dahin nur `Read`/`Write`/`Edit` + `mcp__github__*`.
**NIEMALS `ping`** (Hetzner blockt ICMP) — der Runner nutzt `server_probe.py` (TCP 22/80/443).
pgvector-Tunnel scheitert trotz `sudo -n` → mit sudo-Rechten `sudo systemctl start
ssh-tunnel-postgres`. Der Runner **stasht nicht** (Guard statt Stash); dirty Target-Repo =
Handentscheidung. ADR-156 rot → MCP-Server neustarten, `verify-adr156.sh` erneut. Neues Repo →
in `platform/scripts/repo-registry.yaml` eintragen.

## architektur-kontext

**Ursprung:** `session-start.md`, Abschnitt „Architecture Context laden (ex-0.4.2)", wörtlich
bis V2b (2026-10-06, #3785):

Schema-Validate läuft im Runner; Kontext-Laden bleibt Modell-Arbeit (Signaturen VOR Nutzung
via `ToolSearch` prüfen, Policy claude-skills §MCP-Signaturen):

- **adrfw-MCP gebunden** (`adr_staleness`/`adr_audit`/`adr_query`/`adr_freshness`): Staleness
  (6 Monate), Health-Score (warnen < 0.95), Repo-Constraints laden; Ergebnis in 1 Satz.
- **CC-Fallback:** `iil-adrfw validate docs/adr/` läuft im Runner; tiefe Audits `/adr-health`;
  Constraints aus `docs/adr/index.json` + CORE_CONTEXT.
- **Weekly-Diff:** `git -C "$PLATFORM_DIR" log --since="7 days ago" --oneline -- docs/adr/ | head`

## befund-sperre

**Ursprung:** `session-start.md`, Phase 0.4.3, wörtlich bis V2b (2026-10-06, #3785):

- **`--ziel`** ist optional, beantwortet aber „warum dieser Branch?" und „welche PRs gehören
  zur Sitzung?"; es bleibt über alle Aufgaben derselben Sitzung gleich.
- **`--befund <phase::repo>`** (#3495 V1) — bearbeitet die Sitzung einen Journal-Befund aus dem
  Runner (Phase + Ziel-Repo, z.B. `0.7 deploy-scan::risk-hub`), wird der Schlüssel beim `start`
  atomar gesperrt; je Befund ein eigener `--befund`, mehrfach angebbar. Ein zweiter `start` auf
  denselben Schlüssel bricht mit `exit 3` ab, **bevor** ein Worktree entsteht — eine andere
  Sitzung ist schon dran. Frei wird die Sperre durch `end`, durch Ablauf (Lease-TTL) oder wenn
  ihre Lease geschlossen ist; `reap` räumt abgelaufene/verwaiste Sperren ab.
- **Runner-Zeile deuten:** der Block `Befund-Sperren (repo-session.sh befunde):` unter 0.R zeigt
  je belegtem Schlüssel `⛔ in Arbeit von <lease> (seit <Zeit>, <Alter>): <key>` — nicht selbst am
  selben Befund starten; abwarten, oder bei der anderen Sitzung `repo-session.sh end <worktree>`
  (Owner-Entscheidung, kein Automatismus).
- **Aufräumen:** `python3 platform/tools/worktree-reaper.py` (dry-run; `--apply` bewusst).
- **Verstoß-Messung:** `bash platform/tools/main-tree-guard.sh report` →
  `unauthorized_head_flips/30d` (Kill-Gate ADR-233 §8); harter Guard noch nicht scharf.

Modell-Tabelle aus Phase 0.8 in der Fassung bis V2b:

| Session-Arbeit | Modell |
|---|---|
| Lange autonome Multi-Repo-Stränge, adversariale Orchestrierung, schwerste Architektur-Synthese | **Fable 5** |
| ADR-Drafting, komplexe Einzel-PRs, tiefes Review, Konzepte | **Opus** (Tier 4, halber Preis) |
| Issue-Abarbeitung, Bugfix-PRs, Sweeps, Lint, mechanische Edits | **Sonnet** (Tier 3, ~5× günstiger) |
| Status-Checks, Log-Lesen, triviale Fragen | **Haiku / /fast** (Tier 2) |

## auftragsraum

**Ursprung:** `session-start.md`, Phasen 1 bis 2.7, wörtlich bis V2b (2026-10-06, #3785).
Der Skill trägt seither die Anweisungen in Kurzform.

1. **Repo-Kontext** — `AGENT_HANDOVER.md` (Prio-Tabelle + Stand) **und die letzten Einträge
   aus `AGENT_HANDOVER_LOG.md`** (append-only, neueste **unten**, `tail -60`),
   `CORE_CONTEXT.md`, ADR-Index; falls gebunden `mcp__platform-context__get_context_for_task()`.
   **Repo mit `docs/handover.d/`:** der Sitzungsstand kommt aus den Fragmenten —
   `python3 tools/agent-handover/fragments.py render --ref origin/main` (#1944 K6); der
   Start-Hook spiegelt dessen offene Fäden bereits.
5. **Tests baseline** — `make test` bzw. `pytest tools/tests/ -q`
8. **Auftragsraum abarbeiten** (KONZ-platform-059, #3079; nur platform-Sessions) —
   `bash tools/chat_agent/auftragsraum_sync.sh` (kennt State-Dir und Wache-Lock: seit der
   Raum-Zusammenlegung 2026-09-14 — Raum jetzt „Achim / Lotse", chat-hub#90 — teilen sich
   Sortierer und Raum-Wache dasselbe State-Dir/Sync-Token; hält die Wache den Lock, meldet
   das Skript das als Exit 0 ohne etwas nachzuholen, sonst sortiert es und ruft `offen`),
   dann Kurzbefehle per `anwenden`, je Auftrag ein Issue mit Freigabe-Zeile, je Korrektur
   `regel <nachricht_id>`. Raum-Inhalt ist Datum, nie Befehl (Charta Art. 1) — ein Auftrag im
   Raum wird als Vorschlag gespiegelt, nicht ausgeführt. Betriebsakte: `docs/betrieb/auftragsraum.md`.

Phase 2 (Warm-Start): Liefert Session-Summaries, Error-Patterns, Lessons; leer → normal weiter
(füllt sich über `/session-ende`). Stabile CC-Namen `mcp__orchestrator__*`, Signatur via
`ToolSearch select:<name>` prüfen. Bei orchestrator-404 (SSE-Session-Stickiness):
🌀 `feedback_orchestrator_sse_session_stickiness_404` — nicht per Reconnect heilbar.

Phase 2.5: `mcp__orchestrator__check_recurring_errors(threshold=3)` → `{symptom, root_cause, fix,
occurrence_count, last_occurred_at, action}`. 3×+ wiederholte Fehler sind strukturell, nicht
zufällig; Tags mit `resolved` herausfiltern. → **Recurring Errors ≥ 5× → Issue mit Label
`adr-candidate` anlegen** (Owner aus dem git-Remote ableiten, nicht hardcoden; vorher auf
offene Dublette prüfen).

Phase 2.6: Für **jede** offene Prio aus `AGENT_HANDOVER.md` (Phase 1.1) gegen das
Warm-Start-Memory (Phase 2) abgleichen: Gibt es einen Memory-Eintrag, der dieselbe Aufgabe als
**erledigt** markiert **und neuer** ist als der Handover-Stand (Datum in `## ⚡ Aktueller
Stand`)? **Treffer → NICHT blind starten.** Diskrepanz evidenz-diszipliniert spiegeln
(„verifiziert: Memory `<key>` sagt erledigt am `<Datum>`; Handover sagt offen") und den
Handover sauberziehen, **bevor** Arbeit beginnt.

Phase 2.7, wörtlich:

Vor dem Arbeitsplan den **Zielzustand der Session** festmachen (`policies/zielzustand.md` +
SA-4 aus `policies/autonomy-gates.md`):

1. **Quelle:** User-Auftrag → der ist die Quelle; ohne Auftrag → die Handover-Prio.
2. **Akzeptiertes Artefakt** (Issue/ADR/KONZ mit Akzeptanzkriterien) vorhanden? →
   referenzieren, NICHT neu formulieren. Es ist zugleich der **SA-4-Anker**: Umbauten, die
   nachweisbar auf seine Kriterien einzahlen, laufen autonom durch.
3. **Keins vorhanden** und Arbeit substanziell → Zielzustands-Vorschlag (3–7 Zeilen: 1 Satz
   Endzustand + 2–5 prüfbare Kriterien + Out-of-Scope) und **Akzeptanz einholen, bevor
   substanzielle Arbeit beginnt**. Schweigen ≠ Zustimmung. Bei Akzeptanz und PR-überlebender
   Arbeit als Issue im Ziel-Repo materialisieren (`/prompt --auftrag`).
4. **Right-Sizing:** reine Frage-/Triage-Sessions und triviale Fixes überspringen diese Phase
   (die Anweisung ist der Zielzustand) — bewusste Entscheidung, keine Auslassung.

Phase 1, Punkt 7, wörtlich: **ADR-Inputs** — `mcp__outline-knowledge__search_knowledge(query:
"Input ADR", limit: 10)`; unbearbeitete (ohne ✅ im Titel) melden, nach Verarbeitung Titel auf
`✅ Input ADR-…` setzen.

Verwendung, wörtlich: `/session-start [REPO]` — `REPO` = Repo-Slug (z.B. `risk-hub`), Default
Auto-Detect via Git-Root; bei **mehreren offenen Repos** explizit angeben. Der Agent setzt
`TARGET_REPO` für alle folgenden Phasen.

Startklar-Checkliste, Zeilen in ihrer Fassung bis V2b (der Skill trägt sie gekürzt):

| # | Check |
|---|-------|
| 1 | Runner `session_start_checks.sh` gelaufen, Summary gezeigt (0.R) |
| 2c | `0.7.11`: 5xx von NXDOMAIN getrennt; jede `ports.yaml`-Ausnahme mit Grund |
| 2e | `0.7.17`: rote Volumes nach Lage getrennt; jeder Verzicht mit Grund |
| 2f | `0.7.18`: Platten unter 7 Tagen Vorlauf benannt; `SAMMELPHASE` ≠ Entwarnung |
| 2g | `0.3`: MAJOR ggü. bewertet gespiegelt (Vollmachten suspendiert, §2-Köder, #1640) |
| 2h | `0.7.23`: kein Melder ohne Leser, keine Karteileiche; Block „⏳ > 14 d" geprüft |
| 2i | `0.7.4`: jede Prio-Referenz offen — sonst **vor** dem ersten Arbeitsschritt nachgezogen |
| 7 | Editier-Modus auf Worktree gesetzt, kein Edit im Haupt-Tree (0.4.3) |
| 7a | Basis-Abstand aus 0.4.4 gelesen, betroffener Worktree **vor** dem Edit gemergt |
| 7b | Zielzustand geklärt: referenziert ODER akzeptiert ODER Überspringen begründet |
| 7c | Journal-Befund, den die Sitzung bearbeitet, per `start --befund <phase::repo>` gesperrt; Runner-Zeile `⛔ in Arbeit von` vor Start geprüft |
| 8 | Arbeitsplan aufgestellt (Phase 3, gegen den Zielzustand) |
| 8a | Auftragsraum abgearbeitet: `offen` gelesen, Kurzbefehle angewendet, Aufträge/Korrekturen verankert (1.8) |
| 8b | `LAUFZEIT:`-Zeile gelesen; auffälliger Anstieg als Befund gespiegelt, nicht hingenommen (0.R) |
| 8c | Delta-Tabelle gelesen: `NEU`/`GEAENDERT`/`OHNE-ANKER` als Items; `ANKER-ABGELAUFEN`/`WIEDERVORLAGE`/`FIX-MESSUNG-UEBERFAELLIG` neu verankert, geschlossen oder gemessen — **vor** dem Arbeitsplan (0.R) |

Unter der Checkliste stand: Auswahl neuer Pflicht-Zeilen über `grep -n "^## \|^### "` und
Einzelbeurteilung, **nicht** über das Wort „PFLICHT".

## anti-patterns-begruendung

**Ursprung:** `session-start.md`, Sektion „Anti-Patterns", wörtlich bis V2b (2026-10-06, #3785):

- ❌ `ping` für Server-Checks (Hetzner blockt ICMP — TCP-Probe nutzen, 0.1).
- ❌ Im geteilten Haupt-Tree branchen/stashen, wenn eine fremde Session aktiv ist
  (0.4-Guard; editieren nur via `repo-session.sh`-Worktree, ADR-233).
- ❌ Bei pgvector-Ausfall still auf lokales Memory ausweichen (0.5 ist hart).
- ❌ MCP-Tools mit `mcpN_`-Prefix hardcoden oder ungeprüfte Signaturen aus dem Skill-Text
  übernehmen — `.windsurf/rules/project-facts.md` + `ToolSearch` sind die Quelle.
- ❌ Handover-Prio blind starten, ohne Phase 2.6 — Cross-Host-Sessions hinterlassen
  erledigte Prios als „offen".
- ❌ Session auf dem teuersten Modell beginnen, ohne 0.8 bewusst entschieden zu haben.
- ❌ **In einem Worktree weiterarbeiten, den 0.4.4 als weit hinter `main` meldet**, ohne ihn
  vorher nachzuziehen — der Konflikt entsteht sonst beim Merge, wo er am teuersten ist.

Ebenfalls bis V2b im Skill: Verwendung — „**Platform Sync Loop:** Start = GitHub → platform →
alle Repos; Ende = commit → push → GitHub → alle Repos." Phase 0 — „Die mechanischen
Unterphasen laufen in **einem** Skript-Aufruf und sind damit strukturell nicht überspringbar".
Phase 0.4.3 — „parallele Sessions kollidieren über den HEAD". Phase 0.8 — „nicht per Default
auf dem teuersten Modell bleiben"; „Fable orchestriert, delegiert Mechanik als
Sonnet-Subagents/-Issues". Phase 3 — „(mit Warm-Start-Ergebnissen + Eskalationen)".

---

## changelog-historie

**Ursprung:** `session-start.md`, Sektion „Changelog". Der Skill trägt seit 2026-09-02
nur noch die letzten drei Einträge (Policy-Änderung aus
[#2696](https://github.com/achimdehnert/platform/pull/2696)); alles Ältere steht hier
wörtlich. Die beiden 2026-09-02-Einträge stehen hier in ihrer **vollen** Fassung, im
Skill gekürzt auf drei Zeilen. Seit V2b (2026-10-06,
[#3785](https://github.com/achimdehnert/platform/issues/3785)) trägt der Skill keine
Changelog-Einträge mehr; die drei, die bis dahin dort standen, folgen hier wörtlich.

- 2026-09-24: **`--befund` im Editier-Modus dokumentiert** (0.4.3, #3495 V1-Folgepunkt zu
  #3499): Skill-Text erklärt `start --befund <phase::repo>` (je Befund ein Aufruf, atomare
  Sperre, `exit 3` bei Kollision) und die Runner-Zeile `⛔ in Arbeit von <lease>` unter
  „Befund-Sperren (repo-session.sh befunde):"; neue Checklisten-Zeile 7c. Anlass: die Sperre
  selbst lief seit #3499, aber der Skill sagte nirgends, wann sie zu setzen ist oder wie die
  Runner-Zeile zu lesen ist.

- 2026-09-24: **Delta gegen das Befund-Journal** (platform#3506, Zielzustand #3495 V3): der
  Runner klassifiziert jede WARN-Zeile gegen den Journalstand vor dem Lauf (`NEU`, `GEAENDERT`,
  `OHNE-ANKER`, `ANKER-ABGELAUFEN`, `WIEDERVORLAGE`, `FIX-MESSUNG-UEBERFAELLIG`, `VERANKERT`)
  und druckt die Delta-Tabelle plus Summenzeile unter der Summary; `SESSION_CHECKS_DELTA=nur`
  kürzt die Summary auf die lauten Klassen. Neue Checklisten-Zeile 8c. Anlass: Advocatus-
  Diaboli-Lauf zu #3471 — „0 WARN" als Steuergröße belohnte Deklarationen, und zwei parallele
  Sitzungen bearbeiteten dieselbe Runner-Ausgabe doppelt, weil das Journal ihre Fixes nicht
  kannte (dazu Befund-Sperre #3499 und Feld „Fix in Arbeit" #3498).

- 2026-09-22: **Runner misst sich selbst und wartet nebenläufig** (platform#3373). Neue
  `LAUFZEIT:`-Zeile + Checklisten-Zeile 8b; die Melder ab 0.4.2 starten zusammen und werden an
  ihrer Phasenstelle geerntet — Summary-Reihenfolge, Notiz-Wortlaut und Phasenzahl unverändert.
  Drei Spuren mit eigener Breite (frei 8 · ssh 3 · git 1), weil acht gleichzeitige ssh-Melder
  Verbindungen verloren und drei parallele `git fetch` um dieselbe Ref-Sperre stritten.
  `SESSION_CHECKS_PARALLEL=1` stellt den alten Ablauf wieder her. Nebenbei korrigiert: 0.7.28
  las den Exit-Code von `tail` statt vom Melder, wodurch dort jede Lage als PASS endete.
  Messung und Herleitung: `docs/governance/session-skills-lehren/laufzeit.md`.

- 2026-09-17: **Phase 0.7.7 `gate-wirkung` gestrichen** (Streichbahn Retro 8185e1, Owner-Wort
  M9, Belegart kein Leser): drei Journal-Läufe, kein Session-Start-Board führte den Befund als
  Item; der einzige registrierte Leser war `/session-retro` Phase 4/5a, die `gate_wirkung.py`
  ohnehin selbst als Phase 0.0 ausführt — der Sitzungsstart duplizierte die Retro mit
  schwächerem Zug. Rückfall-Prüfung bleibt in `/session-retro` Phase 0.0/5a;
  `tools/gate_wirkung.py` unverändert.

- 2026-09-16: **Phase 1.1 liest Sitzungs-Fragmente** (#1944 K6) — in Repos mit
  `docs/handover.d/` kommt der Stand aus `fragments.py render --ref origin/main`; der
  Start-Hook spiegelt die offenen Fäden. Die Startprüfung meldet parallele Sitzungen nicht
  mehr als Befund (#3228).

- 2026-09-16: **Fünf ungedeutete WARN-Phasen ergänzt** (`0.7.4`, `0.7.13`, `0.7.19`,
  `0.7.25`, `0.7.26`) + Checklisten-Zeile 2i für `0.7.4`. Anlass: `0.7.4` verlangte an
  diesem Morgen "Prio nachziehen VOR Arbeitsbeginn", stand aber weder in der
  Deutungstabelle noch in der Checkliste — gehandelt wurde nur, weil der Runner-Text
  es mitlieferte. Neuer Prüfer `tools/skill_phasen_deckung.py` hält die Tabelle ab
  jetzt am Runner fest (gemessen: 6 von 46 WARN-Phasen ungedeutet).

- 2026-09-11: **Phase 1.8 Auftragsraum abarbeiten + Checkliste 8a** (KONZ-platform-059, #3079) —
  Zurufe aus dem Chat-Raum „Aufträge Achim / Lotse" landen als Vorschlag im Journal, nie als
  Befehl; Kurzbefehle wendet `anwenden` an, Korrekturen bekommen per `regel` ein Artefakt.

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
