---
description: Repo tief optimieren (Stufe-1, fleet-aware): geerdete Befunde, Action-Board, gegatete Artefakte. Fleet: /platform-audit.
mode: write
---

> **mode: write — non-idempotent.** Die Analyse (Step 0–3) ist read-only und beliebig
> wiederholbar; Step 4 darf Branches/Issues/PRs anlegen, aber NUR gegated (Direkt-Umsetzen-Kriterien)
> und NIE Prod/Publish/Deploy/Merge autonom. **Re-Run ohne Step 0.5 (Kollisions-/Carry-over-Check)
> ist verboten** — Realfall 2026-07-02: zwei Parallel-Sessions → 4 Duplikat-PRs (#95–#98).

# /repo-optimize

> **Ziel:** Ein Repo langfristig wartbarer, robuster, testbarer und besser anschlussfähig
> für zukünftige LLMs/Coding-Agents machen — geerdet, evidenzbasiert, mit klarer Trennung
> **repo-lokal vs. Fleet-Muster**.
> **Wann:** vor/bei größerer Arbeit an einem Repo · LLM-Readiness-Check · Tech-Debt-Inventur.
> **Wann NICHT:** Fleet/Cross-Repo → `/platform-audit`. Nur 3 nächste Schritte → `/next`.
> Reines Quality-Gate vor Publish/Deploy → `/repo-health-check`.

**Methode (SSoT):** `platform/docs/prompts/repo-enterprise-optimization.md` (Stufe-1). Diese
Skill orchestriert ihn mit **frischen read-only Subagenten** (Richter≠Angeklagter).

**Trigger:** Manuell (`/repo-optimize`).

## Verwendung
```
/repo-optimize            # aktives Repo
/repo-optimize <pfad>     # anderes Repo unter ~/github
```

## Eiserne Regeln (nicht verhandelbar)
- **Richter≠Angeklagter:** Befunde von **frischen read-only Subagenten** erzeugen, geerdet an
  Artefakten (Datei:Zeile / PR / run-log), **nicht** aus der Session-Erzählung.
- **Evidenz vor Behauptung:** jeden prüfbaren Marker erst checken, dann schreiben. Sichtbar
  trennen: BEOBACHTUNG | HYPOTHESE | EMPFEHLUNG | UMGESETZT. „Gebaut + lokal grün" ≠ „funktioniert".
- **Read-only bis Report steht:** während Step 0–3 keine Commits/PRs/Issues anlegen — jede
  Umsetzung erst in Step 4 nach Report + Gate-Prüfung (Realfälle 2026-07: Commits während des
  Laufs, PR während der Analyse).
- **Kein autonomer Prod/Publish/Deploy/Merge.** Artefakte sind Vorschläge bis zur Freigabe.

## Step 0 — Repo-Kontext (NIE hardcoden)
Lies: `CLAUDE.md`, `CORE_CONTEXT.md`, `project-facts.md`, `README`, `Makefile` (`grep '^test'`),
`.github/workflows/`, vorhandene `docs/adr`-Verweise, Verzeichnisstruktur. Test-Kommando aus der
Konfig, **nicht raten** (Django: `make test`, nie rohes pytest).

## Step 0.5 — Kollisions- & Carry-over-Check (Pflicht, vor dem ersten Finder)
1. **Vor-Reports:** `ls ~/shared/repo-optimize-*<repo>* 2>/dev/null` (fängt beide Alt-Namensschemata:
   repo-zuerst und datum-zuerst) + `ls ~/shared/platform-audit-inbox-*<repo>* 2>/dev/null`.
2. **Offene Artefakte:** `gh pr list --state open` + `git branch -a | grep session/` + offene
   Issues aus Vor-Reports — läuft oder lief hier schon ein Optimierungs-Lauf?
3. **Parallel-Session:** tauchen während des Laufs fremde frische PRs/Branches auf → anhalten
   und dem User spiegeln statt weiterarbeiten.
4. **Carry-over-Modus** (Vor-Report existiert): dessen Befund-IDs **fortführen** (keine neue
   ID-Serie), netto-neue Befunde gegen **ALLE** Vor-Reports dedupen (nicht nur den letzten —
   Realfall: „netto-neuer" B-6 war R08 aus dem Vor-Vor-Report), angekündigte-aber-nie-angelegte
   Artefakte aus Vor-Reports als Carry-over-Sektion listen.

## Step 1 — Befunde (frische Agenten, read-only, je Dimension)
Pro Dimension ein Subagent (sonnet), der die Erzählung nicht kennt — **alle 8 besetzen, nicht
reduzieren** (Messung 2026-07: der 3-Finder-Lauf lieferte den schwächsten Report; zwei
unabhängige 8-Finder-Läufe auf demselben Commit hatten nur ~30 % Befund-Overlap, der einzige
RCE-Befund kam aus dem Zweitlauf → ein Einzel-Lauf ist nie erschöpfend, Disclaimer in Fußzeile):
Architektur · Funktionalität · Tests · Dokumentation · Developer-Experience ·
LLM-/Agenten-Tauglichkeit · CI/CD · Sicherheit/Robustheit.
Je Befund: `ID · Kategorie · Reichweiten-Label · Beobachtung · Evidenz (Datei:Zeile) · Schweregrad · Maßnahme · GitHub-Aktion`.
**Reichweiten-Label (Pflicht):**
- `[REPO-LOCAL]` — Ursache + Fix allein in diesem Repo.
- `[FLEET-PATTERN]` — plausibel über mehrere Repos → Ursache an die QUELLE (platform/shared-ci/
  Template/ADR), nicht als Einzel-Patch; Stufe-2-Kandidat für `/platform-audit`.
- `[LLM-READINESS]` — verbessert, wie schnell/sicher ein LLM hier weiterarbeitet.
**Label-Konsistenz:** gleiches Muster wie in einem Vor-Report/einer Inbox eines anderen Repos
(z. B. SECRET_KEY-ohne-Prod-Guard, `skip_tests:true`) → gleiches Label; Ein-Repo-Beleg bleibt
Hypothese bis zum Cross-Repo-Check.

## Step 2 — Falsifikation (tragende Befunde)
Kritische/hohe Befunde: ein **Skeptiker-Subagent** zieht den Beleg **unabhängig neu** (breiter/
rekursiv, nicht den Finder-Befehl wiederholen). Verdikt **ternär**:
- **SURVIVES** — unabhängig bestätigt.
- **SURVIVES-EINGESCHRÄNKT** — bestätigt, aber Reichweite/Schwere kleiner als behauptet →
  Schweregrad anpassen und die Einschränkung benennen (Realfall: „Traceback an 4 Stellen" → 1 Stelle, H→M).
- **REFUTED** — fliegt raus (im Falsifikations-Abschnitt dokumentieren, warum).
Der Skeptiker **zitiert seine eigenen Kommandos/Belege** — bloße ✅-Marken zählen nicht.
Nicht geprüfte M/N-Befunde ehrlich markieren: „geerdet (nicht skeptiker-geprüft)".

## Step 3 — Output: ACTION BOARD + Report
Beginne mit **Action Board** (Org-Standard): Buckets 🟢 dein Zug · 🔵 ich sofort · 🟡-⛔ wip · ✅ done;
Spalten `# | Item | Repo | PR/Issue/ADR | Status | Next Step` (stabile IDs) — **exakt diese
Spalten, keine „Headline-Befunde" als Ersatz** (Compliance-Messung 2026-07: nur 2/17 konform). Dann:
Repo-Landkarte · Befund-Tabelle · **LLM-Readiness-Review** (mit Datei/Modulbezug) ·
Roadmap (Quick Wins · 1–2 Wochen · Monat · Architektur; **`[FLEET-PATTERN]` = Kandidaten für `/platform-audit`**) ·
Nicht-sofort-ändern · memory_candidates (Pflichtsektion, ggf. „keine").
**Report-Datei (kanonisch, self-contained — nie „siehe Chat"):**
`~/shared/repo-optimize-<repo>-<YYYY-MM-DD>.md` (repo-zuerst; Zweitlauf am selben Tag: Suffix `-runB`).
**Fußzeile (Pflicht):** Commit-SHA · Finder-Anzahl · Falsifikations-Bilanz (n SURVIVES / n
eingeschränkt / n REFUTED) · Coverage-Disclaimer („Einzel-Lauf, nicht erschöpfend").

## Step 4 — Gegatete Umsetzung
- **DIREKT (Branch+PR)** NUR wenn ALLE: klein+abgrenzbar · Nutzen hoch/mittel · Risiko niedrig ·
  durch Tests absicherbar. Editieren via `tools/repo-session.sh start <repo> --task <slug>`
  (ADR-233-Worktree); vor Push lokale Hard-Gates (`make check-push` wo vorhanden); `make test`, nie rohes pytest.
- **Sonst Issue/ADR-Vorschlag** (architektonisch weitreichend / mehrere Module-Repos /
  Datenmodell-Auth-Security-Deploy-Migration / Absicht unklar / Risiko unklar). ADR-Schwelle:
  Ergänzung nach Muster = kein ADR (CHANGELOG/PR genügt).
- **Angekündigt = angelegt:** jede im Report versprochene GitHub-Aktion noch in dieser Session
  ausführen ODER explizit als offener Carry-over in den Report (Realfall: 4 angekündigte Issues
  nie angelegt, erst der nächste Lauf fand es).
- **`[FLEET-PATTERN]` NIEMALS als Einzel-Patch** — an `/platform-audit` eskalieren (Fix an der Quelle).
- **Scope-Checkpoint:** ab dem 3. berührten Repo ODER Prod/Publish innehalten und spiegeln.

## Step 5 — Verankern
- `memory_candidates` vorschlagen (Mensch entscheidet) — Pflichtsektion im Report, ggf. „keine".
- Report **durabel** persistieren (kanonischer Pfad aus Step 3), nicht nur im Chat.
- **`[FLEET-PATTERN]`-Befunde vorhanden → Pflicht-Inbox-Datei**
  `~/shared/platform-audit-inbox-<YYYY-MM-DD>-<repo>-fleet.md` — je Muster: `FP-n · Label ·
  BEOBACHTUNG · EVIDENZ (Datei:Zeile) · SOURCE-FIX-Vorschlag` + Verweis auf den Quell-Report.
  Eine deklarative Übergabe („nehme ich in die nächste Runde auf") zählt NICHT (Messung 2026-07:
  16/17 Läufe versandet, nur 1 Inbox-Datei). `/platform-audit` liest diese Inbox in Phase 0.

## Output-Format
```
Datei: ~/shared/repo-optimize-<repo>-<YYYY-MM-DD>.md   (self-contained)

## Action Board
🟢 Dein Zug (Entscheidung/Berechtigung) · 🔵 Quick-Wins (gate-frei) · 🟡 Issues (Judgment/größer) · 🔵 [FLEET-PATTERN] → /platform-audit
Spalten: # | Item | Repo | PR/Issue/ADR | Status | Next Step   (# = stabile ID, bei Re-Run fortgeführt)

## Carry-over             (nur bei Re-Run: Stand der Vor-Report-Items + nie-angelegte Artefakte)
## Befund-Tabelle
# | Kategorie | Reichweite([REPO-LOCAL]/[FLEET-PATTERN]/[LLM-READINESS]) | Beobachtung | Evidenz(Datei:Zeile) | Schwere(H/M/N) | Maßnahme | GitHub-Aktion

## LLM-Readiness-Verdikt   (mit Datei/Modulbezug)
## Falsifikation          (High-Befunde: SURVIVES/SURVIVES-EINGESCHRÄNKT/REFUTED, Skeptiker-Beleg zitiert)
## Roadmap                (Quick Wins · 1–2 Wochen · Monat · Architektur; [FLEET-PATTERN] markiert)
## Nicht sofort ändern    (mit Grund)
## memory_candidates      (Pflicht, ggf. „keine")

Fußzeile: Commit-SHA · n Finder · Falsifikations-Bilanz · Coverage-Disclaimer
+ bei [FLEET-PATTERN]: ~/shared/platform-audit-inbox-<YYYY-MM-DD>-<repo>-fleet.md
```

## Anti-Patterns
- ❌ Aus dem eigenen Session-Kontext urteilen statt frischer read-only Agent.
- ❌ Befund ohne Artefakt-Beleg / generische Aussage („Tests verbessern").
- ❌ `[FLEET-PATTERN]` als Repo-Einzel-Patch statt Quell-Fix.
- ❌ Autonomer Prod/Publish/Deploy/Merge.
- ❌ Test-Kommando raten statt aus der Konfig lesen.
- ❌ Finder-Befund mit leerem/falschem Pfad-Beleg übernehmen — bei Leer-Treffer Pfad neu prüfen (Realfall ttz-hub views.py verschachtelt).
- ❌ Start ohne Step 0.5 / Re-Run mit neuer ID-Serie statt Fortführung.
- ❌ Commits/PRs/Issues während Step 0–3 (read-only-Phase).
- ❌ Report nicht self-contained („Action Board siehe Chat") oder Board durch „Headline-Befunde" ersetzt.
- ❌ Falsifikation als bloße ✅-Marke ohne zitierten Skeptiker-Beleg.
- ❌ FLEET-Handoff nur als Absichtserklärung statt Inbox-Datei.

## Changelog
- 2026-06-30: Initial. Aus der Stufe-1/-2-Methode der Session 2026-06-30 codifiziert.
  Dogfood: `/repo-optimize ~/github/ttz-hub` → 26 geerdete Befunde (3 Finder + Falsifikation),
  Headline data-sovereignty (OpenAI-Default in ttz-lif-Repo) cross-finder-konvergent + confirmed.
- 2026-06-30: Compliance-Nachzug (mode:write + non-idempotent-Note, Output-Format-Block,
  Changelog, Anti-Pattern „leerer Pfad-Beleg") nach `claude-skills`-Policy-Review.
- 2026-07-02: v2 nach Audit aller 17 Realläufe (2026-06-30…07-02): Step 0.5 Kollisions-/Carry-over-
  Check (Realfall Duplikat-PRs #95–#98), kanonischer Report-Dateiname (2 Schemata im Umlauf),
  Pflicht-Inbox-Datei für FLEET-Handoff (16/17 versandet), ternäres Falsifikations-Verdikt inkl.
  Schwere-Downgrade, Read-only-bis-Report-Regel, „Angekündigt = angelegt", Pflicht-Fußzeile,
  memory_candidates-Pflichtsektion (6/17 fehlend), 8-Finder-Pflicht (A/B-Overlap nur ~30 %),
  Description ≤120 Zeichen (Policy).
