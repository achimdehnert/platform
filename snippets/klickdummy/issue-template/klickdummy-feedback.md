---
name: 💬 Klickdummy-Feedback
about: Feedback aus dem Klickdummy-Feedback-Widget (Co-Development-Loop, Pfad A)
title: "[Klickdummy-Feedback] "
labels: ["klickdummy-feedback"]
assignees: []
---

<!--
Vorlage für Issues, die das Klickdummy-Feedback-Widget erzeugt
(opt-in via ?feedback=on). Der Coding-Agent reagiert auf Issues mit
diesem Label und versucht einen PR mit den vorgeschlagenen Änderungen.

Der Endpoint (feedback.iil.pet pro platform:ADR-214) sollte das vom
Widget gelieferte Markdown direkt unten einfügen.
-->

## Kontext

- **Spec:** _(aus payload.spec_id)_
- **Klasse:** _(aus payload.klickdummy_class)_
- **Screen:** _(aus payload.screen)_
- **Kategorie:** _(bug | feature | ux | spec | ki)_

## Feedback

_(Markdown aus dem Widget hier einfügen — vom Endpoint übernommen.)_

## Erwartetes Vorgehen (Coding-Agent)

1. Issue lesen, Klassifikation übernehmen (Kategorie + Screen).
2. Repro-Schritte oder Spec-Abgleich.
3. PR mit Änderungen am Klickdummy ODER Hinweis im Issue, falls Diskussion vor Code nötig.
4. Bei `category: spec`: erst Spec anpassen, dann Render.

## Bezug

- `platform:ADR-211` (Klickdummy-Cross-Repo-Rahmen)
- `platform:ADR-214` (Plattform-Heimat, dieses Issue-Template)
