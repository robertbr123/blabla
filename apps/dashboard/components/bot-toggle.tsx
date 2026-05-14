'use client'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useConfigKey, useSetConfig } from '@/lib/api/queries'

const CONFIG_KEY = 'bot.ativo'

export function BotToggle() {
  const cfg = useConfigKey(CONFIG_KEY)
  const setConfig = useSetConfig()
  const [checked, setChecked] = useState(true)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (cfg.data !== undefined) {
      // Regra: None (chave ausente/404) ou true → ativo. Só false → desativado.
      setChecked(cfg.data.value !== false)
    }
  }, [cfg.data])

  // Chave ausente no banco → 404 → bot está ativo (default implícito)
  const notFound = cfg.error && (cfg.error as { status?: number }).status === 404
  const loading = cfg.isLoading && !notFound

  async function handleToggle(value: boolean) {
    setChecked(value)
    setStatus(null)
    setError(null)
    try {
      await setConfig.mutateAsync({ key: CONFIG_KEY, value })
      setStatus(value ? 'Bot ativado.' : 'Bot desativado.')
    } catch (e) {
      setChecked(!value)
      setError(e instanceof Error ? e.message : 'Falha ao salvar')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Bot WhatsApp</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <p className="text-xs text-muted-foreground">Carregando…</p>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="bot-toggle">Bot ativo</Label>
                <p className="text-xs text-muted-foreground">
                  Quando desativado, mensagens são salvas mas o bot não responde automaticamente.
                </p>
              </div>
              <Switch
                id="bot-toggle"
                checked={checked}
                onCheckedChange={handleToggle}
                disabled={setConfig.isPending}
              />
            </div>
            {status && <p className="text-xs text-emerald-600">{status}</p>}
            {error && <p className="text-xs text-destructive">{error}</p>}
          </>
        )}
      </CardContent>
    </Card>
  )
}
