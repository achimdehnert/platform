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

<!-- WICHTIG (session-retro 2026-07-02, SI-1): `Closes #N` nur ankreuzen, wenn ALLE
     Akzeptanzkriterien des Issues erfüllt sind. Ein offener Punkt → `Refs #N` nutzen
     ODER vor dem Merge ein Folge-Issue anlegen und hier verlinken. -->

- [ ] Alle Akzeptanzkriterien des referenzierten Issues sind erfüllt (sonst `Refs #N` statt `Closes #N`, Folge-Issue verlinkt)

Refs #<!-- N -->
