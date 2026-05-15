#!/bin/bash
# Inicia todos os serviços em modo PRODUÇÃO via imagens GHCR.
# Uso: ./scripts/start-prod.sh [--pull]
# --pull: força pull das imagens antes de subir (útil para update manual)

set -e

cd "$(dirname "$0")/.."
ROOT=$(pwd)

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${CYAN}[prod]${NC} $1"; }
success() { echo -e "${GREEN}[ok]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[aviso]${NC} $1"; }
fail()    { echo -e "${RED}[erro]${NC}  $1"; exit 1; }

PULL=false
[[ "${1:-}" == "--pull" ]] && PULL=true

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}   Ondeline — Inicialização PRODUÇÃO        ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""

COMPOSE="docker compose -f infra/docker-compose.prod.yml"

# 1. Parar stack de dev se estiver rodando
info "Parando stack de desenvolvimento (se ativa)..."
docker compose -f infra/docker-compose.dev.yml down 2>/dev/null || true

# 2. Pull opcional
if [ "$PULL" = true ]; then
  info "Baixando imagens GHCR..."
  $COMPOSE pull
  success "Imagens atualizadas"
fi

# 3. Subir stack completa
info "Subindo stack Docker de produção..."
$COMPOSE up -d
success "Stack iniciada"

# 4. Aguardar API
info "Aguardando API..."
for i in $(seq 1 20); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/livez 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    success "API respondendo (200 OK)"
    break
  fi
  sleep 3
  if [ "$i" = "20" ]; then
    fail "API não respondeu após 60s. Veja: docker logs blabla-api"
  fi
done

# 5. Status final
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}   Tudo rodando em PRODUÇÃO!               ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
docker ps --format "  🐳 {{.Names}}\t{{.Status}}" | grep blabla || true
echo ""
echo -e "  🌐 Dashboard:    http://localhost:3002"
echo -e "  📱 Tecnico PWA:  http://localhost:3003"
echo -e "  🔧 API:          http://localhost:8000"
echo ""
echo -e "  Logs:       ${CYAN}docker compose -f infra/docker-compose.prod.yml logs -f${NC}"
echo -e "  Parar:      ${CYAN}docker compose -f infra/docker-compose.prod.yml down${NC}"
echo -e "  Atualizar:  ${CYAN}./scripts/start-prod.sh --pull${NC}  (ou aguarde Watchtower)"
echo ""
