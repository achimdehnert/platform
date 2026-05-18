# ADR-209 — Evolution v1 → v2 → v3 (Externer Review)

> **Zweck dieses Dokuments:** Material für einen externen Review. Es zeigt
> dieselbe Entscheidung in drei Fassungen plus die *Begründung jedes
> Übergangs*. Der Übergang selbst (warum geschrumpft, nicht erweitert) ist
> Teil dessen, was reviewt werden soll.
>
> **Stand:** Live auf Branch `chore/adr-209-ci-health-program` (PR #194) ist
> **v2**. **v3** ist Vorschlag, noch nicht committet — der externe Review
> entscheidet, ob v2→v3.
>
> **Meta-Warnung (ehrlich vorab):** Dies sind **3 Iterationen derselben
> Entscheidung in einer Session**. Die Plattform-Heuristik
> (`feedback_iteration_count_as_signal`) sagt: 3+ Iterationen ohne Konvergenz
> = falsches *Framing*, nicht falsche Architektur; smallest-viable schlägt
> monolithisch. v3 ist bewusst der *konvergente, kleinere* Schnitt. Eine
> legitime Review-Antwort ist: „auch v3 ist zu viel — nur Code, kein ADR".

---

## Kontext (für alle Versionen gleich)

48 Repos unter einer Org, je eigene unabhängig rottende CI. Ziel des Users:
develop→staging→prod stabil über alle Repos, Methoden so dokumentiert, dass
künftige stärkere Modelle den Zustand jederzeit fortführen/reviewen können.

**Empirischer Kern-Befund (Lauf 1, 2026-05-18):** *Ein* Fix in der reusable
`_ci-python.yml` (gitleaks-Permission, PR #191) entsperrte **alle** Consumer-
Repos gleichzeitig. Dieselbe Tatsache ist zweideutig lesbar — und genau diese
Zweideutigkeit treibt die Evolution:
- optimistisch: „geteilte Quelle ist der Hebel" → Zentralisierung
- pessimistisch: „geteilte Quelle ist ein Single Point of Failure mit
  Blast-Radius = alles"

---

# v1 — „Wiederkehrendes gegatetes Programm (Contract-First)"

**Wie es entstand:** Nach Lauf 1 (manuelles Survey→Triage→Issue→Queue über 48
Repos) sollten die empirischen Lehren als wiederholbarer Prozess festgehalten
werden, damit der nächste Lauf nicht dieselben Fehlgriffe macht.

```markdown
# ADR-209: Cross-Repo CI-Health als wiederkehrendes gegatetes Programm (Contract-First)

## Entscheidung
CI-Health wird als wiederkehrender Loop mit Triage-Gating betrieben:
Survey → Triage(verify) → Gate → Issue(Schema) → Queue/Direct → Merge → Lehren.

Gates (empirisch Lauf 1):
- G1 Survey-Korrektheit: Status = letzter push/PR-Lauf; `--limit 1` verboten.
- G2 Verify vor Handlung.
- G3 Versions-/API-Check vor Dependency-Swap.
- G4 Cross-cutting zuerst.
- G5 Deploy/Infra nie in autonome Queue.
- G6 Judgment-Gate: Test-vs-Code/Coverage-Senkung → manuell, nicht `auto`.
- G7 Contract-First: jedes Issue benennt die wiederhergestellte Regel.

Modell-Routing: Opus = Triage/Cross-cutting/Judgment; Sonnet = mechanisch.

## Kadenz
Survey+Triage monatlich; Lehren-Rückschrieb Pflicht-Abschluss.
```

*(Volltext: git `5389c47:docs/adr/ADR-209-cross-repo-ci-health-program.md`)*

---

## Übergang v1 → v2 — Advocatus-Diaboli Runde 1

Self-Red-Team **vor** Merge. Sechs Treffer:

| # | Angriff | Konsequenz |
|---|---------|------------|
| A1 | v1 institutionalisiert die Sprawl-Krankheit — Maschinerie zum ewigen Rasenmähen statt Pflastern. Der #191-Beweis sagt: Hebel ist die *geteilte Quelle*, nicht der Loop. | → Prävention vor Detektion |
| A2 | v1 ist reaktiv für an-der-Quelle-verhinderbare Klassen (Lint, Python-Pin, toter Dep). | → Klassen strukturell unrepräsentierbar machen |
| A3 | v1 macht Opus zum *Eingang* → skaliert nicht, nicht modell-fortführbar. | → Gates als Code, Opus = Eskalation |
| A4 | Monatlicher Survey = `--limit 1`-Fehler auf Makro-Ebene; CI ist Event-Stream. | → event-driven |
| A5 | „durchgehend grün" ist Goodhart-anfällig — Lauf 1 senkte selbst Gates (80→35, `# noqa`). | → Anti-Goodhart-Invariante |
| A6 | v1 ohne Verfallsdatum → wird selbst verwaiste Infra (genau das, was die Session sonst dekommissioniert). | → Portfolio-Triage + Exit-Kriterium |

---

# v2 — „Konvergenz-Programm mit Verfallsdatum (Prävention vor Detektion)"

**Wie es entstand:** v1 + die 6 Angriffe als 5 Prinzipien re-synthetisiert.

```markdown
# ADR-209: CI-Health als Konvergenz-Programm mit Verfallsdatum

## Entscheidung — fünf Prinzipien
1. Prävention vor Detektion: 48 per-Repo-CIs → EINE gehärtete reusable
   Workflow-Familie + Conformance-Check (python-from-requires-python,
   org-ruff, git+subdirectory = Hard-Fail). Eliminiert Klassen permanent.
2. Event-driven statt Polling: CI-rot → klassifizieren → autonom fixen /
   eskalieren. Survey nur einmaliger Bootstrap.
3. Gates G1–G7 als Code-Klassifizierer; Opus nur bei UNKNOWN.
4. Anti-Goodhart: kein Gate senken ohne ablaufenden Waiver (sonst CI-Fail).
5. Portfolio-Triage (live/maintenance/dead) zuerst; Exit-Kriterium:
   ≥90 % live-Repos auf shared CI & Red-Rate <10 %/30d → Selbstabschaltung.
```

*(Volltext: git `dc713fa:docs/adr/ADR-209-cross-repo-ci-health-program.md`)*

---

## Übergang v2 → v3 — Advocatus-Diaboli Runde 2 (+ frischer Empirie-Treffer)

| # | Angriff auf v2 |
|---|----------------|
| D1 | „48 CIs → 1 shared reusable" ist **SPOF als DRY verkleidet**. #191 beweist *beide* Lesarten. Zentralisierung ohne Release-Engineering verschiebt den Blast-Radius von 48 unabhängigen auf 1 korrelierten = alles. Die echte Lehre ist „shared infra braucht **Versionierung + Canary**", nicht „zentralisieren". |
| D2 | Der Conformance-Check (`git+subdirectory` = Hard-Fail) ist **selbst neue Rot-Fläche** + Waiver-Sprawl-Risiko → erzeugt, was v2 bekämpft. |
| D3 | **Iteration 3 derselben Entscheidung.** Plattform-Memory: das signalisiert Framing-Fehler; smallest-viable schlägt monolithisch. Ein v3 *gleicher Schwere* würde den Satz durch Verstoß beweisen → v3 muss **schrumpfen**. |
| D4 | „Selbstabschaltung" ist **unfalsifizierbar**: nichts in der Plattform hat sich je selbst abgeschaltet; der Exit-Meter *ist* das verbotene Polling. Ohne gebauten Meter = Deko. |
| D5 | Event-driven Auto-Fix = **ungescopeter Security-Blast-Radius** (org-weiter autonomer Code-Schreiber, angreifer-triggerbares rot-Signal). v2 commited das abstrakt mit. |
| **E** | **Frischer Empirie-Treffer:** Der erste Phase-0-Lauf *unter v2* lief auf Shallow-Clones → „kein totes Repo" ist ein **Mess-Artefakt**, kein Befund (lokale History beginnt erst ~2026-04-21; Deadness braucht GitHub `pushedAt`). v2s abstrakte Regel G1 fing diesen konzeptidentischen Fehler **nicht** ab. → Ein Governance-ADR, das den nächsten konkreten Fehler nicht verhindert, ist Governance-Theater (stützt D3). |

**Schlussfolgerung des Übergangs:** v2 hat als Überreaktion auf v1s
Unterdenken *überbaut*. Konvergenz = schrumpfen, nicht erweitern. Das Prozedurale
gehört nicht in Governance; der einzige echte Tradeoff ist „geteilte CI, und wie
man sie sicher betreibt".

---

# v3 — „Versionierte geteilte CI als einzige Entscheidung" (Vorschlag)

```markdown
---
status: proposed
date: 2026-05-18
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-111, ADR-196, platform#191, platform#194]
---

# ADR-209: Versionierte geteilte CI (einzige Entscheidung)

## Kontext
Empirie #191: ein Fix in reusable _ci-python.yml entsperrte alle — und hätte
bei einem Bug alle gebrochen. v1/v2 waren zu groß; 3 Iterationen = Framing-
Signal. v3 schneidet auf die eine echte Architektur-Entscheidung.

## Entscheidung
Per-Repo-CI konvergiert auf eine VERSIONIERTE, CANARY'd shared reusable
Workflow-Familie (`org/.github/.../_ci-*.yml@vN`). Konsumenten pinnen einen
TAG, nicht `@main`. Änderungen rollen via neuen Tag über eine Canary-Kohorte
(3 Repos) vor Fleet. Abweichung erfordert einen ablaufenden Waiver
(`docs/ci-waivers.md`, `expires:<datum>`; abgelaufen = CI-Fail).

Das ist die einzige Entscheidung mit echtem Tradeoff/Challenger. Alles
Prozedurale (Survey/Triage/Klassifizierer/Loop) ist IMPLEMENTIERUNG, lebt im
Skill `/ci-green-program` (darf iterieren), NICHT in Governance.

## Explizit ausgeschlossen (je eigene spätere ADRs)
- Event-getriebener Auto-Fix (autonomer org-weiter Code-Schreiber) —
  Threat-Model-ADR erforderlich.
- „Programm mit Selbstabschaltung" — kein unfalsifizierbares Exit-Versprechen
  ohne gebauten Meter.

## Erstes Deliverable = Code, nicht Doku
`platform-doctor`: ein exekutierbarer Contract-Check (CI-Konformanz, Dep-
Hygiene, Deploy-Erreichbarkeit), druckt Wahrheits-Report. DAS ist „für
künftige Modelle lesbar" (User-Vision) — exekutierbare Ground-Truth statt
Prosa. „Fertig" = platform-doctor grün → kein Programm zu betreiben.

## Konsequenzen
+ Eine challengebare Entscheidung; Versionierung+Canary = release-engineered
  statt SPOF; Prozess-Rot raus aus Governance; Code erfüllt die Vision direkt.
− Vorab-Invest (Tag/Canary-Mechanik); platform-doctor neue (kleine, read-only)
  Komponente; Konvergenz-Aufwand real. Reversibel: Tag-Pin/doctor entfernen.
```

---

## Offene Fragen an den externen Reviewer

1. **Tag-Pin vs `@main`:** v3 fordert versionierte shared CI mit Canary.
   Richtige Kohortengröße (3)? Update-Latenz vs. SPOF-Schutz akzeptabel?
2. **`platform-doctor` neu bauen** vs. den bestehenden Repo-Health-Agent
   (dev-hub#38) erweitern? Doppelung vermeiden.
3. **Konvergenz vs. Monorepo:** Bei 48 heterogenen Repos (Django-Hubs, fw-
   Libs, MCP-Server, Odoo) — ist „eine Workflow-Familie" realistisch oder
   wird es ein God-Workflow mit 20 Conditional-Inputs?
4. **Braucht es überhaupt ein ADR-209?** D3 konsequent zu Ende: vielleicht
   nur `platform-doctor` + versionierte shared CI als Code+README, gar keine
   Governance-Schicht. Ist der ADR selbst der Smell?
5. **Goodhart bleibt:** Auch v3s Waiver-Mechanik kann zu Waiver-Sprawl führen
   (D2). Ist eine ablaufende Ausnahme wirklich besser als gar keine?

## Empfehlung des Autors (transparent, nicht bindend)
v3 + Frage 4 ernst nehmen: ADR auf die *eine* Entscheidung (versionierte
geteilte CI + Waiver) minimieren, Prozess in den Skill, Event-Auto-Fix
vertagen, und das erste echte Deliverable als **Code** (`platform-doctor`)
statt weiterer Doku liefern. Wenn der externe Review Frage 4 mit „kein ADR"
beantwortet: #194 schließen, nur Code.
