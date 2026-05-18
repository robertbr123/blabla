'use client'
import { useCanais } from '@/lib/api/queries'
import { Badge } from '@/components/ui/badge'

export default function CanaisPage() {
  const { data, isLoading, error } = useCanais()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Canais WhatsApp</h1>
        <p className="text-sm text-muted-foreground">
          Cada canal mapeia uma instância Evolution (Suporte, Comercial, etc.) com regras próprias.
          Crie/edite via API (POST/PATCH /api/v1/canais) — UI completa em fase futura.
        </p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <div className="rounded-md border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Nome</th>
                <th className="px-4 py-3">Slug</th>
                <th className="px-4 py-3">Evolution instance</th>
                <th className="px-4 py-3">Prompt</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-muted-foreground">
                    Nenhum canal cadastrado. O canal default será criado automaticamente no próximo restart do API.
                  </td>
                </tr>
              )}
              {data.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3 font-medium">{c.nome}</td>
                  <td className="px-4 py-3 font-mono text-xs">{c.slug}</td>
                  <td className="px-4 py-3 font-mono text-xs">{c.evolution_instance}</td>
                  <td className="px-4 py-3 text-xs">{c.prompt_variant}</td>
                  <td className="px-4 py-3">
                    <Badge variant={c.ativo ? 'default' : 'outline'}>
                      {c.ativo ? 'Ativo' : 'Desativado'}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
