<!-- Kurz halten. Der Review-Gate liest die Checkboxen. -->

## Was

<!-- 1-3 Sätze: was ändert dieser PR und warum. -->

## Verifikation

<!-- Wie geprüft (Test-/CI-/gh-Output). Bei Vollständigkeits-Claims nach einem
     Sweep/Refactor: Verifikations-Query MUSS breiter/anders sein als das Bau-Muster
     (policies/evidence-discipline.md §How-to-apply Punkt 5, ×4 gate-pflichtig). -->

## Scope-Checkpoint / Freigabe

<!-- WICHTIG (session-retros ×2, GATE-PFLICHT `scope-checkpoint-not-durably-recorded`):
     Berührt dieser PR einen Prod-Schritt (Deploy/Publish/Release/Migration) ODER ein
     drittes Repo im selben Arbeitsstrang? Dann muss die Freigabe HIER im PR-Body stehen,
     nicht nur im Chat — sonst ist der Scope-Checkpoint nicht durabel dokumentiert.
     Realfälle: PR#762 Prod-Deploy 2. Repo ohne Checkpoint-Satz; iil-klickdummy SI-1. -->

- [ ] Kein Prod-Schritt / kein 3.-Repo — Scope-Checkpoint n/a, **oder** die menschliche Freigabe ist unten zitiert:

Freigabe (Wortlaut / Artefakt-Link, falls Prod/Publish/3.-Repo): <!-- z.B. "User: 'go' auf Freigabe-Block", oder AskUserQuestion-Ergebnis -->

## Issue-Bezug

<!-- ZIEL (Owner 2026-09-21): Issues und PRs sollen so schnell wie moeglich
     geschlossen werden und verschwinden. Der Standardfall ist deshalb `Closes`,
     nicht `Refs`.

     ACHTUNG, zwei gemessene Fallen:

     1. GitHub kennt NUR englische Schluesselwoerter — Closes / Fixes / Resolves.
        "Schliesst #N" auf Deutsch bewirkt NICHTS. Realfall platform#3334: der
        Fix war gemergt, das Issue #3333 blieb offen stehen.
     2. Eine nackte Nummer (`#3337`) verknuepft ebenfalls nichts. Am 2026-09-21
        taten das 53 % von 120 gemergten PRs, weitere 17 % schrieben `Refs` —
        Ergebnis: genau EIN offenes Issue von 445 hatte einen verknuepften PR.

     `Refs` bleibt richtig, wenn der PR das Issue nachweislich NICHT erledigt.
     Dann gehoert ein Grund dazu, in dieselbe Zeile (session-retro 2026-07-02,
     SI-1: `Closes` nur, wenn ALLE Akzeptanzkriterien erfuellt sind). -->

- [ ] Alle Akzeptanzkriterien des Issues sind erfuellt -> unten `Closes #N`
- [ ] Nicht erfuellt -> `Refs #N` **mit Grund in derselben Zeile**

Closes #<!-- N — oder die Zeile loeschen und stattdessen: Refs #N — Teil von; offen bleibt <…> -->
