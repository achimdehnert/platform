---
description: Tiefes evidenzbasiertes Single-Repo-Audit — Steelman + Advocatus Diabolus + Maintainer 2028, Platform-Konformität (P1–P9), optionaler --deep Fan-out. Gegenstück zu /platform-audit (Breite) und /repo-health-check (Gate).
---

# /repo-audit

> **Ziel:** EIN Repo tief, evidenzbasiert und kontrovers auditieren — nicht nur Fehler finden,
> sondern Systemqualität aus 3 Rollen + 15 Dimensionen bewerten und in actionable Befunde + Roadmap überführen.
>
> **Abgrenzung (nicht duplizieren):**
> - `/repo-health-check` = mechanisches Vollständigkeits-**Gate** vor Publish/Deploy (pyproject, README, Lockfiles).
> - `/platform-audit` = **Breite über ALLE Repos**.
> - `/compose-audit` = nur docker-compose vs ADR-021.
> - **`/repo-audit` = Tiefe + Urteil in EINEM Repo.**

**Trigger:** `/repo-audit <repo>` · `/repo-audit <repo> --deep` · vor Übernahme/Refactor eines fremden Repos, nach größeren Changes, bei Due-Diligence.

**Argumente:**
- `<repo>` — Pfad unter `~/github/` oder `ORG/REPO` oder URL. Default: aktuelles Repo.
- `--deep` — Multi-Agent-Fan-out (1 Sub-Agent pro Dimension). Ohne Flag: **LITE** (Single-Pass, priorisiert).

---

## ⚠️ Modus-Entscheidung (erster Schritt, ehrlich deklarieren)

„Sehr tief" × 15 Dimensionen × 3 Rollen sprengt ein Context-Window. Wähle bewusst:

| Modus | Wann | Verhalten |
|-------|------|-----------|
| **LITE** (default) | schneller Überblick, 1 Pass, Tier-3-Kosten | Priorisiere die in Phase A als Hochrisiko erkannten Dimensionen tief; übrige bewusst flacher. **Benenne explizit, welche Dimensionen nur flach geprüft wurden.** |
| **DEEP** (`--deep`) | Due-Diligence, vollständige Tiefe, höhere Kosten (Opus × N Agents) | Phase 4: je 1 Sub-Agent pro Dimension parallel → adversarial verify → synth. Siehe Block „DEEP-Fan-out" unten. |

> **Niemals** „sehr tief über alles" behaupten, wenn faktisch LITE läuft. Modus in §2 des Reports nennen.

---

## Phase 0 — Zugriff sichern

```bash
REPO_ARG="${1:-$(basename $(pwd))}"
# Pfad auflösen
if [ -d "$HOME/github/$REPO_ARG" ]; then REPO="$HOME/github/$REPO_ARG"
elif [ -d "$REPO_ARG" ]; then REPO="$REPO_ARG"
else echo "⚠️ Repo nicht lokal — Connector/Clone nötig: $REPO_ARG"; fi
echo "Audit-Ziel: ${REPO:-$REPO_ARG}"
git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null && git -C "$REPO" log -1 --format='%h %s' 2>/dev/null
```

Kein Repo-Zugriff → **nicht breit nach Kontext fragen**, sondern minimal anfordern: Repo-Link / ZIP / relevante Dateien.

**Safety (nicht verhandelbar):** Keine Deployments, keine Prod-Zugriffe, keine Migrationen gegen echte Umgebungen, keine Secret-Exfiltration. Secrets nie vollständig ausgeben — nur Fundort + Typ + Redaction.

---

## Phase A — Zwischenlieferung (Inventar + Evidenzkarte + Plan)

**A1 Repo-Inventar** (jedes Element mit Evidenz: Datei/Pfad/Symbol/Config-Key/Workflow/Commit):
Sprachen·Frameworks·Runtimes · Package-Manager+Lockfiles · Einstiegspunkte · Module/Services · Build/Test/CI · DBs/Queues/externe APIs/Auth · Deploy/Infra · Config/Env · Migrationssystem · Observability · auffällige Struktur-Risiken.

**A2 Evidenzkarte:**

| Bereich | Evidenzquellen | Erste Beobachtung | Risiko-Hypothese | Nächster Prüfschritt |
|---|---|---|---|---|

Bereiche mind.: Architektur · Daten/Persistenz · Security · AuthN/AuthZ · Dependencies/Supply-Chain · Tests · CI/CD · Deployment · Observability · Performance · Doku · Wartbarkeit · **Platform-Konformität (P1–P9)**.

**A3 Audit-Plan:** Welche Bereiche tief? Welche Dateien kritisch? Welche Befehle/externen Quellen? Was nicht prüfbar? Welche Risiken zuerst falsifizieren?

→ Danach **automatisch** ins Vollaudit, ohne auf Bestätigung zu warten.

---

## Phase 1 — Evidence Ledger (bindend)

Jede relevante Aussage braucht ≥1 Evidenzart:
- **E1** Repo-Evidenz: Datei + Zeilen/Symbol/Config
- **E2** Ausführung: Test/Build/Lint/Script-Output + reproduzierbarer Befehl
- **E3** Prozess: CI-Workflow / PR / Issue / Release / Commit-History
- **E4** Extern: offizielle Doku / CVE / Advisory
- **H** Hypothese: plausibel, unbewiesen — **muss als H markiert sein**

Regeln (= `~/.claude/policies/evidence-discipline.md`):
- Kein kritischer/hoher Befund ohne E1–E4.
- Aktiv Gegenbelege suchen, **bevor** ein Befund final formuliert wird.
- Widersprüchliche Evidenz dokumentieren statt glattbügeln.
- Tests/Builds nicht ausführbar → explizit sagen, **nicht** scheinbar auf Runtime-Evidenz stützen.

---

## Phase 2 — Steelman (zuerst, vor jeder Kritik)

3–7 evidenzbasierte Sätze: Was ist gut? Welche Entscheidungen wirken bewusst? Wo ist das Repo robuster als es aussieht? Welche Risiken sind schon abgefedert? Wo schlägt Pragmatismus Over-Engineering?

---

## Phase 3 — Drei Rollen

**🟢 Proponent** — Warum ist die Lösung vertretbar? Bewusste Trade-offs? Sinnvoll vermiedene Komplexität? Passend zum Reifegrad?

**😈 Advocatus Diabolus** (Kernfokus) — Leistet das Repo, was es behauptet? Wo klaffen Doku/Tests/Code/Runtime? Versteckte Kopplung, Schein-Sicherheit, Schein-Coverage, Schein-Automation? Was bricht unter Last / bösen Inputs / Parallelität / Rechtewechsel / Netzfehlern / Migrationen / Teamwechsel? Wo sind Risiken nur kommentiert statt enforced? Wo „works on my machine"? Wo erzeugt ein kleiner Refactor ein Security-/Daten-/Betriebsproblem?

**🔮 Maintainer 2028** — Was ist in 2 Jahren schwer verständlich? Was bricht durch Wachstum/Teamwechsel? Welche Deps/Patterns altern schlecht? Wo drohen Legacy/Migration/Security/Test-Debt? Welche heutigen Entscheidungen blockieren spätere Optionen?

---

## Phase 4 — Deep-Dive (LITE: priorisiert · DEEP: je 1 Sub-Agent)

Pro Dimension prüfen, soweit Evidenz vorhanden. **Fett = Platform-Vertrag (Phase 4P).**

- **Architektur:** Schichten/Verantwortlichkeiten **(P1 Service-Layer)** · Zyklen · globaler State · Abstraktion externer Systeme · Fehler als Architektur · God-Module · Architektur im Code vs nur Doku · **(P9 ADR-Abdeckung)**
- **Daten:** Konsistenz **(P2 Integer-PK)** · Migrationsrisiken **(Index-Rename → `SeparateDatabaseAndState` prüfen)** · Transaktionen/Idempotenz · Races/Lost-Updates · Daten-Ownership · fehlende Constraints · Retention/Löschung · gefährliche Datenkopien
- **Security:** Secrets in Repo/Tests/Config/Logs **(P8)** · zentrale vs verstreute AuthZ · Objekt-/Mandanten-Zugriffskontrolle · Injection/SSRF/Path-Traversal/Deser/Template-Injection · Supply-Chain · CI-Rechte/Tokens · unsichere Defaults · Rate-Limits · Fehlerausgaben · Debug/Admin-Endpunkte · Krypto/Session/Token-Lifetime
- **Datenschutz:** PII · sensibles Logging · Retention/Export/Löschung/Zweckbindung · Mandantentrennung · prod-nahe Testdaten · Abfluss via Monitoring/Analytics · **(ttz-lif/meiki-lra: Data-Sovereignty der repo-CLAUDE.md beachten)**
- **Tests:** Testarten · echte Abdeckung · Schein-Coverage · brittle/flaky · fehlende Negativtests · Contract/Integration an Grenzen · Determinismus · **(P4 PG-only, nicht SQLite)** · Fehlerfälle/Rechtewechsel/Parallelität/Migrationen · **(P5 `test_should_*`)** · Happy-Path-Bias · Snapshot-Tests die fachliche Änderungen verdecken
- **CI/CD:** Reproduzierbarkeit **(P6 Shared-CI `_ci-python.yml`)** · getrennte Envs **(ADR-210)** · Release/Rollback · Migrations-Validierung · Health-Checks (`/livez/`) · Observability · Artefakt-Versionierung · minimale CI-Rechte **(z.B. gitleaks braucht `pull-requests: write`, sonst 403)** · richtige Gates · gefährliche `continue-on-error`/`skip`/`allow_failure` (legitime Doku vs stille Umgehung unterscheiden) · Local↔CI-Drift
- **Performance:** N+1 · unbounded Queries/Loops/Queues/Payloads · Caching · Backpressure · Timeouts/Retries · Leaks · unbegrenzte Parallelität · synchrone Großoperationen im Request-Pfad · fehlende Pagination/Limits
- **Codequalität:** riskante Duplikation · überladene Module · tote Pfade · God-Funktionen · Fehlerbehandlung · Typisierung · Lint/Format enforced (ruff) · magische Strings · nur-kommentierte statt enforcete Verträge · Framework-Interna-Kopplung
- **Doku:** README/ADR/Kommentar/Code-Konsistenz · Onboarding-Lücken · realistische Setup-Schritte · dokumentierte Betriebs-/Security-/Migrations-Annahmen · gefährlich veraltete Doku · **CLAUDE.md/CORE_CONTEXT.md/AGENT_HANDOVER.md aktuell?**

### Phase 4P — Platform-Konformität (eigene Befunde, Präfix `PLAT-`)

| # | Vertrag | grep-Signal für Verstoß |
|---|---|---|
| P1 | Service-Layer (views→services→models) | `.objects.`/`.filter(`/`.save(` direkt in `views.py` |
| P2 | Integer-PK | `UUIDField(primary_key=True` |
| P3 | HTMX-Triple | `hx-`-Element ohne alle drei: `hx-target`+`hx-swap`+`hx-indicator` |
| P4 | PG-only Tests (ADR-179) | `sqlite` in Test-Settings |
| P5 | Test-Naming | Testfn ohne `test_should_` |
| P6 | Shared-CI | Inline-CI statt `uses: achimdehnert/platform/.github/workflows/_ci-python.yml@main` |
| P7 | Commit-Konvention | letzte ~20 Commits gg. `[feat\|fix\|...](scope):` |
| P8 | Secrets-Hygiene | Klartext-Secret getrackt; `secrets.env` nicht gitignored |
| P9 | ADR-Pflicht | neue Dep/Service-Grenze/Cross-Cutting ohne ADR (≠ reine Addition, s. `adr-threshold.md`) |

---

## Phase 5 — Suchraster

`TODO`/`FIXME`/`HACK`/`XXX`/`workaround` · `skip`/`xfail`/`continue-on-error`/`allow_failure` · `password`/`secret`/`token`/`apikey`/`private_key` · `admin`/`debug`/`bypass`/`unsafe`/`insecure` · `eval`/`exec`/`pickle`/`deserialize`/`shell=True` · `SELECT *`/rohe SQL · `UUIDField(primary_key` (P2) · ORM-in-`views.py` (P1) · `sqlite` in Test-Settings (P4) · fehlende HTTP/DB/Queue-Timeouts · Catch-all-Except · unbounded loops/retries · permissive CORS/CSRF/Cookie · env-spezifische Sonderlogik.

→ Treffer **nicht mechanisch** werten — jeder braucht Kontext + Gegenprüfung.

---

## Phase 6 — Out-of-the-Box (≥3 Ansätze)

Je: Idee · Vorteil · Nachteil · Wann sinnvoll · Warum evtl. verwerfen. Unkonventionell erlaubt, technisch plausibel zwingend. (z.B. P1–P9 als CI-Linter / Policy-as-code, Strangler-Fig, Read/Write-Model-Split, Property-based Testing, Subsystem entfernen, Observability-first Refactor.)

---

## Phase 7 — Befunde (Tabelle, stabile IDs)

| ID | Rolle | Kategorie | Befund | Evidenz | Schweregrad | Confidence | Betroffener Teil |
|---|---|---|---|---|---|---|---|

Präfixe: `PRO-` (positiv) · `AD-` (Risiko/Lücke) · `M28-` (Zukunft) · `SEC-` · `PRIV-` · `TEST-` · `OPS-` · `ARCH-` · `PERF-` · `DOC-` · **`PLAT-` (P1–P9)**.
Schweregrad: kritisch·hoch·mittel·niedrig·positiv·stark positiv. Confidence: hoch·mittel·niedrig.
Triviale Stilfragen nur bei systematischem Risiko. Jeder Befund → klare Handlung.

---

## Phase 8 — Top-5-Risiken

Je: Warum wichtig · Schadensszenario · Wahrscheinlichkeit · Dringlichkeit · kleinster wirksamer Fix · stützende Evidenz · **geprüfte Gegenbelege**.

---

## Phase 9 — Empfehlungen (`REC-N`)

Je: Bezug auf Befund-ID · Ziel · konkrete Änderung · Aufwand S/M/L · Risiko der Änderung · **Verifikation (wie beweist man die Lösung?)** · Akzeptanzkriterium. Keine generischen „Tests verbessern" ohne Testart+Ort+Akzeptanzkriterium.

---

## Phase 10 — Schlussurteil

`gesund` · `brauchbar mit gezielten Risiken` · `riskant, aber sanierbar` · `architektonisch gefährdet` · `nicht belastbar`.
+ wichtigste Begründung/Stärke/Schwäche/Sofortmaßnahme/Unsicherheit + 30/60/90-Tage-Roadmap.

---

## Report sichern

```bash
mkdir -p "$REPO/audits"
# Report schreiben nach:  $REPO/audits/repo-audit-{YYYY-MM-DD}.md
```
Datumsstempel über `date +%F` einsetzen. Optional via `/knowledge-capture` nach Outline.

---

## DEEP-Fan-out (nur bei `--deep`)

Phase 4 als Multi-Agent-Workflow statt Single-Pass:

```
pipeline über die 9 Dimensionen aus Phase 4:
  stage 1 (review):  je 1 Sub-Agent → Befunde mit Evidence-Ledger (E1–E4/H), strukturiert
  stage 2 (verify):  je Befund 1 adversarialer Sub-Agent → "refute or confirm" (default: refuted bei Unsicherheit)
  → nur bestätigte Befunde übernehmen
synth: Steelman + 3 Rollen + Top-5 + Roadmap aus den verifizierten Befunden
```

Kosten beachten (`session-routing.md`): Fan-out × Opus ist teuer — `--deep` ist **opt-in**, nicht default.
Implementierung als echter Workflow-Skript = **Stufe 3** dieses Skills (folgt, wenn LITE sich bewährt).

---

## Qualitätsregeln (bindend)

Hart in der Sache, fair in der Interpretation · Steelman zuerst · Evidenz/Interpretation/Vermutung trennen · keine Best-Practice-Predigt ohne Repo-Bezug · **keine erfundenen Dateien/Befehle/Testergebnisse/Zeilennummern** · nicht-prüfbares klar sagen · aktiv Gegenbelege suchen · reale Ausfall-/Security-/Daten-/Wartungsrisiken priorisieren · konkrete Fixes statt Diagnosen · keine Secrets vollständig ausgeben · keine destruktiven Aktionen · kein kritischer/hoher Befund ohne Evidenz · Hypothesen als H markieren · **Modus LITE/DEEP ehrlich deklarieren, flach geprüfte Dimensionen benennen**.
