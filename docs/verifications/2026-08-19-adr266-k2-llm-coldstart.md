# Verifikation 2026-08-19 — K2-Rest: AGENTS.md-Rollout + T1a-LLM-Cold-Start (ADR-266, #2075 K2)

## Teil 1 — Rollout: Standard-Einstieg + AGENTS.md über alle 19 aktiv-Pakete

Je Paket: frischer Clone → Makefile-Normalisierung (setup-Target; Test-Rezept
auf `.venv` wo nötig) → AGENTS.md generiert (`tools/gen_pkg_agents_md.py`,
Schema pkg-agents-v1) → Schema-Check → **realer Verify `make setup && make
test` im frischen Clone** → erst dann PR. Ergebnis: **19/19 PRs, alle CI-grün,
alle gemergt** (17 direkt/venvify; weltenfw nach `$(PYTHON)`-Fix; nl2cad als
Schema-Kopf vor der kuratierten Doku, nichts gelöscht).

Kontextdatei-Stand: vorher AGENTS.md 1/19 — nachher **19/19** (18 generiert,
nl2cad kuratiert + Schema-Kopf).

## Teil 2 — T1a-LLM-Cold-Start-Eval: 19/19 PASS

`tools/pypi_coldstart_llm_eval.py`, Modell `openai/gpt-oss-120b` auf Groq
(T1a-Tier): das Modell bekommt NUR AGENTS.md + Wurzel-Listing des frischen
Checkouts, muss Setup-/Test-Kommando als JSON ableiten; ausgeführt wird
**ausschließlich** nach striktem `make <target>`-Muster (Modell-Output ist
Datenlage, kein Befehl — fail-closed, getestet). Abgeleitete Kommandos laufen
danach real im Checkout.

**Ergebnis: 19/19 PASS.** Lehrreicher Zwischenfall: nl2cad fiel zunächst als
`FAIL-unsafe` — das Modell folgte dem uv-Detail im Schema-Kopf statt dem
Einstiegskommando; das Gate blockte korrekt, der Fix war eine präzisere
AGENTS.md-Formulierung (Eval danach PASS). Genau dafür ist der Eval da:
er misst die Kontextdatei am Verhalten, nicht an der Anwesenheit.

## Instrumenten-Befunde (im Bau gefunden)

1. **Policy-Staleness llm-routing.md:** `groq/llama-3.3-70b-versatile`
   (T1a-Default, verifiziert 2026-05-13) existiert im Groq-Katalog nicht mehr
   (gemessen 2026-08-19); Groq hostet jetzt `openai/gpt-oss-120b` = T1a-Slot
   beider Provider. → Policy-Refresh-Issue.
2. **Cloudflare vor Groq blockt `Python-urllib`-UA mit 403** (curl mit
   identischem Key: 200) — Harness setzt eigenen User-Agent.

## Einordnung gegen #2075 K2

Verifiziert: Einstiegskommando + Kontextdatei je aktivem Paket, beides am
Verhalten gemessen (deterministisch UND LLM-getrieben). **Offen bleiben:**
Mini-Änderung-durch-CI als Eval-Stufe 2, CI-Doppellauf-Beweis
(Reproduzierbarkeit), copier-Template als Propagationsweg (Rollout lief über
Generator + Einzel-PRs), Mutation-/Property-Stichprobe Kernpakete.
