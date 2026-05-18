'use client'
import { useState } from 'react'
import { Plus, ArrowDownUp } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { DialogNovoItemEstoque } from '@/components/dialog-novo-item-estoque'
import { DialogNovoMovimentoEstoque } from '@/components/dialog-novo-movimento-estoque'
import {
  useEstoqueItens,
  useEstoqueMovimentos,
  useEstoqueSaldo,
  useTecnicos,
} from '@/lib/api/queries'

const TIPO_LABEL: Record<string, { texto: string; cor: string }> = {
  entrada: { texto: 'Entrada', cor: 'text-green-700' },
  saida: { texto: 'Saída', cor: 'text-red-700' },
  devolucao: { texto: 'Devolução', cor: 'text-orange-700' },
  perda: { texto: 'Perda', cor: 'text-red-900' },
  ajuste_positivo: { texto: 'Ajuste +', cor: 'text-green-700' },
  ajuste_negativo: { texto: 'Ajuste -', cor: 'text-red-700' },
}

export default function EstoquePage() {
  const [tecnicoId, setTecnicoId] = useState<string>('')
  const [showNovoItem, setShowNovoItem] = useState(false)
  const [showNovoMov, setShowNovoMov] = useState(false)

  const { data: itens, isLoading: loadingItens } = useEstoqueItens(false)
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const { data: saldo, isLoading: loadingSaldo } = useEstoqueSaldo(tecnicoId || null)
  const { data: movimentos } = useEstoqueMovimentos({
    tecnico_id: tecnicoId || undefined,
    limit: 20,
  })

  const itemById = new Map((itens ?? []).map((i) => [i.id, i]))
  const tecById = new Map((tecnicos?.items ?? []).map((t) => [t.id, t]))

  return (
    <div className="space-y-8">
      {showNovoItem && (
        <DialogNovoItemEstoque onClose={() => setShowNovoItem(false)} />
      )}
      {showNovoMov && (
        <DialogNovoMovimentoEstoque
          defaultTecnicoId={tecnicoId || undefined}
          onClose={() => setShowNovoMov(false)}
        />
      )}

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Estoque</h1>
          <p className="text-sm text-muted-foreground">
            Catálogo de itens, saldo por técnico e movimentações.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowNovoMov(true)}
            className="gap-2"
          >
            <ArrowDownUp className="h-4 w-4" />
            Novo movimento
          </Button>
          <Button onClick={() => setShowNovoItem(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Novo item
          </Button>
        </div>
      </div>

      {/* Catálogo */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Catálogo</h2>
        {loadingItens && <p className="text-sm text-muted-foreground">Carregando…</p>}
        {itens && (
          <div className="overflow-x-auto rounded-md border bg-card">
            <table className="w-full text-sm">
              <thead className="border-b text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">Categoria</th>
                  <th className="px-4 py-3">Serial?</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {itens.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-6 text-center text-muted-foreground">
                      Nenhum item cadastrado. Clique em <strong>Novo item</strong>.
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
        <h2 className="mb-3 text-lg font-semibold">Saldo por técnico</h2>
        <div className="mb-3 max-w-md">
          <Select value={tecnicoId} onChange={(e) => setTecnicoId(e.target.value)}>
            <option value="">Selecione um técnico…</option>
            {(tecnicos?.items ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </Select>
        </div>
        {tecnicoId && loadingSaldo && (
          <p className="text-sm text-muted-foreground">Carregando saldo…</p>
        )}
        {tecnicoId && saldo && (
          <div className="overflow-x-auto rounded-md border bg-card">
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

      {/* Movimentos recentes */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">
          Movimentos recentes{tecnicoId ? ' (do técnico selecionado)' : ''}
        </h2>
        {movimentos && (
          <div className="overflow-x-auto rounded-md border bg-card">
            <table className="w-full text-sm">
              <thead className="border-b text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3">Tipo</th>
                  <th className="px-4 py-3">Item</th>
                  <th className="px-4 py-3">Técnico</th>
                  <th className="px-4 py-3 text-right">Qtd.</th>
                  <th className="px-4 py-3">Serial</th>
                </tr>
              </thead>
              <tbody>
                {movimentos.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-muted-foreground">
                      Sem movimentos. Clique em <strong>Novo movimento</strong>.
                    </td>
                  </tr>
                )}
                {movimentos.map((m) => {
                  const it = itemById.get(m.item_id)
                  const tec = m.tecnico_id ? tecById.get(m.tecnico_id) : null
                  const conf = TIPO_LABEL[m.tipo] ?? { texto: m.tipo, cor: '' }
                  return (
                    <tr key={m.id} className="border-b last:border-b-0 hover:bg-muted/50">
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {new Date(m.criado_em).toLocaleString('pt-BR')}
                      </td>
                      <td className={`px-4 py-3 text-xs font-medium ${conf.cor}`}>
                        {conf.texto}
                      </td>
                      <td className="px-4 py-3">{it ? it.nome : '—'}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {tec ? tec.nome : '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-medium">{m.quantidade}</td>
                      <td className="px-4 py-3 font-mono text-xs">{m.serial ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
