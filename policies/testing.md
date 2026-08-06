# Policy: Testing — `make test` als kanonischer Einstieg
<!-- rule_class: B | assessed_with: claude-fable-5 | reassess_by: 2027-08-01 -->

**Trigger words:** make test, pytest, testlauf, tests ausführen, run tests, test schlägt fehl, testeinstieg, db credentials test

## Rule (User-Weisung 2026-08-06, org-weit — hebt die bisherige CLAUDE.md-Zeile auf Policy-Ebene)

1. **Lokale Tests laufen IMMER über `make test`** (bzw. das im Repo dokumentierte
   Make-Target) — nie über rohes `pytest`/`python -m pytest`. Django-Repos brauchen
   lebendes Postgres, `POSTGRES_*`-Env und `SECRET_KEY`-Guard; das Make-Target kapselt das.
2. **Repo-Vertrag (cross-repo):** Jedes Repo stellt ein `make test`-Target bereit, das
   seine Test-Umgebung vollständig kapselt. Ein Repo ohne dieses Target ist ein Befund
   (beim Onboarding via `/onboard-repo` bzw. `/teste-repo` melden), kein Anlass zum
   Env-Raten.
3. **Vor dem ersten Testlauf in einem Repo:** `config/settings/test.py` +
   `grep '^test' Makefile` lesen — Env-Variablen und DB-Credentials nie raten.
4. Rohes `pytest` ist zulässig NUR innerhalb von Make-Targets und CI-Workflow-Definitionen
   — dort ist die Env explizit verdrahtet.

## Warum (Evidenz)

2026-06-01: 6 Fehlläufe in Folge durch geratene DB-Credentials bei direktem pytest-Aufruf
(verankert als House Rule in der User-CLAUDE.md; diese Policy macht daraus die org-weite,
hook-injizierbare Form). Der Make-Target-Vertrag ist zudem die Voraussetzung dafür, dass
Agenten-Aufträge („führe die bestehenden Tests aus") deterministisch funktionieren.

## Ausblick (nicht Teil dieser Policy)

Der Repo-Vertrag aus Regel 2 ist maschinell prüfbar („Makefile hat test-Target") und damit
Kandidat für eine Org-Invariante der KONZ-041-Maschinerie — **erst** nach deren bestandenem
Kill-Gate, kein vorgezogener Rollout.

## Changelog

- 2026-08-06: Initial (User-Weisung „make test als cross-repo-weites Prinzip", Session
  Zielzustand-Governance). Quelle der Regeln 1/3: CLAUDE.md-House-Rule seit 2026-06-01.
