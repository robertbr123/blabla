#!/bin/bash
# Inicia todos os serviços em modo PRODUÇÃO
# Uso: ./scripts/start-prod.sh

set -e

# Navegar para a raiz do projeto independente de onde for chamado
cd "$(dirname "$0")/.."
ROOT=$(pwd)

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[prod]${NC} $1"; }
success() { echo -e "${GREEN}[ok]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[aviso]${NC} $1"; }
fail()    { echo -e "${RED}[erro]${NC}  $1"; exit 1; }

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}   Ondeline — Inicialização PRODUÇÃO        ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""

# 1. Parar stack de dev se estiver rodando
info "Parando stack de desenvolvimento (se ativa)..."
docker compose -f infra/docker-compose.dev.yml down 2>/dev/null || true

# 2. Parar frontends dev em background (pnpm dev)
info "Encerrando processos pnpm dev (se existirem)..."
pkill -f "pnpm next dev" 2>/dev/null || true
sleep 1

# 3. Build Next.js — Dashboard
info "Build do Dashboard (porta 3002)..."
cd "$ROOT/apps/dashboard"
INTERNAL_API_URL=http://127.0.0.1:8000 pnpm build --no-color 2>&1 | grep -E "Route|Error|warn|error|✓|○|ƒ" | tail -10
success "Dashboard buildado"

# 4. Build Next.js — Tecnico PWA
info "Build do Tecnico PWA (porta 3003)..."
cd "$ROOT/apps/tecnico-pwa"
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 pnpm build --no-color 2>&1 | grep -E "Route|Error|warn|error|✓|○|ƒ" | tail -10
success "Tecnico PWA buildado"

cd "$ROOT"

# 5. Subir stack Docker de produção (com rebuild da API)
info "Subindo stack Docker de produção..."
make prod-build 2>&1 | grep -E "Container|Image|Built|Started|Error" | sed 's/^/  /'
success "Stack Docker iniciado"

# 6. Aguardar API ficar saudável
info "Aguardando API..."
for i in $(seq 1 20); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/livez 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    success "API respondendo (200 OK)"
    break
  fi
  sleep 2
  if [ "$i" = "20" ]; then
    fail "API não respondeu após 40s. Veja: docker logs ondeline-api"
  fi
done

# 7. Reiniciar serviços systemd dos frontends
info "Iniciando serviços systemd dos frontends..."
systemctl restart ondeline-dashboard ondeline-tecnico-pwa
sleep 4
success "Frontends iniciados"

# 8. Status final
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}   Tudo rodando em PRODUÇÃO!               ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
docker ps --format "  🐳 {{.Names}}\t{{.Status}}" | grep ondeline
echo ""
echo -e "  🌐 Dashboard:    http://localhost:3002"
echo -e "  📱 Tecnico PWA:  http://localhost:3003"
echo -e "  🔧 API:          http://localhost:8000"
echo ""
echo -e "  Logs Docker:    ${CYAN}make prod-logs${NC}"
echo -e "  Logs Dashboard: ${CYAN}journalctl -u ondeline-dashboard -f${NC}"
echo -e "  Logs PWA:       ${CYAN}journalctl -u ondeline-tecnico-pwa -f${NC}"
echo -e "  Parar tudo:     ${CYAN}make prod-down${NC}"
echo ""
