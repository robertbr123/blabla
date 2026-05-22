'use client'
import { Fragment, useMemo, useState } from 'react'
import {
  ArrowRightLeft,
  Boxes,
  Minus,
  Package,
  Pencil,
  Plus,
  Tags,
  Trash2,
  Undo2,
  Users,
  Warehouse,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { DialogNovoItemEstoque } from '@/components/dialog-novo-item-estoque'
import { DialogEditarItemEstoque } from '@/components/dialog-editar-item-estoque'
import { DialogEntradaDeposito } from '@/components/dialog-entrada-deposito'
import { DialogBaixaDeposito } from '@/components/dialog-baixa-deposito'
import { DialogTransferir } from '@/components/dialog-transferir'
import { DialogDevolver } from '@/components/dialog-devolver'
import { DialogGerenciarCategorias } from '@/components/dialog-gerenciar-categorias'
import {
  useDeleteEstoqueItem,
  useDepositoSaldo,
  useEstoqueItens,
  useEstoqueMovimentos,
  useSeriaisAtivos,
  useTecnicos,
  useTecnicosSaldos,
  useUpdateEstoqueItem,
} from '@/lib/api/queries'
import type { EstoqueItem } from '@/lib/api/types'
import { cn } from '@/lib/utils'

type Aba = 'deposito' | 'tecnicos' | 'itens'

const TIPO_LABEL: Record<string, { texto: string; cor: string }> = {
  entrada: { texto: 'Entrada', cor: 'text-success' },
  saida: { texto: 'Saída', cor: 'text-destructive' },
  devolucao: { texto: 'Devolução', cor: 'text-warning' },
  recolhido: { texto: 'Recolhido', cor: 'text-info' },
  perda: { texto: 'Perda', cor: 'text-destructive font-semibold' },
  ajuste_positivo: { texto: 'Ajuste +', cor: 'text-success' },
  ajuste_negativo: { texto: 'Ajuste -', cor: 'text-destructive' },
}

export default function EstoquePage() {
  const [aba, setAba] = useState<Aba>('deposito')
  const [showNovoItem, setShowNovoItem] = useState(false)
  const [showEntrada, setShowEntrada] = useState(false)
  const [showBaixa, setShowBaixa] = useState(false)
  const [showTransfer, setShowTransfer] = useState(false)
  const [showDevolver, setShowDevolver] = useState<
    | true
    | { tecnicoId?: string; itemId?: string; serial?: string }
    | false
  >(false)
  const [showCategorias, setShowCategorias] = useState(false)
  const [itemEditando, setItemEditando] = useState<EstoqueItem | null>(null)
  const [busca, setBusca] = useState('')
  const updateItem = useUpdateEstoqueItem()
  const deleteItem = useDeleteEstoqueItem()

  const { data: deposito } = useDepositoSaldo()
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const { data: tecSaldos } = useTecnicosSaldos()
  const { data: itens } = useEstoqueItens(false)
  const { data: movimentos } = useEstoqueMovimentos({ limit: 30 })
  const { data: seriais } = useSeriaisAtivos()

  // Indexa seriais ativos por (locKey, item_id) — locKey: 'deposito' | tecnicoId
  const seriaisPorLocItem = useMemo(() => {
    const map = new Map<string, Map<string, string[]>>()
    for (const s of seriais?.linhas ?? []) {
      const locKey = s.tecnico_id ?? 'deposito'
      let perLoc = map.get(locKey)
      if (!perLoc) {
        perLoc = new Map<string, string[]>()
        map.set(locKey, perLoc)
      }
      const arr = perLoc.get(s.item_id) ?? []
      arr.push(s.serial)
      perLoc.set(s.item_id, arr)
    }
    return map
  }, [seriais])

  async function handleExcluir(item: EstoqueItem) {
    const ok = confirm(
      `Excluir o item "${item.nome}" (${item.sku})?\n\n` +
        'Se já tem movimentos, vou sugerir desativar (preserva histórico).',
    )
    if (!ok) return
    try {
      await deleteItem.mutateAsync(item.id)
    } catch (e) {
      const msg = e instanceof Error ? e.message : ''
      if (/movimento|409/i.test(msg)) {
        const desativar = confirm(
          'Não dá pra apagar — esse item tem movimentos registrados.\n\n' +
            'Quer desativar? Ele some dos selects novos mas o histórico fica.',
        )
        if (desativar) {
          try {
            await updateItem.mutateAsync({
              id: item.id,
              body: { ativo: false },
            })
          } catch (e2) {
            alert(e2 instanceof Error ? e2.message : 'Erro ao desativar')
          }
        }
      } else {
        alert(msg || 'Erro ao excluir')
      }
    }
  }

  const itemById = useMemo(
    () => new Map((itens ?? []).map((i) => [i.id, i])),
    [itens],
  )
  const tecById = useMemo(
    () => new Map((tecnicos?.items ?? []).map((t) => [t.id, t])),
    [tecnicos],
  )

  // KPIs do header
  const totalDeposito = (deposito?.linhas ?? []).reduce(
    (a, l) => a + (l.saldo > 0 ? l.saldo : 0),
    0,
  )
  const totalEmCampo = (tecSaldos?.linhas ?? []).reduce(
    (a, l) => a + l.saldo,
    0,
  )
  const tecnicosComEstoque = new Set(
    (tecSaldos?.linhas ?? []).map((l) => l.tecnico_id),
  ).size

  return (
    <div className="space-y-6">
      {showNovoItem && (
        <DialogNovoItemEstoque onClose={() => setShowNovoItem(false)} />
      )}
      {showEntrada && (
        <DialogEntradaDeposito onClose={() => setShowEntrada(false)} />
      )}
      {showBaixa && (
        <DialogBaixaDeposito onClose={() => setShowBaixa(false)} />
      )}
      {showTransfer && (
        <DialogTransferir onClose={() => setShowTransfer(false)} />
      )}
      {showDevolver && (
        <DialogDevolver
          onClose={() => setShowDevolver(false)}
          tecnicoIdInicial={
            typeof showDevolver === 'object' ? showDevolver.tecnicoId : undefined
          }
          itemIdInicial={
            typeof showDevolver === 'object' ? showDevolver.itemId : undefined
          }
          serialInicial={
            typeof showDevolver === 'object' ? showDevolver.serial : undefined
          }
        />
      )}
      {showCategorias && (
        <DialogGerenciarCategorias onClose={() => setShowCategorias(false)} />
      )}
      {itemEditando && (
        <DialogEditarItemEstoque
          item={itemEditando}
          onClose={() => setItemEditando(null)}
        />
      )}

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Estoque</h1>
          <p className="text-sm text-muted-foreground">
            Depósito central + estoque em mãos com os técnicos.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setShowEntrada(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Entrada no depósito
          </Button>
          <Button
            variant="default"
            onClick={() => setShowTransfer(true)}
            className="gap-2"
          >
            <ArrowRightLeft className="h-4 w-4" />
            Transferir → técnico
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowNovoItem(true)}
            className="gap-2"
          >
            <Package className="h-4 w-4" />
            Novo item
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowCategorias(true)}
            className="gap-2"
          >
            <Tags className="h-4 w-4" />
            Categorias
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Kpi label="No depósito" value={totalDeposito} icon={Warehouse} tone="info" />
        <Kpi label="Em campo (técnicos)" value={totalEmCampo} icon={Users} tone="success" />
        <Kpi label="Técnicos com estoque" value={tecnicosComEstoque} icon={Boxes} tone="primary" />
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        <TabButton ativo={aba === 'deposito'} onClick={() => setAba('deposito')}>
          <Warehouse className="h-4 w-4" /> Depósito
        </TabButton>
        <TabButton ativo={aba === 'tecnicos'} onClick={() => setAba('tecnicos')}>
          <Users className="h-4 w-4" /> Técnicos
        </TabButton>
        <TabButton ativo={aba === 'itens'} onClick={() => setAba('itens')}>
          <Package className="h-4 w-4" /> Itens
        </TabButton>
      </div>

      {aba === 'deposito' && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Input
              placeholder="Buscar por nome, SKU ou categoria…"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="max-w-sm"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowBaixa(true)}
              className="gap-2"
            >
              <Minus className="h-4 w-4" />
              Registrar perda / ajuste
            </Button>
          </div>
          <TabelaSaldo
            linhas={(deposito?.linhas ?? []).filter((l) =>
              filtrar(l, busca),
            )}
            mostrarTipoQuando="saldo"
            seriaisPorItem={seriaisPorLocItem.get('deposito')}
          />

          {/* Movimentos recentes do depósito */}
          <h3 className="mt-6 text-base font-semibold">Movimentos recentes</h3>
          <TabelaMovimentos
            movimentos={(movimentos ?? []).filter(
              (m) => m.tecnico_id === null || m.tecnico_id === undefined,
            )}
            itemById={itemById}
            tecById={tecById}
          />
        </section>
      )}

      {aba === 'tecnicos' && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Input
              placeholder="Buscar por técnico, item ou SKU…"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="max-w-sm"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDevolver(true)}
              className="gap-2"
            >
              <Undo2 className="h-4 w-4" />
              Devolver → depósito
            </Button>
          </div>
          <TabelaTecnicosSaldos
            linhas={(tecSaldos?.linhas ?? []).filter((l) =>
              [l.tecnico_nome, l.nome, l.sku, l.categoria]
                .join(' ')
                .toLowerCase()
                .includes(busca.toLowerCase()),
            )}
            seriaisPorLocItem={seriaisPorLocItem}
          />

          <h3 className="mt-6 text-base font-semibold">
            Movimentos recentes (técnicos)
          </h3>
          <TabelaMovimentos
            movimentos={(movimentos ?? []).filter(
              (m) => m.tecnico_id !== null && m.tecnico_id !== undefined,
            )}
            itemById={itemById}
            tecById={tecById}
          />
        </section>
      )}

      {aba === 'itens' && (
        <section className="space-y-4">
          <Input
            placeholder="Buscar item…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="max-w-sm"
          />
          <div className="overflow-x-auto rounded-md border bg-card">
            <table className="w-full text-sm">
              <thead className="border-b text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">Categoria</th>
                  <th className="px-4 py-3">Serial?</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {(itens ?? [])
                  .filter((i) =>
                    [i.sku, i.nome, i.categoria]
                      .join(' ')
                      .toLowerCase()
                      .includes(busca.toLowerCase()),
                  )
                  .map((it) => (
                    <tr
                      key={it.id}
                      className="border-b last:border-b-0 hover:bg-muted/50"
                    >
                      <td className="px-4 py-3 font-mono text-xs">{it.sku}</td>
                      <td className="px-4 py-3 font-medium">{it.nome}</td>
                      <td className="px-4 py-3 capitalize text-muted-foreground">
                        {it.categoria}
                      </td>
                      <td className="px-4 py-3">
                        {it.serializado ? 'Sim' : 'Não'}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={it.ativo ? 'default' : 'outline'}>
                          {it.ativo ? 'Ativo' : 'Inativo'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setItemEditando(it)}
                            title="Editar"
                            aria-label={`Editar item ${it.nome}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive"
                            onClick={() => void handleExcluir(it)}
                            title="Excluir"
                            disabled={deleteItem.isPending}
                            aria-label={`Excluir item ${it.nome}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                {!itens?.length && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-muted-foreground">
                      Nenhum item. Clique em <strong>Novo item</strong>.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

function filtrar(
  l: { nome: string; sku: string; categoria: string },
  q: string,
): boolean {
  if (!q) return true
  return [l.nome, l.sku, l.categoria]
    .join(' ')
    .toLowerCase()
    .includes(q.toLowerCase())
}

const ESTOQUE_KPI_TONE: Record<'primary' | 'info' | 'success' | 'warning' | 'muted', string> = {
  primary: 'bg-primary/[0.10] text-primary',
  info: 'bg-info/[0.12] text-info',
  success: 'bg-success/[0.12] text-success',
  warning: 'bg-warning/[0.15] text-warning',
  muted: 'bg-muted text-muted-foreground',
}

function Kpi({
  label,
  value,
  icon: Icon,
  tone = 'muted',
}: {
  label: string
  value: number
  icon: React.ComponentType<{ className?: string }>
  tone?: keyof typeof ESTOQUE_KPI_TONE
}) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </div>
          <div
            className="mt-2 text-3xl font-semibold leading-none"
            style={{ fontVariantNumeric: 'tabular-nums' }}
          >
            {value}
          </div>
        </div>
        <div className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-md', ESTOQUE_KPI_TONE[tone])}>
          <Icon className="h-4 w-4" />
        </div>
      </CardContent>
    </Card>
  )
}

function TabButton({
  ativo,
  onClick,
  children,
}: {
  ativo: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium -mb-px transition-colors',
        ativo
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground',
      )}
    >
      {children}
    </button>
  )
}

function TabelaSaldo({
  linhas,
  mostrarTipoQuando: _ignored,
  seriaisPorItem,
}: {
  linhas: Array<{
    item_id: string
    sku: string
    nome: string
    categoria: string
    serializado: boolean
    saldo: number
  }>
  mostrarTipoQuando: 'saldo'
  seriaisPorItem?: Map<string, string[]>
}) {
  return (
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
          {linhas.length === 0 && (
            <tr>
              <td colSpan={4} className="p-6 text-center text-muted-foreground">
                Sem itens.
              </td>
            </tr>
          )}
          {linhas.map((l) => {
            const seriais = l.serializado
              ? seriaisPorItem?.get(l.item_id) ?? []
              : []
            return (
              <Fragment key={l.item_id}>
                <tr className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3 font-medium">
                    {l.nome}
                    {l.serializado && (
                      <span className="ml-2 inline-flex items-center rounded bg-info/[0.12] px-1.5 py-0.5 text-[10px] font-semibold text-info ring-1 ring-inset ring-info/30">
                        serial
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{l.sku}</td>
                  <td className="px-4 py-3 capitalize text-muted-foreground">
                    {l.categoria}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span
                      className={cn(
                        'rounded-md px-2 py-1 font-semibold',
                        l.saldo > 0
                          ? 'bg-success/[0.12] text-success ring-1 ring-inset ring-success/30'
                          : l.saldo === 0
                            ? 'text-muted-foreground'
                            : 'bg-destructive/[0.12] text-destructive ring-1 ring-inset ring-destructive/30',
                      )}
                      style={{ fontVariantNumeric: 'tabular-nums' }}
                    >
                      {l.saldo}
                    </span>
                  </td>
                </tr>
                {seriais.length > 0 && (
                  <tr className="border-b last:border-b-0 bg-muted/20">
                    <td colSpan={4} className="px-4 py-2">
                      <div className="flex flex-wrap gap-1.5">
                        {seriais.map((s) => (
                          <code
                            key={s}
                            className="rounded bg-background px-1.5 py-0.5 text-[11px] ring-1 ring-inset ring-border"
                          >
                            {s}
                          </code>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function TabelaTecnicosSaldos({
  linhas,
  seriaisPorLocItem,
}: {
  linhas: Array<{
    tecnico_id: string
    tecnico_nome: string
    item_id: string
    sku: string
    nome: string
    categoria: string
    saldo: number
  }>
  seriaisPorLocItem?: Map<string, Map<string, string[]>>
}) {
  // Agrupa por técnico
  const porTec = new Map<string, { nome: string; itens: typeof linhas }>()
  for (const l of linhas) {
    const slot = porTec.get(l.tecnico_id) ?? { nome: l.tecnico_nome, itens: [] }
    slot.itens.push(l)
    porTec.set(l.tecnico_id, slot)
  }

  if (porTec.size === 0) {
    return (
      <div className="rounded-md border bg-card p-6 text-center text-sm text-muted-foreground">
        Nenhum técnico com estoque no momento.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {Array.from(porTec.entries()).map(([tecId, { nome, itens }]) => (
        <div key={tecId} className="overflow-x-auto rounded-md border bg-card">
          <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-2">
            <div className="font-semibold">{nome}</div>
            <div className="text-xs text-muted-foreground">
              {itens.reduce((a, i) => a + i.saldo, 0)} itens ·{' '}
              {itens.length} {itens.length === 1 ? 'tipo' : 'tipos'}
            </div>
          </div>
          <table className="w-full text-sm">
            <tbody>
              {itens.map((it) => {
                const seriais =
                  seriaisPorLocItem?.get(tecId)?.get(it.item_id) ?? []
                return (
                  <Fragment key={it.item_id}>
                    <tr className="border-b last:border-b-0">
                      <td className="px-4 py-2 font-medium">{it.nome}</td>
                      <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                        {it.sku}
                      </td>
                      <td className="px-4 py-2 text-xs capitalize text-muted-foreground">
                        {it.categoria}
                      </td>
                      <td className="px-4 py-2 text-right font-semibold">
                        {it.saldo}
                      </td>
                    </tr>
                    {seriais.length > 0 && (
                      <tr className="border-b last:border-b-0 bg-muted/20">
                        <td colSpan={4} className="px-4 py-2">
                          <div className="flex flex-wrap gap-1.5">
                            {seriais.map((s) => (
                              <code
                                key={s}
                                className="rounded bg-background px-1.5 py-0.5 text-[11px] ring-1 ring-inset ring-border"
                              >
                                {s}
                              </code>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

function TabelaMovimentos({
  movimentos,
  itemById,
  tecById,
}: {
  movimentos: import('@/lib/api/types').EstoqueMovimento[]
  itemById: Map<string, import('@/lib/api/types').EstoqueItem>
  tecById: Map<string, { id: string; nome: string }>
}) {
  return (
    <div className="overflow-x-auto rounded-md border bg-card">
      <table className="w-full text-sm">
        <thead className="border-b text-left text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-4 py-3">Data</th>
            <th className="px-4 py-3">Tipo</th>
            <th className="px-4 py-3">Item</th>
            <th className="px-4 py-3">Origem/destino</th>
            <th className="px-4 py-3 text-right">Qtd.</th>
            <th className="px-4 py-3">Observação</th>
          </tr>
        </thead>
        <tbody>
          {movimentos.length === 0 && (
            <tr>
              <td colSpan={6} className="p-6 text-center text-muted-foreground">
                Sem movimentos.
              </td>
            </tr>
          )}
          {movimentos.map((m) => {
            const it = itemById.get(m.item_id)
            const tec = m.tecnico_id ? tecById.get(m.tecnico_id) : null
            const conf = TIPO_LABEL[m.tipo] ?? { texto: m.tipo, cor: '' }
            return (
              <tr
                key={m.id}
                className="border-b last:border-b-0 hover:bg-muted/50"
              >
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  {new Date(m.criado_em).toLocaleString('pt-BR')}
                </td>
                <td className={`px-4 py-3 text-xs font-medium ${conf.cor}`}>
                  {conf.texto}
                </td>
                <td className="px-4 py-3">{it ? it.nome : '—'}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {tec ? tec.nome : 'Depósito'}
                </td>
                <td className="px-4 py-3 text-right font-medium">
                  {m.quantidade}
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  {m.observacao ?? '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
