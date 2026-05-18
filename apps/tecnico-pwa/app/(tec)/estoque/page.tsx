'use client'
import { useMyEstoqueSaldo } from '@/lib/api/queries'

export default function MeuEstoquePage() {
  const { data, isLoading, error } = useMyEstoqueSaldo()

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Meu estoque</h1>
        <p className="text-sm text-muted-foreground">
          Itens disponíveis na sua van.
        </p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <div className="space-y-2">
          {data.linhas.length === 0 && (
            <p className="text-sm text-muted-foreground">Sem itens cadastrados.</p>
          )}
          {data.linhas.map((l) => (
            <div
              key={l.item_id}
              className="flex items-center justify-between rounded-md border bg-card p-3"
            >
              <div>
                <p className="font-medium">{l.nome}</p>
                <p className="text-xs text-muted-foreground">
                  {l.sku} · {l.categoria}
                  {l.serializado ? ' · serializado' : ''}
                </p>
              </div>
              <div className="text-right">
                <p
                  className={
                    l.saldo < 0
                      ? 'text-2xl font-bold text-destructive'
                      : l.saldo === 0
                        ? 'text-2xl font-bold text-muted-foreground'
                        : 'text-2xl font-bold'
                  }
                >
                  {l.saldo}
                </p>
                <p className="text-xs text-muted-foreground">em estoque</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
