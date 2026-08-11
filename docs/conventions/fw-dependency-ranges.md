# Ziel-Ranges der Kern-Frameworks (SSoT)

> SSoT für [#1900](https://github.com/achimdehnert/platform/issues/1900) —
> jedes aktive Consumer-Repo pinnt die Kern-Frameworks auf **genau diese Range**.
> Änderungen an dieser Datei nur per platform-PR (Owner-Review); der Kontroll-Scan
> gegen die Flotte läuft per Dep-Grep (siehe #1900, Kriterium 3).

| Paket | Ziel-Range | Stand (PyPI, 2026-08-11) |
|---|---|---|
| `iil-aifw` | `>=0.11.7,<1` | 0.11.7 (lazy litellm, aifw#40) |
| `iil-testkit` | `>=0.5.3,<1` | 0.5.3 — Extras (`[smoke]`) bleiben repo-spezifisch |
| `iil-promptfw` | `>=0.8.1,<1` | 0.8.1 — Extras (`[django]`) bleiben repo-spezifisch |
| `iil-authoringfw` | `>=0.11.6,<1` | 0.11.6 |

## Regeln

1. **Untergrenze = aktuelles Release, Obergrenze `<1`.** Bei neuen Framework-Releases
   wird die Untergrenze hier angehoben und per gestaffelter Bump-Welle ausgerollt
   (Preflight je Repo — Lehre aus der Massen-Bump-Welle, nie alle Consumer in einem Rutsch).
2. **Extras bleiben repo-spezifisch** (`[smoke]`, `[django]`, …) — die Range ist einheitlich,
   die Extras nicht.
3. **Eingefrorene Repos sind ausgenommen** (`bfagent`, `research-hub`): Pins dort einfrieren,
   nicht anheben.
4. **Long-Tail-Frameworks** (outlinefw, researchfw, nl2cadfw, learnfw, weltenfw,
   illustrationfw, riskfw, adrfw) sind nicht Teil dieser SSoT — je 1–3 Nutzer,
   Harmonisierung lohnt erst bei Mehrfachnutzung.
