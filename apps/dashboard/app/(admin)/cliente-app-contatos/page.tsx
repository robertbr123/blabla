'use client'

import { useState } from 'react'
import {
  PhoneCall,
  Plus,
  MessageCircle,
  Phone,
  Mail,
  MapPin,
  Instagram,
  Facebook,
  Globe,
  HelpCircle,
  Trash2,
  Edit3,
  Eye,
  EyeOff,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import {
  useContatosOperadora,
  useCreateContatoOperadora,
  usePatchContatoOperadora,
  useDeleteContatoOperadora,
} from '@/lib/api/queries'
import type {
  AdminContatoOperadora,
  ContatoOperadoraIn,
  ContatoOperadoraTipo,
} from '@/lib/api/types'

const TIPO_OPCOES: { value: ContatoOperadoraTipo; label: string; icon: React.ComponentType<{ className?: string }>; hint: string }[] = [
  { value: 'whatsapp', label: 'WhatsApp', icon: MessageCircle, hint: 'só números, ex: 5592999999999' },
  { value: 'telefone', label: 'Telefone', icon: Phone, hint: 'ex: 9233330000' },
  { value: 'email', label: 'E-mail', icon: Mail, hint: 'contato@ondeline.com.br' },
  { value: 'endereco', label: 'Endereço', icon: MapPin, hint: 'Texto livre, abre Google Maps' },
  { value: 'instagram', label: 'Instagram', icon: Instagram, hint: 'instagram.com/ondeline' },
  { value: 'facebook', label: 'Facebook', icon: Facebook, hint: 'facebook.com/ondeline' },
  { value: 'site', label: 'Site', icon: Globe, hint: 'https://ondeline.com.br' },
  { value: 'outro', label: 'Outro', icon: HelpCircle, hint: 'Texto livre' },
]

function tipoMeta(t: ContatoOperadoraTipo) {
  return TIPO_OPCOES.find((o) => o.value === t) ?? TIPO_OPCOES[TIPO_OPCOES.length - 1]
}

export default function ContatosPage() {
  const { data: contatos, isLoading } = useContatosOperadora()
  const [showForm, setShowForm] = useState(false)

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-cyan-50 text-cyan-600">
            <PhoneCall className="size-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Fale conosco — App cliente</h1>
            <p className="text-sm text-muted-foreground">
              Meios de contato exibidos na tela &ldquo;Fale conosco&rdquo; do app cliente.
            </p>
          </div>
        </div>
        <Button onClick={() => setShowForm((s) => !s)} variant={showForm ? 'outline' : 'default'}>
          {showForm ? (
            'Cancelar'
          ) : (
            <>
              <Plus className="mr-1 size-4" /> Novo contato
            </>
          )}
        </Button>
      </div>

      {showForm && <NovoContatoForm onDone={() => setShowForm(false)} />}

      {isLoading && (
        <div className="text-sm text-muted-foreground">Carregando…</div>
      )}

      {!isLoading && (!contatos || contatos.length === 0) && !showForm && (
        <Card>
          <CardContent className="py-12 text-center">
            <PhoneCall className="mx-auto mb-3 size-10 text-muted-foreground" />
            <p className="font-semibold">Nenhum contato cadastrado</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Adicione WhatsApp 24h, telefone, endereço e redes sociais.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {(contatos ?? [])
          .slice()
          .sort((a, b) => a.ordem - b.ordem)
          .map((c) => (
            <ContatoRow key={c.id} contato={c} />
          ))}
      </div>
    </div>
  )
}

function NovoContatoForm({ onDone }: { onDone: () => void }) {
  const create = useCreateContatoOperadora()
  const [form, setForm] = useState<ContatoOperadoraIn>({
    tipo: 'whatsapp',
    label: 'WhatsApp 24h',
    valor: '',
    subtitle: '',
    ordem: 0,
    ativo: true,
  })
  const meta = tipoMeta(form.tipo)

  async function salvar() {
    if (!form.valor.trim()) return
    await create.mutateAsync({
      ...form,
      subtitle: form.subtitle?.trim() || null,
    })
    onDone()
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Novo contato</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <Label>Tipo</Label>
            <select
              value={form.tipo}
              onChange={(e) =>
                setForm((f) => ({ ...f, tipo: e.target.value as ContatoOperadoraTipo }))
              }
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              {TIPO_OPCOES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted-foreground">{meta.hint}</p>
          </div>
          <div>
            <Label>Label (visível pro cliente)</Label>
            <Input
              value={form.label}
              onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              placeholder="Ex: WhatsApp 24h"
            />
          </div>
        </div>
        <div>
          <Label>Valor</Label>
          <Input
            value={form.valor}
            onChange={(e) => setForm((f) => ({ ...f, valor: e.target.value }))}
            placeholder={meta.hint}
          />
        </div>
        <div>
          <Label>Subtítulo (opcional)</Label>
          <Input
            value={form.subtitle ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, subtitle: e.target.value }))}
            placeholder="Ex: Atendimento 24h, segunda a sexta"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Ordem</Label>
            <Input
              type="number"
              value={form.ordem ?? 0}
              onChange={(e) => setForm((f) => ({ ...f, ordem: Number(e.target.value) }))}
            />
          </div>
          <div className="flex items-end gap-2">
            <Switch
              checked={form.ativo ?? true}
              onCheckedChange={(checked) =>
                setForm((f) => ({ ...f, ativo: checked }))
              }
            />
            <span className="text-sm">Ativo</span>
          </div>
        </div>
        <div className="flex gap-2 pt-2">
          <Button onClick={salvar} disabled={create.isPending || !form.valor.trim()}>
            {create.isPending ? 'Salvando…' : 'Salvar'}
          </Button>
          <Button variant="outline" onClick={onDone}>
            Cancelar
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function ContatoRow({ contato }: { contato: AdminContatoOperadora }) {
  const patch = usePatchContatoOperadora(contato.id)
  const del = useDeleteContatoOperadora()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    label: contato.label,
    valor: contato.valor,
    subtitle: contato.subtitle ?? '',
    ordem: contato.ordem,
  })
  const meta = tipoMeta(contato.tipo)
  const Icon = meta.icon

  async function salvar() {
    await patch.mutateAsync({
      label: form.label,
      valor: form.valor,
      subtitle: form.subtitle.trim() || null,
      ordem: form.ordem,
    })
    setEditing(false)
  }

  async function toggleAtivo() {
    await patch.mutateAsync({ ativo: !contato.ativo })
  }

  async function excluir() {
    if (!confirm(`Excluir "${contato.label}"?`)) return
    await del.mutateAsync(contato.id)
  }

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-zinc-100 text-zinc-600">
            <Icon className="size-5" />
          </div>
          <div className="flex-1">
            {editing ? (
              <div className="space-y-2">
                <Input
                  value={form.label}
                  onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
                  placeholder="Label"
                />
                <Input
                  value={form.valor}
                  onChange={(e) => setForm((f) => ({ ...f, valor: e.target.value }))}
                  placeholder="Valor"
                />
                <Input
                  value={form.subtitle}
                  onChange={(e) => setForm((f) => ({ ...f, subtitle: e.target.value }))}
                  placeholder="Subtítulo (opcional)"
                />
                <div className="flex items-center gap-2">
                  <Label className="text-xs">Ordem</Label>
                  <Input
                    type="number"
                    value={form.ordem}
                    onChange={(e) => setForm((f) => ({ ...f, ordem: Number(e.target.value) }))}
                    className="w-20"
                  />
                </div>
              </div>
            ) : (
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold">{contato.label}</p>
                  <Badge variant="outline" className="text-xs">
                    {meta.label}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    ordem {contato.ordem}
                  </Badge>
                  {!contato.ativo && (
                    <Badge variant="outline" className="border-zinc-300 bg-zinc-100 text-xs text-zinc-600">
                      <EyeOff className="mr-1 size-3" /> inativo
                    </Badge>
                  )}
                </div>
                <p className="mt-0.5 break-all text-sm text-muted-foreground">{contato.valor}</p>
                {contato.subtitle && (
                  <p className="mt-0.5 text-xs text-muted-foreground italic">{contato.subtitle}</p>
                )}
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-1">
            {editing ? (
              <>
                <Button size="sm" onClick={salvar} disabled={patch.isPending}>
                  Salvar
                </Button>
                <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
                  Cancelar
                </Button>
              </>
            ) : (
              <>
                <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                  <Edit3 className="size-3" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={toggleAtivo}
                  disabled={patch.isPending}
                  title={contato.ativo ? 'Desativar' : 'Reativar'}
                >
                  {contato.ativo ? <EyeOff className="size-3" /> : <Eye className="size-3" />}
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
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
