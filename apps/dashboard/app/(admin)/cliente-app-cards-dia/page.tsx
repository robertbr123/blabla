'use client'

import { useState } from 'react'
import {
  Sparkles,
  Plus,
  Trash2,
  Edit3,
  Eye,
  EyeOff,
  ArrowRight,
  Wifi,
  Gift,
  Star,
  CreditCard,
  Headphones,
  Zap,
  PartyPopper,
  HelpCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import {
  useCardsDia,
  useCreateCardDia,
  usePatchCardDia,
  useDeleteCardDia,
} from '@/lib/api/queries'
import type {
  AdminCardDia,
  CardDiaIn,
} from '@/lib/api/types'

// Icones suportados (precisa estar no promo_icon_map.dart do app — senao
// cliente cai no fallback 'campaign_rounded').
const ICONS: { value: string; label: string; Icon: React.ComponentType<{ className?: string }> }[] = [
  { value: 'wifi_rounded', label: 'WiFi', Icon: Wifi },
  { value: 'card_giftcard_rounded', label: 'Presente', Icon: Gift },
  { value: 'star_rounded', label: 'Estrela', Icon: Star },
  { value: 'payments_rounded', label: 'Pagamento', Icon: CreditCard },
  { value: 'support_agent_rounded', label: 'Suporte', Icon: Headphones },
  { value: 'flash_on_rounded', label: 'Raio', Icon: Zap },
  { value: 'celebration_rounded', label: 'Festa', Icon: PartyPopper },
  { value: 'campaign_rounded', label: 'Megafone', Icon: HelpCircle },
]

const GRADIENTS: { from: string; to: string; label: string }[] = [
  { from: '14B8B0', to: '0F8F89', label: 'Ciano Ondeline' },
  { from: 'E8A33D', to: 'FF8E53', label: 'Laranja' },
  { from: '8B5CF6', to: '6D28D9', label: 'Roxo' },
  { from: '3B82F6', to: '1D4ED8', label: 'Azul' },
  { from: 'E0455A', to: 'B91C1C', label: 'Vermelho' },
  { from: '14B8B0', to: '0B1F3A', label: 'Ciano → Navy' },
  { from: 'F472B6', to: 'BE185D', label: 'Rosa' },
  { from: '10B981', to: '047857', label: 'Verde' },
]

const ACTIONS: { value: string; label: string }[] = [
  { value: 'info', label: 'Só informativo (sem clique)' },
  { value: 'tela:/home', label: 'Tab Início' },
  { value: 'tela:/faturas', label: 'Tab Faturas' },
  { value: 'tela:/suporte', label: 'Tab Suporte' },
  { value: 'tela:/perfil', label: 'Tab Perfil' },
  { value: 'tela:/fidelidade', label: 'Fidelidade' },
  { value: 'tela:/indicacao', label: 'Indique e ganhe' },
  { value: 'tela:/contatos', label: 'Fale conosco' },
  { value: 'tela:/faq', label: 'Ajuda (FAQ)' },
  { value: 'tela:/notificacoes', label: 'Notificações' },
  { value: 'url:CUSTOM', label: 'URL externa (custom)' },
]

function iconMeta(name: string | null | undefined) {
  return ICONS.find((i) => i.value === name) ?? ICONS[ICONS.length - 1]
}

const EMPTY_FORM: CardDiaIn = {
  slug: '',
  titulo: '',
  corpo: '',
  cta_label: 'Saiba mais',
  cta_action: 'info',
  icon: 'star_rounded',
  gradient_from: '14B8B0',
  gradient_to: '0F8F89',
  ativo: true,
}

export default function CardsDiaPage() {
  const { data: cards, isLoading } = useCardsDia()
  const [showForm, setShowForm] = useState(false)

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-amber-50 text-amber-600">
            <Sparkles className="size-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Card do dia — App cliente</h1>
            <p className="text-sm text-muted-foreground">
              Cards rotativos exibidos na Home. Cliente vê 1 ativo por dia
              (escolhido por hash determinístico — o mesmo card por 24h).
            </p>
          </div>
        </div>
        <Button onClick={() => setShowForm((s) => !s)} variant={showForm ? 'outline' : 'default'}>
          {showForm ? (
            'Cancelar'
          ) : (
            <>
              <Plus className="mr-1 size-4" /> Novo card
            </>
          )}
        </Button>
      </div>

      {showForm && (
        <CardForm
          mode="create"
          initial={EMPTY_FORM}
          onDone={() => setShowForm(false)}
        />
      )}

      {isLoading && <div className="text-sm text-muted-foreground">Carregando…</div>}

      {!isLoading && (!cards || cards.length === 0) && !showForm && (
        <Card>
          <CardContent className="py-12 text-center">
            <Sparkles className="mx-auto mb-3 size-10 text-muted-foreground" />
            <p className="font-semibold">Nenhum card cadastrado</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Crie dicas, promoções ou avisos que rotacionam na Home do app.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {(cards ?? []).map((c) => <CardRow key={c.id} card={c} />)}
      </div>
    </div>
  )
}

function CardForm({
  mode,
  initial,
  cardId,
  onDone,
}: {
  mode: 'create' | 'edit'
  initial: CardDiaIn
  cardId?: string
  onDone: () => void
}) {
  const create = useCreateCardDia()
  const patch = usePatchCardDia(cardId ?? '')
  const [form, setForm] = useState<CardDiaIn>(initial)
  const [customUrl, setCustomUrl] = useState(
    initial.cta_action?.startsWith('url:') ? initial.cta_action.slice(4) : '',
  )

  const isUrlMode = form.cta_action === 'url:CUSTOM' || form.cta_action?.startsWith('url:')

  async function salvar() {
    if (!form.slug.trim() || !form.titulo.trim() || !form.corpo.trim()) return
    let finalAction = form.cta_action ?? 'info'
    if (isUrlMode) {
      finalAction = `url:${customUrl.trim()}`
      if (!customUrl.trim()) return
    }
    const payload = { ...form, cta_action: finalAction }
    if (mode === 'create') {
      await create.mutateAsync(payload)
    } else {
      await patch.mutateAsync(payload)
    }
    onDone()
  }

  const isPending = create.isPending || patch.isPending
  const isClickable = form.cta_action !== 'info'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {mode === 'create' ? 'Novo card' : 'Editar card'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Form */}
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Slug (único)</Label>
                <Input
                  value={form.slug}
                  onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
                  placeholder="ex: promo_natal_2026"
                  disabled={mode === 'edit'}
                />
              </div>
              <div className="flex items-end gap-2">
                <Switch
                  checked={form.ativo ?? true}
                  onCheckedChange={(checked) => setForm((f) => ({ ...f, ativo: checked }))}
                />
                <span className="text-sm">{form.ativo ? 'Ativo' : 'Inativo'}</span>
              </div>
            </div>
            <div>
              <Label>Título</Label>
              <Input
                value={form.titulo}
                onChange={(e) => setForm((f) => ({ ...f, titulo: e.target.value }))}
                placeholder="Ex: Indique amigos e ganhe"
                maxLength={120}
              />
            </div>
            <div>
              <Label>Corpo</Label>
              <Textarea
                value={form.corpo}
                onChange={(e) => setForm((f) => ({ ...f, corpo: e.target.value }))}
                placeholder="Mensagem que aparece embaixo do título."
                rows={3}
                maxLength={2000}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Texto do botão</Label>
                <Input
                  value={form.cta_label ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, cta_label: e.target.value }))}
                  placeholder="Saiba mais"
                  maxLength={48}
                />
              </div>
              <div>
                <Label>Ao tocar</Label>
                <select
                  value={
                    form.cta_action?.startsWith('url:') ? 'url:CUSTOM' : form.cta_action ?? 'info'
                  }
                  onChange={(e) => setForm((f) => ({ ...f, cta_action: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {ACTIONS.map((a) => (
                    <option key={a.value} value={a.value}>
                      {a.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {isUrlMode && (
              <div>
                <Label>URL externa</Label>
                <Input
                  value={customUrl}
                  onChange={(e) => setCustomUrl(e.target.value)}
                  placeholder="https://ondeline.com.br/promo"
                />
              </div>
            )}
            <div>
              <Label>Ícone</Label>
              <div className="mt-2 flex flex-wrap gap-2">
                {ICONS.map(({ value, label, Icon }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, icon: value }))}
                    title={label}
                    className={`flex h-10 w-10 items-center justify-center rounded-md border-2 transition ${
                      form.icon === value
                        ? 'border-cyan-500 bg-cyan-50 text-cyan-700'
                        : 'border-zinc-200 text-zinc-600 hover:border-zinc-400'
                    }`}
                  >
                    <Icon className="size-5" />
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label>Cor (gradient)</Label>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {GRADIENTS.map((g) => {
                  const selected =
                    form.gradient_from === g.from && form.gradient_to === g.to
                  return (
                    <button
                      key={`${g.from}-${g.to}`}
                      type="button"
                      onClick={() =>
                        setForm((f) => ({ ...f, gradient_from: g.from, gradient_to: g.to }))
                      }
                      className={`flex h-14 items-center justify-center rounded-md border-2 text-xs font-bold text-white transition ${
                        selected ? 'border-zinc-900 scale-105' : 'border-transparent'
                      }`}
                      style={{
                        background: `linear-gradient(135deg, #${g.from}, #${g.to})`,
                      }}
                    >
                      {selected && '✓ '}{g.label}
                    </button>
                  )
                })}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Custom: use os campos abaixo (hex sem #).
              </p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <Input
                  value={form.gradient_from ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, gradient_from: e.target.value }))}
                  placeholder="Hex from (ex: 14B8B0)"
                  maxLength={8}
                />
                <Input
                  value={form.gradient_to ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, gradient_to: e.target.value }))}
                  placeholder="Hex to (ex: 0F8F89)"
                  maxLength={8}
                />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <Button
                onClick={salvar}
                disabled={
                  isPending ||
                  !form.slug.trim() ||
                  !form.titulo.trim() ||
                  !form.corpo.trim()
                }
              >
                {isPending ? 'Salvando…' : 'Salvar'}
              </Button>
              <Button variant="outline" onClick={onDone}>
                Cancelar
              </Button>
            </div>
          </div>

          {/* Preview */}
          <div>
            <Label className="mb-2 block">Preview (como aparece no app)</Label>
            <div className="rounded-lg border bg-zinc-50 p-4">
              <CardPreview card={form} clickable={isClickable} />
              <p className="mt-3 text-center text-xs text-muted-foreground">
                Posição: Home, abaixo do card &ldquo;Fidelidade / Fale conosco&rdquo;.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function CardPreview({
  card,
  clickable,
}: {
  card: Partial<AdminCardDia> | CardDiaIn
  clickable: boolean
}) {
  const from = card.gradient_from || '14B8B0'
  const to = card.gradient_to || '0F8F89'
  const meta = iconMeta(card.icon)
  const Icon = meta.Icon

  return (
    <div
      className="rounded-2xl p-5 shadow-lg"
      style={{
        background: `linear-gradient(135deg, #${from}, #${to})`,
        boxShadow: `0 6px 16px #${from}40`,
      }}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/20">
          <Icon className="size-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-base font-extrabold leading-tight text-white">
            {card.titulo || 'Título do card'}
          </p>
          <p className="mt-1 text-[13px] leading-snug text-white/90">
            {card.corpo || 'Corpo do card vai aqui. Texto curto explicando a dica ou promoção.'}
          </p>
          {clickable && (
            <div className="mt-2 flex items-center gap-1 text-[13px] font-extrabold text-white">
              {card.cta_label || 'Saiba mais'}
              <ArrowRight className="size-4" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function CardRow({ card }: { card: AdminCardDia }) {
  const patch = usePatchCardDia(card.id)
  const del = useDeleteCardDia()
  const [editing, setEditing] = useState(false)
  const meta = iconMeta(card.icon)
  const Icon = meta.Icon

  async function toggleAtivo() {
    await patch.mutateAsync({ ativo: !card.ativo })
  }

  async function excluir() {
    if (!confirm(`Excluir "${card.titulo}"?`)) return
    await del.mutateAsync(card.id)
  }

  if (editing) {
    const initial: CardDiaIn = {
      slug: card.slug,
      titulo: card.titulo,
      corpo: card.corpo,
      cta_label: card.cta_label,
      cta_action: card.cta_action,
      icon: card.icon,
      gradient_from: card.gradient_from,
      gradient_to: card.gradient_to,
      ativo: card.ativo,
    }
    return (
      <CardForm
        mode="edit"
        cardId={card.id}
        initial={initial}
        onDone={() => setEditing(false)}
      />
    )
  }

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start gap-3">
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-white"
            style={{
              background: `linear-gradient(135deg, #${card.gradient_from ?? '14B8B0'}, #${card.gradient_to ?? '0F8F89'})`,
            }}
          >
            <Icon className="size-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold">{card.titulo}</p>
              <Badge variant="outline" className="text-xs">{card.slug}</Badge>
              {!card.ativo && (
                <Badge variant="outline" className="border-zinc-300 bg-zinc-100 text-xs text-zinc-600">
                  <EyeOff className="mr-1 size-3" /> inativo
                </Badge>
              )}
            </div>
            <p className="mt-0.5 text-sm text-muted-foreground line-clamp-2">{card.corpo}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              CTA: <span className="font-mono">{card.cta_label}</span> →{' '}
              <span className="font-mono">{card.cta_action}</span>
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
              <Edit3 className="size-3" />
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={toggleAtivo}
              disabled={patch.isPending}
              title={card.ativo ? 'Desativar' : 'Ativar'}
            >
              {card.ativo ? <EyeOff className="size-3" /> : <Eye className="size-3" />}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={excluir}
              disabled={del.isPending}
              className="text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="size-3" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
