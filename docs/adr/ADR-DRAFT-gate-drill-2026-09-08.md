---
id: ADR-000
status: proposed
decision_date: 2026-09-08
deciders: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: [ADR-228]
implementation_status: not_started
last_reviewed: 2026-09-08
staleness_months: 6
---

<!--
  ADR-DRAFT — Nummer faellt beim Merge (ADR-228, tools/adr_allocate.py).
-->

# ADR-DRAFT: Feueruebung fuer das Entwurfs-Tor aus ADR-228

## Context and Problem Statement

ADR-228 ist umgesetzt (PR #2954): ein ADR beginnt als `ADR-DRAFT-<slug>.md` mit
`id: ADR-000`, und `tools/adr_draft_guard.py` verhindert, dass ein Entwurf nach
`main` gelangt. Das Tor ist **lokal** in beiden Richtungen geprueft.

Nicht geprueft war, ob es **in der CI** greift: der Umsetzungs-PR selbst enthielt
keinen Entwurf, also gab es dort nichts zu blockieren. Genau diese Luecke meint
die Hausregel „gebaut + lokal gruen ist nicht dasselbe wie wirkt im Zielkontext".

## Decision

Diese Datei ist die Feueruebung. Sie existiert, damit der Pflichtcheck
**rot** wird. Der PR wird danach geschlossen, nicht gemergt — die Nummer bleibt
unverbraucht, `main` bleibt unberuehrt.

**Diese Datei darf nie gemergt werden.** Wenn sie auf `main` auftaucht, hat
genau das Tor versagt, dessen Wirkung sie belegen soll.

## Consequences

Belegt oder widerlegt in einem Lauf, ob das Tor im Zielkontext wirkt.
