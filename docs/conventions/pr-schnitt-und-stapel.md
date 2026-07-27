# Convention: PR-Schnitt und gestapelte PRs

> Gilt für alle Repos, die per **Squash-Merge** auf `main` mergen — also für den
> gesamten Fleet. Besonders relevant für Django-Repos, weil dort die
> Migrationskette zusätzlich koppelt.

## Die Regel

Ein Stapel gestapelter PRs (`base` zeigt auf den Branch des Vorgängers) ist fast
immer das **Symptom einer falsch gewählten Schnittgröße**, nicht ein eigenes
Problem. Deshalb:

| Situation | Vorgehen | Warum |
|---|---|---|
| Fachlich gekoppelt — B ergibt ohne A keinen Sinn | **Ein PR**, mehrere `Closes #N` | kein Stapel, eine Migration, ein Review |
| Unabhängig, beide mit Migration | **Parallel von `main`**, Nummernkonflikt in Kauf nehmen | `update-branch` bleibt konfliktfrei, solange keine fremden Commits im Branch sind |
| Nachfolger braucht Vorgänger zum Bauen/Testen | **Erst mergen, dann bauen** | Stapel nur, wenn technisch unvermeidbar |

Die Trennlinie ist nicht „ein Issue = ein PR", sondern **ob der Diff ohne den
anderen überhaupt Sinn ergibt**. Mehrere Issues in einem PR zu schließen ist
ausdrücklich erlaubt und oft besser reviewbar als vier gestapelte Diffs.

## Warum Squash-Merge Stapel bricht

Ein Squash-Merge erzeugt auf `main` **einen neuen Commit** mit dem gesamten
Inhalt. Ein Nachfolger-Branch, der noch die **Original-Commits** des Vorgängers
trägt, gilt danach als divergente Historie: GitHub meldet `CONFLICTING`, und
`gh pr update-branch` hilft **nicht** — der Branch muss neu aufgesetzt werden
(von `main` abzweigen, eigene Dateien selektiv übernehmen).

Das ist keine Fehlkonfiguration, sondern die Natur von Squash. Ein PR, der die
Commits des anderen **nicht** enthält, lässt sich dagegen problemlos aktualisieren.

## Migrationsnummern sind kein Grund zu stapeln

Der häufigste Anlass fürs Stapeln ist die Angst vor kollidierenden
Migrationsnummern (zweimal `0006_…`). Das ist billiger als der Neuaufbau:

- Django meldet konkurrierende Leaf-Nodes erst beim **Anwenden**, nicht beim Mergen.
- `python manage.py makemigrations --merge` erzeugt die Merge-Migration in einem
  Commit.

Zusätzlich hilft: **Migrationen am Ende einer Arbeitseinheit erzeugen**, nicht je
Teilschritt. Drei Modelländerungen ergeben eine Migration statt drei — weniger
Kollisionsfläche, und die Nummer entsteht erst, wenn der Stand feststeht.

## Zwei operative Handgriffe

**Beim Squash-Merge `--delete-branch` setzen.** Wird der Base-Branch gelöscht,
hängt GitHub offene PRs automatisch auf dessen Base um. Scheitert das (typisch:
der Branch ist von einem `repo-session`-Worktree belegt), muss
`gh pr edit <N> --base main` von Hand nachgezogen werden. Worktree deshalb vor
dem Merge freigeben.

**Bei „strict" Branch-Protection wird jeder offene PR nach jedem Merge `BEHIND`.**
Dann ist pro PR ein `update-branch` **plus ein voller CI-Lauf** fällig. Bei einer
Kette von N PRs sind das N Nachzieh-Runden — ein Kostenfaktor, der unabhängig von
den Squash-Konflikten für größere Schnitte spricht.

## Was NICHT die Lösung ist

**Auf Merge-Commits statt Squash umzustellen.** Das würde die Stapel-Konflikte
technisch beseitigen, aber die Historie für einen Sonderfall inkonsistent machen
— die bisherigen `main`-Commits tragen alle das `(#N)`-Squash-Muster, und deren
Lesbarkeit ist mehr wert als die ersparte Neuaufbau-Arbeit in einer Session.

## Herkunft

Geerdet an einer realen Session (frist-hub, 2026-07-27): sechs PRs, davon zwei
Ketten (`#85 → #86` und `#80 → #83 → #91`). Beide Nachfolger mussten nach dem
Squash-Merge ihres Vorgängers **komplett neu aufgebaut** werden; dazu kamen
mehrere `BEHIND`-Nachzieh-Runden. Nach dieser Regel wären es drei PRs gewesen —
ohne einen einzigen Konflikt.
