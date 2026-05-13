'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useConfigKey, useSetConfig } from '@/lib/api/queries'

export function ConfigEditor() {
  const [key, setKey] = useState('')
  const [valueText, setValueText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const setConfig = useSetConfig()
  const cfg = useConfigKey(key)

  async function handleLoad() {
    setError(null)
    cfg.refetch().then((r) => {
      if (r.data) setValueText(JSON.stringify(r.data.value, null, 2))
      else setValueText('')
    })
  }

  async function handleSave() {
    setError(null)
    try {
      const value: unknown = JSON.parse(valueText)
      await setConfig.mutateAsync({ key, value })
    } catch {
      setError('JSON inválido')
    }
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Configurações (k/v)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Label htmlFor="key">Chave</Label>
            <Input
              id="key"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="planos, ack_text, …"
            />
          </div>
          <Button variant="outline" onClick={handleLoad} disabled={!key}>
            Carregar
          </Button>
        </div>
        <div>
          <Label htmlFor="value">Valor (JSON)</Label>
          <Textarea
            id="value"
            value={valueText}
            onChange={(e) => setValueText(e.target.value)}
            rows={12}
            className="font-mono text-xs"
            placeholder='{"exemplo": true}'
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {cfg.error && (
          <p className="text-sm text-muted-foreground">
            Chave não encontrada — salvar criará uma nova.
          </p>
        )}
        <Button onClick={handleSave} disabled={!key || setConfig.isPending}>
          {setConfig.isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </CardContent>
    </Card>
  )
}
