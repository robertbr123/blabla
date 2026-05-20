import { CheckCircle2, Clock, PlayCircle, XCircle, HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

type OsStatus = 'pendente' | 'em_andamento' | 'concluida' | 'cancelada' | (string & {})

interface Spec {
  label: string
  icon: React.ComponentType<{ className?: string }>
  tone: 'info' | 'warning' | 'success' | 'destructive' | 'muted'
}

const SPECS: Record<string, Spec> = {
  pendente: { label: 'Pendente', icon: Clock, tone: 'info' },
  em_andamento: { label: 'Em andamento', icon: PlayCircle, tone: 'warning' },
  concluida: { label: 'Concluída', icon: CheckCircle2, tone: 'success' },
  cancelada: { label: 'Cancelada', icon: XCircle, tone: 'destructive' },
}

const TONE_CLASSES: Record<Spec['tone'], string> = {
  info: 'bg-info/[0.12] text-info ring-info/30',
  warning: 'bg-warning/[0.15] text-warning ring-warning/30',
  success: 'bg-success/[0.12] text-success ring-success/30',
  destructive: 'bg-destructive/[0.12] text-destructive ring-destructive/30',
  muted: 'bg-muted text-muted-foreground ring-border',
}

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
    size === 'sm' ? 'px-2 py-0.5 text-xs gap-1' : 'px-2.5 py-1 text-sm gap-1.5'
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium ring-1 ring-inset',
        TONE_CLASSES[spec.tone],
        sizing,
        className,
      )}
    >
      <Icon className={iconSize} />
      {spec.label}
    </span>
  )
}
