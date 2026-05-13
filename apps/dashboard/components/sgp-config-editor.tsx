'use client'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConfigKey, useSetConfig } from '@/lib/api/queries'

interface SgpValue {
  base_url: string
  token: string
  app: string
}

const INSTANCES: { key: string; title: string; envHint: string }[] = [
  {
    key: 'sgp.ondeline',
    title: 'SGP Ondeline (primary)',
    envHint: 'fallback: SGP_ONDELINE_BASE/TOKEN/APP no .env',
  },
  {
    key: 'sgp.linknetam',
    title: 'SGP LinkNetAM (secondary)',
    envHint: 'fallback: SGP_LINKNETAM_BASE/TOKEN/APP no .env',
  },
]

function SgpInstanceCard({ configKey, title, envHint }: { configKey: string; title: string; envHint: string }) {
  const cfg = useConfigKey(configKey)
  const setConfig = useSetConfig()

  const [baseUrl, setBaseUrl] = useState('')
  const [token, setToken] = useState('')
  const [app, setApp] = useState('')
  const [showToken, setShowToken] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (cfg.data?.value && typeof cfg.data.value === 'object') {
      const v = cfg.data.value as Partial<SgpValue>
      setBaseUrl(v.base_url ?? '')
      setToken(v.token ?? '')
      setApp(v.app ?? '')
    }
  }, [cfg.data])

  async function handleSave() {
    setStatus(null)
    setError(null)
    const value: SgpValue = { base_url: baseUrl.trim(), token: token.trim(), app: app.trim() }
    try {
      await setConfig.mutateAsync({ key: configKey, value })
      setStatus('Salvo. Workers vão usar na próxima task (sem reiniciar).')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao salvar')
    }
  }

  const notFound = cfg.error && (cfg.error as { status?: number }).status === 404
  const loading = cfg.isLoading && !notFound

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">{envHint}</p>
        {loading ? (
          <p className="text-xs text-muted-foreground">Carregando…</p>
        ) : (
          <>
            <div className="space-y-1.5">
              <Label htmlFor={`${configKey}-base`}>Base URL</Label>
              <Input
                id={`${configKey}-base`}
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://ondeline.sgp.tsmx.com.br"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`${configKey}-token`}>Token</Label>
              <div className="flex gap-2">
                <Input
                  id={`${configKey}-token`}
                  type={showToken ? 'text' : 'password'}
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="••••••••••••"
                  autoComplete="off"
                />
                <Button type="button" variant="outline" onClick={() => setShowToken((v) => !v)}>
                  {showToken ? 'Ocultar' : 'Mostrar'}
                </Button>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`${configKey}-app`}>App</Label>
              <Input
                id={`${configKey}-app`}
                value={app}
                onChange={(e) => setApp(e.target.value)}
                placeholder="mikrotik"
              />
            </div>
            {status && <p className="text-xs text-emerald-600">{status}</p>}
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex justify-end">
              <Button onClick={handleSave} disabled={setConfig.isPending}>
                {setConfig.isPending ? 'Salvando…' : 'Salvar'}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export function SgpConfigEditor() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">SGP (provedores)</h2>
        <p className="text-sm text-muted-foreground">
          Credenciais por instância. Salvas em <code>config</code> (k/v); ficam por cima dos env vars.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {INSTANCES.map((i) => (
          <SgpInstanceCard key={i.key} configKey={i.key} title={i.title} envHint={i.envHint} />
        ))}
      </div>
    </div>
  )
}
