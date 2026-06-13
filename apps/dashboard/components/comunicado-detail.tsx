'use client'
import { useState } from 'react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { useCampanha, useTestCampanha } from '@/lib/api/queries'

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-card p-4">
      <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  )
}

export function ComunicadoDetail({ id }: { id: string }) {
  const { data: c, isLoading } = useCampanha(id)
  const testSend = useTestCampanha(id)
  const [testNum, setTestNum] = useState('')

  if (isLoading || !c) return <p className="text-sm text-muted-foreground">Carregando…</p>

  const counts = c.status_counts ?? {}

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{c.titulo}</h1>
          <p className="mt-1 text-sm text-muted-foreground font-mono">{c.template_name}</p>
        </div>
        <Badge variant="outline">{c.status}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Metric label="Total" value={c.total_destinatarios} />
        <Metric label="Enviadas" value={c.enviadas} />
        <Metric label="Entregues" value={counts.entregue ?? 0} />
        <Metric label="Lidas" value={counts.lida ?? 0} />
        <Metric label="Falhas" value={c.falhas} />
      </div>

      <div className="rounded-md border p-4 space-y-3 max-w-md">
        <p className="text-sm font-medium">Enviar teste</p>
        <div className="flex gap-3">
          <Input placeholder="5592999999999" value={testNum}
                 onChange={(e) => setTestNum(e.target.value)} />
          <button
            type="button"
            onClick={() =>
              testSend.mutate(testNum, {
                onSuccess: () => toast.success('Teste enviado'),
                onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro'),
              })
            }
            className="rounded-md border px-3 py-2 text-sm hover:bg-accent whitespace-nowrap"
          >
            Enviar
          </button>
        </div>
      </div>
    </div>
  )
}
