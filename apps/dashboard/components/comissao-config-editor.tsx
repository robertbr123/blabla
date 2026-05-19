'use client'
import { useEffect, useState } from 'react'
import { Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConfigKey, useSetConfig } from '@/lib/api/queries'

const KEYS = {
  valor_por_os: 'comissao.valor_por_os',
  bonus_csat_5: 'comissao.bonus_csat_5',
  bonus_csat_4: 'comissao.bonus_csat_4',
} as const

function readNumeric(cfg: { data?: { value: unknown } | undefined }): number {
  const v = cfg.data?.value
  if (typeof v === 'number') return v
  if (typeof v === 'string') {
    const n = parseFloat(v)
    return isFinite(n) ? n : 0
  }
  if (v && typeof v === 'object' && 'value' in v) {
    const inner = (v as { value: unknown }).value
    if (typeof inner === 'number') return inner
    if (typeof inner === 'string') {
      const n = parseFloat(inner)
      return isFinite(n) ? n : 0
    }
  }
  return 0
}

interface Props {
  onSaved?: () => void
}

export function ComissaoConfigEditor({ onSaved }: Props) {
  const valorCfg = useConfigKey(KEYS.valor_por_os)
  const bonus5Cfg = useConfigKey(KEYS.bonus_csat_5)
  const bonus4Cfg = useConfigKey(KEYS.bonus_csat_4)
  const setConfig = useSetConfig()

  const [valor, setValor] = useState('')
  const [bonus5, setBonus5] = useState('')
  const [bonus4, setBonus4] = useState('')
  const [savedMsg, setSavedMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Sincroniza quando os dados chegam
  useEffect(() => {
    if (!valorCfg.isLoading) setValor(String(readNumeric(valorCfg)))
  }, [valorCfg.isLoading, valorCfg.data])
  useEffect(() => {
    if (!bonus5Cfg.isLoading) setBonus5(String(readNumeric(bonus5Cfg)))
  }, [bonus5Cfg.isLoading, bonus5Cfg.data])
  useEffect(() => {
    if (!bonus4Cfg.isLoading) setBonus4(String(readNumeric(bonus4Cfg)))
  }, [bonus4Cfg.isLoading, bonus4Cfg.data])

  function parse(s: string): number | null {
    const n = parseFloat(s.replace(',', '.'))
    if (!isFinite(n) || n < 0) return null
    return Math.round(n * 100) / 100
  }

  async function handleSave() {
    setError(null)
    setSavedMsg(null)

    const v = parse(valor)
    const b5 = parse(bonus5)
    const b4 = parse(bonus4)
    if (v === null || b5 === null || b4 === null) {
      setError('Use apenas números positivos. Decimais aceitos (ex: 30 ou 30,50).')
      return
    }

    try {
      await Promise.all([
        setConfig.mutateAsync({ key: KEYS.valor_por_os, value: v }),
        setConfig.mutateAsync({ key: KEYS.bonus_csat_5, value: b5 }),
        setConfig.mutateAsync({ key: KEYS.bonus_csat_4, value: b4 }),
      ])
      setSavedMsg('Valores salvos. Recarregando relatório…')
      // Refetch dos cfgs
      valorCfg.refetch()
      bonus5Cfg.refetch()
      bonus4Cfg.refetch()
      onSaved?.()
      setTimeout(() => setSavedMsg(null), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao salvar')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Configurar comissão</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          Fórmula: <code>(OS concluídas × valor por OS) + (CSAT 5 × bônus 5) + (CSAT 4 × bônus 4)</code>.
          Valores em reais. Decimais aceitos (use vírgula ou ponto).
        </p>

        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <Label htmlFor="valor_por_os">Valor por OS (R$)</Label>
            <Input
              id="valor_por_os"
              type="text"
              inputMode="decimal"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              placeholder="0"
            />
          </div>
          <div>
            <Label htmlFor="bonus_5">Bônus CSAT 5 (R$)</Label>
            <Input
              id="bonus_5"
              type="text"
              inputMode="decimal"
              value={bonus5}
              onChange={(e) => setBonus5(e.target.value)}
              placeholder="0"
            />
            <p className="mt-1 text-xs text-muted-foreground">Extra por OS com avaliação 5.</p>
          </div>
          <div>
            <Label htmlFor="bonus_4">Bônus CSAT 4 (R$)</Label>
            <Input
              id="bonus_4"
              type="text"
              inputMode="decimal"
              value={bonus4}
              onChange={(e) => setBonus4(e.target.value)}
              placeholder="0"
            />
            <p className="mt-1 text-xs text-muted-foreground">Extra por OS com avaliação 4.</p>
          </div>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}
        {savedMsg && <p className="text-sm text-green-700">{savedMsg}</p>}

        <Button onClick={handleSave} disabled={setConfig.isPending} className="gap-2">
          <Save className="h-4 w-4" />
          {setConfig.isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </CardContent>
    </Card>
  )
}
