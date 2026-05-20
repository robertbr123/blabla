'use client'
import { useEffect, useState } from 'react'
import { AlertCircle, Clock } from 'lucide-react'

function elapsed(since: string): string {
  const ms = Date.now() - new Date(since).getTime()
  const m = Math.floor(ms / 60000)
  const s = Math.floor((ms % 60000) / 1000)
  return `${m}m ${s.toString().padStart(2, '0')}s`
}

export function ConversaSlaTimer({
  transferredAt,
  slaMinutes,
}: {
  transferredAt: string
  slaMinutes: number
}) {
  const [display, setDisplay] = useState(elapsed(transferredAt))
  const [exceeded, setExceeded] = useState(false)

  useEffect(() => {
    const tick = () => {
      setDisplay(elapsed(transferredAt))
      const ms = Date.now() - new Date(transferredAt).getTime()
      setExceeded(ms > slaMinutes * 60 * 1000)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [transferredAt, slaMinutes])

  const tone = exceeded
    ? 'bg-destructive/[0.12] text-destructive ring-destructive/30'
    : 'bg-warning/[0.15] text-warning ring-warning/30'
  const Icon = exceeded ? AlertCircle : Clock

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${tone}`}
      title={exceeded ? `SLA de ${slaMinutes}min excedido` : `SLA ${slaMinutes}min`}
      role={exceeded ? 'alert' : undefined}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span style={{ fontVariantNumeric: 'tabular-nums' }}>{display}</span>
    </div>
  )
}
