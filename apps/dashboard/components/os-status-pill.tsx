'use client'
import { CheckCircle2, Clock, PlayCircle, XCircle, HelpCircle } from 'lucide-react'
import { TONE_SOFT, type Tone } from '@/components/noc/primitives'
import { cn } from '@/lib/utils'

type OsStatus = 'pendente' | 'em_andamento' | 'concluida' | 'cancelada' | (string & {})

interface Spec {
  label: string
  icon: React.ComponentType<{ className?: string }>
  tone: Extract<Tone, 'info' | 'warning' | 'success' | 'destructive' | 'muted'>
}

const SPECS: Record<string, Spec> = {
  pendente: { label: 'Pendente', icon: Clock, tone: 'info' },
  em_andamento: { label: 'Em andamento', icon: PlayCircle, tone: 'warning' },
  concluida: { label: 'Concluída', icon: CheckCircle2, tone: 'success' },
  cancelada: { label: 'Cancelada', icon: XCircle, tone: 'destructive' },
}

/** Status da OS: sempre icone + texto (a cor so reforca). */
export function OsStatusPill({
  status,
  size = 'md',
  className,
}: {
  status: OsStatus
  size?: 'sm' | 'md'
  className?: string
}) {
  const spec = SPECS[status] ?? { label: status, icon: HelpCircle, tone: 'muted' as const }
  const Icon = spec.icon
  const sizing =
    size === 'sm' ? 'h-[22px] gap-1 px-2 text-xs' : 'h-7 gap-1.5 px-2.5 text-[13px]'
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center whitespace-nowrap rounded-md font-medium ring-1 ring-inset',
        TONE_SOFT[spec.tone],
        sizing,
        className,
      )}
    >
      <Icon aria-hidden className={cn('shrink-0', iconSize)} />
      {spec.label}
    </span>
  )
}
