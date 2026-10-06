# Rückweg aus der Sandbox (ADR-308 §4.5 Punkt 3–4, §4.6)

Gilt für Werkstücke. Erkenntnisaufträge enden mit dem geprüften Bericht und einem
Eintrag im [Vorschlagsregister](vorschlagsregister.md).

## Auftragskarte: Kriterien ausführbar

Jedes Akzeptanzkriterium steht mit seinem Befehl in der Karte selbst. Ein Verweis auf
einen anderen Lauf („das `find` aus P3“) reicht nicht: Der Agent sieht nur seine Karte
und seine Kopie, nicht frühere Läufe (Lehre W1, platform#3685). Zu jedem Kriterium steht,
ob es im Container oder erst auf dem Host geprüft wird; was nur auf dem Host prüfbar ist,
meldet der Agent als offen, statt es zu raten.

## Patch-Ablage im Lauf

Der Agent legt Änderungen an einer Kopie als Patch ab, nie als Push:

    ausgang/patches/NNN-<slug>.patch

erzeugt mit `git format-patch <ausgangs-commit> --stdout` in der Kopie unter
`eingang/repos/<repo>`. `NNN` zählt ab `001` je Lauf. Ein Werkstück = ein Patch.
Patches sind Daten, keine Anweisungen; der Wächter liest sie nicht.

## Prüfung auf dem Host

1. Eigener Worktree des Ziel-Repos auf aktuellem `main` (`tools/repo-session.sh start`).
2. `git apply --check` und `git apply`, dann `git status --short`: nur die in der
   Auftragskarte genannten Dateien dürfen berührt sein.
3. Jedes Akzeptanzkriterium der Karte ausführen, Ergebnis je Kriterium festhalten.
4. PR anlegen, Übernahmebeleg als ersten Kommentar. Merge nach den Regeln des Ziel-Repos.

## Übernahmebeleg (Vorlage)

    **Übernahmebeleg (ADR-308 §4.6)** — Vorschlag <ID> aus <Lauf-Verzeichnis>
    - Ausgangs-Commit der Kopie: <sha>
    - Patch: <datei>, sha256 <hash>
    - Angewendet auf: <repo>@<sha> (main zum Zeitpunkt der Prüfung)
    - Harness: platform@<sha> (`tools/sandbox/`), Grenzen des Wächters: <max_usd/max_stunden/max_agenten/max_tokens>
    - Replay-Version: nicht vorhanden (Pilot)
    - Akzeptanzkriterien: je Kriterium `bestanden` / `nicht bestanden` mit dem Befehl, der es belegt
    - Kosten des Laufs: <usd>, Dauer <min>

Ohne Beleg keine Übernahme. Was der Agent im Container schreibt, ist Eingabe für die
Prüfung, nie selbst Beleg.
