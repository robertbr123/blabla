'use client'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import {
  useEstoqueItens,
  useEstoqueSaldo,
  useTecnicos,
} from '@/lib/api/queries'

export default function EstoquePage() {
  const [tecnicoId, setTecnicoId] = useState<string>('')
  const { data: itens, isLoading: loadingItens } = useEstoqueItens(false)
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const { data: saldo, isLoading: loadingSaldo } = useEstoqueSaldo(tecnicoId || null)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Estoque</h1>
        <p className="text-sm text-muted-foreground">
          Catálogo de itens e saldo por técnico. Operações (entrada/saída/devolução)
          via API por enquanto — UI completa em fase futura.
        </p>
      </div>

      {/* Catálogo */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Catálogo</h2>
        {loadingItens && <p className="text-sm text-muted-foreground">Carregando…</p>}
        {itens && (
          <div className="rounded-md border bg-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">Categoria</th>
                  <th className="px-4 py-3">Serializado?</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {itens.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-6 text-center text-muted-foreground">
                      Nenhum item cadastrado. Use POST /api/v1/estoque/itens.
                    </td>
                  </tr>
                )}
                {itens.map((it) => (
                  <tr key={it.id} className="border-b last:border-b-0 hover:bg-muted/50">
                    <td className="px-4 py-3 font-mono text-xs">{it.sku}</td>
                    <td className="px-4 py-3 font-medium">{it.nome}</td>
                    <td className="px-4 py-3 capitalize text-muted-foreground">
                      {it.categoria}
                    </td>
                    <td className="px-4 py-3">{it.serializado ? 'Sim' : 'Não'}</td>
                    <td className="px-4 py-3">
                      <Badge variant={it.ativo ? 'default' : 'outline'}>
                        {it.ativo ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Saldo por técnico */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Saldo por técnico</h2>
        <div className="mb-3 max-w-md">
          <Select value={tecnicoId} onChange={(e) => setTecnicoId(e.target.value)}>
            <option value="">Selecione um técnico…</option>
            {(tecnicos?.items ?? []).map((t) => (
              <option key={t.id} value={t.id}>{t.nome}</option>
            ))}
          </Select>
        </div>
        {tecnicoId && loadingSaldo && (
          <p className="text-sm text-muted-foreground">Carregando saldo…</p>
        )}
        {tecnicoId && saldo && (
          <div className="rounded-md border bg-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Item</th>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Categoria</th>
                  <th className="px-4 py-3 text-right">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {saldo.linhas.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-6 text-center text-muted-foreground">
                      Sem itens no catálogo.
                    </td>
                  </tr>
                )}
                {saldo.linhas.map((l) => (
                  <tr key={l.item_id} className="border-b last:border-b-0 hover:bg-muted/50">
                    <td className="px-4 py-3 font-medium">{l.nome}</td>
                    <td className="px-4 py-3 font-mono text-xs">{l.sku}</td>
                    <td className="px-4 py-3 capitalize text-muted-foreground">
                      {l.categoria}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={
                          l.saldo < 0
                            ? 'font-bold text-destructive'
                            : l.saldo === 0
                              ? 'text-muted-foreground'
                              : 'font-semibold'
                        }
                      >
                        {l.saldo}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
