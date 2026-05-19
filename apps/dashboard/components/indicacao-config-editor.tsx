'use client'
import { useEffect, useState } from 'react'
import { Gift, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConfigKey, useSetConfig } from '@/lib/api/queries'

const KEY = 'indicacao.whatsapp_alvo'

function readString(cfg: { data?: { value: unknown } | undefined }): string {
  const v = cfg.data?.value
  if (typeof v === 'string') return v
  if (v && typeof v === 'object' && 'value' in v) {
    const inner = (v as { value: unknown }).value
    if (typeof inner === 'string') return inner
  }
  return ''
}

function onlyDigits(s: string): string {
  return s.replace(/\D/g, '')
}

function format(s: string): string {
  // Mostra com máscara amigável: +DDDDDDDDDDDDD (sem +)
  const d = onlyDigits(s)
  if (d.length < 4) return d
  if (d.length <= 4) return `+${d}`
  // BR: 55 47 99999 8888 → "+55 47 99999-8888"
  if (d.startsWith('55') && d.length >= 12) {
    const ddi = d.slice(0, 2)
    const ddd = d.slice(2, 4)
    const meio = d.slice(4, d.length - 4)
    const fim = d.slice(-4)
    return `+${ddi} ${ddd} ${meio}-${fim}`
  }
  return `+${d}`
}

export function IndicacaoConfigEditor() {
  const cfg = useConfigKey(KEY)
  const setConfig = useSetConfig()

  const [valor, setValor] = useState('')
  const [savedMsg, setSavedMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!cfg.isLoading) setValor(readString(cfg))
  }, [cfg.isLoading, cfg.data])

  const digits = onlyDigits(valor)
  const valido = digits.length >= 12 && digits.length <= 15

  async function handleSave() {
    setError(null)
    setSavedMsg(null)
    if (!valido) {
      setError('Número inválido. Use formato internacional só com dígitos. Ex: 5547999998888')
      return
    }
    try {
      await setConfig.mutateAsync({ key: KEY, value: digits })
      setSavedMsg('Número salvo.')
      cfg.refetch()
      setTimeout(() => setSavedMsg(null), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao salvar')
    }
  }

  const linkExemplo = digits
    ? `https://wa.me/${digits}?text=Indicado%20por%20XXXXXX`
    : ''

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Gift className="h-4 w-4" /> Indicação "Indicou, ganhou"
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          Número de WhatsApp da empresa que recebe os contatos indicados.
          Use formato internacional só com dígitos (ex: <code className="font-mono">5547999998888</code> = +55 47 99999-8888).
        </p>

        <div>
          <Label htmlFor="indicacao-numero">Número (E.164 sem +)</Label>
          <Input
            id="indicacao-numero"
            type="text"
            inputMode="numeric"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder="5547999998888"
          />
          {digits && (
            <p className="mt-1 text-xs text-muted-foreground">
              Será salvo como: <code className="font-mono">{digits}</code>
              {' · '}Formato leitura: {format(digits)}
            </p>
          )}
        </div>

        {digits && valido && (
          <div className="rounded-md border bg-muted/30 p-3 text-xs">
            <p className="font-medium mb-1">Link que o bot vai gerar:</p>
            <code className="break-all font-mono text-[11px]">{linkExemplo}</code>
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}
        {savedMsg && <p className="text-sm text-green-700">{savedMsg}</p>}

        <Button
          onClick={handleSave}
          disabled={setConfig.isPending || !valido}
          className="gap-2"
        >
          <Save className="h-4 w-4" />
          {setConfig.isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </CardContent>
    </Card>
  )
}
