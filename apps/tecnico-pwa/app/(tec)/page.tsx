'use client'
import { OsCard } from '@/components/os-card'
import { Button } from '@/components/ui/button'
import { useMyOs } from '@/lib/api/queries'

export default function HomePage() {
  const { data, isLoading, error, refetch } = useMyOs()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Minhas OS</h1>
          <p className="text-xs text-muted-foreground">
            Pendentes e em andamento
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Atualizar
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <div className="space-y-3">
          {data.length === 0 ? (
            <div className="rounded-lg border bg-card p-6 text-center text-sm text-muted-foreground">
              Nenhuma OS atribuída
            </div>
          ) : (
            data.map((os) => <OsCard key={os.id} os={os} />)
          )}
        </div>
      )}
    </div>
  )
}
