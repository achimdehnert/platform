#!/bin/bash
# Grosse Trainingslaeufe und der vLLM-Dienst passen nicht gleichzeitig in die
# 121 GB des GB10: der Dienst haelt rund 36 GB, ein Lauf mit 20.480 Umgebungen
# brauchte 75 GB (platform#2544, robo-lab#58).
#
# Aufruf: ~/training-mit-speicher.sh <kommando…>
#   Beispiel: ~/training-mit-speicher.sh python scripts/train.py Unitree-G1-Flat \
#               --env.scene.num-envs=20480 --agent.max-iterations=20 --agent.logger tensorboard
set -u
WAR_AKTIV=$(systemctl --user is-active vllm.service 2>/dev/null || true)
if [ "$WAR_AKTIV" = "active" ]; then
  echo "[speicher] halte vllm.service an (gibt rund 36 GB frei)"
  systemctl --user stop vllm.service
  sleep 5
fi
set +e
"$@"
RC=$?
set -e
if [ "$WAR_AKTIV" = "active" ]; then
  echo "[speicher] starte vllm.service wieder"
  systemctl --user start vllm.service
fi
echo "[speicher] Kommando beendet mit RC=$RC"
exit $RC
