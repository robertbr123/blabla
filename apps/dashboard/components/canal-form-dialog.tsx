'use client'
import { useEffect, useState } from 'react'
import { X, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useCreateCanal, usePatchCanal } from '@/lib/api/queries'
import type { CanalOut, CanalProvider } from '@/lib/api/types'

interface Props {
  open: boolean
  canal: CanalOut | null
  onClose: () => void
}

interface Draft {
  slug: string
  nome: string
  provider: CanalProvider
  evolution_instance: string
  cloud_phone_id: string
  cloud_waba_id: string
  prompt_variant: string
  ativo: boolean
}

function emptyDraft(): Draft {
  return {
    slug: '',
    nome: '',
    provider: 'evolution',
    evolution_instance: '',
    cloud_phone_id: '',
    cloud_waba_id: '',
    prompt_variant: 'default',
    ativo: true,
  }
}

function fromExisting(c: CanalOut): Draft {
  return {
    slug: c.slug,
    nome: c.nome,
    provider: c.provider,
    evolution_instance: c.evolution_instance ?? '',
    cloud_phone_id: c.cloud_phone_id ?? '',
    cloud_waba_id: c.cloud_waba_id ?? '',
    prompt_variant: c.prompt_variant,
    ativo: c.ativo,
  }
}

export function CanalFormDialog({ open, canal, onClose }: Props) {
  const [draft, setDraft] = useState<Draft>(emptyDraft())
  const [error, setError] = useState<string | null>(null)
  const create = useCreateCanal()
  const patch = usePatchCanal()
  const isEditing = canal !== null

  useEffect(() => {
    if (open) {
      setDraft(canal ? fromExisting(canal) : emptyDraft())
      setError(null)
    }
  }, [open, canal])

  if (!open) return null

  function setField<K extends keyof Draft>(k: K, v: Draft[K]) {
    setDraft((d) => ({ ...d, [k]: v }))
  }

  async function handleSave() {
    setError(null)
    try {
      if (isEditing && canal) {
        await patch.mutateAsync({
          id: canal.id,
          body: {
            nome: draft.nome,
            provider: draft.provider,
            evolution_instance:
              draft.provider === 'evolution' ? draft.evolution_instance : null,
            cloud_phone_id:
              draft.provider === 'cloud' ? draft.cloud_phone_id : null,
            cloud_waba_id:
              draft.provider === 'cloud' ? draft.cloud_waba_id || null : null,
            prompt_variant: draft.prompt_variant,
            ativo: draft.ativo,
          },
        })
      } else {
        await create.mutateAsync({
          slug: draft.slug,
          nome: draft.nome,
          provider: draft.provider,
          evolution_instance:
            draft.provider === 'evolution' ? draft.evolution_instance : null,
          cloud_phone_id:
            draft.provider === 'cloud' ? draft.cloud_phone_id : null,
          cloud_waba_id:
            draft.provider === 'cloud' && draft.cloud_waba_id
              ? draft.cloud_waba_id
              : null,
          prompt_variant: draft.prompt_variant,
          ativo: draft.ativo,
        })
      }
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao salvar')
    }
  }

  const saving = create.isPending || patch.isPending

  return (
    <div className="fixed inset-0 z-50 flex">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden
      />
      <div className="relative ml-auto flex h-full w-full max-w-xl flex-col bg-background shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold">
              {isEditing ? `Editar canal — ${canal?.slug}` : 'Novo canal'}
            </h2>
            <p className="text-xs text-muted-foreground">
              {draft.provider === 'cloud'
                ? 'WhatsApp Cloud API oficial (Meta).'
                : 'Evolution API (Baileys self-hosted).'}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          {/* Provider toggle — destaque visual */}
          <div className="rounded-md border bg-muted/30 p-3">
            <Label className="mb-2 block text-xs uppercase tracking-wider text-muted-foreground">
              Provedor
            </Label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setField('provider', 'evolution')}
                disabled={isEditing}
                className={`rounded-md border px-3 py-2 text-sm transition-colors ${
                  draft.provider === 'evolution'
                    ? 'border-primary bg-primary/10 font-medium'
                    : 'border-border hover:bg-accent/40'
                } ${isEditing ? 'cursor-not-allowed opacity-60' : ''}`}
              >
                Evolution
                <span className="block text-[10px] text-muted-foreground">
                  Baileys self-hosted
                </span>
              </button>
              <button
                type="button"
                onClick={() => setField('provider', 'cloud')}
                disabled={isEditing}
                className={`rounded-md border px-3 py-2 text-sm transition-colors ${
                  draft.provider === 'cloud'
                    ? 'border-primary bg-primary/10 font-medium'
                    : 'border-border hover:bg-accent/40'
                } ${isEditing ? 'cursor-not-allowed opacity-60' : ''}`}
              >
                Cloud API
                <span className="block text-[10px] text-muted-foreground">
                  Meta oficial
                </span>
              </button>
            </div>
            {isEditing && (
              <p className="mt-2 text-[10px] text-muted-foreground">
                Provider não pode ser alterado depois de criado.
              </p>
            )}
          </div>

          {/* Comuns */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="slug">Slug *</Label>
              <Input
                id="slug"
                value={draft.slug}
                onChange={(e) => setField('slug', e.target.value)}
                disabled={isEditing}
                placeholder="cloud-suporte"
                maxLength={40}
              />
            </div>
            <div>
              <Label htmlFor="nome">Nome *</Label>
              <Input
                id="nome"
                value={draft.nome}
                onChange={(e) => setField('nome', e.target.value)}
                placeholder="Suporte (Oficial)"
                maxLength={80}
              />
            </div>
          </div>

          {/* Campos provider-específicos */}
          {draft.provider === 'evolution' ? (
            <div>
              <Label htmlFor="evolution_instance">Evolution instance *</Label>
              <Input
                id="evolution_instance"
                value={draft.evolution_instance}
                onChange={(e) => setField('evolution_instance', e.target.value)}
                placeholder="hermes-wa"
                maxLength={80}
              />
              <p className="mt-1 text-[11px] text-muted-foreground">
                Nome da instância configurada na Evolution.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <Label htmlFor="cloud_phone_id">Phone Number ID *</Label>
                <Input
                  id="cloud_phone_id"
                  value={draft.cloud_phone_id}
                  onChange={(e) => setField('cloud_phone_id', e.target.value)}
                  placeholder="123456789012345"
                  maxLength={40}
                />
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Encontre em business.facebook.com → WhatsApp Manager →
                  número.
                </p>
              </div>
              <div>
                <Label htmlFor="cloud_waba_id">WABA ID</Label>
                <Input
                  id="cloud_waba_id"
                  value={draft.cloud_waba_id}
                  onChange={(e) => setField('cloud_waba_id', e.target.value)}
                  placeholder="opcional — usado pra listar templates"
                  maxLength={40}
                />
              </div>
              <div className="rounded-md bg-amber-500/10 border border-amber-500/30 p-3 text-[11px] text-amber-700 dark:text-amber-300">
                <p className="font-semibold mb-1">Setup necessário:</p>
                <ol className="list-decimal pl-4 space-y-0.5">
                  <li>
                    Webhook URL no Meta:{' '}
                    <code className="font-mono">/webhook/whatsapp-cloud</code>
                  </li>
                  <li>
                    Subscribe to: <code className="font-mono">messages</code>
                  </li>
                  <li>
                    Env vars na VPS:{' '}
                    <code className="font-mono">WHATSAPP_CLOUD_*</code>
                  </li>
                  <li>Templates cadastrados no Meta Business</li>
                </ol>
              </div>
            </div>
          )}

          <div>
            <Label htmlFor="prompt_variant">Prompt variant</Label>
            <Input
              id="prompt_variant"
              value={draft.prompt_variant}
              onChange={(e) => setField('prompt_variant', e.target.value)}
              placeholder="default"
              maxLength={40}
            />
          </div>

          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <Label htmlFor="ativo" className="cursor-pointer">
                Canal ativo
              </Label>
              <p className="text-[11px] text-muted-foreground">
                Canais inativos não roteiam mensagens.
              </p>
            </div>
            <Switch
              id="ativo"
              checked={draft.ativo}
              onCheckedChange={(v) => setField('ativo', v)}
            />
          </div>

          {error && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t px-6 py-4">
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? 'Salvando…' : 'Salvar'}
          </Button>
        </div>
      </div>
    </div>
  )
}
