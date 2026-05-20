import { cn } from '@/lib/utils'

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'rounded-md border bg-card p-12 text-center',
        className,
      )}
    >
      <Icon className="mx-auto h-10 w-10 text-muted-foreground/50" />
      <h3 className="mt-3 text-sm font-medium">{title}</h3>
      {description && (
        <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
