#!/bin/bash
# Inicia todos os serviços em modo DESENVOLVIMENTO.
# Uso: ./scripts/start-dev.sh
#
# API:         hot-reload automático ao salvar .py (Docker local build)
# Dashboard:   pnpm dev --turbopack na porta 3002 (log em /tmp/dashboard-dev.log)
# Tecnico PWA: pnpm dev --turbopack na porta 3003 (log em /tmp/tecnico-pwa-dev.log)

set -e

cd "$(dirname "$0")/.."
ROOT=$(pwd)

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${BLUE}[dev]${NC}  $1"; }
success() { echo -e "${GREEN}[ok]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[aviso]${NC} $1"; }
fail()    { echo -e "${RED}[erro]${NC}  $1"; exit 1; }

echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}   Ondeline — Inicialização DESENVOLVIMENTO ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# 1. Parar stack de produção se estiver rodando
info "Parando stack de produção (se ativa)..."
docker compose -f infra/docker-compose.prod.yml down 2>/dev/null || true

# 2. Parar qualquer pnpm dev anterior
info "Encerrando processos dev anteriores..."
pkill -f "pnpm next dev" 2>/dev/null || true
sleep 1

# 3. Subir stack Docker de desenvolvimento (com rebuild)
info "Subindo stack Docker de desenvolvimento (build local)..."
docker compose -f infra/docker-compose.dev.yml up -d --build 2>&1 \
  | grep -E "Container|Image|Built|Started|Error" | sed 's/^/  /'
success "Stack Docker iniciada"

# 4. Aguardar API
info "Aguardando API (hot-reload ativo)..."
for i in $(seq 1 20); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/livez 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    success "API respondendo (200 OK) — hot-reload ativo em apps/api/src/"
    break
  fi
  sleep 2
  if [ "$i" = "20" ]; then
    fail "API não respondeu após 40s. Veja: docker logs blabla-api"
  fi
done

# 5. Iniciar Dashboard em modo dev (background)
info "Iniciando Dashboard dev (porta 3002)..."
cd "$ROOT/apps/dashboard"
nohup pnpm dev > /tmp/dashboard-dev.log 2>&1 &
success "Dashboard dev PID=$! → /tmp/dashboard-dev.log"

# 6. Iniciar Tecnico PWA em modo dev (background)
info "Iniciando Tecnico PWA dev (porta 3003)..."
cd "$ROOT/apps/tecnico-pwa"
nohup pnpm dev > /tmp/tecnico-pwa-dev.log 2>&1 &
success "Tecnico PWA dev PID=$! → /tmp/tecnico-pwa-dev.log"

cd "$ROOT"

# 7. Aguardar frontends
info "Aguardando frontends (Turbopack)..."
sleep 8
for port in 3002 3003; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port 2>/dev/null || echo "000")
  if [ "$STATUS" != "000" ]; then
    success "Porta $port respondendo"
  else
    warn "Porta $port ainda iniciando — verifique os logs"
  fi
done

# 8. Status final
echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}   Tudo rodando em DESENVOLVIMENTO!        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""
docker ps --format "  🐳 {{.Names}}\t{{.Status}}" | grep blabla || true
echo ""
echo -e "  🌐 Dashboard:    http://localhost:3002  (Turbopack)"
echo -e "  📱 Tecnico PWA:  http://localhost:3003  (Turbopack)"
echo -e "  🔧 API:          http://localhost:8000  (hot-reload)"
echo ""
echo -e "  Edite .py em apps/api/src/ → API recarrega automaticamente"
echo ""
echo -e "  Logs API:       ${CYAN}docker compose -f infra/docker-compose.dev.yml logs -f api${NC}"
echo -e "  Logs Dashboard: ${CYAN}tail -f /tmp/dashboard-dev.log${NC}"
echo -e "  Logs PWA:       ${CYAN}tail -f /tmp/tecnico-pwa-dev.log${NC}"
echo -e "  Parar Docker:   ${CYAN}docker compose -f infra/docker-compose.dev.yml down${NC}"
echo ""
