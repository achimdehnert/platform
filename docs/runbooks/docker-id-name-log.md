# Runbook — Container-ID → Name auflösen (OOM-Forensik)

**Zweck:** Einen Kernel-OOM einem konkreten Container zuordnen, auch wenn dieser
inzwischen entfernt oder neu erzeugt wurde.

**Anlass:** [platform#1303](https://github.com/achimdehnert/platform/issues/1303) —
beim trading-hub-Ausfall vom 2026-07-20 waren Ausfallfenster und OOM-Fenster
belegbar, die Zuordnung „welcher Container" aber nicht mehr.

## Das Problem

Der Kernel benennt in OOM-Meldungen ausschließlich die cgroup:

```
oom-kill:constraint=CONSTRAINT_MEMCG,...,oom_memcg=/system.slice/
docker-7c29b3a246fec3ab171267b02fd85df628d1ecb37dd5817854e3796bbe2d123a.scope,
task=gunicorn,pid=1932391
```

`docker-<ID>.scope` enthält die volle Container-ID. Solange der Container lebt,
löst `docker ps -a --no-trunc` das auf. Ist er weg — entfernt, neu erzeugt, per
Deploy ersetzt — kennt Docker die ID nicht mehr, und es gibt **keine** Historie.
Der OOM ist dann anonym, und die Ursachenanalyse endet an dieser Stelle.

## Die Abhilfe

`scripts/server/docker-id-name-log.sh` schreibt stündlich einen Schnappschuss der
Zuordnung nach `/var/log/docker-id-name/<YYYY-MM-DD>.log`:

```
2026-07-21T15:00:07Z 7c29b3a246fec3ab...123a trading_hub_web running
```

Aufbewahrung 30 Tage (`DOCKER_ID_NAME_RETENTION_DAYS`). Das Skript ruft
ausschließlich `docker ps` auf — es verändert nichts.

## Installation auf einem Host

```bash
sudo install -m 755 scripts/server/docker-id-name-log.sh /opt/scripts/docker-id-name-log.sh
sudo /opt/scripts/docker-id-name-log.sh            # einmal manuell, erzeugt das Verzeichnis
( sudo crontab -l 2>/dev/null; echo '7 * * * * /opt/scripts/docker-id-name-log.sh' ) | sudo crontab -
```

Minute 7 statt 0, damit der Lauf nicht mit den zur vollen Stunde gestarteten
Wartungs-Jobs kollidiert.

## Anwendung im Ernstfall

1. cgroup-ID aus der OOM-Meldung ziehen:
   ```bash
   journalctl --since "<zeitpunkt>" | grep -oP 'docker-\K[0-9a-f]{64}' | sort -u
   ```
2. Im Protokoll nachschlagen:
   ```bash
   grep -h "<id>" /var/log/docker-id-name/*.log | tail -1
   ```
3. Fehlt die ID im Protokoll, ist der Container **zwischen** zwei stündlichen
   Läufen entstanden und gestorben — dann bleibt nur die zeitliche Korrelation.

## Grenzen

- Auflösung ist eine Stunde. Container mit kürzerer Lebensdauer (CI-Jobs,
  einmalige `migrate`-Container) können durchrutschen.
- Das Protokoll beantwortet **wer**, nicht **warum**. Für die Frage, weshalb ein
  Container *entfernt* statt neu gestartet wurde, hilft es nicht.
