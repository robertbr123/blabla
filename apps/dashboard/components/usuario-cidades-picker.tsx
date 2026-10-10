'use client'
import { useId, useMemo, useState } from 'react'
import { Plus, Search, X } from 'lucide-react'
import { TONE_SOFT } from '@/components/noc/primitives'
import { Input } from '@/components/ui/input'
import { useUsuariosCidades } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

/** Minusculas e sem acento — busca tolerante ("sao" acha "São"). */
export function normalizar(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

const LINK_BTN =
  'rounded-sm text-xs font-medium text-primary underline-offset-4 transition-colors hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:text-muted-foreground disabled:opacity-60'

/**
 * Seletor das cidades de um atendente: busca + checklist alimentado pela base
 * de clientes, chips removiveis no topo e inclusao manual (digitar + Enter)
 * pra cidade que ainda nao tem cliente.
 */
export function UsuarioCidadesPicker({
  value,
  onChange,
}: {
  value: string[]
  onChange: (next: string[]) => void
}) {
  const { data, isLoading, error } = useUsuariosCidades()
  const [busca, setBusca] = useState('')
  const buscaId = useId()
  const ajudaId = useId()

  // Lista conhecida + as ja marcadas que nao estao nela (adicionadas a mao).
  const todas = useMemo(() => {
    const set = new Set<string>([...(data ?? []), ...value])
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'pt-BR'))
  }, [data, value])

  const termo = normalizar(busca)
  const texto = busca.trim().replace(/\s+/g, ' ')
  const visiveis = termo ? todas.filter((c) => normalizar(c).includes(termo)) : todas
  const selecionadas = new Set(value)
  const existente = termo ? todas.find((c) => normalizar(c) === termo) : undefined
  const podeAdicionar = texto !== '' && !existente
  const todasVisiveisMarcadas = visiveis.length > 0 && visiveis.every((c) => selecionadas.has(c))

  function alternar(cidade: string) {
    onChange(selecionadas.has(cidade) ? value.filter((c) => c !== cidade) : [...value, cidade])
  }

  function confirmarBusca() {
    if (existente) {
      if (!selecionadas.has(existente)) onChange([...value, existente])
    } else if (podeAdicionar) {
      onChange([...value, texto])
    } else {
      return
    }
    setBusca('')
  }

  function selecionarVisiveis() {
    onChange([...value, ...visiveis.filter((c) => !selecionadas.has(c))])
  }

  return (
    <fieldset className="min-w-0 space-y-2">
      <legend className="text-sm font-medium leading-none">Cidades atendidas</legend>
      <p id={ajudaId} className="text-xs text-muted-foreground">
        O atendente só vê conversas e ordens de serviço de clientes das cidades marcadas.{' '}
        <span className="font-medium text-foreground">
          Sem nenhuma cidade marcada, o atendente vê todas.
        </span>
      </p>

      {value.length > 0 ? (
        <ul aria-label="Cidades selecionadas" className="flex flex-wrap gap-1.5">
          {value.map((c) => (
            <li
              key={c}
              className={cn(
                'inline-flex h-6 max-w-full items-center gap-0.5 rounded-md pl-2 pr-0.5 text-xs font-medium ring-1 ring-inset',
                TONE_SOFT.primary,
              )}
            >
              <span className="truncate">{c}</span>
              <button
                type="button"
                onClick={() => alternar(c)}
                title={`Remover ${c}`}
                aria-label={`Remover ${c}`}
                className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-sm transition-colors hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <X aria-hidden className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
          Nenhuma cidade marcada — acesso a todas as cidades.
        </p>
      )}

      <div className="overflow-hidden rounded-md border">
        <div className="relative border-b">
          <Search
            aria-hidden
            className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          />
          <label htmlFor={buscaId} className="sr-only">
            Buscar ou adicionar cidade
          </label>
          <Input
            id={buscaId}
            type="text"
            autoComplete="off"
            enterKeyHint="done"
            placeholder="Buscar ou digitar uma cidade…"
            aria-describedby={ajudaId}
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            onKeyDown={(e) => {
              if (e.key !== 'Enter') return
              // Nunca deixa o Enter enviar o formulario do dialog.
              e.preventDefault()
              confirmarBusca()
            }}
            className="rounded-none border-0 pl-8 focus-visible:ring-inset focus-visible:ring-offset-0"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b bg-muted/50 px-3 py-1.5">
          <span className="num text-[11px] text-muted-foreground">
            {value.length} de {todas.length} marcadas
          </span>
          <span className="flex items-center gap-3">
            <button
              type="button"
              className={LINK_BTN}
              onClick={selecionarVisiveis}
              disabled={visiveis.length === 0 || todasVisiveisMarcadas}
            >
              {termo ? 'Selecionar filtradas' : 'Selecionar todas'}
            </button>
            <button
              type="button"
              className={LINK_BTN}
              onClick={() => onChange([])}
              disabled={value.length === 0}
            >
              Limpar
            </button>
          </span>
        </div>

        <div className="max-h-48 overflow-y-auto py-1">
          {isLoading && (
            <p role="status" className="px-3 py-2 text-xs text-muted-foreground">
              Carregando cidades…
            </p>
          )}
          {error && (
            <p role="alert" className="px-3 py-2 text-xs text-destructive">
              Não foi possível carregar a lista de cidades
              {error instanceof Error && error.message ? ` (${error.message})` : ''}. Você ainda
              pode digitar o nome e pressionar Enter.
            </p>
          )}
          {visiveis.map((c) => (
            <label
              key={c}
              className="flex min-h-8 cursor-pointer items-center gap-2.5 px-3 py-1 text-sm transition-colors hover:bg-elevated"
            >
              <input
                type="checkbox"
                checked={selecionadas.has(c)}
                onChange={() => alternar(c)}
                className="h-4 w-4 shrink-0 cursor-pointer accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <span className="min-w-0 break-words">{c}</span>
            </label>
          ))}
          {podeAdicionar && (
            <button
              type="button"
              onClick={confirmarBusca}
              className="flex min-h-8 w-full items-center gap-2.5 px-3 py-1 text-left text-sm text-primary transition-colors hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
            >
              <Plus aria-hidden className="h-4 w-4 shrink-0" />
              <span className="min-w-0 break-words">Adicionar &quot;{texto}&quot;</span>
            </button>
          )}
          {!isLoading && !error && visiveis.length === 0 && !podeAdicionar && (
            <p className="px-3 py-2 text-xs text-muted-foreground">
              Nenhuma cidade na base de clientes ainda. Digite o nome e pressione Enter para
              adicionar.
            </p>
          )}
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        A lista traz só cidades que já têm clientes. Para outra cidade, digite o nome e
        pressione Enter.
      </p>
    </fieldset>
  )
}
