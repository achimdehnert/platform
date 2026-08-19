# <dist-name> — Agent-Kontext

> Schema: pkg-agents-v1 · geprüft von `platform/tools/check_agents_md.py` ·
> Quelle dieses Templates: `platform/docs/templates/pkg-AGENTS.md` (#2075 K2, ADR-266).
> Ein LLM-Agent muss mit NUR dieser Datei + frischem Clone aufsetzen können.

## Zweck

<1 Absatz: Was das Paket tut, für wen, und was es bewusst NICHT tut.>

## Setup & Test (Einstiegskommando)

Ein Kommando, frischer Clone, keine Vorbedingungen außer Python 3.11+:

```bash
make setup && make test
```

<Abweichungen (z.B. benötigte Env-Variablen, Postgres) hier explizit nennen —
jede ungenannte Vorbedingung ist ein Schema-Verstoß.>

## Public API

<Die öffentliche Oberfläche: Top-Level-Module, Haupt-Klassen/Funktionen,
Extras (`pip install <dist>[extra]`). Bei Änderung mitpflegen — Drift-Check
kommt über den API-Surface-Export (#2075 K3).>

## Architektur-Constraints

<Nicht verhandelbare Invarianten: z.B. stdlib-only, keine Django-Abhängigkeit
im Core, Fehlerbilder als eigene Exceptions, Layering-Regeln.>

## Release

<Publish-Pfad: Workflow-Datei + Auth-Modus (OIDC Trusted Publishing).
Nie manuell publizieren — Gate-Regel ADR-226/ADR-266; Agent-Publish ist
hart geblockt, Release nur über CI.>
