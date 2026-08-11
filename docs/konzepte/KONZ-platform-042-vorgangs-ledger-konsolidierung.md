---
concept_id: KONZ-platform-042
title: Vorgangs-Ledger konsolidieren — geht die JSON-Datei im Vorgang-Modell auf?
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: Amendment
review_by: 2026-11-11
kill_criteria: "Der Board-Dienst braucht für die Anzeige einen Netzpfad zur dev-hub-Datenbank UND die drei fehlenden Board-Felder (frist, bucket, gegenueber) lassen sich nicht ohne Amendment an ADR-288 §4.1 im Vorgang-Modell unterbringen — dann bleibt die Trennung und dieses Konzept geht auf sunset."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "~/.claude/mail-vorgaenge.json", commit_or_pr: "n/a (lokal, nicht versioniert)", opened_in_session: true}
  - {claim_id: C2, source_path: "dev-hub/apps/mail_agent/models.py", commit_or_pr: "n/a (Arbeitskopie)", opened_in_session: true}
  - {claim_id: C3, source_path: "dev-hub/apps/mail_agent/management/commands/mail_vorgang.py", commit_or_pr: "n/a (Arbeitskopie)", opened_in_session: true}
  - {claim_id: C4, source_path: "platform/tools/todo_board/todo_board.py", commit_or_pr: "#1926", opened_in_session: true}
  - {claim_id: C5, source_path: "platform/docs/adr/ADR-288-mail-recherche-hybride-projektion.md", commit_or_pr: "n/a (status proposed)", opened_in_session: true}
  - {claim_id: C6, source_path: "~/.claude/policies/platform-agents.md", commit_or_pr: "n/a", opened_in_session: true}
created: 2026-08-11
---

# KONZ-platform-042 — Vorgangs-Ledger konsolidieren

## 1 Executive Summary

**Die Frage lautete: Geht der JSON-Ledger im `Vorgang`-Modell auf? Die belegte Antwort ist: nur zur Hälfte — und die andere Hälfte ist genau die, die das Board braucht.**

Beide Bestände existieren wirklich und führen denselben Gegenstand: `~/.claude/mail-vorgaenge.json` mit 18 Vorgängen (C1) und `Vorgang`/`VorgangsZuordnung` in `dev-hub/apps/mail_agent` (C2), letzteres mit Kommandozeilen-Zugriff über `mail_vorgang` (C3). Das ist eine echte Doppelquelle, kein Missverständnis.

Beim Öffnen des Modells zeigt sich aber: `Vorgang` trägt **vier** fachliche Felder — `schluessel`, `titel`, `status`, `notiz` (C2). Der Ledger trägt **vierzehn**. Die Differenz ist nicht Beiwerk: es fehlen `frist`, `bucket` und `gegenueber` — also Fälligkeit, Wer-ist-am-Zug und Gegenüber. Der Board-Dienst existiert ausweislich seines eigenen Docstrings genau deswegen, weil Fristen „dort schlummerten, wo niemand hinsieht" (C4). Ein Umzug auf das heutige Modell würde dem Board sein Thema nehmen.

Dazu kommt eine Kostenseite, die leicht übersehen wird: Der Ledger ist eine **Datei auf dem Arbeitsrechner**, das Modell lebt in der **dev-hub-Datenbank in Produktion**. Der Board-Dienst bezieht seine Sicherheitsbegründung daraus, dass er „nur das Ledger kennt, kein IMAP spricht und genau eine Seite hat" (C4). Wer ihn an die Datenbank hängt, tauscht eine Dateiabhängigkeit gegen eine Netz- und Zugangsdaten-Abhängigkeit — und schwächt damit ausgerechnet das Argument, mit dem der Dienst hinter Cloudflare Access vertretbar ist.

**Empfehlung: Konsolidieren, aber in der anderen Richtung als zunächst gedacht** — nicht „Board zieht in die Datenbank", sondern „Modell bekommt die drei fehlenden Felder, `/mailcheck` schreibt dorthin, und der Board-Dienst liest einen exportierten Auszug". Details in §12.

---

## 2 Scope und Evidenzbasis

**In Scope:** Ob und wie der handgepflegte JSON-Vorgangs-Ledger und das `Vorgang`-Modell zu einer Quelle werden.

**Out of Scope:** Der Mail-Index selbst (ADR-288), Datenschutz und Aufbewahrung (ADR-286, organisatorisch geregelt), die Frage nach einem eigenen „lotse"-Repo (in dieser Sitzung beantwortet: nein, der Ort ist dev-hub, C6).

**Geöffnet in dieser Sitzung** — siehe `evidence_manifest`. Alle Zahlen unten sind Messungen vom 2026-08-11, keine Schätzungen.

**Ausdrücklich nicht ausgeführt:** Der für T3 vorgesehene adversariale Agenten-Fan-out (Skill-Step 3) lief **nicht** — der Owner hat für diese Sitzung stehend verfügt, den Agent-Tool nicht ohne ausdrückliche Anforderung zu benutzen. Advocatus Diabolus und Maintainer-2028 stehen deshalb unten als eigene Abschnitte, aber aus einer Feder. Das ist eine reale Schwächung der Gegenrede und hier benannt, nicht kaschiert.

**Ein Eingang steht aus:** Die externe Pre-Mortem-Zweitmeinung zu ADR-288 (Briefing vom 2026-08-11 in `~/shared/`) fragt unter Punkt 3 ausdrücklich nach genau dieser Doppelführung. Ihre Antwort ist ein **noch fehlender Input** zu diesem Konzept — §13 nennt den Ort, an dem sie eingearbeitet wird.

---

## 3 Infrastruktur-Fit

| Sache | Ledger (heute) | `Vorgang`-Modell (heute) |
|---|---|---|
| Ort | Datei auf dem Arbeitsrechner | Postgres in dev-hub-Prod |
| Erreichbarkeit | lokal, immer | über Netz/SSH |
| Schreiber | `/mailcheck`, per Hand | `mail_vorgang`-Kommando |
| Backup | keines | Datenbank-Backup |
| Migration | keine | Django-Migrationen |
| Integrität | keine | Constraints, `PROTECT` |
| Mandantenschutz | Datei im Home | Tenant-Trennung |

Der Ledger gewinnt in genau einer Zeile — Erreichbarkeit — und verliert in allen anderen.

---

## 4 Steelman: warum die heutige Trennung vernünftig ist

Die Doppelführung sieht nach Nachlässigkeit aus. Sie ist aber, wohlwollend gelesen, eine tragfähige Arbeitsteilung.

Der Ledger ist **Sitzungsgedächtnis eines Assistenten**: was habe ich zuletzt geprüft, was ist der nächste Zug, wer ist dran, wann läuft es ab. Er wird bei jedem `/mailcheck` fortgeschrieben, ist eine Datei, braucht keine Verbindung und überlebt jeden Ausfall der Datenbank. Für ein Werkzeug, das täglich früh laufen und dabei nichts voraussetzen soll, ist das die robusteste denkbare Form.

Das `Vorgang`-Modell ist **Aktenführung**: welcher Sachverhalt existiert, welche Nachrichten gehören dazu, ist er offen. Sein Docstring sagt das selbst — es sei „das Einzige, was das Werkzeug wirklich produziert", während Ordnerstruktur und Index nur Beobachtung seien (C2). Es trägt zusätzlich eine Funktion, die der Ledger gar nicht haben kann: `ist_aktiv` ist das **Tor**, das nach ADR-286 überhaupt erst dauerhaften Volltext erlaubt.

Dass beide vier Felder gemeinsam haben, macht sie nicht zu Dubletten. Ein Kalender und eine Akte über denselben Fall sind auch keine.

---

## 5 Konzeptdefinition

**Kernthese:** Der Ledger geht im heutigen `Vorgang`-Modell **nicht** auf, weil dem Modell die drei Felder fehlen, die das Board überhaupt erst nützlich machen. Er geht auf, sobald das Modell sie bekommt — und dann ist die Datei nicht mehr Quelle, sondern Ausgabe.

**Zielbild:** Eine Quelle (`Vorgang` in dev-hub), zwei Leser (Kommandozeile, Board), ein Schreiber (`/mailcheck` über das bestehende `mail_vorgang`-Kommando). Der Board-Dienst bleibt, was er ist: ein Ding, das eine Datei liest und eine Seite ausgibt — nur wird diese Datei jetzt **erzeugt** statt gepflegt.

---

## 6 Adversariale Analyse

### 6.1 Advocatus Diabolus

**„Ihr löst ein Problem, das niemandem weh tut."** Die Doppelführung kostet heute nichts: eine Person, ein Rechner, ein Schreiber. Der Schmerz ist hypothetisch, der Umbau real. — *Teilweise berechtigt.* Der Schmerz ist heute klein, aber nicht null: der Ledger hat kein Backup und keine Integritätsprüfung, und er trägt Mandantennamen. Ein verlorenes Home-Verzeichnis kostet den kompletten Vorgangsstand.

**„Ihr macht das Board von der Produktion abhängig."** Bisher zeigt es auch dann etwas, wenn alles andere brennt. — *Trifft.* Deshalb steht in §12 ausdrücklich der Export-Weg und nicht der Direktzugriff.

**„Drei Felder anfügen heißt: ADR-288 §4.1 anfassen."** Der ADR beschreibt die durable Schicht bewusst schmal. Wer Board-Zustand hineinschreibt, verwässert sie. — *Trifft, und das ist der teuerste Punkt.* `frist` und `gegenueber` sind unstrittig Vorgangs-Sachverhalt und gehören dorthin. `bucket` („wer ist am Zug") ist **Anzeigelogik** und gehört es nicht. Konsequenz in §12: zwei von drei Feldern wandern, `bucket` bleibt ableitbar statt gespeichert.

**„Ihr behauptet eine Quelle und habt dann zwei."** Sobald die Datei erzeugt wird, steht ein zweiter Stand herum, den jemand versehentlich editiert. — *Trifft.* Gegenmittel in §12 REC-4: die erzeugte Datei trägt einen Erzeugungsstempel, und der Board-Dienst warnt sichtbar, wenn sie älter ist als der Datenbankstand — dieselbe Mechanik wie das bereits existierende Frische-Banner (C4).

### 6.2 Maintainer 2028

Was findet jemand in zwei Jahren vor? Ein Board, das eine Datei liest, die ein Kommando erzeugt, das eine Datenbank liest, die ein Skill schreibt. Vier Glieder für eine Liste mit achtzehn Zeilen.

Die ehrliche Frage ist nicht „ist das sauber", sondern „hätte man es einfacher haben können". Ja — indem das Board direkt gegen die Datenbank läuft. Der Grund dagegen ist keine Ästhetik, sondern die Angriffsfläche (§7). Diese Begründung **muss im Code stehen**, sonst baut sie 2028 jemand als vermeintliche Vereinfachung zurück und wundert sich, warum die Sicherheitsargumentation nicht mehr trägt.

---

## 7 Deep-Dive: die Angriffsflächen-Kopplung

Der Board-Dienst hält Mandantennamen und Betreffs. Seine Rechtfertigung, hinter Cloudflare Access zu stehen, lautet wörtlich: er kennt nur das Ledger, spricht kein IMAP, hat genau eine Seite (C4). Genau deshalb wurde er auch bewusst von `mail_link_server.py` getrennt, der Postfachinhalt live rendert.

Ein direkter Datenbankzugriff bricht zwei Drittel dieser Begründung: der Dienst bekäme Zugangsdaten und eine Netzverbindung in ein Produktionssystem. Damit wäre er kein Anzeiger einer Datei mehr, sondern ein Client der Produktion — und die Frage „darf der öffentlich hängen" müsste neu beantwortet werden.

**Der Export-Weg vermeidet das vollständig:** Das Board bleibt ein Dateileser. Nur der *Erzeuger* der Datei spricht mit der Datenbank, und der läuft ohnehin schon dort, wo die Zugangsdaten liegen.

---

## 8 Alternativen

| # | Alternative | Für | Gegen | Verdikt |
|---|---|---|---|---|
| A | Alles bleibt | kostenlos | Ledger ohne Backup trägt Mandantendaten | verworfen |
| B | Board liest direkt die Datenbank | eine Quelle, kein Zwischenstand | bricht die Angriffsflächen-Begründung (§7) | verworfen |
| C | **Modell erweitern, Datei exportieren** | eine Quelle, Board bleibt Dateileser | vier Glieder, Amendment nötig | **gewählt** |
| D | Ledger wird Quelle, Modell fällt weg | einfachste Kette | verliert Tenant-Trennung, `PROTECT`, das `ist_aktiv`-Tor aus ADR-286 | verworfen |

---

## 9 Out-of-the-Box

**Braucht das Board überhaupt eine Datei?** `mail_vorgang zeigen` gibt den Stand bereits aus (C3). Ein Board, das dieses Kommando aufruft und die Ausgabe rendert, käme ohne eigenen Datenbestand aus. — Verworfen, weil das Kommando über SSH läuft und das Board damit doch wieder eine Netzabhängigkeit bekäme, nur schlechter versteckt.

**Braucht es das Board?** Wenn die Vorgänge in dev-hub liegen, könnte dev-hub sie anzeigen — dort steht Django, dort ist Authentifizierung gelöst. — **Ernsthaft erwägenswert und in §12 nicht abschließend beantwortet.** Dagegen spricht heute nur, dass das Board existiert und funktioniert. Das ist ein Bestands-, kein Sachargument. Wird das Board je grundlegend überarbeitet, ist diese Frage zuerst zu stellen.

---

## 10 Befunde

| ID | Befund | Evidenz | Schwere |
|---|---|---|---|
| B1 | Zwei Bestände führen denselben Gegenstand | C1, C2 | mittel |
| B2 | `Vorgang` fehlen `frist`, `gegenueber` — beides Vorgangs-Sachverhalt | C2 | hoch |
| B3 | Der Ledger trägt Mandantennamen ohne Backup und ohne Integritätsprüfung | C1 | hoch |
| B4 | `thread_key` passt nicht in `schluessel` (SlugField, 64 Zeichen) — Werte sind langer Freitext | C1, C2 | mittel |
| B5 | `bucket` ist Anzeigelogik, kein durabler Sachverhalt | C1, C4 | niedrig |
| B6 | Direktzugriff des Boards auf die Datenbank bräche dessen Sicherheitsbegründung | C4 | hoch |
| B7 | ADR-288 ist `proposed`, während die Anlage produktiv läuft — dieses Konzept baut auf einer noch nicht entschiedenen Grundlage auf | C5 | mittel |

---

## 11 Top-5-Risiken

| # | Risiko | Wirkung | Gegenmittel |
|---|---|---|---|
| R1 | Erzeugte Datei wird von Hand editiert, Stände laufen auseinander | still falscher Board-Stand | Erzeugungsstempel + sichtbare Warnung (REC-4) |
| R2 | Amendment an ADR-288 §4.1 verwässert die durable Schicht | Zweckbindung wird Etikett | nur `frist`/`gegenueber`, `bucket` bleibt draußen (REC-2) |
| R3 | Export-Job fällt aus, Board zeigt alten Stand als aktuell | beruhigt fälschlich | vorhandenes Frische-Banner deckt das ab (C4) |
| R4 | Umzug verliert Vorgangs-Historie aus den `notiz`-Ketten | Verlauf weg | Migration überträgt `notiz` unverändert, Gegenprobe je Vorgang (REC-5) |
| R5 | ADR-288 wird nicht akzeptiert oder verändert sich | Konzept baut auf Sand | Kill-Gate §13 (a) |

---

## 12 Empfehlungen

| ID | Empfehlung | Konkret |
|---|---|---|
| REC-1 | Frage beantwortet festhalten: der Ledger geht **nicht** im heutigen Modell auf | dieses Dokument; keine Umzugsarbeit beginnen, bevor REC-2 entschieden ist |
| REC-2 | `Vorgang` um `frist` (DateField, null erlaubt) und `gegenueber` (CharField) erweitern | `dev-hub/apps/mail_agent/models.py`; Amendment an ADR-288 §4.1, weil die durable Schicht dort abschließend beschrieben ist |
| REC-3 | `bucket` **nicht** speichern, sondern aus `status` + `frist` + `next_trigger` ableiten | Ableitungsregel in `todo_board.py`, nicht im Modell — hält Anzeigelogik aus der durablen Schicht |
| REC-4 | Export-Kommando `mail_vorgang export --ziel <datei>` ergänzen, das exakt das heutige Ledger-Format schreibt, inkl. Erzeugungsstempel | `dev-hub/apps/mail_agent/management/commands/mail_vorgang.py` — neuer Unterbefehl neben den sechs bestehenden |
| REC-5 | Einmal-Migration der 18 Vorgänge, mit Gegenprobe je Vorgang (Feld für Feld, nicht Stichprobe) | Migrationsskript; `thread_key` wandert nach `titel`, `schluessel` bekommt einen erzeugten Slug (B4) |
| REC-6 | `/mailcheck` schreibt danach über `mail_vorgang`, nicht mehr in die Datei | Skill-Datei; die Datei wird ab dann nur noch gelesen |
| REC-7 | Die Begründung gegen Direktzugriff als Kommentar in `todo_board.py` verankern | sonst baut sie jemand 2028 als Vereinfachung zurück (§6.2) |

---

## 13 Entscheidung, Kill-Gate, 30/60/90

**Vorgeschlagene Entscheidung:** Alternative C. Nicht sofort umsetzen — erst REC-2 entscheiden, weil daran alles Weitere hängt.

**Kill-Gate.** Dieses Konzept geht auf `sunset`, wenn eines eintritt:

| Kriterium | Status | Beleg |
|---|---|---|
| (a) ADR-288 wird nicht akzeptiert oder ändert §4.1 so, dass `frist`/`gegenueber` dort nicht unterkommen | offen | externes Pre-Mortem ausstehend, Briefing 2026-08-11 in `~/shared/` |
| (b) Das Amendment für REC-2 wird abgelehnt | offen | — |
| (c) Der Export-Weg (REC-4) erweist sich als aufwendiger als ein Direktzugriff, ohne dass §7 entkräftet wäre | offen | — |
| (d) Bis 2026-11-11 ist REC-2 nicht entschieden | offen | `review_by` |

**Exception-Budget:** bis **2026-11-11** darf die Doppelführung bestehen bleiben. Danach ist entweder umgesetzt oder das Konzept auf `sunset` — ein drittes Jahr Doppelführung ist keine Option, weil B3 (Mandantendaten ohne Backup) mit der Zeit nicht besser wird.

**30/60/90:**
- **30 Tage:** REC-2 entschieden (Amendment ja/nein). Externes Pre-Mortem eingearbeitet, insbesondere dessen Punkt 3 zur Doppelführung — als eigene Zeile in der Befunde-Tabelle §10, nicht als Prosa-Absatz.
- **60 Tage:** REC-4 und REC-5 umgesetzt, Migration mit Gegenprobe belegt.
- **90 Tage:** REC-6 wirksam, die Datei wird nur noch erzeugt. REC-7 im Code.
