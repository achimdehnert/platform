# ADR-209 v4 — Amendment 2026-05-18 (Red-Team V4.3 + Code-first)

Autoritative Ergänzung zu `ADR-209-v4-rationale.md` (externer Review).
Wo dieses Dokument der Rationale widerspricht, gilt dieses.

## 1. Reverse-Smoke exzidiert (V4.3)

Der `reverse-smoke`-Job (Rationale §4.1, Draft D4 alt) ist **gestrichen**,
nicht „später". Gründe:

- **Invertierter SPOF:** ein flakiger Consumer-Smoke blockiert das
  Library-Release für *alle anderen* Consumer — der Blast-Radius, gegen den
  v4 antritt, gespiegelt.
- **Falsches Artefakt:** `pip install -e <checkout>` testet Source/editable,
  nicht das gebaute Wheel — exakt die hatchling-Flat-Layout-Klasse, an der
  mcp-hub diese Session scheiterte.
- **Willkürliches N=3** gegen genau den Long-Tail, der bricht.
- **Inkonsistenz:** v4 vertraut Dependabot für Workflow-SHA-Bumps, aber
  nicht für Library-Versionen — obwohl es Library-Versionen als das größere
  Risiko nennt.

**Ersatz (Draft D4 neu):** library-seitiges **`api-diff`** (Semver-Bruch
ohne Major = rot) + Consumer pinnt **exakte** Version + **Dependabot**-PR
läuft durch die **Consumer-eigene CI** (echtes Wheel, richtiger Kontext).
`consumers.yaml` entfällt komplett.

Rationale §4.4 / §6 (Reverse-Smoke-Posten) / §8 A2,A4,A5 sind damit
gegenstandslos.

## 2. platform-doctor: dynamisch (User-Constraint)

Keine hartkodierte Repo-Liste — Repo-Zahl/-Set ändert sich, eine fixe
Liste wäre selbst Drift. `scripts/platform_doctor.py` entdeckt Repos zur
Laufzeit (`$GITHUB_DIR`-Scan → origin; `gh ... pushedAt` statt
Shallow-Clone-`git log`).

## 3. Erster Doctor-Lauf (2026-05-18) — Empirie statt Runde 5

51 Repos dynamisch entdeckt · 🟢 17 · 🟡 3 · 🔴 31. Befunde
cross-validieren die bisherigen Wellen unabhängig:

- Flächendeckend interne reusable Workflows `@main`/`@v1` statt SHA-Pin
  (D2-Verstoß) — der real größte, messbare Konformanz-Gap.
- `aifw/promptfw/authoringfw/illustration-fw/outlinefw`: CI py3.11 <
  requires-python 3.12 (deckt sich mit Welle-1-Issues).
- `cad/illustration/learn/pptx/recruiting/research/risk-hub`:
  `git+…#subdirectory`-Dep (deckt sich mit Welle-0a, teils noch nicht gemerged).
- Bekannter Rand: `platform-pinned`/`platform-workflows` sind Worktrees von
  `platform` → in v0.2 deduplizieren (origin-slug-Gruppierung).

## 4. Status

ADR-209 bleibt `proposed`, **eingefroren bis Doctor-Daten reviewt**. Kein
v5. Nächster Schritt mit Informationsgehalt = Doctor-Output mit Entscheider
durchgehen, nicht weitere Doku.
