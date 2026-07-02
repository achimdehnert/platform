---
status: proposed
date: 2026-07-02
decision-makers: Achim Dehnert
consulted: –
informed: –
implementation_status: not-started
domains: [security, ci-cd, tooling, drift-prevention]
scope: platform
amends: [ADR-229]
relates_to: [ADR-230]
tags: [windsurf, rules-distribution, push-to-main, supply-chain, repository-dispatch, least-privilege]
---

# ADR-263 — `receive-windsurf-rules.yml`: PR statt Push-to-main, Typ-Filter, Least-Privilege

> **Amends ADR-229**: ADR-229 stellte die *Windsurf-Workflow*-Distribution als YAGNI zurück, ließ aber
> den **bereits live ausgerollten Empfänger-Workflow** `receive-windsurf-rules.yml` unadressiert.
> Dieses ADR entscheidet dessen Sicherheits-Härtung (oder Stilllegung).
> **Nummer provisorisch (263) — Allokation zur Merge-Zeit (ADR-065).**

## Kontext

Die Fleet-Konvergenz-Runde 2026-07-02 (Cluster F) fand in authoringfw/promptfw ein Muster, das der
Cross-Repo-grep auf **19 Repos** hochskaliert (`ls */.github/workflows/receive-windsurf-rules.yml`):

Der Workflow checkt `achimdehnert/platform` aus, kopiert `.md`-Regeln und **`git push`t sie direkt auf
`main`** — mit `contents: write`, `[skip ci]`, getriggert per extern feuerbarem `repository_dispatch`.
Konkrete Probleme (file:line-belegt in authoringfw FP-1/FP-2):

1. **Ungeprüfter externer Content landet auf `main`** (unlinted/unscanned, kein Review, `[skip ci]`
   umgeht sogar die CI).
2. **Externe Auslösbarkeit** über `repository_dispatch` → Angriffsfläche.
3. **Falsche Regeln für den Repo-Typ:** Django/Docker/htmx-Regeln + `run-local/staging/prod`-Workflows
   werden in **pure-library**-Repos (authoringfw) synct; `project-facts.md` (`always_on`) behauptet dort
   `.venv`/`.env`/Hetzner-`apt-get`, die es nicht gibt, und widerspricht dem Makefile (`make test`).
4. **Unbewachtes `cp`** einer fehlenden Quelle lässt den Run hart fehlschlagen.

Das steht in Spannung zu ADR-229 („consumed not mirrored", Windsurf nur noch für ADR-Review, Coding
CC-first). Ein live-in-19-Repos-Workflow mit `contents:write` + push-to-main + externem Trigger ist ein
org-weiter Automatismus im Sinne des Gates `autonomous-no-human-review` → ADR-Entscheidung nötig.

## Entscheidung

**Primär: Stilllegen, wo konsistent mit ADR-229** (Windsurf wird nicht mehr zum Coden genutzt; das
Regel-Mirroring in Consumer-Repos ist der von ADR-229 verworfene „mirror"-Ansatz). Wo der Empfang
weiter gebraucht wird, **härten** statt push-to-main:

1. **PR statt Push.** Kein `git push origin main`; stattdessen Branch + `gh pr create` (Review-Gate),
   `[skip ci]` entfernen, damit CI den externen Content prüft.
2. **Least-Privilege.** `permissions: contents: read` als Default; Schreibrechte nur im PR-Schritt,
   Cross-Repo-Token-Scope verifiziert. `repository_dispatch`-Trigger absichern/entfernen.
3. **Typ-Filter an der Quelle.** Der platform-Distributor liefert nach Repo-`type` (library vs
   django-app): Libraries nur generische Regeln (platform-principles, reviewer, testing, iil-packages)
   + ein library-taugliches `project-facts`. Kein Django/Docker/Deploy-Regelwerk in Libraries.
4. **Guards.** Jedes `cp -f` mit Existenz-Check; fehlende Quelle = kontrollierter Skip, kein Hard-Fail.

## Konsequenzen

- **Positiv:** entfernt einen extern-triggerbaren push-to-main-Automatismus aus 19 Repos; beseitigt
  falsch-typisierte Regeln, die LLM-Agenten in Libraries fehlleiten; bringt den Ist-Zustand in Einklang
  mit ADR-229.
- **Negativ / Risiko:** falls einzelne Repos den Auto-Empfang real nutzen, entsteht manueller
  PR-Merge-Schritt (gewollt). Entscheidung Stilllegen-vs-Härten je Repo an Repo-`type` festmachen.
- **Rollout:** org-weiter Change → **Dry-Run-in-CI ODER Vier-Augen** vor Scharfschaltung (Gate
  `autonomous-no-human-review`); zuerst an einem library-Repo (authoringfw) verifizieren.

## Verifiziert / nicht verifiziert

- **Verifiziert:** 19 Repos mit dem Workflow (grep); push-to-main + `contents:write` + `[skip ci]` +
  falsch-typisierte Regeln in authoringfw (file:line, FP-1/FP-2).
- **Nicht verifiziert:** wie viele der 19 den Empfang tatsächlich nutzen (vs. totes Relikt) — billigster
  Check ist `gh run list --workflow receive-windsurf-rules.yml` je Repo vor der Stilllegen-vs-Härten-Wahl.
