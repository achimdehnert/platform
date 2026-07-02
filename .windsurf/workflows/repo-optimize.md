---
description: Einzelnes Repo tief optimieren (Stufe-1, fleet-aware) — read-only Befunde mit Reichweiten-Tags + Action-Board + gegatete Artefakt-Vorschläge. Fleet → /platform-audit.
mode: write
---

> **mode: write — non-idempotent.** Die Analyse (Step 0–3) ist read-only und beliebig
> wiederholbar; Step 4 darf Branches/Issues/PRs anlegen, aber NUR gegated (Direkt-Umsetzen-Kriterien)
> und NIE Prod/Publish/Deploy/Merge autonom. Vor einem Re-Run prüfen, ob bereits Artefakte existieren.

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
- **Kein autonomer Prod/Publish/Deploy/Merge.** Artefakte sind Vorschläge bis zur Freigabe.

## Step 0 — Repo-Kontext (NIE hardcoden)
Lies: `CLAUDE.md`, `CORE_CONTEXT.md`, `project-facts.md`, `README`, `Makefile` (`grep '^test'`),
`.github/workflows/`, vorhandene `docs/adr`-Verweise, Verzeichnisstruktur. Test-Kommando aus der
Konfig, **nicht raten** (Django: `make test`, nie rohes pytest).

## Step 1 — Befunde (frische Agenten, read-only, je Dimension)
Pro Dimension ein Subagent (sonnet), der die Erzählung nicht kennt:
Architektur · Funktionalität · Tests · Dokumentation · Developer-Experience ·
LLM-/Agenten-Tauglichkeit · CI/CD · Sicherheit/Robustheit.
Je Befund: `ID · Kategorie · Reichweiten-Label · Beobachtung · Evidenz (Datei:Zeile) · Schweregrad · Maßnahme · GitHub-Aktion`.
**Reichweiten-Label (Pflicht):**
- `[REPO-LOCAL]` — Ursache + Fix allein in diesem Repo.
- `[FLEET-PATTERN]` — plausibel über mehrere Repos → Ursache an die QUELLE (platform/shared-ci/
  Template/ADR), nicht als Einzel-Patch; Stufe-2-Kandidat für `/platform-audit`.
- `[LLM-READINESS]` — verbessert, wie schnell/sicher ein LLM hier weiterarbeitet.

## Step 2 — Falsifikation (tragende Befunde)
Kritische/hohe Befunde: ein **Skeptiker-Subagent** zieht den Beleg **unabhängig neu** (breiter/
rekursiv, nicht den Finder-Befehl wiederholen) → binär **SURVIVES/REFUTED**. Nur Survivor in den Report.

## Step 3 — Output: ACTION BOARD + Report
Beginne mit **Action Board** (Org-Standard): Buckets 🟢 dein Zug · 🔵 ich sofort · 🟡-⛔ wip · ✅ done;
Spalten `# | Item | Repo | PR/Issue/ADR | Status | Next Step` (stabile IDs). Dann:
Repo-Landkarte · Befund-Tabelle · **LLM-Readiness-Review** (mit Datei/Modulbezug) ·
Roadmap (Quick Wins · 1–2 Wochen · Monat · Architektur; **`[FLEET-PATTERN]` = Kandidaten für `/platform-audit`**) ·
Nicht-sofort-ändern.

## Step 4 — Gegatete Umsetzung
- **DIREKT (Branch+PR)** NUR wenn ALLE: klein+abgrenzbar · Nutzen hoch/mittel · Risiko niedrig ·
  durch Tests absicherbar. Editieren via `tools/repo-session.sh start <repo> --task <slug>`
  (ADR-233-Worktree); vor Push lokale Hard-Gates (`make check-push` wo vorhanden); `make test`, nie rohes pytest.
- **Sonst Issue/ADR-Vorschlag** (architektonisch weitreichend / mehrere Module-Repos /
  Datenmodell-Auth-Security-Deploy-Migration / Absicht unklar / Risiko unklar). ADR-Schwelle:
  Ergänzung nach Muster = kein ADR (CHANGELOG/PR genügt).
- **`[FLEET-PATTERN]` NIEMALS als Einzel-Patch** — an `/platform-audit` eskalieren (Fix an der Quelle).
- **Scope-Checkpoint:** ab dem 3. berührten Repo ODER Prod/Publish innehalten und spiegeln.

## Step 5 — Verankern
`memory_candidates` vorschlagen (Mensch entscheidet) + Report **durabel** persistieren
(`~/shared/` oder `docs/`), nicht nur im Chat. `[FLEET-PATTERN]`-Befunde an die nächste
`/platform-audit`-Runde übergeben.

## Output-Format
```
## Action Board
🟢 Dein Zug (Entscheidung/Berechtigung) · 🔵 Quick-Wins (gate-frei) · 🟡 Issues (Judgment/größer) · 🔵 [FLEET-PATTERN] → /platform-audit
Spalten: # | Item | Repo | PR/Issue/ADR | Status | Next Step   (# = stabile ID)

## Befund-Tabelle
# | Kategorie | Reichweite([REPO-LOCAL]/[FLEET-PATTERN]/[LLM-READINESS]) | Beobachtung | Evidenz(Datei:Zeile) | Schwere(H/M/N) | Maßnahme | GitHub-Aktion

## LLM-Readiness-Verdikt   (mit Datei/Modulbezug)
## Falsifikation          (High-Befunde: SURVIVES/REFUTED, unabhängig nachgezogen)
## Roadmap                (Quick Wins · 1–2 Wochen · Monat · Architektur; [FLEET-PATTERN] markiert)
## Nicht sofort ändern    (mit Grund)
```

## Anti-Patterns
- ❌ Aus dem eigenen Session-Kontext urteilen statt frischer read-only Agent.
- ❌ Befund ohne Artefakt-Beleg / generische Aussage („Tests verbessern").
- ❌ `[FLEET-PATTERN]` als Repo-Einzel-Patch statt Quell-Fix.
- ❌ Autonomer Prod/Publish/Deploy/Merge.
- ❌ Test-Kommando raten statt aus der Konfig lesen.
- ❌ Finder-Befund mit leerem/falschem Pfad-Beleg übernehmen — bei Leer-Treffer Pfad neu prüfen (Realfall ttz-hub views.py verschachtelt).

## Changelog
- 2026-06-30: Initial. Aus der Stufe-1/-2-Methode der Session 2026-06-30 codifiziert.
  Dogfood: `/repo-optimize ~/github/ttz-hub` → 26 geerdete Befunde (3 Finder + Falsifikation),
  Headline data-sovereignty (OpenAI-Default in ttz-lif-Repo) cross-finder-konvergent + confirmed.
- 2026-06-30: Compliance-Nachzug (mode:write + non-idempotent-Note, Output-Format-Block,
  Changelog, Anti-Pattern „leerer Pfad-Beleg") nach `claude-skills`-Policy-Review.
