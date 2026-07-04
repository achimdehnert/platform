# ADR-Fleet-Audit — 2026-07-04

> Erster Lauf von `/adr-fleet-audit` (Skill-Version: source_commit 50d9b2a4c242).
> Read-only-Analyse; alle Zahlen zur Laufzeit ermittelt (Step 0), nichts aus Index/Gedächtnis.
> Artefakte: `adr_inventory.json`, `adr_findings.json` (Session-Scratchpad).

**Abdeckung:** 33 lokale Repos mit ADRs (663 Dateien; Inventar-Zeilen 663 == find-Zählung 663) ·
5 Orgs remote abgeglichen (achimdehnert, bahn-sqf, iilgmbh, meiki-lra, ttz-lif — dynamisch aus
Clone-Remotes) · 9 remote-only Repos per Tree-Scan geprüft, davon **0 mit ADR-Bestand**
(adr-doctor, ifc-mcp, iil-demo-fixture, iil-testkit, schutztat-reporting, demo-repository,
desktop-setup, django-lms-lite, iil-data) · 16 Clones hinter origin, davon **3 mit
docs/adr-Delta**: platform (1 Commit: ADR-266-Revision aus #912), platform-pinned (by design,
s. F-10), weltenhub (2 Commits: ADR-095 + Index).

`NEXT_FREE` laut INDEX.md: **267**. Platform-Korpus: 211 ADR-Dateien inkl. ADR-266 (proposed, 2026-07-04).

## Vorbefunde aus der Vor-Session — Verifikationsergebnis

| Vorbefund | Ergebnis |
|-----------|----------|
| platform-pinned-Drift (ADR-265 fehlte in platform) | **Überholt/erklärt**: pinned ist ein detached Checkout desselben Remotes, gepinnt auf d4241cb; heute fehlt dort umgekehrt ADR-266. Drift = Mechanik (Pin-Lag), nicht Datenverlust → F-10 (C) |
| Status-Inkonsistenzen in platform (`"accepted"` gequotet, `draft \| reviewed \| approved`) | **Widerlegt** (False Positives): Treffer liegen im Body (ADR-083:142 Code-Beispiel, ADR-211:663 Template-Beispiel); Frontmatter beider Dateien = `accepted` (Z. 2/4). `paused-pending-second-consumer` in ADR-200:34 ist ein Zweitblock im Body; Frontmatter = `superseded` (Z. 4) |
| adr-doctor leer | **Bestätigt**: size 0, kein Branch. Funktion (Self-Supersede, dangling refs) heute ohne das Tool gefunden (F-5, F-6) → F-12 (C) |

## Befunde

| # | Item | Repo | Klasse | Evidenz | Status | Next Step |
|---|------|------|--------|---------|--------|-----------|
| F-1 | 117 ADRs ohne YAML-Frontmatter (Hotspots: risk-hub 21/30, bfagent 15/17, travel-beat 15/16, coach-hub 14/15, odoo-hub 14/14) | 20 Sub-Repos | B | `adr_findings.json → phase1.*.no_fm`; Stichprobe risk-hub/docs/adr/ADR-038-…md Z. 1 (kein `---`) | 🟢 | du: Welle freigeben — ich generiere Frontmatter-PRs je Hub |
| F-2 | Doppelte ADR-Nummern innerhalb eines Repos: risk-hub ADR-39+54 (je 2×), bfagent ADR-79+81+85 (je 2×), odoo-hub ADR-1 (2×), nl2cad ADR-1 (3×), pptx-hub ADR-2 (2×, inhaltlich fast identische Dateien `…evolution.md`/`…evolution-optimized.md`) | 5 Sub-Repos | B | `phase1.*.dup_nums` | 🟢 | du: pro Repo kanonische Datei bestimmen (via /adr-curator), ich baue Umbenennungs-PRs |
| F-3 | 24 stale `proposed` >90 Tage — platform: ADR-092 (125d), ADR-101 (120d), ADR-104 (119d); ältester Fleet: risk-hub ADR-038 (138d) | fleet | B | `phase1.*.stale_proposed` | 🔵 | ich: Triage-Liste je ADR (accept/void) als Entscheidungsvorlage |
| F-4 | 69 Dateien mit Template-Resten/Platzhaltern; 2 Mini-Dateien <400 B | fleet | B | `phase1.*.template_rest`, `.tiny` | 🔵 | ich: Liste beilegen, in F-1-Welle mit beheben |
| F-5 | Supersession platform: ADR-153 `supersedes: ADR-152`, das nicht existiert; ADR-200 `status: superseded` ohne `superseded_by` | platform | B | ADR-153 Frontmatter; ADR-200:4 | 🟢 | du: Nachfolger benennen — dann trage ich nach (mech. Teil ist A) |
| F-6 | Self-Supersede: meiki-hub ADR-006 `supersedes: ADR-6` (sich selbst), Ziel-Status 'Accepted' | meiki-hub | B | meiki-hub/docs/adr/ADR-006-temporal-rag-pilot.md Frontmatter | 🔵 | ich: Fix-PR (supersedes entfernen) nach Freigabe |
| F-7 | Status-Vokabular-Abweichungen fleet: 22× `Accepted`, 9× `Proposed`, 1× `Superseded` (Groß), 2× `Deferred` (meiki-hub ADR-007/008), 1× `rejected` (writing-hub ADR-181), 1× `Rejected (as bundle)` | Sub-Repos | C→B | `grep -hE '^status:' fleet`, Verteilung im Report-Anhang | 🟢 | du: Vokabular-Entscheid — `rejected`/`deferred` offiziell aufnehmen ODER normalisieren; danach B-Welle |
| F-8 | 18 Repo→Ziel-Paare referenzieren superseded/void platform-ADRs (häufigste Ziele: ADR-75 5 Repos, ADR-120 4 Repos, ADR-200, ADR-156) — Kaveat: teils historische Erwähnungen, kein aktiver Verstoß per se | fleet | B | Phase-2.5-Scan (Kommando im Skill §2.5) | 🔵 | ich: pro Paar prüfen ob aktive Abhängigkeit; nur diese fixen |
| F-9 | Echte Cross-Repo-Titel-Duplikate (pinned-Mirror rausgerechnet): „postgresql only testing" (coach-hub × platform), „unified agent loop on aifw" (mcp-hub × platform) | coach-hub, mcp-hub | B | `phase2.cross_repo_title_dups` gefiltert | 🔵 | ich: /adr-curator je Thema, Kanonik klären |
| F-10 | platform-pinned: detached Pin auf d4241cb, 6 Commits/1 ADR (ADR-266) hinter main; Update-Kadenz nirgends definiert (Hypothese — kein Kadenz-Dokument gefunden; billigster Check: grep in platform docs/tools nach pin-update) | platform-pinned | C | `git -C platform-pinned branch --show-current` = leer; `log -1` = d4241cb; diff -rq = 1 Datei + 2 Indizes | 🟢 | du: Pin-Update-Regel entscheiden (z.B. wöchentlich / nach jedem ADR-Merge) |
| F-11 | Scope-Kandidaten für Hebung nach platform: risk-hub ADR-039 „Windsurf Agent Workflows — Cross-Repo Standard" (Windsurf-Ära, evtl. stattdessen void), cad-hub ADR-034 „ETL+Chat-Agent als Platform-Service" (Service-Grenze) | risk-hub, cad-hub | B | Titel + adr-threshold.md-Kriterien | 🟢 | du: je Kandidat heben/void entscheiden |
| F-12 | adr-doctor (achimdehnert) leer; Funktionsumfang durch iil-adrfw-Auditor `supersession_hygiene` + diesen Audit abgedeckt (F-5/F-6 ohne Tool gefunden) | adr-doctor | C | `gh api repos/…/adr-doctor` size=0; iil-adrfw Auditor-Liste in /adr-health §2 | 🟢 | du: archivieren (Empfehlung) |
| F-13 | 16 Clones hinter origin (nur weltenhub mit ADR-Delta relevant: ADR-095 + Index 2 Commits) | fleet | B | Phase-0.3-Lauf | 🔵 | ich: gezielt weltenhub pullen (nach Freigabe), Rest via /sync-repo-Routine |
| F-14 | Klasse-A-Bestand platform ist minimal: no_fm-Treffer sind Begleit-Dokus (ARCHITECT-OVERVIEW.md, ARCHIVE-ANALYSE-2026-05-17.md — keine ADRs); einziger mech. Fix wäre INDEX-Regeneration nach F-5 | platform | A | Step-Phase-1-Lauf | 🔵 | ich: nach F-5-Entscheid `gen_adr_index.py` im Session-Worktree |

**Verifiziert:** Inventar 663==663; 9/9 remote-only Repos tree-gescannt; alle 3 Vorbefunde
adversarial geprüft (2 widerlegt/erklärt, 1 bestätigt); Status-Rohwerte fleet-weit gezählt;
Supersession-Ketten repo-lokal geprüft; pinned-Mechanik per git belegt.
**Nicht verifiziert:** (a) voller iil-adrfw-Audit des Platform-Korpus — MCP-Tools
(`adr_validate`/`adr_audit`) in dieser Session nicht geladen; billigster Check: `/adr-health`
in einer Session mit adrfw-MCP. (b) Ob F-8-Referenzen aktive Abhängigkeiten sind (nur
Existenz gezählt). (c) MADR-Struktur-Heuristik (Context/Decision-Headings) ist grob —
Struktur-Aussagen nur als Hinweis gewertet, nicht als Befund gelistet.

## Anhang: Status-Rohwerte fleet-weit

```
366 accepted · 124 proposed · 22 Accepted · 12 superseded · 9 Proposed · 4 void · 4 draft
2 Deferred · 1 Superseded · 1 rejected · 1 "Rejected (as bundle)" (+ Body-False-Positives, s.o.)
```
