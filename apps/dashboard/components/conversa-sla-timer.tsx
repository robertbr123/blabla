'use client'
import { useEffect, useState } from 'react'

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

  return (
    <div
      className={`rounded-md border px-3 py-2 text-center text-sm font-mono ${
        exceeded
          ? 'border-destructive bg-destructive/10 text-destructive'
          : 'border-yellow-400 bg-yellow-50 dark:bg-yellow-950/20 text-yellow-700 dark:text-yellow-400'
      }`}
    >
      <p className="text-xs opacity-70">Aguardando há</p>
      <p className="font-semibold">{display}</p>
      {exceeded && <p className="text-xs">⚠️ SLA excedido</p>}
    </div>
  )
}
