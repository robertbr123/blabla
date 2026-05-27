'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useCreateEstoqueItem, useEstoqueCategorias } from '@/lib/api/queries'

const schema = z.object({
  sku: z
    .string()
    .min(1, 'Obrigatório')
    .max(40)
    .regex(/^[A-Za-z0-9-_]+$/, 'Use letras, números, hífen ou underline'),
  nome: z.string().min(1, 'Obrigatório').max(120),
  categoria: z.string().min(1, 'Selecione uma categoria'),
  unidade: z.enum(['UN', 'metro', 'CX', 'PC']),
  serializado: z.boolean(),
  ativo: z.boolean(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onClose: () => void
}

export function DialogNovoItemEstoque({ onClose }: Props) {
  const create = useCreateEstoqueItem()
  const { data: categorias } = useEstoqueCategorias(true)
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      sku: '',
      nome: '',
      categoria: '',
      unidade: 'UN',
      serializado: false,
      ativo: true,
    },
  })

  const serializado = watch('serializado')
  const ativo = watch('ativo')

  async function onSubmit(values: FormValues) {
    try {
      await create.mutateAsync(values)
      onClose()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Erro ao criar item')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <h2 className="text-lg font-semibold">Novo item de estoque</h2>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label htmlFor="sku">SKU *</Label>
            <Input
              id="sku"
              placeholder="Ex: ONU-XPON-ZTE"
              {...register('sku')}
              autoFocus
            />
            {errors.sku && (
              <p className="mt-1 text-xs text-destructive">{errors.sku.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="nome">Nome *</Label>
            <Input
              id="nome"
              placeholder="Ex: ONU XPON ZTE F660"
              {...register('nome')}
            />
            {errors.nome && (
              <p className="mt-1 text-xs text-destructive">{errors.nome.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="categoria">Categoria *</Label>
            <Select id="categoria" {...register('categoria')}>
              <option value="">Selecione…</option>
              {(categorias ?? []).map((c) => (
                <option key={c.id} value={c.slug}>
                  {c.nome}
                </option>
              ))}
            </Select>
            {errors.categoria && (
              <p className="mt-1 text-xs text-destructive">
                {errors.categoria.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="unidade">Unidade de medida *</Label>
            <Select id="unidade" {...register('unidade')}>
              <option value="UN">UN — unidade (ONU, roteador, conector)</option>
              <option value="metro">Metro — cabo DROP, fio</option>
              <option value="CX">CX — caixa</option>
              <option value="PC">PC — peça</option>
            </Select>
            <p className="mt-1 text-xs text-muted-foreground">
              Define como o técnico digita a quantidade no app. Quantidade é
              sempre inteira.
            </p>
          </div>

          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <p className="text-sm font-medium">Serializado?</p>
              <p className="text-xs text-muted-foreground">
                Marque pra ONU/roteador (tem serial único). Conector/cabo: deixe desligado.
              </p>
            </div>
            <Switch
              checked={serializado}
              onCheckedChange={(v) => setValue('serializado', v)}
            />
          </div>

          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <p className="text-sm font-medium">Ativo?</p>
              <p className="text-xs text-muted-foreground">
                Itens inativos não aparecem em movimentos novos.
              </p>
            </div>
            <Switch
              checked={ativo}
              onCheckedChange={(v) => setValue('ativo', v)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Criando…' : 'Criar item'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
