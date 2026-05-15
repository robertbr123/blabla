'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useCreateOs, useSgpLookup, useTecnicos } from '@/lib/api/queries'
import type { SgpClienteOut } from '@/lib/api/types'

const schema = z.object({
  tecnico_id: z.string().uuid('Selecione o técnico responsável'),
  problema: z.string().min(1, 'Obrigatório').max(2000),
  endereco: z.string().min(1, 'Obrigatório').max(500),
  agendamento_at: z.string().optional().nullable(),
  pppoe_login: z.string().max(120).optional().nullable(),
  pppoe_senha: z.string().max(120).optional().nullable(),
})

type FormValues = z.infer<typeof schema>

export function FormOsCreate() {
  const router = useRouter()
  const createOs = useCreateOs()
  const sgpLookup = useSgpLookup()
  const { data: tecnicos } = useTecnicos({ ativo: true })

  const [cpfInput, setCpfInput] = useState('')
  const [sgpCliente, setSgpCliente] = useState<SgpClienteOut | null>(null)
  const [sgpNotFound, setSgpNotFound] = useState(false)
  const [clienteId, setClienteId] = useState<string | null>(null)
  const [showSenha, setShowSenha] = useState(false)

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function handleSgpBuscar() {
    if (!cpfInput.trim()) return
    setSgpNotFound(false)
    setSgpCliente(null)
    setClienteId(null)
    try {
      const cli = await sgpLookup.mutateAsync(cpfInput.trim())
      setSgpCliente(cli)
      if (cli.cliente_id) setClienteId(cli.cliente_id)
      if (cli.endereco) setValue('endereco', cli.endereco)
      if (cli.pppoe_login) setValue('pppoe_login', cli.pppoe_login)
      if (cli.pppoe_senha) setValue('pppoe_senha', cli.pppoe_senha)
    } catch {
      setSgpNotFound(true)
    }
  }

  function handleSgpLimpar() {
    setSgpCliente(null)
    setSgpNotFound(false)
    setClienteId(null)
    setCpfInput('')
    setValue('endereco', '')
    setValue('pppoe_login', '')
    setValue('pppoe_senha', '')
  }

  async function onSubmit(values: FormValues) {
    const created = await createOs.mutateAsync({
      ...(clienteId ? { cliente_id: clienteId } : {}),
      tecnico_id: values.tecnico_id,
      problema: values.problema,
      endereco: values.endereco,
      agendamento_at: values.agendamento_at || null,
      pppoe_login: values.pppoe_login || null,
      pppoe_senha: values.pppoe_senha || null,
    })
    router.push(`/os/${created.id}`)
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Nova OS</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          {/* Bloco SGP */}
          <div>
            <Label htmlFor="cpf_cnpj">
              Cliente — busca no SGP <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            {sgpCliente ? (
              <div className="mt-1 rounded-md border border-green-500 bg-green-50 px-4 py-3 text-sm dark:bg-green-950">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <p className="font-semibold text-green-800 dark:text-green-200">{sgpCliente.nome}</p>
                    {sgpCliente.plano && (
                      <p className="text-green-700 dark:text-green-300">
                        Plano: {sgpCliente.plano}
                      </p>
                    )}
                    {sgpCliente.status_contrato && (
                      <p className="text-green-700 dark:text-green-300">
                        Contrato: {sgpCliente.status_contrato}
                      </p>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-muted-foreground shrink-0"
                    onClick={handleSgpLimpar}
                  >
                    Limpar
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-1 flex gap-2">
                <Input
                  id="cpf_cnpj"
                  placeholder="CPF ou CNPJ"
                  value={cpfInput}
                  onChange={(e) => { setCpfInput(e.target.value); setSgpNotFound(false) }}
                  autoComplete="off"
                  className="flex-1"
                />
                <Button
                  type="button"
                  disabled={sgpLookup.isPending || !cpfInput.trim()}
                  onClick={handleSgpBuscar}
                >
                  {sgpLookup.isPending ? 'Buscando…' : 'Buscar no SGP'}
                </Button>
              </div>
            )}
            {sgpNotFound && (
              <p className="mt-1 text-xs text-destructive">
                Cliente não encontrado no SGP — preencha os dados manualmente.
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="tecnico_id">Técnico responsável *</Label>
            <Select id="tecnico_id" {...register('tecnico_id')} defaultValue="">
              <option value="" disabled>Selecione o técnico responsável</option>
              {tecnicos?.items.map((t) => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </Select>
            {errors.tecnico_id && (
              <p className="mt-1 text-xs text-destructive">{errors.tecnico_id.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="problema">Problema *</Label>
            <Textarea id="problema" {...register('problema')} />
            {errors.problema && (
              <p className="mt-1 text-xs text-destructive">{errors.problema.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="endereco">Endereço *</Label>
            <Input id="endereco" {...register('endereco')} />
            {errors.endereco && (
              <p className="mt-1 text-xs text-destructive">{errors.endereco.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="agendamento_at">Agendamento (opcional)</Label>
            <Input id="agendamento_at" type="datetime-local" {...register('agendamento_at')} />
          </div>

          <div>
            <Label htmlFor="pppoe_login">PPPoE Login</Label>
            <Input id="pppoe_login" {...register('pppoe_login')} autoComplete="off" />
            {errors.pppoe_login && (
              <p className="mt-1 text-xs text-destructive">{errors.pppoe_login.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="pppoe_senha">PPPoE Senha</Label>
            <div className="flex gap-2">
              <Input
                id="pppoe_senha"
                type={showSenha ? 'text' : 'password'}
                {...register('pppoe_senha')}
                autoComplete="new-password"
                className="flex-1"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="shrink-0"
                onClick={() => setShowSenha((v) => !v)}
                aria-label={showSenha ? 'Ocultar senha' : 'Mostrar senha'}
              >
                {showSenha ? 'Ocultar' : '👁 Mostrar'}
              </Button>
            </div>
            {errors.pppoe_senha && (
              <p className="mt-1 text-xs text-destructive">{errors.pppoe_senha.message}</p>
            )}
          </div>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Criando…' : 'Criar OS'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
