# GenieACS — ACS TR-069 pra gerencia remota das ONUs (trocar senha WiFi,
# listar aparelhos conectados, reboot, diagnostico).
# Nao existe imagem oficial; buildamos a partir do node (genieacs 1.2 e JS puro,
# sem deps nativas). Pin de versao pra estabilidade em producao.
FROM node:20-alpine

RUN npm install -g genieacs@1.2.13

# Dir de extensoes (scripts de provisionamento custom no futuro).
ENV GENIEACS_EXT_DIR=/opt/genieacs/ext
RUN mkdir -p /opt/genieacs/ext

# O processo real (genieacs-cwmp / -nbi / -fs / -ui) e definido por servico
# via `command:` no docker-compose. Todos compartilham esta mesma imagem.
