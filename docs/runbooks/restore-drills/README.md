# Restore-Feuerübungen (ADR-241 §5 / §Confirmation 4)

Quartalsweise: jüngstes **risk-hub**-Backup in ein Wegwerf-Postgres restoren,
Smoke-Query, Protokoll hier als Repo-Artefakt ablegen. Der `backup-meter`
(`tools/backup_meter.py`) prüft, dass ein Protokoll **< 100 Tage alt** ist —
`~/shared/` ist maschinen-lokal und für GitHub Actions unsichtbar, deshalb
gehört der Nachweis ins Repo.

## Dateibenennung

`YYYY-MM-DD-<app>.md` (z. B. `2026-06-21-risk-hub.md`). `README.md` wird vom
Meter ignoriert.

## Mindest-Inhalt eines Protokolls

- Datum, ausführende Person
- Quell-Snapshot (restic snapshot-id / Tag, Alter)
- Restore-Ziel (Wegwerf-Postgres, Version)
- Smoke-Query + Ergebnis (z. B. Tenant-Count, jüngster Datensatz)
- RTO-Ist (wie lange hat der Restore gedauert) vs. Soll (4 h für risk-hub)
- Auffälligkeiten / Abweichungen

> Die erste Feuerübung ist Akzeptanzkriterium G3 (ADR-241 §7). Bis dahin meldet
> der Meter `restore-drill` als **deferred** (Scaffold-Modus), nicht als
> Verletzung.
