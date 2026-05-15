#!/bin/bash
# setup.sh — Configuração inicial da VPS (roda UMA VEZ)
# Instala Docker, cria .env, sobe stack, roda migrations e seed do admin.
# Depois use: docker compose -f infra/docker-compose.prod.yml up -d

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$(pwd)

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[setup]${NC} $1"; }
success() { echo -e "${GREEN}[ok]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[aviso]${NC} $1"; }
fail()    { echo -e "${RED}[erro]${NC}   $1"; exit 1; }
ask()     { echo -e "${BOLD}$1${NC}"; }

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Ondeline — Setup Inicial (VPS)         ║${NC}"
echo -e "${GREEN}║       Rode apenas UMA VEZ por máquina        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Verificar root ─────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  fail "Execute como root: sudo ./scripts/setup.sh"
fi

# ── 2. Detectar OS ────────────────────────────────────────────────────────────
if ! command -v apt-get &>/dev/null; then
  fail "Este script suporta apenas Debian/Ubuntu."
fi

# ── 3. Instalar Docker ────────────────────────────────────────────────────────
apt-get update -qq
if ! command -v docker &>/dev/null; then
  info "Instalando Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
  success "Docker instalado"
else
  success "Docker já instalado ($(docker --version | cut -d' ' -f3 | tr -d ','))"
fi

apt-get install -y openssl -qq 2>/dev/null || true

# ── 4. Criar .env ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD} Configuração do .env                          ${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "$ROOT/.env" ]; then
  warn ".env já existe. Pulando criação (delete-o para reconfigurar)."
else
  JWT_SECRET=$(openssl rand -hex 32)
  PII_ENCRYPTION_KEY=$(openssl rand -hex 16)
  PII_HASH_PEPPER=$(openssl rand -hex 32)
  POSTGRES_PASS=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 20)

  echo -e "${YELLOW}Preencha os campos abaixo. Deixe em branco para configurar depois.${NC}"
  echo ""

  ask "GitHub owner (usuário/org do GHCR, ex: robertbr123):"
  read -r GHCR_OWNER_INPUT
  GHCR_OWNER_INPUT=${GHCR_OWNER_INPUT:-robertbr123}

  ask "Evolution API Server URL pública (ex: https://evolution.seudominio.com):"
  read -r EVOLUTION_SERVER_URL_INPUT

  ask "Evolution API Key (chave de autenticação):"
  read -r EVOLUTION_KEY_INPUT

  ask "Evolution HMAC Secret (webhook secret):"
  read -r EVOLUTION_HMAC_INPUT

  ask "Evolution Instance name (ex: hermes-wa):"
  read -r EVOLUTION_INSTANCE_INPUT
  EVOLUTION_INSTANCE_INPUT=${EVOLUTION_INSTANCE_INPUT:-hermes-wa}

  ask "SGP Ondeline Token (deixe vazio se não usa):"
  read -r SGP_TOKEN_INPUT

  ask "SGP LinkNetAM Token (deixe vazio se não usa):"
  read -r SGP_LINKNETAM_TOKEN_INPUT

  ask "Hermes LLM URL (ex: http://127.0.0.1:8642/v1):"
  read -r HERMES_URL_INPUT
  HERMES_URL_INPUT=${HERMES_URL_INPUT:-http://127.0.0.1:8642/v1}

  ask "Hermes API Key:"
  read -r HERMES_KEY_INPUT

  echo ""
  info "Gerando secrets de criptografia automaticamente..."

  cat > "$ROOT/.env" <<EOF
# Aplicação
ENV=production
LOG_LEVEL=INFO

# GHCR — owner das imagens Docker
GHCR_OWNER=${GHCR_OWNER_INPUT}

# Banco de dados
POSTGRES_USER=ondeline
POSTGRES_PASSWORD=${POSTGRES_PASS}
POSTGRES_DB=ondeline
DATABASE_URL=postgresql+asyncpg://ondeline:${POSTGRES_PASS}@postgres:5432/ondeline
DATABASE_URL_SYNC=postgresql+psycopg://ondeline:${POSTGRES_PASS}@postgres:5432/ondeline

# Redis
REDIS_URL=redis://redis:6379/0

# Evolution API (WhatsApp)
EVOLUTION_URL=http://evolution-api:8080
EVOLUTION_SERVER_URL=${EVOLUTION_SERVER_URL_INPUT}
EVOLUTION_KEY=${EVOLUTION_KEY_INPUT}
EVOLUTION_HMAC_SECRET=${EVOLUTION_HMAC_INPUT}
EVOLUTION_INSTANCE=${EVOLUTION_INSTANCE_INPUT}
EVOLUTION_IP_ALLOWLIST=

# Webhook
WEBHOOK_MAX_BODY_BYTES=1048576
WEBHOOK_RATE_LIMIT=100/minute

# Bot
BOT_ACK_TEXT=Olá! Recebi sua mensagem. Em instantes um de nossos atendentes vai falar com você.

# SGP
SGP_ONDELINE_BASE=https://ondeline.sgp.tsmx.com.br
SGP_ONDELINE_TOKEN=${SGP_TOKEN_INPUT}
SGP_ONDELINE_APP=mikrotik
SGP_LINKNETAM_BASE=https://linknetam.sgp.net.br
SGP_LINKNETAM_TOKEN=${SGP_LINKNETAM_TOKEN_INPUT}
SGP_LINKNETAM_APP=APP

# Hermes LLM
HERMES_URL=${HERMES_URL_INPUT}
HERMES_API_KEY=${HERMES_KEY_INPUT}
HERMES_MODEL=Hermes-3

# LLM controls
LLM_MAX_ITER=5
LLM_TIMEOUT_SECONDS=30
LLM_MAX_TOKENS_PER_CONVERSA_DIA=50000
LLM_HISTORY_TURNS=12

# SGP cache TTLs (segundos)
SGP_CACHE_TTL_CLIENTE=3600
SGP_CACHE_TTL_FATURAS=300
SGP_CACHE_TTL_NEGATIVO=300

# Auth — gerados automaticamente
JWT_SECRET=${JWT_SECRET}
PII_ENCRYPTION_KEY=${PII_ENCRYPTION_KEY}
PII_HASH_PEPPER=${PII_HASH_PEPPER}
DUMMY_PASSWORD_HASH=

# Observabilidade — opcional
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=ondeline-api

# Dashboard — URLs (vazias = caminhos relativos no browser)
NEXT_PUBLIC_API_URL=
INTERNAL_API_URL=http://api:8000

# Admin inicial
ADMIN_EMAIL=
ADMIN_PASSWORD=
ADMIN_NAME=
EOF

  success ".env criado com secrets gerados automaticamente"
fi

# ── 5. Pull das imagens GHCR ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD} Pull das imagens GHCR                        ${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

OWNER=$(grep '^GHCR_OWNER=' "$ROOT/.env" | cut -d= -f2)
warn "As imagens GHCR precisam ser PÚBLICAS em: https://github.com/users/${OWNER}/packages"
warn "Configure visibilidade antes de continuar. Pressione ENTER quando feito."
read -r

info "Baixando imagens GHCR..."
docker compose -f "$ROOT/infra/docker-compose.prod.yml" --env-file "$ROOT/.env" pull
success "Imagens baixadas"

# ── 6. Subir postgres e redis para migrations ──────────────────────────────────
echo ""
info "Iniciando banco de dados..."
docker compose -f "$ROOT/infra/docker-compose.prod.yml" --env-file "$ROOT/.env" \
  up -d postgres redis

info "Aguardando PostgreSQL..."
for i in $(seq 1 30); do
  if docker exec blabla-postgres pg_isready -U ondeline -d ondeline &>/dev/null 2>&1; then
    success "PostgreSQL pronto"
    break
  fi
  sleep 2
  [ "$i" = "30" ] && fail "PostgreSQL não respondeu após 60s. Verifique: docker logs blabla-postgres"
done

# ── 7. Migrations Alembic ──────────────────────────────────────────────────────
echo ""
info "Subindo container API para migrations..."
docker compose -f "$ROOT/infra/docker-compose.prod.yml" --env-file "$ROOT/.env" up -d api
sleep 8

info "Rodando migrations..."
docker exec blabla-api sh -c "cd /app && alembic upgrade head" 2>&1 | sed 's/^/  /'
success "Migrations aplicadas"

# ── 8. Seed do usuário admin ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD} Criação do usuário administrador             ${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

ask "Email do admin:"
read -r ADMIN_EMAIL_INPUT

ask "Senha do admin (mínimo 8 caracteres):"
read -rs ADMIN_PASS_INPUT
echo ""

ask "Nome do admin:"
read -r ADMIN_NAME_INPUT

sed -i "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=${ADMIN_EMAIL_INPUT}|" "$ROOT/.env"
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${ADMIN_PASS_INPUT}|" "$ROOT/.env"
sed -i "s|^ADMIN_NAME=.*|ADMIN_NAME=${ADMIN_NAME_INPUT}|" "$ROOT/.env"

info "Criando usuário admin..."
docker exec \
  -e ADMIN_EMAIL="$ADMIN_EMAIL_INPUT" \
  -e ADMIN_PASSWORD="$ADMIN_PASS_INPUT" \
  -e ADMIN_NAME="$ADMIN_NAME_INPUT" \
  blabla-api \
  python -m ondeline_api.scripts.seed_admin 2>&1 | sed 's/^/  /'

success "Admin criado: ${ADMIN_EMAIL_INPUT}"

# ── 9. Subir stack completa ───────────────────────────────────────────────────
echo ""
info "Subindo stack completa..."
docker compose -f "$ROOT/infra/docker-compose.prod.yml" --env-file "$ROOT/.env" up -d
success "Stack em execução"

# ── 10. Resumo final ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup concluído com sucesso!               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
docker ps --format "  🐳 {{.Names}}\t{{.Status}}" | grep blabla || true
echo ""
echo -e "  🌐 Dashboard:   http://localhost:3002"
echo -e "  📱 Tecnico PWA: http://localhost:3003"
echo -e "  🔧 API:         http://localhost:8000"
echo ""
echo -e "  Secrets em: ${CYAN}${ROOT}/.env${NC}  — guarde em local seguro, NÃO está no git!"
echo ""
echo -e "  Watchtower monitora GHCR a cada 30s e atualiza automaticamente."
echo -e "  Para forçar update: ${CYAN}docker compose -f infra/docker-compose.prod.yml pull && docker compose ... up -d${NC}"
echo ""
