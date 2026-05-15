# Build Optimization Design

**Date:** 2026-05-14  
**Status:** Approved

## Problema

O fluxo de dev sofre com builds lentos em dois lugares:

1. **API Docker**: qualquer mudança de `.py` força reinstalação completa de todas as ~30 deps Python porque o `src/` é copiado antes do `pip install`. Tempo estimado: 2-5 min por rebuild.
2. **Frontends Next.js**: cold start e hot-reload lentos por falta de Turbopack.

## Abordagem Escolhida: Quick wins + hot-reload sem rebuild (B)

### API Docker

**Problema atual:**
```
COPY src/          ← invalida cache
RUN pip install .  ← reinstala tudo: ~2-5min
```

**Solução:**
1. `.dockerignore` → context menor (exclui `.venv`, `__pycache__`, `tests/`)
2. Trocar `pip` por `uv` (10-100x mais rápido) + BuildKit cache mount
3. Separar layer de deps de layer de código:
   - Layer 1: `pyproject.toml` + `uv.lock` → `uv sync --frozen --no-install-project` (só deps)
   - Layer 2: `src/` → `uv sync --frozen` (só instala o pacote)
4. Remover `build-essential` (uv usa wheels pré-compilados para todos os pacotes do projeto)
5. Remover `apt-get purge build-essential` (layer extra desnecessária)

**hot-reload em dev:** montar `src/` como volume + `uvicorn --reload`. Mudanças de código refletem em <1s sem nenhum rebuild.

**Worker/beat em dev:** sem volume mount — usam a imagem cacheada. Reinício manual quando necessário.

### Frontends

Adicionar `--turbopack` ao script `dev` no `package.json` do `dashboard` e `tecnico-pwa`. Next.js 15.1.0 tem Turbopack estável.

### Makefile

Separar `make dev` (sem `--build`) de `make dev-build` (força rebuild). Hoje `make dev` sempre reconstrói desnecessariamente.

## Não muda

- `docker-compose.prod.yml` — zero alterações
- Estrutura de código, rotas, banco, workers em produção
- Comportamento funcional da API

## Riscos

- **Baixo**: volume mount no dev sobrescreve `/app/src`; como uv instala em modo editável (`.pth` aponta para `/app/src`), mudanças são vistas imediatamente.
- **Baixo**: remoção de `build-essential` — uv usa wheels. Se algum pacote futuro precisar compilar, basta reintroduzir.
- **Nenhum para prod**: `docker-compose.prod.yml` não é tocado.
