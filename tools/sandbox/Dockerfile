# Sandbox-Bild (platform#3685): Claude Code + Werkzeuge, keine Zugangsdaten im Bild.
# Die Markierung IIL_SANDBOX=1 setzt bewusst nur sandbox.sh, nicht das Bild.
FROM node:22-bookworm-slim

ARG CLAUDE_CODE_VERSION=2.1.288
RUN apt-get update \
 && apt-get install -y --no-install-recommends git python3 python3-pytest make ca-certificates curl gh \
 && rm -rf /var/lib/apt/lists/*
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

COPY selbstpruefung.py waechter.py egress_proxy.py start.sh /sandbox/
RUN chmod 0555 /sandbox/*.py /sandbox/start.sh

USER node
ENV SANDBOX_ARBEIT=/arbeit
WORKDIR /arbeit
ENTRYPOINT ["/sandbox/start.sh"]
