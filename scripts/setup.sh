#!/bin/bash
# setup.sh — Configuração inicial da Ondeline em uma máquina nova
# Roda UMA VEZ. Depois use ./scripts/start-prod.sh para iniciar.
#
# Uso: ./scripts/setup.sh

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$(pwd)

# ── Cores ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[setup]${NC} $1"; }
success() { echo -e "${GREEN}[ok]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[aviso]${NC} $1"; }
fail()    { echo -e "${RED}[erro]${NC}   $1"; exit 1; }
ask()     { echo -e "${BOLD}$1${NC}"; }

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Ondeline — Setup Inicial               ║${NC}"
echo -e "${GREEN}║       Rode apenas UMA VEZ por máquina        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Verificar root ─────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  fail "Execute como root: sudo ./scripts/setup.sh"
fi

# ── 2. Detectar OS ────────────────────────────────────────────────────────────
if ! command -v apt-get &>/dev/null; then
  fail "Este script suporta apenas Debian/Ubuntu (apt-get não encontrado)."
fi

# ── 3. Instalar dependências de sistema ───────────────────────────────────────
info "Atualizando pacotes..."
apt-get update -qq

# Docker
if ! command -v docker &>/dev/null; then
  info "Instalando Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
  success "Docker instalado"
else
  success "Docker já instalado ($(docker --version | cut -d' ' -f3 | tr -d ','))"
fi

# Node.js 22
if ! command -v node &>/dev/null || [[ "$(node --version | cut -d'.' -f1 | tr -d 'v')" -lt 20 ]]; then
  info "Instalando Node.js 22..."
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs -qq
  success "Node.js instalado ($(node --version))"
else
  success "Node.js já instalado ($(node --version))"
fi

# pnpm
if ! command -v pnpm &>/dev/null; then
  info "Instalando pnpm..."
  npm install -g pnpm@9 -q
  success "pnpm instalado"
else
  success "pnpm já instalado ($(pnpm --version))"
fi

# openssl (para gerar secrets)
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
  # Gerar secrets automaticamente
  JWT_SECRET=$(openssl rand -hex 32)
  PII_ENCRYPTION_KEY=$(openssl rand -hex 16)   # 32 chars hex = 16 bytes
  PII_HASH_PEPPER=$(openssl rand -hex 32)
  POSTGRES_PASS=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 20)

  # Perguntar campos obrigatórios de negócio
  echo -e "${YELLOW}Preencha os campos abaixo. Deixe em branco para configurar depois.${NC}"
  echo ""

  ask "Evolution API URL (ex: http://SEU-IP:8080):"
  read -r EVOLUTION_URL_INPUT
  EVOLUTION_URL_INPUT=${EVOLUTION_URL_INPUT:-http://localhost:8080}

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

# Banco de dados
POSTGRES_USER=ondeline
POSTGRES_PASSWORD=${POSTGRES_PASS}
POSTGRES_DB=ondeline
DATABASE_URL=postgresql+asyncpg://ondeline:${POSTGRES_PASS}@postgres:5432/ondeline
DATABASE_URL_SYNC=postgresql+psycopg://ondeline:${POSTGRES_PASS}@postgres:5432/ondeline

# Redis
REDIS_URL=redis://redis:6379/0

# Evolution API (WhatsApp)
EVOLUTION_URL=${EVOLUTION_URL_INPUT}
EVOLUTION_KEY=${EVOLUTION_KEY_INPUT}
EVOLUTION_HMAC_SECRET=${EVOLUTION_HMAC_INPUT}
EVOLUTION_INSTANCE=${EVOLUTION_INSTANCE_INPUT}
EVOLUTION_IP_ALLOWLIST=

# Webhook
WEBHOOK_MAX_BODY_BYTES=1048576
WEBHOOK_RATE_LIMIT=100/minute

# Bot
BOT_ACK_TEXT=Olá! 😊 Recebi sua mensagem. Em instantes um de nossos atendentes vai falar com você.

# Celery
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=

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

# Admin inicial — preenchido abaixo
ADMIN_EMAIL=
ADMIN_PASSWORD=
ADMIN_NAME=
EOF

  success ".env criado com secrets gerados automaticamente"
fi

# ── 5. Criar apps/dashboard/.env.local ───────────────────────────────────────
if [ ! -f "$ROOT/apps/dashboard/.env.local" ]; then
  info "Criando apps/dashboard/.env.local..."
  cat > "$ROOT/apps/dashboard/.env.local" <<EOF
NEXT_PUBLIC_API_URL=
INTERNAL_API_URL=http://127.0.0.1:8000
EOF
  success "apps/dashboard/.env.local criado"
else
  # Garantir que o IP está correto mesmo que o arquivo já exista
  if grep -q "172\." "$ROOT/apps/dashboard/.env.local" 2>/dev/null; then
    warn "Corrigindo INTERNAL_API_URL com IP de Docker antigo..."
    sed -i 's|INTERNAL_API_URL=.*|INTERNAL_API_URL=http://127.0.0.1:8000|' "$ROOT/apps/dashboard/.env.local"
    success "INTERNAL_API_URL corrigido"
  else
    success "apps/dashboard/.env.local já existe"
  fi
fi

# ── 6. Instalar dependências dos frontends ────────────────────────────────────
echo ""
info "Instalando dependências do Dashboard..."
cd "$ROOT/apps/dashboard" && pnpm install --frozen-lockfile 2>&1 | tail -3
success "Dashboard: dependências instaladas"

info "Instalando dependências do Tecnico PWA..."
cd "$ROOT/apps/tecnico-pwa" && pnpm install --frozen-lockfile 2>&1 | tail -3
success "Tecnico PWA: dependências instaladas"

cd "$ROOT"

# ── 7. Criar serviços systemd ─────────────────────────────────────────────────
echo ""
info "Registrando serviços systemd..."

cat > /etc/systemd/system/ondeline-dashboard.service <<EOF
[Unit]
Description=Ondeline Dashboard (Next.js)
After=network.target

[Service]
Type=simple
WorkingDirectory=${ROOT}/apps/dashboard
ExecStart=/usr/bin/pnpm next start --port 3002
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/ondeline-tecnico-pwa.service <<EOF
[Unit]
Description=Ondeline Tecnico PWA (Next.js)
After=network.target

[Service]
Type=simple
WorkingDirectory=${ROOT}/apps/tecnico-pwa
ExecStart=/usr/bin/pnpm next start --port 3003
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ondeline-dashboard ondeline-tecnico-pwa
success "Serviços systemd registrados e habilitados no boot"

# ── 8. Build do Docker (API) ──────────────────────────────────────────────────
echo ""
info "Fazendo build da imagem Docker da API..."
docker compose -f "$ROOT/infra/docker-compose.prod.yml" --env-file "$ROOT/.env" build 2>&1 \
  | grep -E "CACHED|DONE|error|Error|warning" | tail -10
success "Imagem Docker buildada"

# ── 9. Subir postgres e redis para rodar migrations ───────────────────────────
echo ""
info "Iniciando banco de dados para migrations..."
docker compose -f "$ROOT/infra/docker-compose.prod.yml" --env-file "$ROOT/.env" \
  up -d postgres redis

info "Aguardando PostgreSQL ficar pronto..."
for i in $(seq 1 30); do
  if docker exec ondeline-postgres pg_isready -U ondeline -d ondeline &>/dev/null 2>&1; then
    success "PostgreSQL pronto"
    break
  fi
  sleep 2
  if [ "$i" = "30" ]; then
    fail "PostgreSQL não respondeu após 60s. Verifique: docker logs ondeline-postgres"
  fi
done

# ── 10. Rodar migrations Alembic ──────────────────────────────────────────────
echo ""
info "Rodando migrations do banco de dados..."

# Subir o container api temporariamente para rodar o alembic
docker compose -f "$ROOT/infra/docker-compose.prod.yml" --env-file "$ROOT/.env" \
  up -d api

sleep 8

docker exec ondeline-api \
  sh -c "cd /app && alembic upgrade head" 2>&1 | sed 's/^/  /'

success "Migrations aplicadas com sucesso"

# ── 11. Seed do usuário admin ─────────────────────────────────────────────────
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

# Atualizar .env com dados do admin
sed -i "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=${ADMIN_EMAIL_INPUT}|" "$ROOT/.env"
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${ADMIN_PASS_INPUT}|" "$ROOT/.env"
sed -i "s|^ADMIN_NAME=.*|ADMIN_NAME=${ADMIN_NAME_INPUT}|" "$ROOT/.env"

info "Criando usuário admin..."
docker exec \
  -e ADMIN_EMAIL="$ADMIN_EMAIL_INPUT" \
  -e ADMIN_PASSWORD="$ADMIN_PASS_INPUT" \
  -e ADMIN_NAME="$ADMIN_NAME_INPUT" \
  ondeline-api \
  python -m ondeline_api.scripts.seed_admin 2>&1 | sed 's/^/  /'

success "Usuário admin criado: ${ADMIN_EMAIL_INPUT}"

# ── 12. Build dos frontends Next.js ───────────────────────────────────────────
echo ""
info "Build do Dashboard Next.js..."
cd "$ROOT/apps/dashboard"
INTERNAL_API_URL=http://127.0.0.1:8000 pnpm build --no-color 2>&1 \
  | grep -E "✓|error|Error|warn" | tail -5
success "Dashboard buildado"

info "Build do Tecnico PWA Next.js..."
cd "$ROOT/apps/tecnico-pwa"
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 pnpm build --no-color 2>&1 \
  | grep -E "✓|error|Error|warn" | tail -5
success "Tecnico PWA buildado"

cd "$ROOT"

# ── 13. Iniciar tudo via start-prod.sh ────────────────────────────────────────
echo ""
info "Iniciando todos os serviços em produção..."
bash "$ROOT/scripts/start-prod.sh"

# ── 14. Resumo final ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup concluído com sucesso!               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Secrets gerados estão em: ${CYAN}${ROOT}/.env${NC}"
echo -e "  Guarde o .env em local seguro — NÃO está no git!"
echo ""
echo -e "  Próximos inícios:"
echo -e "    ${CYAN}./scripts/start-prod.sh${NC}   (produção)"
echo -e "    ${CYAN}./scripts/start-dev.sh${NC}    (desenvolvimento)"
echo ""
