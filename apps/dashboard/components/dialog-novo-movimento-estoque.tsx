'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  useCreateEstoqueMovimento,
  useEstoqueItens,
  useTecnicos,
} from '@/lib/api/queries'

const TIPOS: { value: string; label: string; sinal: string }[] = [
  { value: 'entrada', label: 'Entrada (almoxarifado → técnico)', sinal: '+' },
  { value: 'saida', label: 'Saída (entrega ao cliente / consumo)', sinal: '-' },
  { value: 'devolucao', label: 'Devolução (técnico → almoxarifado)', sinal: '-' },
  { value: 'perda', label: 'Perda (extravio / dano)', sinal: '-' },
  { value: 'ajuste_positivo', label: 'Ajuste positivo (correção +)', sinal: '+' },
  { value: 'ajuste_negativo', label: 'Ajuste negativo (correção -)', sinal: '-' },
]

const schema = z
  .object({
    item_id: z.string().uuid('Selecione o item'),
    tipo: z.enum([
      'entrada',
      'saida',
      'devolucao',
      'perda',
      'ajuste_positivo',
      'ajuste_negativo',
    ]),
    quantidade: z.coerce.number().int().min(1, 'Mínimo 1'),
    tecnico_id: z.string().uuid('Selecione o técnico').optional().or(z.literal('')),
    serial: z.string().max(120).optional().or(z.literal('')),
    observacao: z.string().max(500).optional().or(z.literal('')),
  })
  .refine(
    (v) =>
      v.tipo === 'entrada' || (v.tecnico_id && v.tecnico_id.length > 0),
    { message: 'Técnico obrigatório para saída/devolução/perda/ajuste', path: ['tecnico_id'] },
  )

type FormValues = z.infer<typeof schema>

interface Props {
  onClose: () => void
  /** Pré-seleciona técnico (vindo da tela de saldo) */
  defaultTecnicoId?: string
}

export function DialogNovoMovimentoEstoque({ onClose, defaultTecnicoId }: Props) {
  const create = useCreateEstoqueMovimento()
  const { data: itens } = useEstoqueItens(true) // só ativos
  const { data: tecnicos } = useTecnicos({ ativo: true })

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      tipo: 'entrada',
      quantidade: 1,
      tecnico_id: defaultTecnicoId ?? '',
    },
  })

  const itemId = watch('item_id')
  const tipo = watch('tipo')
  const itemSelecionado = itens?.find((i) => i.id === itemId)
  const serializado = !!itemSelecionado?.serializado
  const tipoConfig = TIPOS.find((t) => t.value === tipo)

  async function onSubmit(values: FormValues) {
    try {
      await create.mutateAsync({
        item_id: values.item_id,
        tipo: values.tipo,
        quantidade: values.quantidade,
        tecnico_id: values.tecnico_id || null,
        serial: values.serial || null,
        observacao: values.observacao || null,
      })
      onClose()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Erro ao registrar movimento')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <h2 className="text-lg font-semibold">Novo movimento de estoque</h2>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label htmlFor="tipo">Tipo *</Label>
            <Select id="tipo" {...register('tipo')}>
              {TIPOS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.sinal} {t.label}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <Label htmlFor="item_id">Item *</Label>
            <Select id="item_id" {...register('item_id')} defaultValue="">
              <option value="" disabled>
                Selecione o item
              </option>
              {(itens ?? []).map((it) => (
                <option key={it.id} value={it.id}>
                  {it.nome} ({it.sku})
                </option>
              ))}
            </Select>
            {errors.item_id && (
              <p className="mt-1 text-xs text-destructive">{errors.item_id.message}</p>
            )}
            {itemSelecionado && (
              <p className="mt-1 text-xs text-muted-foreground">
                {itemSelecionado.serializado
                  ? 'Item serializado — quantidade obrigatoriamente 1 + serial obrigatório.'
                  : 'Item por quantidade.'}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="quantidade">Quantidade *</Label>
              <Input
                id="quantidade"
                type="number"
                min={1}
                step={1}
                disabled={serializado}
                {...register('quantidade', { valueAsNumber: true })}
              />
              {errors.quantidade && (
                <p className="mt-1 text-xs text-destructive">{errors.quantidade.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="serial">
                Serial {serializado ? '*' : '(opcional)'}
              </Label>
              <Input
                id="serial"
                placeholder={serializado ? 'Ex: ZTEGD1234567' : '—'}
                disabled={!serializado}
                {...register('serial')}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="tecnico_id">
              Técnico {tipoConfig?.sinal === '-' ? '*' : '(opcional se entrada)'}
            </Label>
            <Select id="tecnico_id" {...register('tecnico_id')}>
              <option value="">— Almoxarifado / sem técnico —</option>
              {(tecnicos?.items ?? []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nome}
                </option>
              ))}
            </Select>
            {errors.tecnico_id && (
              <p className="mt-1 text-xs text-destructive">{errors.tecnico_id.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="observacao">Observação</Label>
            <Textarea
              id="observacao"
              rows={2}
              placeholder="Ex: entregue para OS #1234"
              {...register('observacao')}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando…' : 'Registrar movimento'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
