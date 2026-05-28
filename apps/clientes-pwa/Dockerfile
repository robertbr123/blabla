# Imagem mínima pra servir landing + /.well-known/ no clientes.ondeline.com.br.
# Objetivo principal: hospedar `assetlinks.json` (Android App Links) e
# `apple-app-site-association` (iOS Universal Links) com MIME correto, e
# uma landing simples como fallback quando o app cliente nao esta instalado.
#
# Se um dia virar PWA de verdade, substituir por Next.js como tecnico-pwa.
FROM nginx:1.27-alpine

# Remove config default; usamos a nossa pra controlar MIME do AASA.
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/clientes-pwa.conf
COPY public/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/.well-known/assetlinks.json || exit 1
