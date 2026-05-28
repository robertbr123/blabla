# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# ── Dependências ──────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/clientes-pwa/package.json ./apps/clientes-pwa/
RUN --mount=type=cache,id=pnpm-clientes-pwa,sharing=locked,target=/pnpm/store \
    pnpm install --frozen-lockfile

# ── Build ─────────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/clientes-pwa/node_modules ./apps/clientes-pwa/node_modules
COPY pnpm-workspace.yaml ./
COPY apps/clientes-pwa ./apps/clientes-pwa
RUN pnpm --filter=ondeline-clientes-pwa build && \
    mkdir -p /app/apps/clientes-pwa/public

# ── Runner ────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=builder /app/apps/clientes-pwa/.next/standalone ./
COPY --from=builder /app/apps/clientes-pwa/.next/static ./apps/clientes-pwa/.next/static
COPY --from=builder /app/apps/clientes-pwa/public ./apps/clientes-pwa/public
RUN addgroup -S nodejs && adduser -S nextjs -G nodejs
USER nextjs
EXPOSE 3000
CMD ["node", "apps/clientes-pwa/server.js"]
