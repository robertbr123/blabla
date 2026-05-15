# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# ── Dependências ──────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/tecnico-pwa/package.json ./apps/tecnico-pwa/
RUN --mount=type=cache,id=pnpm-tecnico-pwa,sharing=locked,target=/pnpm/store \
    pnpm install --frozen-lockfile

# ── Build ─────────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/tecnico-pwa/node_modules ./apps/tecnico-pwa/node_modules
COPY pnpm-workspace.yaml ./
COPY apps/tecnico-pwa ./apps/tecnico-pwa
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN pnpm --filter=ondeline-tecnico-pwa build && \
    mkdir -p /app/apps/tecnico-pwa/public

# ── Runner ────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=builder /app/apps/tecnico-pwa/.next/standalone ./
COPY --from=builder /app/apps/tecnico-pwa/.next/static ./apps/tecnico-pwa/.next/static
COPY --from=builder /app/apps/tecnico-pwa/public ./apps/tecnico-pwa/public
RUN addgroup -S nodejs && adduser -S nextjs -G nodejs
USER nextjs
EXPOSE 3000
CMD ["node", "apps/tecnico-pwa/server.js"]
