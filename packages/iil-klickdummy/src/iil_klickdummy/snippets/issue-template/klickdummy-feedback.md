---
name: 💬 Klickdummy-Feedback
about: Feedback aus dem Klickdummy-Feedback-Widget (Co-Development-Loop)
title: "[Klickdummy-Feedback] "
labels: ["klickdummy-feedback"]
assignees: []
---

<!--
Vorlage für Issues, die das Klickdummy-Feedback-Widget per GitHub-Direkt-API
erzeugt (Submit-Mode 'github', User-PAT in localStorage.klickdummy_github_token).
Issue-Author ist der reale GitHub-User. Coding-Agent (z. B. GitHub-Action mit
Claude-Code-Action) reagiert auf das Label `klickdummy-feedback`.
-->

## Kontext

- **Spec:** _(aus payload.spec_id)_
- **Klasse:** _(aus payload.klickdummy_class)_
- **Scope:** _(app | klickdummy-tool — aus payload.feedback_scope)_
- **Screen:** _(aus payload.screen)_
- **Kategorie:** _(bug | feature | ux | spec | ki — konfigurierbar via KLICKDUMMY_CATEGORIES)_

## Feedback

_(Markdown aus dem Widget — vom Widget direkt eingefügt.)_

## Erwartetes Vorgehen

1. Issue lesen, Klassifikation übernehmen (Kategorie + Screen + Scope).
2. Bei `scope: klickdummy-tool` → Widget/Snippet-Anpassung in `iil-klickdummy`.
3. Bei `scope: app` → Spec-Anpassung im Repo, dann Render.
4. PR mit Änderungen ODER Klärungs-Kommentar.

## Bezug

- `platform:ADR-211` Rev 13 (Konvention + Distribution + Co-Creation-Pfade)
