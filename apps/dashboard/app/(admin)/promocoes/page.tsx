'use client'
import { useMemo, useState } from 'react'
import {
  Megaphone,
  Plus,
  ArrowUp,
  ArrowDown,
  Eye,
  MousePointerClick,
  Gift,
  Tag,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  usePromocoesAdmin,
  useReorderPromocoes,
} from '@/lib/api/queries'
import type { PromocaoAdmin } from '@/lib/api/types'
import { PromocaoFormDialog } from '@/components/promocao-form-dialog'

// Resolve base da API (servidas em /static/promocoes/...). Em prod o nginx
// faz proxy, então caminho relativo já funciona.
const API_BASE = ''

export default function PromocoesPage() {
  const { data, isLoading } = usePromocoesAdmin()
  const reorder = useReorderPromocoes()
  const [editing, setEditing] = useState<PromocaoAdmin | null>(null)
  const [creating, setCreating] = useState(false)

  const sorted = useMemo(
    () =>
      [...(data ?? [])].sort((a, b) => {
        if (a.ordem !== b.ordem) return a.ordem - b.ordem
        return a.created_at.localeCompare(b.created_at)
      }),
    [data],
  )

  const ativas = sorted.filter((p) => p.ativa).length
  const totalViews = sorted.reduce((s, p) => s + p.views, 0)
  const totalClicks = sorted.reduce((s, p) => s + p.clicks, 0)
  const ctrGlobal =
    totalViews > 0 ? Math.round((totalClicks / totalViews) * 10000) / 100 : 0

  async function moveItem(idx: number, dir: -1 | 1) {
    const next = idx + dir
    if (next < 0 || next >= sorted.length) return
    const ids = sorted.map((p) => p.id)
    ;[ids[idx], ids[next]] = [ids[next], ids[idx]]
    await reorder.mutateAsync(ids)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <Megaphone className="h-6 w-6" /> Promoções (app cliente)
          </h1>
          <p className="text-sm text-muted-foreground">
            Cards do carrossel da home do app. Refletidos em tempo real após salvar.
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="mr-1 h-4 w-4" /> Nova
        </Button>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">{sorted.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Ativas</p>
            <p className="text-2xl font-bold text-emerald-600">{ativas}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <Eye className="h-3 w-3" /> Views totais
            </p>
            <p className="text-2xl font-bold">{totalViews}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <MousePointerClick className="h-3 w-3" /> CTR global
            </p>
            <p className="text-2xl font-bold">{ctrGlobal}%</p>
          </CardContent>
        </Card>
      </div>

      {/* Lista */}
      <Card>
        <CardContent className="p-0">
          {isLoading && (
            <p className="p-6 text-sm text-muted-foreground">Carregando…</p>
          )}
          {!isLoading && sorted.length === 0 && (
            <div className="p-10 text-center">
              <Megaphone className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Nenhuma promoção cadastrada ainda.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => setCreating(true)}
              >
                Criar a primeira
              </Button>
            </div>
          )}
          {sorted.length > 0 && (
            <ul className="divide-y">
              {sorted.map((p, idx) => (
                <li
                  key={p.id}
                  className="flex items-center gap-3 p-3 hover:bg-muted/30"
                >
                  <div className="flex flex-col gap-0.5">
                    <button
                      type="button"
                      className="rounded p-1 hover:bg-accent disabled:opacity-30"
                      onClick={() => moveItem(idx, -1)}
                      disabled={idx === 0 || reorder.isPending}
                      aria-label="Mover pra cima"
                    >
                      <ArrowUp className="h-3 w-3" />
                    </button>
                    <button
                      type="button"
                      className="rounded p-1 hover:bg-accent disabled:opacity-30"
                      onClick={() => moveItem(idx, 1)}
                      disabled={idx === sorted.length - 1 || reorder.isPending}
                      aria-label="Mover pra baixo"
                    >
                      <ArrowDown className="h-3 w-3" />
                    </button>
                  </div>

                  <div
                    className="h-12 w-16 shrink-0 rounded-md"
                    style={{
                      background: `linear-gradient(135deg, ${
                        p.gradient_from || '#8B5CF6'
                      }, ${p.gradient_to || '#5B6CFF'})`,
                    }}
                  />

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-medium">{p.titulo}</p>
                      {!p.ativa && (
                        <Badge variant="outline" className="text-[10px]">
                          inativa
                        </Badge>
                      )}
                      {p.tipo === 'indicacao' && (
                        <Badge
                          variant="outline"
                          className="border-pink-200 bg-pink-50 text-pink-700 text-[10px]"
                        >
                          <Gift className="mr-0.5 h-2.5 w-2.5" /> indicação
                        </Badge>
                      )}
                      {p.segmento !== 'todos' && (
                        <Badge
                          variant="outline"
                          className="text-[10px]"
                        >
                          <Tag className="mr-0.5 h-2.5 w-2.5" /> {p.segmento}
                        </Badge>
                      )}
                    </div>
                    <p className="line-clamp-1 text-xs text-muted-foreground">
                      {p.subtitulo || '—'}
                    </p>
                  </div>

                  <div className="hidden text-right text-xs sm:block">
                    <p>
                      <span className="font-medium">{p.views}</span>{' '}
                      <span className="text-muted-foreground">views</span>
                    </p>
                    <p>
                      <span className="font-medium">{p.clicks}</span>{' '}
                      <span className="text-muted-foreground">
                        clicks · {p.ctr}% CTR
                      </span>
                    </p>
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setEditing(p)}
                  >
                    Editar
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {(creating || editing) && (
        <PromocaoFormDialog
          open={creating || !!editing}
          promocao={editing}
          apiBase={API_BASE}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
        />
      )}
    </div>
  )
}
